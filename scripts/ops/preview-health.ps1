# Every 10 min: check API (:8000), Caddy (:8080, basic auth) and the public tunnel URL.
# Local service down -> full restart (stop + start). Only the tunnel down -> restart just the tunnel.
# A new tunnel URL is written to .agents/PREVIEW_URL.md and pushed as its own commit (that file only).
# Does nothing when the preview was never started (no PID file), so it cannot race preview-start.ps1.
$root = Resolve-Path "$PSScriptRoot\..\.."
$data = Join-Path $root "apps\api\data"; $logs = Join-Path $data "logs"
$pidFile = Join-Path $data "preview.pids.json"; $urlFile = Join-Path $root ".agents\PREVIEW_URL.md"
function Log($m) { Add-Content (Join-Path $logs "health.log") "$(Get-Date -Format s) $m" }
function Get-Url($f) { if (Test-Path $f) { ((Get-Content $f -Raw) | Select-String "https://[a-z0-9-]+\.trycloudflare\.com").Matches.Value } }
if (-not (Test-Path $pidFile)) { Log "no PID file, preview not started"; return }

$cred = @{}; Get-Content (Join-Path $data "preview-credentials.txt") | ForEach-Object { $k, $v = $_ -split "=", 2; $cred[$k] = $v }
$auth = @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($cred.user):$($cred.pass)")) }
function Up($url, $h = @{}) { try { (Invoke-WebRequest $url -Headers $h -UseBasicParsing -TimeoutSec 15).StatusCode -eq 200 } catch { $false } }

$url = Get-Url $urlFile
$api = Up "http://127.0.0.1:8000/v1/health"
$caddy = Up "http://127.0.0.1:8080/v1/health" $auth
$tunnel = [bool]$url -and (Up "$url/v1/health" $auth)
Log "api=$api caddy=$caddy tunnel=$tunnel"
if ($api -and $caddy -and $tunnel) { return }

if (-not ($api -and $caddy)) {
  & "$PSScriptRoot\preview-stop.ps1"
  & "$PSScriptRoot\preview-start.ps1"
} else {
  $pids = Get-Content $pidFile | ConvertFrom-Json
  taskkill /PID $pids.tunnel /T /F *> $null
  $cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
  if (-not $cf) { $cf = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter cloudflared.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName }
  Remove-Item "$logs\tunnel.*.log" -ErrorAction SilentlyContinue
  $p = Start-Process $cf "tunnel --url http://127.0.0.1:8080 --no-autoupdate" -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$logs\tunnel.out.log" -RedirectStandardError "$logs\tunnel.err.log"
  $pids.tunnel = $p.Id; $pids | ConvertTo-Json | Set-Content $pidFile
  $new = $null
  for ($i = 0; $i -lt 45 -and -not $new; $i++) {
    Start-Sleep 2
    $new = (Select-String -Path "$logs\tunnel.err.log", "$logs\tunnel.out.log" -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1).Matches.Value
  }
  if (-not $new) { Log "tunnel restart: no URL"; exit 1 }
  Set-Content $urlFile "Preview URL (changes on tunnel restart): $new" -Encoding utf8
}

$new = Get-Url $urlFile
if ($new -and $new -ne $url) {
  Log "new URL $new"
  Push-Location $root
  if ((git branch --show-current) -eq "feat/backend-v2") {   # never push from another branch
    git add -f .agents/PREVIEW_URL.md
    git commit -m "Update preview URL" -- .agents/PREVIEW_URL.md *> $null
    git push origin feat/backend-v2 *> $null
    Log "push exit=$LASTEXITCODE"
  } else { Log "not on feat/backend-v2, URL not pushed" }
  Pop-Location
}
