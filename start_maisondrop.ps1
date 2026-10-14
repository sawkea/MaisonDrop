# Je définis les chemins de mon projet MaisonDrop.
$ProjectPath = "C:\PROJETSDEV\MaisonDrop"
$PythonPath = "$ProjectPath\.venv\Scripts\python.exe"

# Je dois mettre ici le nom de mon fichier Python principal.
$AppPath = "$ProjectPath\app.py"

# Je crée un dossier pour conserver les journaux.
$LogPath = "$ProjectPath\logs"
New-Item -ItemType Directory -Force -Path $LogPath | Out-Null

# Je crée un journal pour chaque tentative de démarrage.
$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$StdoutLog = "$LogPath\stdout_$Date.log"
$StderrLog = "$LogPath\stderr_$Date.log"
$StartLog = "$LogPath\demarrage_$Date.log"

try {
    # Je vérifie que les fichiers nécessaires existent.
    if (!(Test-Path $PythonPath)) {
        throw "Python introuvable : $PythonPath"
    }

    if (!(Test-Path $AppPath)) {
        throw "Fichier principal introuvable : $AppPath"
    }

    # Je me place dans le dossier du projet.
    Set-Location $ProjectPath

    # Je note le début du lancement.
    "[$(Get-Date)] Je lance MaisonDrop." |
        Set-Content -Path $StartLog

    # Je démarre Python en arrière-plan et je récupère les erreurs.
    $Process = Start-Process `
        -FilePath $PythonPath `
        -ArgumentList @("-u", "`"$AppPath`"") `
        -WorkingDirectory $ProjectPath `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -WindowStyle Hidden `
        -PassThru

    # Je note l'identifiant du processus.
    "[$(Get-Date)] Processus lancé avec le PID $($Process.Id)." |
        Add-Content -Path $StartLog

    # Je laisse quelques secondes pour vérifier le démarrage.
    Start-Sleep -Seconds 5

    # Je vérifie si Python tourne encore.
    $Process.Refresh()

    if ($Process.HasExited) {
        "[$(Get-Date)] Python s'est arrêté avec le code $($Process.ExitCode)." |
            Add-Content -Path $StartLog
    }
    else {
        "[$(Get-Date)] Python tourne toujours en arrière-plan." |
            Add-Content -Path $StartLog
    }
}
catch {
    # Je conserve l'erreur pour pouvoir la retrouver.
    "[$(Get-Date)] ERREUR : $($_.Exception.Message)" |
        Add-Content -Path $StartLog

    throw
}