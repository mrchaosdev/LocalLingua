$ErrorActionPreference = 'Stop'
$project = Join-Path $PSScriptRoot '../apps/windows/LocalLingua.ProcessCapture'
cmake -S $project -B (Join-Path $project 'build') -A x64
if ($LASTEXITCODE) { throw 'CMake configure failed; install VS C++ tools and Windows SDK.' }
cmake --build (Join-Path $project 'build') --config Release
if ($LASTEXITCODE) { throw 'Native capture build failed.' }
