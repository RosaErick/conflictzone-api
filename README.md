# ConflictZone API

Camada de **ingestão + persistência + analytics** sobre os dados de violência
armada da Fogo Cruzado (escopo: **Rio de Janeiro**). Não é um proxy: lê de um
PostgreSQL+PostGIS próprio, populado por um job idempotente e auditável. Roda
100% em free tier.

## Início rápido

```sh
docker compose up -d --build
docker compose run --rm web python manage.py sync_occurrences   # popula últimos 3 dias
curl http://localhost/health/
```

## Documentação

Tudo em **[`docs/`](docs/)** — comece pelo [índice](docs/README.md).

- [Visão geral](docs/overview.md) · [Ingestão](docs/ingestion.md) ·
  [Modelo de dados](docs/data-model.md) · [API](docs/api.md)
- [Deploy](docs/deployment.md) · [Decisões](docs/decisions.md) ·
  [Roadmap](docs/roadmap.md)
- **Agentes/devs novos:** [docs/agents.md](docs/agents.md)
