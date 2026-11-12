$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../apps/web')
if (-not (Test-Path node_modules)) { npm.cmd ci }
npm.cmd run dev
