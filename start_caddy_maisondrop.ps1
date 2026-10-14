# Je définis les chemins utilisés pour lancer Caddy avec la configuration de MaisonDrop.
$DossierProjet = "C:\PROJETSDEV\MaisonDrop"
$FichierCaddy = "C:\Users\Sonia\AppData\Local\Microsoft\WinGet\Packages\CaddyServer.Caddy_Microsoft.Winget.Source_8wekyb3d8bbwe\caddy.exe"
$FichierConfig = Join-Path $DossierProjet "Caddyfile"

# Je vérifie que Caddy n'est pas déjà lancé pour éviter de démarrer une deuxième instance.
$CaddyActif = Get-CimInstance Win32_Process -Filter "Name = 'caddy.exe'" |
    Where-Object {
        $_.ExecutablePath -eq $FichierCaddy
    }

if ($CaddyActif) {
    exit 0
}

# Je vérifie que les fichiers nécessaires sont présents avant de lancer le serveur.
if (-not (Test-Path $FichierCaddy)) {
    throw "Le fichier caddy.exe est introuvable : $FichierCaddy"
}

if (-not (Test-Path $FichierConfig)) {
    throw "Le fichier Caddyfile est introuvable : $FichierConfig"
}

# Je me place dans le dossier du projet pour que Caddy utilise les bons chemins.
Set-Location $DossierProjet

# Je lance Caddy en gardant le processus actif pour que la tâche Windows le supervise.
& $FichierCaddy run --config $FichierConfig
