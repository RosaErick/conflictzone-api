# Multi-arch friendly (works on Oracle Ampere A1 / arm64 and x86).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# GeoDjango needs GDAL/GEOS/PROJ at runtime; postgresql-client is handy for ops.
RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils libproj-dev gdal-bin postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching. gunicorn is the prod server.
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# core.wsgi:app — the callable is named `app` in core/wsgi.py
CMD ["sh", "-c", "gunicorn core.wsgi:app --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 120 --access-logfile - --error-logfile -"]
