Todo agente deve desenvolver pensando em confiabilidade, rastreabilidade, idempotência e evolução de dados.

Esta API não deve ser apenas um proxy da Fogo Cruzado. Ela deve funcionar como uma camada própria de ingestão, persistência, enriquecimento, consulta e visualização analítica, capaz de sustentar dashboards, mapas, filtros geográficos, séries temporais e análises históricas.

# Engineering Rules

This project is a data ingestion and analytics API built with Django, DRF, PostgreSQL, PostGIS, Celery and Redis.

The system ingests data from the Fogo Cruzado API, normalizes it, stores it locally and exposes stable endpoints for analytical products such as tables, maps, heatmaps, time series and dashboards.

## Non-negotiable principles

- Reliability over cleverness.
- Idempotent ingestion.
- External API isolation.
- Explicit data contracts.
- Auditable background jobs.
- Secure token handling.
- Timezone correctness.
- Geospatial-first modeling.
- Observable failures.
- Tests for every transformation.

## Forbidden

- Business logic in views.
- Direct frontend access to the external provider.
- Synchronous ingestion in public requests.
- Silent failures.
- Hardcoded secrets.
- Unpaginated list endpoints.
- Unindexed analytical queries.
- Duplicated external records.
- Naive datetime handling.
- Raw payload as the only query model.