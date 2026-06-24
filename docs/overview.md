# Visão geral

## O problema

Dados de tiroteios/violência armada da Fogo Cruzado precisam virar dashboards,
mapas, heatmaps, séries temporais e filtros. A versão antiga era um **proxy
síncrono**: cada request do frontend logava na Fogo Cruzado, baixava tudo,
agregava em Python e respondia — lento, frágil e refém da API externa.

## A arquitetura atual

```
                 ┌───────────────────────────────────────────────┐
  Fogo Cruzado   │  Ingestão (job auditável, idempotente)        │
  (API externa)  │  client (HTTP) → normalize (puro) → upsert    │
        └────────┼──>  IngestionRun (auditoria)                  │
                 │              │                                 │
                 │              ▼                                 │
                 │     PostgreSQL + PostGIS  ← fonte de verdade   │
                 │              ▲                                 │
   Frontend ─────┼── API DRF (lê do DB, agrega em SQL) ──────────┘
                 └───────────────────────────────────────────────┘
```

**Princípio central:** o request público **nunca toca o provedor externo**. Ele
lê do Postgres e agrega em SQL indexado. A ingestão roda em background (cron).

## Fluxo de dados (ponta a ponta)

1. **Cron** (1x/hora) dispara `manage.py sync_occurrences` — sem datas, pega os
   últimos 3 dias. Ver [ingestion.md](ingestion.md).
2. **`client.py`** fala HTTP com a Fogo Cruzado (login, paginação, token) e
   devolve registros crus, página por página. Não conhece o banco.
3. **`normalize.py`** (funções puras) transforma cada registro cru num DTO
   tipado: parse de data tz-aware, contagem de vítimas **humanas**, coordenadas.
4. **`ingest.py`** faz o **upsert idempotente** por `external_id` e grava um
   `IngestionRun` (status + contagens).
5. **API DRF** (`views.py` → `selectors.py`) lê do banco, valida parâmetros
   (`serializers.py`) e agrega em SQL. Mesmo contrato de endpoints de sempre.

## Stack

| Camada | Tecnologia |
|---|---|
| Web | Django 4.2 LTS + Django REST Framework + drf-spectacular (OpenAPI) |
| Banco | PostgreSQL 16 + **PostGIS** (GeoDjango) |
| Servidor | gunicorn atrás de nginx |
| Orquestração | Docker Compose (`db`, `web`, `nginx`) |
| Agendamento | cron do SO chamando o management command |
| Infra | Oracle Cloud Always Free (VM ARM Ampere A1) |
| Qualidade | ruff (lint) + pytest + GitHub Actions |

## Onde estão as coisas no código

```
api/
  models.py            Occurrence (geo) + IngestionRun
  selectors.py         camada de query/agregação (SQL)
  serializers.py       validação de params + contrato de resposta
  views.py             endpoints (finos: validam, chamam selectors)
  middleware.py        log de request (método, rota, status, duração)
  schemas.py           docs OpenAPI dos endpoints
  services/
    fogo_cruzado/
      client.py        cliente HTTP isolado (sem models)
      normalize.py     transformações puras (sem Django)
    ingest.py          orquestra fetch→normalize→upsert→auditoria
  management/commands/
    sync_occurrences.py  o comando de ingestão (cron + backfill)
  tests/               testes por transformação
core/
  settings.py          config 12-factor (env-driven)
```
