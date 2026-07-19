#!/usr/bin/env bash
set -euo pipefail

# Apply DB migrations if any revisions exist. Safe to run on every boot;
# `alembic upgrade head` is a no-op when the DB is already current.
if [ -d "migrations/versions" ] && [ -n "$(ls -A migrations/versions 2>/dev/null | grep -v __pycache__ || true)" ]; then
  echo "[entrypoint] running alembic upgrade head..."
  alembic upgrade head
else
  echo "[entrypoint] no migrations found, skipping alembic."
fi

# Seed the suggestion catalog ONCE here (idempotent + additive), before
# workers start — avoids concurrent seeding races across gunicorn workers.
echo "[entrypoint] seeding catalog..."
python -m app.db.seed_run

# Gunicorn with uvicorn workers = production-grade ASGI serving.
# WEB_CONCURRENCY controls worker count (tune per ECS task CPU).
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-2}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --access-logfile - \
  --error-logfile - \
  --timeout 120
