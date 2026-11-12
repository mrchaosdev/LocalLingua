param([switch]$Gpu)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$engine = Join-Path $root 'services/engine'
Set-Location $engine
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE) { throw 'Python 3.11 is required.' }
}
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE) { throw 'Dependency installation failed.' }
if ($Gpu) {
    & ./.venv/Scripts/python.exe -m pip install -r requirements-gpu.txt
    if ($LASTEXITCODE) { throw 'GPU dependency installation failed.' }
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Output 'Dependencies installed. Models and CUDA prerequisites require separate target-PC setup.'
