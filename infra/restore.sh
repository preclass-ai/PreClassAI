#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${BACKUP_IDENTITY_FILE:?BACKUP_IDENTITY_FILE is required}"

case "$DATABASE_URL" in
  *localhost*|*127.0.0.1*|*restore*|*staging*) : ;;
  *) echo 'Refusing restore unless DATABASE_URL names an isolated restore/staging target' >&2; exit 1 ;;
esac

age -d -i "$BACKUP_IDENTITY_FILE" "$BACKUP_FILE" \
  | gzip -d \
  | psql "$DATABASE_URL"
echo "restore_completed=$BACKUP_FILE"
