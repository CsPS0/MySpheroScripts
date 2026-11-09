# Sphero BOLT Web Dashboard - PowerShell Launcher
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path (Join-Path $ScriptDir "sphero-neu")

$PythonExe = $null
if (Test-Path ".venv\Scripts\python.exe") {
    $PythonExe = ".venv\Scripts\python.exe"
} elseif (Test-Path "..\.venv\Scripts\python.exe") {
    $PythonExe = "..\.venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
} else {
    Write-Host "[HIBA / ERROR] Python 3.10+ nem talalhato a rendszeren!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org or Microsoft Store." -ForegroundColor Yellow
    exit 1
}

Write-Host "[*] Inditas / Starting Sphero Web Server ($PythonExe)..." -ForegroundColor Cyan
& $PythonExe web\server.py --host 0.0.0.0 --port 8080 @args
