# GitLab driver (Windows PowerShell 5.1 compatible). Runs the steps converted from the GitHub workflow.
# Steps marked coe never fail the job; steps marked always run even after an earlier failure.
$ErrorActionPreference = 'Continue'
$env:GITHUB_WORKSPACE = (Get-Location).Path
$m = Get-Content ci/gl/manifest.json -Raw -Encoding utf8 | ConvertFrom-Json
$pw = (Get-Command pwsh -ErrorAction SilentlyContinue)
if (-not $pw) {
  Write-Host 'pwsh missing: downloading PowerShell 7 zip (free, public release)'
  New-Item -ItemType Directory -Force C:/pwsh7 | Out-Null
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/PowerShell-7.4.6-win-x64.zip' -OutFile C:/pwsh7.zip
  Expand-Archive C:/pwsh7.zip C:/pwsh7 -Force
  $env:Path = 'C:\pwsh7;' + $env:Path
}
$bash = (Get-Command bash -ErrorAction SilentlyContinue)
if (-not $bash) { foreach ($p in 'C:\Program Files\Git\bin','C:\Program Files\Git\usr\bin') { if (Test-Path "$p\bash.exe") { $env:Path = "$p;" + $env:Path } } }
$failed = $false
foreach ($s in $m) {
  if ($failed -and -not $s.always) { Write-Host ('SKIP (earlier failure): ' + $s.name); continue }
  Write-Host ('::: STEP ' + $s.name)
  if ($s.shell -eq 'bash') { & bash -e $s.file } else { & pwsh -NoProfile -ExecutionPolicy Bypass -Command ('$ErrorActionPreference="Stop"; & ./' + $s.file) }
  $code = $LASTEXITCODE
  if ($code -ne 0) {
    Write-Host ('STEP EXIT ' + $code + ' coe=' + $s.coe)
    if (-not $s.coe) { $failed = $true }
  }
}
if ($failed) { exit 1 }
