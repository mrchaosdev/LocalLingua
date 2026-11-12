Write-Output 'LocalLingua environment report — Windows 11 target'
Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsBuildNumber
Write-Output '--- .NET ---'; dotnet --info
Write-Output '--- Python ---'; py -0p
Write-Output '--- Node ---'; node --version; npm --version
Write-Output '--- NVIDIA ---'; nvidia-smi
Write-Output '--- Ollama ---'; ollama list
Write-Output 'Do not publish this report with personal host/user paths.'
