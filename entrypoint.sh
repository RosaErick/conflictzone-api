#!/bin/sh
# Runs on every container start: apply migrations, gather static, then launch
# whatever CMD was passed (gunicorn).
set -e

echo "[entrypoint] applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] collecting static files..."
python manage.py collectstatic --noinput

echo "[entrypoint] starting: $*"
exec "$@"
