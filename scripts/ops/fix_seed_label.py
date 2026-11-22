# ruff: noqa: E501
"""Remove the "(DỮ LIỆU MINH HỌA)" label from titles and notes of an existing database. NEVER runs automatically.

    cd apps/api
    $env:DATABASE_URL = "<connection string>"                       # PowerShell, this session only
    uv run python ../../scripts/ops/fix_seed_label.py               # dry run (default): lists what would change
    uv run python ../../scripts/ops/fix_seed_label.py --apply       # rewrites the editable fields in one transaction

Only editable fields are rewritten: source_asset.title, source_asset.license_note, lesson.title. Source anchors, published
snapshots and approved blocks are immutable (database triggers) and are only counted; to change those, publish a new version.
"""
import argparse
import asyncio
import os
import re
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.getcwd())  # run from apps/api
from app.config import get_settings  # noqa: E402

LABEL = re.compile(r"\s*\(?\bDỮ LIỆU MINH HỌA\b\)?\s*:?", re.IGNORECASE)
FIELDS = (("source_asset", "title"), ("source_asset", "license_note"), ("lesson", "title"))
IMMUTABLE = (("source_anchor", "excerpt"), ("published_version", "snapshot::text"), ("content_block", "payload::text"))


def clean(value: str) -> str:
    out = LABEL.sub(" ", value).strip(" :")
    return re.sub(r"\s{2,}", " ", out)


async def run(apply: bool) -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        total = 0
        for table, col in FIELDS:
            sql = f"SELECT id, {col} AS v FROM {table} WHERE {col} ILIKE '%DỮ LIỆU MINH HỌA%'"  # noqa: S608 constants
            rows = (await conn.execute(text(sql))).all()
            for r in rows:
                new = clean(r.v)
                print(f"{table}.{col} {r.id}: {r.v!r} -> {new!r}")
                if apply:
                    await conn.execute(text(f"UPDATE {table} SET {col} = :v WHERE id = :i"), {"v": new, "i": r.id})  # noqa: S608
            total += len(rows)
        for table, expr in IMMUTABLE:
            n = (await conn.execute(text(f"SELECT count(*) FROM {table} WHERE {expr} ILIKE '%DỮ LIỆU MINH HỌA%'"))).scalar_one()  # noqa: S608
            if n:
                print(f"{table}: {n} immutable row(s) still contain the label (not touched)")
        print(f"{'rewrote' if apply else 'would rewrite'} {total} field(s)" + ("" if apply else "; dry run, nothing changed. Use --apply."))
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    asyncio.run(run(ap.parse_args().apply))
