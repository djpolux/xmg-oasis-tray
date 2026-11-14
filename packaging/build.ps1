# Build a single, self-contained Windows executable (no Python needed to run it).
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install --upgrade pip | Out-Null
python -m pip install -r "$root\requirements.txt" "pyinstaller>=6,<7" | Out-Null

Remove-Item "$root\dist\XMG-OASIS-Tray.exe" -ErrorAction SilentlyContinue

python -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name "XMG-OASIS-Tray" `
    --icon "$root\assets\icon.ico" `
    --paths "$root\src" `
    --hidden-import "pystray._win32" `
    --distpath "$root\dist" --workpath "$root\build" --specpath "$root\build" `
    "$root\packaging\launcher.py"

if ($LASTEXITCODE -ne 0 -or -not (Test-Path "$root\dist\XMG-OASIS-Tray.exe")) {
    throw "PyInstaller build failed"
}
Write-Host "Built: $root\dist\XMG-OASIS-Tray.exe"
