# Engineering handbook

O *porquê* e o *como* por trás das regras do [`CLAUDE.md`](../CLAUDE.md) (que é o
resumo vinculante). Aqui mora o detalhe; os docs por área
([api](api.md) · [data-model](data-model.md) · [ingestion](ingestion.md) ·
[deployment](deployment.md)) têm o resto — **linke, não duplique**.

## Protocolo de mudança

1. **Entenda antes de escrever.** Trace o fluxo end-to-end e leia os arquivos que
   a mudança toca. A doutrina ponytail encurta a *solução*, nunca a *leitura*.
2. **Causa-raiz, não sintoma.** Um bug nomeia um sintoma; antes de editar, faça
   `grep` nos callers da função e conserte uma vez onde todos passam.
3. **Menor diff que resolve** — depois de entender o problema. Diff pequeno no
   lugar errado é um segundo bug.
4. **Um concern por PR.** PR pequeno, revisável, com a doc da mudança junto.

## Invariantes (porquê + como verificar)

1. **Request lê do banco.** O proxy síncrono foi removido de propósito (lento,
   refém do provedor). Verificar: os endpoints usam `selectors`, não o `client`;
   nenhum import de `services.fogo_cruzado` nas views.
2. **Datetime tz-aware UTC; séries em America/Sao_Paulo.** `USE_TZ=True`; agrupar
   com `Trunc*(tzinfo=LOCAL_TZ)`. Verificar: teste de virada de dia perto da
   meia-noite (`test_selectors.py::TimeseriesTzTests`).
3. **Ingestão idempotente.** Upsert por `external_id` (constraint `unique`).
   Verificar: rodar `sync_occurrences` 2× não duplica (`created=0` na 2ª).
4. **Lista sempre paginada.** Teto rígido em `PaginationQuerySerializer` (`take`
   máx). Verificar: `take` acima do máx → 400.
5. **Query analítica indexada.** Índices btree/GiST no modelo. Verificar:
   `EXPLAIN ANALYZE` sem seq scan em volume nos filtros de data/cidade/tipo/bbox.
6. **Falha honesta.** 400 para input inválido (serializer), 503 quando a ingestão
   está ausente/defasada (`_stale_response`). Nunca `except: return []`.
7. **Isolamento de camadas.** `client.py` só fala HTTP; `normalize.py` é puro (sem
   Django) — por isso roda em teste local sem GDAL. `ingest.py` é o único elo com
   o ORM.

## Padrão de testes

- **Cada transformação não-trivial tem teste** em `api/tests/` (parser, contagem,
  agregação, dedup, contrato de erro).
- **Sem rede.** Provedor é mockado/fake (`FakeClient`); nada de HTTP real.
- **Funções puras** (`normalize`) rodam no venv local; **geo/DB** rodam em
  docker/CI (PostGIS + GDAL). Use `TestCase`/`SimpleTestCase` (rodam no runner do
  Django e no pytest).
- Cobrir o **contrato de erro** (400/503), não só o caminho feliz.

## Checklist de segurança

- **Segredos só por env** — nunca em código, commit, log ou corpo de PR.
  `SECRET_KEY` obrigatória com `DEBUG=False`.
- **SQL cru SEMPRE parametrizado** — nunca interpolar entrada do usuário (ex.:
  `selectors.density_grid` passa `cell`/bbox como parâmetro, não por f-string).
- **Não logar PII** nem despejar o `raw` em resposta/log.
- **CORS por env** (`CORS_ALLOWED_ORIGINS`); aberto só em dev.
- **Validar input na fronteira** — serializers de query param antes de qualquer
  query; rejeitar (400), não adivinhar.

## Glossário de domínio

- **`external_id`** — UUID do provedor; chave de deduplicação da ingestão.
- **`occurred_at`** — quando a ocorrência aconteceu, UTC tz-aware (indexado).
- **`situation`** (da vítima) — `Dead` / `Wounded` / … **×** **`type`** —
  `People` / `Animals`. **Casualidade humana = só `type == 'People'`** (o código
  antigo contava animais — bug corrigido).
- **`main_reason`** — tipo da ocorrência (`contextInfo.mainReason.name`).
- **`weight`** — score heurístico de severidade.
- **`IngestionRun`** — auditoria de cada execução do job (status
  `success`/`partial`/`failed`, `fetched`/`created`/`updated`, `error`).
- **`location`** — `PointField` geography (SRID 4326) com índice **GiST**.
- **`LOCAL_TZ`** — `America/Sao_Paulo`, usado só para bucketizar séries.
