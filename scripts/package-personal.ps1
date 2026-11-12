param([string]$Output,[switch]$Installer)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Output) { $Output = Join-Path $root ('release/LocalLingua-' + (Get-Date -Format yyyyMMdd-HHmmss)) }
if (Test-Path -LiteralPath $Output) { throw 'Choose a new output directory; existing releases are never overwritten.' }
if (-not ((dotnet --list-sdks) -match '^10\.')) { throw 'Install .NET 10 SDK; framework downgrade is prohibited.' }
py -3.11 --version
if ($LASTEXITCODE) { throw 'Install Python 3.11.' }
New-Item -ItemType Directory -Force $Output | Out-Null
$Output = (Resolve-Path $Output).Path
Push-Location (Join-Path $root 'apps/web')
try {
    npm.cmd ci
    if ($LASTEXITCODE) { throw 'npm ci failed' }
    npm.cmd run build
    if ($LASTEXITCODE) { throw 'Web build failed' }
    npx.cmd @astryxdesign/cli doctor --built dist
    if ($LASTEXITCODE) { throw 'Astryx built artifact verification failed' }
    node (Join-Path $root 'scripts/collect-web-licenses.mjs') (Join-Path $Output 'notices/web')
    if ($LASTEXITCODE) { throw 'Web license collection failed' }
} finally { Pop-Location }
Copy-Item -Recurse (Join-Path $root 'apps/web/dist') (Join-Path $Output 'web')
foreach ($name in @('AudioHost','Overlay','Launcher')) {
    $project = Join-Path $root "apps/windows/LocalLingua.$name/LocalLingua.$name.csproj"
    dotnet publish $project -c Release -r win-x64 --self-contained true -o $Output
    if ($LASTEXITCODE) { throw "Publish failed: $name" }
}
& (Join-Path $PSScriptRoot 'build-process-capture.ps1')
Copy-Item (Join-Path $root 'apps/windows/LocalLingua.ProcessCapture/build/Release/LocalLingua.ProcessCapture.exe') $Output
$engine = Join-Path $root 'services/engine'
$venv = Join-Path $engine '.venv-build'
py -3.11 -m venv $venv
if ($LASTEXITCODE) { throw 'Build venv failed' }
$python = Join-Path $venv 'Scripts/python.exe'
& $python -m pip install -r (Join-Path $engine 'requirements.txt') -r (Join-Path $engine 'requirements-gpu.txt') pyinstaller
if ($LASTEXITCODE) { throw 'Python dependency install failed' }
& $python -m pip freeze | Set-Content -Encoding utf8 (Join-Path $Output 'python-dependencies.txt')
& $python (Join-Path $root 'scripts/collect-python-licenses.py') (Join-Path $Output 'notices/python')
if ($LASTEXITCODE) { throw 'Python license collection failed' }
Push-Location $engine
try {
    & $python -m PyInstaller --noconfirm --clean --onedir --name LocalLingua.Engine --paths . --collect-all uvicorn --collect-all soxr --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --collect-all huggingface_hub --collect-data certifi --distpath (Join-Path $engine 'build/frozen') --workpath (Join-Path $engine 'build/work') --specpath (Join-Path $engine 'build') engine_entry.py
    if ($LASTEXITCODE) { throw 'Engine freeze failed' }
} finally { Pop-Location }
Copy-Item -Recurse (Join-Path $engine 'build/frozen/LocalLingua.Engine') (Join-Path $Output 'engine')
Copy-Item (Join-Path $engine '.env.example') (Join-Path $Output 'engine/.env')
Copy-Item (Join-Path $engine '.env.gpu.example') (Join-Path $Output 'engine/.env.gpu.example')
Copy-Item (Join-Path $root 'docs/15-PERSONAL-RELEASE.md') (Join-Path $Output 'START-HERE.md')
Copy-Item (Join-Path $root 'LICENSE-THIRD-PARTY.md') $Output
Copy-Item (Join-Path $root 'docs/16-COMPLETE-IMPLEMENTATION.md') (Join-Path $Output 'FEATURES.md')
New-Item -ItemType Directory -Force (Join-Path $Output 'notices/native') | Out-Null
Copy-Item (Join-Path $root 'installer/THIRD-PARTY-NOTICES.md') (Join-Path $Output 'notices/native')
foreach($projectName in @('AudioHost','Overlay','Launcher')) {
    $assetsPath=Join-Path $root "apps/windows/LocalLingua.$projectName/obj/project.assets.json"
    if(-not (Test-Path $assetsPath)){continue}
    $assets=Get-Content -Raw $assetsPath | ConvertFrom-Json
    foreach($package in $assets.libraries.PSObject.Properties) {
        if($package.Value.type -ne 'package'){continue}
        foreach($cache in $assets.packageFolders.PSObject.Properties.Name) {
            $packagePath=Join-Path $cache $package.Value.path
            if(-not (Test-Path $packagePath)){continue}
            $noticeDir=Join-Path $Output ('notices/native/'+$package.Name.Replace('/','-'))
            New-Item -ItemType Directory -Force $noticeDir | Out-Null
            Get-ChildItem -LiteralPath $packagePath -Recurse -File | Where-Object {$_.Name -match '(?i)^(license|notice|copying)|\.nuspec$'} | ForEach-Object {
                Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $noticeDir $_.Name)
            }
        }
    }
}
@{ created = (Get-Date -Format o); acceptance = 'UNVERIFIED'; tests = 'DEFERRED'; modelsBundled = $false } | ConvertTo-Json | Set-Content (Join-Path $Output 'BUILD-STATUS.json')
Get-ChildItem -Recurse -File $Output | Get-FileHash -Algorithm SHA256 | Select-Object @{Name='File';Expression={$_.Path.Substring($Output.Length+1)}},Hash | ConvertTo-Json | Set-Content (Join-Path $Output 'SHA256.json')
Compress-Archive -Path (Join-Path $Output '*') -DestinationPath ($Output+'.zip')
if($Installer) {
    $compiler=Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if(-not $compiler){throw 'Install Inno Setup 6 and add ISCC.exe to PATH. Portable bundle has already been produced.'}
    & $compiler.Source "/DBundleDir=$Output" (Join-Path $root 'installer/LocalLingua.iss')
    if($LASTEXITCODE){throw 'Installer compilation failed.'}
}
Write-Output "Development bundle created: $Output. Acceptance tests still required."
