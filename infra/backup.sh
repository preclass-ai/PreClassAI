#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_DIR:?BACKUP_DIR is required}"
: "${BACKUP_ENCRYPTION_KEY_FILE:?BACKUP_ENCRYPTION_KEY_FILE is required}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$BACKUP_DIR/preclass-$timestamp.sql.gz.age"

pg_dump --format=plain --no-owner --no-privileges "$DATABASE_URL" \
  | gzip -9 \
  | age -R "$BACKUP_ENCRYPTION_KEY_FILE" -o "$output"

find "$BACKUP_DIR" -type f -name 'preclass-*.sql.gz.age' -mtime +14 -delete
echo "backup_created=$output"
