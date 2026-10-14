from pathlib import Path
from functools import wraps
import hmac
import os
import secrets
import socket
import time

import qrcode
from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request,
    session, url_for, send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
CONFIG_FILE = ROOT / "pin.txt"
PIN_HASH_FILE = ROOT / "pin.hash"
SECRET_FILE = ROOT / "secret.key"
SESSION_VERSION_FILE = ROOT / "session_version.txt"

UPLOAD_DIR.mkdir(exist_ok=True)

# Je garde une durée maximale de session, même si j'utilise MaisonDrop régulièrement.
MAX_SESSION_SECONDS = 8 * 60 * 60

# Je garde une limite de 20 minutes sans activité.
IDLE_TIMEOUT_SECONDS = 20 * 60

# Après 5 erreurs, je bloque l'adresse IP pendant 5 minutes.
# Cette limite est en mémoire et repart donc de zéro au redémarrage du serveur.
failed_attempts = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60


def create_pin_hash():
    """Crée le hash du PIN ou migre l'ancien fichier si nécessaire."""
    pin_was_generated = False

    if PIN_HASH_FILE.exists():
        pin_hash = PIN_HASH_FILE.read_text(encoding="utf-8").strip()
        if not pin_hash.startswith("pbkdf2:sha256:"):
            raise RuntimeError(
                "Le hash du PIN est invalide. Vérifie le fichier pin.hash."
            )

        # Si un ancien fichier en clair traîne encore, je le supprime seulement
        # après avoir vérifié que le hash existant est utilisable.
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

        return pin_hash, None

    if CONFIG_FILE.exists():
        initial_pin = CONFIG_FILE.read_text(encoding="utf-8").strip()
        if not initial_pin:
            raise RuntimeError(
                "Le fichier pin.txt est vide. Ajoute le PIN actuel avant de relancer MaisonDrop."
            )
    else:
        # Au premier lancement, je crée un PIN à 6 chiffres et je l'affiche une seule fois.
        initial_pin = f"{secrets.randbelow(900000) + 100000}"
        pin_was_generated = True

    pin_hash = generate_password_hash(
        initial_pin,
        method="pbkdf2:sha256",
        salt_length=16,
    )

    # J'écris d'abord le hash dans un fichier temporaire pour éviter un fichier incomplet.
    temp_file = PIN_HASH_FILE.with_suffix(".tmp")
    temp_file.write_text(pin_hash + "\n", encoding="utf-8")
    os.replace(temp_file, PIN_HASH_FILE)

    # Une fois le hash enregistré, je retire l'ancien PIN en clair.
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()

    return pin_hash, initial_pin if pin_was_generated else None


PIN_HASH, FIRST_PIN = create_pin_hash()

# La clé de session reste stable après redémarrage. Je ne dois pas supprimer ce fichier.
if not SECRET_FILE.exists():
    SECRET_FILE.write_text(secrets.token_hex(32), encoding="ascii")
    try:
        SECRET_FILE.chmod(0o600)
    except OSError:
        # Les permissions POSIX ne sont pas disponibles sur toutes les versions de Windows.
        pass

SECRET_KEY = SECRET_FILE.read_text(encoding="ascii").strip()
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Le fichier secret.key est invalide. Arrête MaisonDrop et restaure sa sauvegarde."
    )

# Je crée une version de session qui me permet de révoquer toutes les sessions d'un coup.
if not SESSION_VERSION_FILE.exists():
    SESSION_VERSION_FILE.write_text("1\n", encoding="ascii")


def get_session_version():
    try:
        return int(SESSION_VERSION_FILE.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as exc:
        # Si le fichier est illisible, je préfère arrêter plutôt que d'accepter une session sans contrôle.
        raise RuntimeError(
            "Le fichier session_version.txt est absent ou invalide."
        ) from exc


def revoke_all_sessions():
    """Invalide les sessions existantes de MaisonDrop."""
    version = get_session_version() + 1
    temp_file = SESSION_VERSION_FILE.with_suffix(".tmp")
    temp_file.write_text(str(version) + "\n", encoding="ascii")
    os.replace(temp_file, SESSION_VERSION_FILE)


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    MAX_CONTENT_LENGTH=1024 * 1024 * 1024,  # 1 Gio par requête
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # J'utilise HTTP sur mon réseau local.
    PERMANENT_SESSION_LIFETIME=20 * 60,  # 20 minutes pour le cookie permanent.
)


def is_ajax_upload():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_session_and_csrf():
    # Je vérifie la version globale pour pouvoir déconnecter toutes les sessions.
    if session.get("authenticated"):
        current_version = get_session_version()

        if session.get("session_version") != current_version:
            session.clear()

            if request.method == "POST" and is_ajax_upload():
                return jsonify(
                    ok=False,
                    error="Session révoquée. Reconnecte-toi avec le PIN.",
                ), 401

            if request.endpoint not in ("login", "static"):
                flash("Session révoquée. Reconnecte-toi avec le PIN.", "error")
                return redirect(url_for("login"))

    # Je vérifie l'inactivité et la durée totale de la session.
    if session.get("authenticated"):
        now = time.time()
        login_time = session.get("login_time", now)
        last_activity = session.get("last_activity", now)

        if now - login_time > MAX_SESSION_SECONDS:
            session.clear()

            if request.method == "POST" and is_ajax_upload():
                return jsonify(
                    ok=False,
                    error="Durée maximale de session atteinte. Reconnecte-toi.",
                ), 401

            if request.endpoint not in ("login", "static"):
                flash("Durée maximale de session atteinte. Reconnecte-toi.", "error")
                return redirect(url_for("login"))

        elif now - last_activity > IDLE_TIMEOUT_SECONDS:
            session.clear()

            if request.method == "POST" and is_ajax_upload():
                return jsonify(
                    ok=False,
                    error="Session expirée. Reconnecte-toi avec le PIN.",
                ), 401

            if request.endpoint not in ("login", "static"):
                flash("Session expirée pour ta sécurité. Saisis à nouveau le PIN.", "error")
                return redirect(url_for("login"))
        else:
            session["last_activity"] = now
            session.permanent = True

    # Je protège tous les formulaires POST avec un jeton CSRF.
    if request.method == "POST":
        expected = session.get("csrf_token", "")
        supplied = (
            request.headers.get("X-CSRF-Token", "")
            or request.form.get("csrf_token", "")
        )

        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            if is_ajax_upload():
                return jsonify(
                    ok=False,
                    error="Vérification de sécurité échouée. Recharge la page et réessaie.",
                ), 400

            abort(400, description="Vérification de sécurité échouée. Recharge la page puis réessaie.")


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'"
    )
    return response


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            if is_ajax_upload():
                return jsonify(
                    ok=False,
                    error="Session expirée. Recharge la page et reconnecte-toi.",
                ), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def unique_destination(filename):
    safe = secure_filename(filename) or "fichier_sans_nom"
    stem, suffix = Path(safe).stem, Path(safe).suffix
    dest = UPLOAD_DIR / safe
    n = 1

    while dest.exists():
        dest = UPLOAD_DIR / f"{stem}_{n}{suffix}"
        n += 1

    return dest


@app.get("/")
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    files = sorted(
        (p for p in UPLOAD_DIR.iterdir() if p.is_file() and p.name != ".keep"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return render_template("index.html", files=files)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        now = time.time()
        state = failed_attempts.get(ip, {"count": 0, "until": 0})

        if state["until"] > now:
            flash("Trop de tentatives. Réessaie dans quelques minutes.", "error")
            return render_template("login.html"), 429

        submitted_pin = request.form.get("pin", "")

        if check_password_hash(PIN_HASH, submitted_pin):
            failed_attempts.pop(ip, None)
            session.clear()
            session["authenticated"] = True
            session["login_time"] = now
            session["last_activity"] = now
            session["session_version"] = get_session_version()
            session["csrf_token"] = secrets.token_urlsafe(32)
            session.permanent = True
            return redirect(url_for("index"))

        state["count"] += 1
        if state["count"] >= MAX_FAILED_ATTEMPTS:
            state = {"count": 0, "until": now + LOCKOUT_SECONDS}

        failed_attempts[ip] = state
        flash("Code incorrect.", "error")

    return render_template("login.html")


@app.post("/upload")
@require_login
def upload():
    items = request.files.getlist("files")

    if not items or all(not f.filename for f in items):
        msg = "Choisis au moins un fichier."
        if is_ajax_upload():
            return jsonify(ok=False, error=msg), 400
        flash(msg, "error")
        return redirect(url_for("index"))

    saved = []

    try:
        for item in items:
            if item and item.filename:
                dest = unique_destination(item.filename)
                item.save(dest)
                saved.append(dest.name)
    except Exception:
        # Je garde les détails dans les logs, mais je n'affiche pas d'informations internes au navigateur.
        app.logger.exception("Erreur pendant l’enregistrement")
        if is_ajax_upload():
            return jsonify(
                ok=False,
                error="Le PC n’a pas pu enregistrer le fichier. Vérifie l’espace disque et réessaie.",
            ), 500
        raise

    msg = f"{len(saved)} fichier(s) reçu(s) et enregistré(s) sur le PC."
    if is_ajax_upload():
        return jsonify(ok=True, message=msg, count=len(saved), files=saved)

    flash(msg, "success")
    return redirect(url_for("index"))


@app.get("/download/<path:filename>")
@require_login
def download(filename):
    return send_from_directory(
        UPLOAD_DIR,
        filename,
        as_attachment=True,
        conditional=True,
    )


@app.post("/logout")
@require_login
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.post("/revoke-sessions")
@require_login
def revoke_sessions():
    # Je change la version globale, ce qui invalide les autres sessions encore ouvertes.
    revoke_all_sessions()
    session.clear()
    flash("Toutes les sessions ont été révoquées.", "success")
    return redirect(url_for("login"))


@app.errorhandler(400)
def bad_request(error):
    return str(error.description or "Requête incorrecte."), 400


@app.errorhandler(413)
def too_large(_error):
    msg = "Envoi trop volumineux : la limite est de 1 Gio par requête."
    if is_ajax_upload():
        return jsonify(ok=False, error=msg), 413
    return msg, 413


def local_ip_for_lan():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        probe.connect(("192.0.2.1", 80))
        ip = probe.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        probe.close()

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except OSError:
        pass

    return None


if __name__ == "__main__":
    print("\nMaisonDrop démarre.")

    if FIRST_PIN is not None:
        print("PIN initial (note-le maintenant) :", FIRST_PIN)
        print("Ce PIN ne sera pas réaffiché au prochain démarrage.")

    ip = local_ip_for_lan()

    if ip:
        address = f"http://{ip}:8000"
        print("Adresse locale :", address)
        qr_path = ROOT / "maisonDrop_qr.png"
        qrcode.make(address).save(qr_path)
        print("QR code créé :", qr_path)

        try:
            if hasattr(os, "startfile"):
                os.startfile(str(qr_path))
            else:
                print("Ouvre manuellement le QR code :", qr_path)
        except OSError:
            print("Ouvre manuellement le QR code :", qr_path)
    else:
        print("Impossible de détecter l’adresse IP locale. Vérifie le réseau.")

    print("Scanne le QR code avec l’iPhone. Garde cette fenêtre ouverte. Arrêt : Ctrl+C\n")
    app.run(host="0.0.0.0", port=8000, debug=False)
