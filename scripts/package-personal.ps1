param([string]$Output)
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
Push-Location $engine
try {
    & $python -m PyInstaller --noconfirm --clean --onedir --name LocalLingua.Engine --paths . --collect-all uvicorn --collect-all soxr --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --distpath (Join-Path $engine 'build/frozen') --workpath (Join-Path $engine 'build/work') --specpath (Join-Path $engine 'build') engine_entry.py
    if ($LASTEXITCODE) { throw 'Engine freeze failed' }
} finally { Pop-Location }
Copy-Item -Recurse (Join-Path $engine 'build/frozen/LocalLingua.Engine') (Join-Path $Output 'engine')
Copy-Item (Join-Path $engine '.env.example') (Join-Path $Output 'engine/.env')
Copy-Item (Join-Path $engine '.env.gpu.example') (Join-Path $Output 'engine/.env.gpu.example')
Copy-Item (Join-Path $root 'docs/15-PERSONAL-RELEASE.md') (Join-Path $Output 'START-HERE.md')
Copy-Item (Join-Path $root 'LICENSE-THIRD-PARTY.md') $Output
@{ created = (Get-Date -Format o); acceptance = 'UNVERIFIED'; tests = 'DEFERRED'; modelsBundled = $false } | ConvertTo-Json | Set-Content (Join-Path $Output 'BUILD-STATUS.json')
Get-ChildItem -Recurse -File $Output | Get-FileHash -Algorithm SHA256 | Select-Object @{Name='File';Expression={$_.Path.Substring($Output.Length+1)}},Hash | ConvertTo-Json | Set-Content (Join-Path $Output 'SHA256.json')
Write-Output "Development bundle created: $Output. Acceptance tests still required."
