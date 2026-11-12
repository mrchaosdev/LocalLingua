param([switch]$Publish)
$ErrorActionPreference = 'Stop'
# Use the existing Git Credential Manager session. Never print/persist credentials.
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'
$credentialLines = "protocol=https`nhost=github.com`nusername=mrchaosdev`n`n" | git -c credential.interactive=false credential fill 2>$null
if ($LASTEXITCODE) { throw 'Git Credential Manager has no usable GitHub login. Authenticate GitHub on this laptop first.' }
$credential = @{}
foreach ($line in $credentialLines) { if ($line -match '^([^=]+)=(.*)$') { $credential[$matches[1]] = $matches[2] } }
if (-not $credential.password) { throw 'No GitHub credential available.' }
$headers = @{ Authorization = 'Bearer ' + $credential.password; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }
try {
    $account = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers
    Write-Output ('Authenticated GitHub account: ' + $account.login)
    if ($account.login -ne 'mrchaosdev') { throw 'Authenticated account differs from requested mrchaosdev; publication stopped.' }
    if (-not $Publish) { return }
    $repoApi = 'https://api.github.com/repos/mrchaosdev/LocalLingua'
    $existing = $null
    try { $existing = Invoke-RestMethod -Uri $repoApi -Headers $headers }
    catch { if ([int]$_.Exception.Response.StatusCode -ne 404) { throw 'Cannot inspect destination repository.' } }
    if ($existing) { throw 'LocalLingua repository already exists; refusing to overwrite an existing repository.' }
    $body = @{ name = 'LocalLingua'; private = $true; description = 'Local-first Windows 11 EN to VI live subtitles. Development implementation; acceptance tests deferred.' } | ConvertTo-Json
    $created = Invoke-RestMethod -Uri 'https://api.github.com/user/repos' -Headers $headers -Method Post -Body $body -ContentType 'application/json'
    $project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path.Replace('\','/')
    git -c "safe.directory=$project" -C $project remote add origin $created.clone_url
    if ($LASTEXITCODE) { throw 'Could not configure Git remote.' }
    git -c "safe.directory=$project" -C $project push -u origin main
    if ($LASTEXITCODE) { throw 'Git push failed.' }
    Write-Output ('Published: ' + $created.html_url)
} finally { $credential.Clear(); $headers.Clear(); $credentialLines = $null }
