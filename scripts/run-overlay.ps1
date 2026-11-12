$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../apps/windows/LocalLingua.Overlay')
if (-not $env:LOCALLINGUA_TOKEN) { throw 'Set the same LOCALLINGUA_TOKEN as the engine session.' }
dotnet run
