#!/bin/sh
# Migrate on every start (idempotent); seed demo data only when SEED_DEMO=true (seed refuses APP_ENV=production).
set -eu
alembic upgrade head
if [ "${SEED_DEMO:-false}" = "true" ]; then python -m seed.seed; fi
exec "$@"
