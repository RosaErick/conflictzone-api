#!/bin/sh
# Roda a cada start do container: aplica migrations, coleta estáticos e então
# executa o CMD passado (gunicorn).
set -e

echo "[entrypoint] applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] collecting static files..."
python manage.py collectstatic --noinput

echo "[entrypoint] starting: $*"
exec "$@"
