# Roadmap — feito, não feito, e atalhos com gatilho

## Feito (validado)

- [x] **Fase 0 — Fundação.** Settings 12-factor (`SECRET_KEY` obrigatória em prod,
  CORS por env), logging stdout (sem `print`), requirements pinados + Django 4.2
  LTS, ruff + pytest + GitHub Actions.
- [x] **Fase 1 — Modelo + PostGIS.** `Occurrence` geoespacial (PointField + GiST),
  `IngestionRun`, índices, migrations resetadas. Migrate cria as tabelas + extensão.
- [x] **Fase 2 — Ingestão.** `client.py` isolado, `normalize.py` puro, `ingest.py`
  com upsert idempotente + auditoria, command `sync_occurrences` (incremental +
  backfill). Validado contra a API real: 2ª execução não duplica.
- [x] **Fase 3 — API lê do DB.** `selectors.py`, `serializers.py`, views finas;
  mesmo contrato de endpoints; erros 400/503 honestos; `/timeseries/`.
- [x] **Fase 5 — Testes.** 29 testes (transformações, idempotência, falha parcial,
  tz, agregações, contratos de erro). Sem rede.
- [x] **Fase 4 — Observabilidade.** Middleware de log por request; índices
  verificados; idade da ingestão em `/health/`.

## Não feito / em aberto (decisões pendentes do dono)

- [ ] **Backup automatizado.** `pg_dump` agendado → Object Storage (Oracle 10 GB /
  Backblaze B2 10 GB grátis). **É o item nº1 antes de chamar de "produção".**
- [ ] **Backfill histórico 2020+.** Rodar a carga fatiada por ano (ver
  [ingestion.md](ingestion.md#backfill-histórico-a-partir-de-2020)).
- [ ] **HTTPS + domínio.** Trocar nginx por Caddy (TLS automático) ou certbot.
- [ ] **CORS restrito em prod.** Setar `CORS_ALLOWED_ORIGINS` para o domínio do
  frontend (hoje aberto só em dev).
- [ ] **Migrar VM para shape Always Free** se a atual for paga (ver
  [decisions.md](decisions.md#adr-001)).

## Atalhos deliberados (ponytail ledger) — com gatilho de upgrade

| Atalho | Teto atual | Gatilho de upgrade |
|---|---|---|
| Cron + management command (não Celery) | sem retry/concorrência | retry/concorrência/agendamento-no-app → Celery beat |
| Sem cache de agregação | recomputa toda request (~8 ms) | profiler mostrar quente → cache DB-backend → Redis |
| Janela fixa de 3 dias (não cursor) | re-busca a sobreposição | muitos dados/dia → guardar último `occurred_at` |
| Contagem derivada (sem tabela `Victim`) | sem query por atributo de vítima | filtro por idade/raça/sexo → tabela `Victim` |
| Token em memória por run | re-login a cada run | logins caros/frequentes → cache compartilhado |

## Ideias de visualização espacial (PostGIS, custo zero)

São "mais query no Postgres que você já tem", não serviço pago:
- **Clustering server-side** (`ST_ClusterDBSCAN`) — manda clusters, não 50k pontos.
- **Heatmap por grid** (`ST_SnapToGrid`) — agrega em células, devolve poucos polígonos.
- **Vector tiles** (`ST_AsMVT`) — tiles `.mvt` para MapLibre/Mapbox.
- **Export estático** (GeoJSON/PMTiles por nginx/CDN) — tira o DB do hot path se
  as visualizações forem "pontos + heatmap + filtros simples". Avaliar se há
  necessidade real de query espacial dinâmica antes.
