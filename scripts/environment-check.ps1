param([string]$OutputReport)
$ErrorActionPreference='Continue'
function VersionOf([string]$Command,[string[]]$Arguments) {
    $found=Get-Command $Command -ErrorAction SilentlyContinue
    if(-not $found){return @{available=$false;version=$null}}
    $output=& $found.Source @Arguments 2>&1
    return @{available=($LASTEXITCODE -eq 0);version=($output | Out-String).Trim()}
}
$os=Get-CimInstance Win32_OperatingSystem | Select-Object Version,BuildNumber,OSArchitecture
$dotnet=VersionOf 'dotnet.exe' @('--list-sdks')
$python=VersionOf 'py.exe' @('-3.11','--version')
$node=VersionOf 'node.exe' @('--version')
$npm=VersionOf 'npm.cmd' @('--version')
$cmake=VersionOf 'cmake.exe' @('--version')
$ollama=VersionOf 'ollama.exe' @('--version')
$gpu=VersionOf 'nvidia-smi.exe' @('--query-gpu=name,driver_version,memory.total,memory.used','--format=csv,noheader,nounits')
$cuda=@{}
foreach($library in @('cublas64_12.dll','cudnn64_9.dll')) {
    $cuda[$library]=@(($env:PATH -split ';') | Where-Object {$_ -and (Test-Path -LiteralPath (Join-Path $_ $library))}).Count -gt 0
}
$report=[ordered]@{os=$os;dotnet=$dotnet;python311=$python;node=$node;npm=$npm;cmake=$cmake;ollama=$ollama;gpu=$gpu;cudaLibrariesOnPath=$cuda;
    targetDotnet10=([string]$dotnet.version -match '(?m)^10\.');innoSetupAvailable=([bool](Get-Command ISCC.exe -ErrorAction SilentlyContinue));
    note='Environment discovery only; no capture, model inference or tests executed.'}
$json=$report | ConvertTo-Json -Depth 6
Write-Output $json
if($OutputReport){$json | Set-Content -Encoding utf8 -LiteralPath $OutputReport}
