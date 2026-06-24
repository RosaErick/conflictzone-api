# ConflictZone API — Plano de Implementação (para o próximo agente)

Este documento é o **plano fiel e completo** para transformar a API de um proxy
síncrono numa **camada de ingestão + persistência + analytics**, conforme o
contrato em `backend-engineer.md`. Cada decisão de implementação foi passada pela
**escada do ponytail** (a solução mais preguiçosa que funciona), com o **gatilho
de upgrade** nomeado quando algo for deliberadamente adiado.

> Como ler: os **não-negociáveis** e a lista de **proibidos** do
> `backend-engineer.md` são lei. O ponytail decide *como* implementar cada um —
> nunca *se* implementa. Onde adio algo, está marcado `🪶 ponytail:` com o gatilho.

---

## 0. Contrato (de `backend-engineer.md`) — lei, não sugestão

**Não-negociáveis:** reliability over cleverness · ingestão idempotente ·
isolamento da API externa · contratos de dados explícitos · jobs de background
auditáveis · token seguro · timezone correto · modelagem geoespacial · falhas
observáveis · testes para cada transformação.

**Proibido:** lógica de negócio em views · frontend acessando o provedor direto ·
ingestão síncrona em requests públicos · falhas silenciosas · segredos hardcoded ·
endpoints de lista sem paginação · queries analíticas sem índice · registros
externos duplicados · datetime naive · payload cru como único modelo de consulta.

A seção 9 mapeia **cada** item acima para a fase onde é satisfeito. Se algo não
estiver coberto lá, o plano falhou.

---

## 1. Estado atual (ponto de partida — não re-descobrir)

- Django 4.1.3 + DRF + drf-spectacular; **SQLite**; deploy em produção na **Oracle
  Cloud Always Free** via Docker Compose (gunicorn + nginx) em `http://137.131.217.162/`.
- Hoje é **proxy síncrono**: cada request faz login no Fogo Cruzado → pagina tudo →
  agrega em Python. O modelo `Occurrence` existe mas **não é persistido** no fluxo.
- Já corrigido nesta fase de bootstrap (não refazer): cache de token+dados em
  memória, paginação upstream com `hasNextPage`, timeouts, `take` reduzido,
  multi-tipo, contagem de feridos (`situation == 'Wounded'`), settings env-driven
  mínimo (`DJANGO_SECRET_KEY`/`DJANGO_DEBUG`/`DJANGO_ALLOWED_HOSTS`/`SQLITE_DIR`).
- **Contratos de endpoint que o frontend já consome (manter idênticos no cutover):**
  `GET /health/`, `/health/fogo-cruzado/`, `/occurrences/`, `/occurrences/stats/`,
  `/occurrences/monthly/`, `/occurrences/by-city/`, `/occurrences/filters/`.
  Query params: `initialdate`, `finaldate`, `type` (repetível), `city`,
  `policePresent`, `victimStatus`, `page`, `take`.

### Fatos de domínio descobertos (usar, não re-investigar)
- Identificador único do provedor: `occurrence.id` (UUID) → **chave de dedup**.
- Datas vêm ISO-8601 com `Z` (UTC). Agrupamento "local" deve ser **America/Sao_Paulo**.
- Vítimas: campo `situation` ∈ {`Dead`, `Wounded`, ...}; `type` ∈ {`People`, `Animals`}.
  **Mortos/feridos humanos = filtrar `type == 'People'`** (hoje conta tudo — corrigir).
- `idState` (RJ) e `CITY_IDS` estão hardcoded; **`CITY_IDS` tem UUIDs placeholder
  falsos** (`a1234567-...`) — buscar a lista real do provedor ou remover.

---

## 2. Arquitetura-alvo

```
                 ┌──────────────────────────────────────────┐
  Fogo Cruzado   │  Ingestão (job auditável, idempotente)    │
  (API externa)  │  client isolado → normaliza → upsert      │
        └────────┼──>  IngestionRun (auditoria)              │
                 │       │                                   │
                 │       ▼                                   │
                 │   PostgreSQL (+ PostGIS)  ← fonte de verdade
                 │       ▲                                   │
   Frontend ─────┼── API DRF (lê do DB, agrega em SQL) ──────┘
                 └──────────────────────────────────────────┘
```

Princípio central: **o request público nunca toca o provedor externo**. Ele lê do
Postgres e agrega em SQL (indexado). A ingestão roda em background.

---

## 3. Doutrina ponytail para este plano

1. Cada item do contrato é implementado pela **menor solução que o satisfaz**.
2. Dep nova só quando algumas linhas / o que já existe não resolve. Toda dep
   adiada vira `🪶 ponytail:` com gatilho de upgrade.
3. Cada transformação não-trivial deixa **um check executável** (`assert`/`test_*`),
   sem framework além do `pytest` (exigido pelo contrato: "tests for every transformation").
4. Sem abstração especulativa: nada de interface com 1 implementação, factory para
   1 produto, config para valor que nunca muda.
5. Contratos de endpoint **não mudam** no cutover — o frontend não pode quebrar.

### Decisões lazy explícitas (honram o contrato, adiam o peso)
| Contrato pede | Lazy agora | Gatilho de upgrade |
|---|---|---|
| Celery + Redis (jobs) | **management command + cron do SO**, auditado em `IngestionRun` | Quando precisar de retry/concorrência/agendamento-no-app → Celery beat |
| Redis (cache) | **`django.core.cache.backends.db` (cache em tabela)** — compartilhado entre workers gunicorn, zero dep | Quando o cache em DB medir lento/quente → Redis (Upstash free) |
| PostGIS / geoespacial | **`PointField` + índice GiST desde a modelagem** (é não-negociável e barato no momento da migração) | já incluso — não adiar; migração depois custa caro |

> O Postgres em si **não** é lazy-adiável: PostGIS exige Postgres e o contrato pede
> ambos. Entra na Fase 1.

---

## 4. Plano por fases (cada fase é entregável e testável)

### Fase 0 — Fundação (sem mudança de comportamento)
**Objetivo:** base segura para tudo. Nenhuma alteração de resposta de API.
- [ ] Settings 12-factor: `django-environ` (ou `os.environ` puro — 🪶 ponytail:
      `os.environ` já cobre, `django-environ` só se a config crescer). Split
      `settings/base|dev|prod` **só se** divergirem de fato; senão um arquivo com
      flags por env. `SECRET_KEY` obrigatório em prod (sem fallback inseguro quando
      `DEBUG=False`).
- [ ] `logging` configurado (handler stdout, formato simples). **Banir `print()`.**
- [ ] Pinar `requirements.txt` (hashes via `pip-tools`/`uv`) e subir para **Django
      LTS** (4.2 ou 5.x). Remover dead code: arquivo `re`, `save_data` não usado.
- [ ] `ruff` + `black` + `mypy` + `pre-commit` + 1 GitHub Action (lint+test).
**Aceite:** `ruff`/`mypy` limpos; app sobe igual; zero `print` no `api/`.

### Fase 1 — Modelo de dados + Postgres/PostGIS
**Objetivo:** fonte de verdade local, geoespacial, sem duplicação.
- [ ] Adicionar serviço `db` (postgis/postgis) ao `docker-compose.yml`; `DATABASES`
      via env; GeoDjango (`django.contrib.gis`).
- [ ] Remodelar `Occurrence` (contrato explícito, **não** payload cru):
      `external_id` (UUID, `unique=True`) · `occurred_at` (tz-aware, index) ·
      `location = PointField(geography=True)` (+ índice GiST) · `address` ·
      `neighborhood` · `city` · `main_reason` (tipo) · `police_action` ·
      `agent_presence` · `fatalities` (int) · `injuries` (int) · `weight` ·
      `raw = JSONField` (payload original p/ auditoria/reprocesso) ·
      `ingested_at`. Índices btree em `occurred_at`, `city`, `main_reason`.
- [ ] Modelar vítimas: 🪶 ponytail: **contagens derivadas** (`fatalities`/`injuries`)
      no upsert + `raw` guardado, **em vez de** tabela `Victim` normalizada —
      add tabela `Victim` quando houver query por atributo de vítima (idade/raça).
      Contagem = vítimas com `type == 'People'` e `situation` em `Dead`/`Wounded`.
- [ ] Constraint de unicidade em `external_id` (dedup idempotente).
**Aceite:** `migrate` cria as tabelas + extensão PostGIS; inserir o mesmo
`external_id` duas vezes não duplica (teste).

### Fase 2 — Ingestão (job auditável, idempotente, isolada)
**Objetivo:** trazer e normalizar dados fora do caminho do request.
- [ ] `services/fogo_cruzado/client.py`: cliente isolado (só fala HTTP com o
      provedor), `requests.Session`, timeouts, token via cache seguro, paginação
      por `hasNextPage`, UUIDs/estado por **config** (matar placeholders falsos).
      Nenhum import de Django models aqui (isolamento da API externa).
- [ ] `services/fogo_cruzado/normalize.py`: payload cru → DTO `@dataclass` tipado
      (contrato explícito). Funções puras (testáveis): parse de datetime tz-aware,
      contagem de vítimas humanas, `mainReason`, validação de coordenada → `Point`.
- [ ] Modelo `IngestionRun` (auditoria): `started_at`, `finished_at`, `status`
      (`success`/`partial`/`failed`), `fetched`, `created`, `updated`, `error`.
- [ ] `management/commands/sync_occurrences.py`: fetch → normalize → **upsert
      idempotente** (`update_or_create` por `external_id`) → grava `IngestionRun`.
      Falha de página = run `partial` + log (nunca silenciosa, nunca zera o já gravo).
- [ ] Agendamento: 🪶 ponytail: **cron do SO** na VM chamando o command (ou
      `docker compose run`), 1x/hora. Documentar no `DEPLOY.md`. Upgrade → Celery beat.
**Aceite:** rodar o command popula o DB; rodar de novo não duplica e marca
`updated`; derrubar o upstream no meio gera run `partial` com dados parciais salvos.

### Fase 3 — API lê do DB (cutover sem quebrar o frontend)
**Objetivo:** trocar o proxy por leitura local, contratos idênticos.
- [ ] `selectors.py` (camada de consulta — **tira a lógica das views**): funções
      que recebem filtros validados e retornam querysets/agregados.
- [ ] Agregações em **SQL** (`annotate`, `Count`, `Sum`, `TruncDay/Week/Month` com
      `tzinfo=America/Sao_Paulo`) sobre colunas **indexadas**. `/monthly/` vira
      `/timeseries/?granularity=day|week|month` (manter `/monthly/` como alias do
      `month` para não quebrar contrato; 🪶 ponytail: alias de 1 linha, não duplicar lógica).
- [ ] DRF: **serializers de query params** (validação na fronteira) e de resposta
      (contrato explícito). Manter exatamente os campos que o frontend espera
      (`id,lat,lng,address,date,type,fatalities,injuries,policePresent,neighborhood,city,weight`).
- [ ] **Paginação obrigatória** em `/occurrences/` (DRF pagination). Sem lista
      ilimitada.
- [ ] **Erros honestos:** 400 para input inválido, 503 quando a ingestão está
      defasada/sem dados — **nunca** retornar `[]` mascarando falha. `/health/`
      reporta idade do último `IngestionRun`.
- [ ] `/by-city/` → manter contrato, mas como tudo é RJ, expor breakdown por
      **bairro** (o frontend já espera isso). 🪶 ponytail: reusar a mesma query
      agregada, só trocar o `GROUP BY`.
**Aceite:** todos os endpoints respondem do DB com o **mesmo shape** de hoje;
frontend em `137.131.217.162` continua funcionando sem alteração; nenhum request
público chama o Fogo Cruzado (verificar logs).

### Fase 4 — Cache, performance, observabilidade
- [ ] Cache de agregações: 🪶 ponytail: `cache_page`/cache em **DB backend**
      (compartilhado entre workers), TTL curto. Upgrade → Redis.
- [ ] Confirmar índices cobrindo cada query analítica (`EXPLAIN`); sem seq scan
      em filtro de data/cidade/tipo.
- [ ] Métrica mínima: contadores no log por endpoint + duração; idade da ingestão
      exposta em `/health/`.
**Aceite:** `EXPLAIN` sem seq scan nas queries de dashboard; p95 do dashboard < 300ms.

### Fase 5 — Testes (exigência do contrato) + CI gate
- [ ] `pytest` + `pytest-django`. Mock do provedor (`responses`/`respx`) — **zero
      rede nos testes**.
- [ ] Teste para **cada transformação**: parse datetime tz, contagem de vítimas
      humanas, dedup/idempotência do upsert, cada agregação (day/week/month/bairro),
      validação de query params, contrato de erro (400/503).
- [ ] CI roda lint + mypy + testes; bloqueia merge se falhar.
**Aceite:** suíte verde no CI; cobertura das funções puras de `normalize` e `selectors`.

---

## 5. Modelo de dados (contrato explícito)

`Occurrence`: `external_id (UUID, unique)`, `occurred_at (tz-aware, index)`,
`location (PointField geography, GiST)`, `address`, `neighborhood`, `city (index)`,
`main_reason (index)`, `police_action (bool)`, `agent_presence (bool)`,
`fatalities (int)`, `injuries (int)`, `weight (float)`, `raw (JSONField)`,
`ingested_at`. Casualties = vítimas `type=='People'` com `situation` em
`Dead`/`Wounded`.

`IngestionRun`: `started_at`, `finished_at`, `status`, `fetched`, `created`,
`updated`, `error`.

🪶 ponytail: tabela `Victim` normalizada **adiada** — `raw` + contagens cobrem os
dashboards atuais; criar quando existir filtro por atributo de vítima.

---

## 6. Timezone (não-negociável)

- Persistir tudo **UTC tz-aware** (`USE_TZ=True`).
- Agrupar séries no fuso **America/Sao_Paulo** (`Trunc*(tzinfo=...)`), senão o
  "dia" fica errado para o usuário. Teste cobrindo virada de dia perto da meia-noite.

---

## 7. Segurança / config (não-negociável)

- Zero segredo hardcoded: `SECRET_KEY`, credenciais Fogo Cruzado e `DATABASE_URL`
  só via env. `DEBUG=False` em prod com `SECRET_KEY` obrigatório.
- Token do provedor em cache com expiração; renovar via `force_refresh` em 401.
- CORS por env (hoje `CORS_ALLOW_ALL_ORIGINS=True` — restringir ao domínio do front).

---

## 8. Cutover (sem downtime perceptível ao frontend)

1. Fases 0–2 não tocam os endpoints (frontend segue no proxy atual).
2. Fase 3 troca a implementação **mantendo o shape**; subir atrás de flag/env
   `READ_FROM_DB=true` para rollback rápido. 🪶 ponytail: 1 flag, não 2 code paths
   permanentes — remover o proxy depois que o DB provar estável.
3. Rodar a ingestão ao menos 1x antes de virar a flag (DB precisa ter dados).

---

## 9. Definition of Done — rastreabilidade do contrato (nada passa)

| Item do `backend-engineer.md` | Onde é satisfeito |
|---|---|
| Ingestão idempotente | F2 (upsert por `external_id`) + teste F5 |
| Isolamento da API externa | F2 (`client.py` sem models) |
| Contratos de dados explícitos | F1 (modelo) + F2 (DTO) + F3 (serializers) |
| Jobs de background auditáveis | F2 (`IngestionRun`) |
| Token seguro | F2 + F7 |
| Timezone correto | F1/F3/F6 + teste |
| Modelagem geoespacial | F1 (`PointField` + GiST) |
| Falhas observáveis | F0 (logging) + F2 (run status) + F3 (erros 4xx/5xx) |
| Testes p/ cada transformação | F5 |
| ❌ Lógica de negócio em view | F3 (`selectors`/`services`) |
| ❌ Frontend → provedor direto | já garantido (frontend usa só esta API) |
| ❌ Ingestão síncrona em request | F2 (job) + F3 (request só lê DB) |
| ❌ Falha silenciosa | F0/F2/F3 (sem `except: return []`) |
| ❌ Segredo hardcoded | F0/F7 |
| ❌ Lista sem paginação | F3 (DRF pagination) |
| ❌ Query analítica sem índice | F1 (índices) + F4 (`EXPLAIN`) |
| ❌ Registro externo duplicado | F1 (unique) + F2 (upsert) |
| ❌ Datetime naive | F1/F6 (`USE_TZ`, tz-aware) |
| ❌ Payload cru como único modelo | F1 (`raw` + colunas tipadas) |

---

## 10. Ledger ponytail (atalhos deliberados + gatilho)

- 🪶 Jobs por **cron + management command**, não Celery → upgrade quando precisar
  de retry/concorrência/agendamento-no-app.
- 🪶 Cache em **DB backend**, não Redis → upgrade quando medir lento/quente.
- 🪶 Vítimas como **contagem derivada + `raw`**, não tabela `Victim` → upgrade no
  primeiro filtro por atributo de vítima.
- 🪶 Settings: `os.environ` direto, split só se divergir → upgrade quando crescer.
- 🪶 Cutover por **1 flag** `READ_FROM_DB`, removida após estabilizar.

> Regra: todo atalho acima precisa de um comentário `# ponytail:` no código que o
> implementa, nomeando o teto e o caminho de upgrade. Não vira "depois = nunca".

---

## 11. Ordem recomendada de execução

F0 → F1 → F2 → (rodar ingestão) → F3 (atrás da flag) → F5 (testes acompanham
cada fase, não no fim) → F4 → remover proxy + flag. Cada fase entra num PR próprio,
verde no CI, sem quebrar o contrato de endpoints.
