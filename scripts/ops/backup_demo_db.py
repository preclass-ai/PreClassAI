"""pg_dump of the demo database to a file OUTSIDE the repository (custom format, restorable with pg_restore).

    cd apps/api
    $env:DATABASE_URL = "<Neon direct connection string>"     # this shell only
    uv run python ../../scripts/ops/backup_demo_db.py [output-dir]   # default: ~/preclass-backups

Uses the pg_dump inside the local `infra-postgres-1` container (docker compose -f infra/compose.dev.yml up -d postgres).
The dump holds demo data and password hashes: keep it private, never commit it. Restore into a scratch database with:
    docker exec -i infra-postgres-1 pg_restore -U preclass -d <scratch_db> < backup.dump
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def libpq_url(url: str) -> str:
    """postgresql+asyncpg://…?ssl=require -> postgresql://…?sslmode=require"""
    p = urlsplit(url)
    q = [("sslmode" if k == "ssl" else k, v) for k, v in parse_qsl(p.query) if k != "channel_binding"]
    return urlunsplit(("postgresql", p.netloc, p.path, urlencode(q), ""))


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL in this shell first.")
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "preclass-backups").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"preclass-{datetime.now():%Y%m%d-%H%M%S}.dump"
    host = urlsplit(url).hostname
    print(f"Dumping {host} -> {out}")
    with out.open("wb") as f:
        r = subprocess.run(["docker", "exec", "infra-postgres-1", "pg_dump", "-Fc", "--no-owner", libpq_url(url)],  # noqa: S603, S607
                           stdout=f, stderr=subprocess.PIPE)
    if r.returncode != 0:
        out.unlink(missing_ok=True)
        sys.exit("pg_dump failed: " + r.stderr.decode(errors="replace")[:400])
    print(f"OK {out.stat().st_size / 1024:.0f} KB. Keep it private; never commit it.")


if __name__ == "__main__":
    main()
