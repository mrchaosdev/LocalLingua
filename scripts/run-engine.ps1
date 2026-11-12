$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$engine = Join-Path $root 'services/engine'
Set-Location $engine
if (-not $env:LOCALLINGUA_TOKEN) {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes); $rng.Dispose()
    $env:LOCALLINGUA_TOKEN = [Convert]::ToBase64String($bytes)
}
Write-Output 'Open the dashboard from this local session link (contains a temporary secret):'
Write-Output ('http://127.0.0.1:8765/#token=' + [uri]::EscapeDataString($env:LOCALLINGUA_TOKEN))
& ./.venv/Scripts/python.exe engine_entry.py
