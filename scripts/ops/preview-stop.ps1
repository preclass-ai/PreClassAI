# Stops ONLY the processes preview.ps1 started (PIDs in apps/api/data/preview.pids.json). Leaves Postgres running.
$pidFile = Join-Path (Resolve-Path "$PSScriptRoot\..\..") "apps\api\data\preview.pids.json"
if (-not (Test-Path $pidFile)) { Write-Host "No preview PID file."; return }
$pids = Get-Content $pidFile | ConvertFrom-Json
foreach ($n in $pids.PSObject.Properties) {
  $proc = Get-Process -Id $n.Value -ErrorAction SilentlyContinue
  if ($proc) { taskkill /PID $n.Value /T /F | Out-Null; Write-Host "stopped $($n.Name) ($($n.Value))" }
}
Remove-Item $pidFile
