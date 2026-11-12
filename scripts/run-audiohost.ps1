param([switch]$SystemDiagnostic)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../apps/windows/LocalLingua.AudioHost')
if (-not $env:LOCALLINGUA_TOKEN) { throw 'Set the same LOCALLINGUA_TOKEN as the engine session.' }
if ($SystemDiagnostic) { dotnet run -- --system-diagnostic } else { dotnet run }
