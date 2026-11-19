# One command preview: postgres -> migrate+seed -> API (uvicorn, 1 worker) -> Prism -> Caddy -> Cloudflare quick tunnel.
# Seed data is mock ("DỮ LIỆU MINH HỌA"). No Docker image is built. Stop with scripts\ops\preview-stop.ps1.
# Basic auth: set PREVIEW_BASIC_AUTH="user:pass", otherwise random credentials are generated and written to
# apps/api/data/preview-credentials.txt (git-ignored). The tunnel URL goes to .agents/PREVIEW_URL.md (git-ignored).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
$api = Join-Path $root "apps\api"
$logs = Join-Path $api "data\logs"
$pidFile = Join-Path $api "data\preview.pids.json"
New-Item -ItemType Directory -Force $logs | Out-Null
if (Test-Path $pidFile) { throw "Preview already running (or stale). Run scripts\ops\preview-stop.ps1 first." }

function Find-Exe($name) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  $hit = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter ($(if ($name -like "*.*") { $name } else { "$name.exe" })) -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($hit) { return $hit.FullName }
  throw "$name not found (winget install --scope user)"
}
$caddy = Find-Exe "caddy"; $cloudflared = Find-Exe "cloudflared"
$pids = @{}

# 1. Postgres (the only container; memory-limited in compose.dev.yml)
docker compose -f "$root\infra\compose.dev.yml" up -d postgres | Out-Null
for ($i = 0; $i -lt 60; $i++) {
  if ((docker inspect -f "{{.State.Health.Status}}" infra-postgres-1 2>$null) -eq "healthy") { break }
  Start-Sleep 2
}

# 2. Environment for the API (dev data only, mock LLM, Secure cookie because the tunnel is HTTPS)
$env:DATABASE_URL = "postgresql+asyncpg://preclass:preclass@127.0.0.1:5432/preclass"
$env:APP_ENV = "development"; $env:LLM_PROVIDER = "mock"; $env:COOKIE_SECURE = "true"; $env:PYTHONUTF8 = "1"; $env:PYTHONPATH = $api
Push-Location $api
uv run python -m alembic upgrade head
uv run python -m seed.seed
Pop-Location
$n = (docker exec infra-postgres-1 psql -U preclass -d preclass -tAc "select count(*) from app_user") -join ""
if ([int]$n -lt 1) { throw "Migration/seed did not populate the preclass database (app_user is empty)." }

# 3. Console build (static)
$dist = Join-Path $root "apps\console\dist"
if (-not (Test-Path "$dist\index.html")) {
  Push-Location "$root\packages\api-client"; npm ci --no-audit --no-fund; Pop-Location
  Push-Location "$root\apps\console"; npm ci --no-audit --no-fund; npm run build; Pop-Location
}

function Start-Bg($file, $argList, $name, $dir) {
  $p = Start-Process -FilePath $file -ArgumentList $argList -WorkingDirectory $dir -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$logs\$name.out.log" -RedirectStandardError "$logs\$name.err.log"
  $script:pids[$name] = $p.Id
  $script:pids | ConvertTo-Json | Set-Content $script:pidFile
}

# 4. API: one worker (login rate limit is per process), venv python directly so the PID is the server
Start-Bg "$api\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1" "api" $api
# 5. Prism mock for routes still answering 501
Start-Bg (Find-Exe "npx.cmd") "--yes @stoplight/prism-cli@5.14.2 mock -p 4010 -h 127.0.0.1 $api\openapi\openapi.json" "prism" $root

# 5b. Web (apps/web, Next). Needs apps/web/.next from `pnpm build`; on Windows the build exits with EPERM at the
# `standalone` symlink step but .next is complete, so `next start` works.
if (-not (Test-Path "$root\apps\web\.next\BUILD_ID")) { throw "apps/web/.next missing: run pnpm build first." }
Start-Bg (Find-Exe "node") "$root\apps\web\node_modules\next\dist\bin\next start -p 3000 -H 127.0.0.1" "web" "$root\apps\web"

# 6. Caddy with basic auth
if ($env:PREVIEW_BASIC_AUTH) { $user, $pass = $env:PREVIEW_BASIC_AUTH -split ":", 2 }
else {
  $user = "preview"
  $pass = -join ((48..57) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
}
Set-Content "$api\data\preview-credentials.txt" "user=$user`npass=$pass" -Encoding ascii
$env:PREVIEW_USER = $user
$env:PREVIEW_HASH = (& $caddy hash-password --plaintext $pass)
$env:CONSOLE_DIST = ($dist -replace "\\", "/")
Start-Bg $caddy "run --config $root\infra\Caddyfile.preview --adapter caddyfile" "caddy" $root

# 7. Quick tunnel (no account). URL changes whenever the tunnel restarts.
Start-Bg $cloudflared "tunnel --url http://127.0.0.1:8080 --no-autoupdate" "tunnel" $root
$url = $null
for ($i = 0; $i -lt 45 -and -not $url; $i++) {
  Start-Sleep 2
  $m = Select-String -Path "$logs\tunnel.err.log", "$logs\tunnel.out.log" -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($m) { $url = $m.Matches[0].Value }
}
if ($url) { Set-Content "$root\.agents\PREVIEW_URL.md" "Preview URL (changes on tunnel restart; do not commit): $url" -Encoding utf8 }
Write-Host "PREVIEW URL: $url"
Write-Host "Credentials: apps\api\data\preview-credentials.txt  Logs: $logs"
