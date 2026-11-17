# Logon entry point for the "PreClass Preview" task: wait for Docker, drop a stale PID file (after reboot), run preview.ps1.
# A non-zero exit makes Task Scheduler retry (see preview-task-install.ps1).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
$pidFile = Join-Path $root "apps\api\data\preview.pids.json"

$dd = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
for ($i = 0; $i -lt 90; $i++) {   # up to 3 minutes
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { break }
  if ($i -eq 0 -and (Test-Path $dd) -and -not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) { Start-Process $dd }
  Start-Sleep 2
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker engine not ready after 3 minutes." }

if (Test-Path $pidFile) {
  # Stale only if none of the recorded PIDs is still a live process (never kill by recycled PID).
  $alive = (Get-Content $pidFile | ConvertFrom-Json).PSObject.Properties | Where-Object { Get-Process -Id $_.Value -ErrorAction SilentlyContinue }
  if ($alive) { Write-Host "Preview already running."; return }
  Remove-Item $pidFile
}
& "$PSScriptRoot\preview.ps1"
