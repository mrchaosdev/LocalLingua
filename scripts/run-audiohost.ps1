$ErrorActionPreference='Stop'
Set-Location "$PSScriptRoot\..pps\windows\LocalLingua.AudioHost"
Write-Warning 'DIAGNOSTIC: captures all system output, NOT only Discord!'
dotnet run
