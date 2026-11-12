param([string]$Directory)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if(-not $Directory){$Directory=Join-Path $env:LOCALAPPDATA 'LocalLingua/models'}
$python=Join-Path $root 'services/engine/.venv/Scripts/python.exe'
if(-not (Test-Path $python)){throw 'Run setup-engine.ps1 -Gpu first.'}
& $python (Join-Path $root 'services/engine/install_models.py') --directory $Directory
if($LASTEXITCODE){throw 'Model installation failed; do not enable incomplete models.'}
