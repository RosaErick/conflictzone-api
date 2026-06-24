# Multi-arch (funciona no Oracle Ampere A1 / arm64 e x86).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# GeoDjango precisa de GDAL/GEOS/PROJ em runtime; postgresql-client ajuda na operação.
RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils libproj-dev gdal-bin postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Deps Python primeiro p/ melhor cache de camadas. gunicorn é o servidor de prod.
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# core.wsgi:app — o callable se chama `app` em core/wsgi.py
CMD ["sh", "-c", "gunicorn core.wsgi:app --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 120 --access-logfile - --error-logfile -"]
