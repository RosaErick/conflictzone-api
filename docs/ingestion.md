# Ingestão

Como os dados entram no banco. Esta é a parte com mais sutilezas — leia inteiro
antes de mexer.

## O comando

```sh
python manage.py sync_occurrences [--initial-date YYYY-MM-DD] [--final-date YYYY-MM-DD] [--days N]
```

Dois modos, decididos pela presença de `--initial-date`:

| Modo | Como dispara | Janela |
|---|---|---|
| **Incremental** | sem `--initial-date` | últimos `N` dias (default `INGESTION_DEFAULT_DAYS=3`) até agora |
| **Backfill** | com `--initial-date`/`--final-date` | exatamente a janela informada |

O cron de produção usa o modo **incremental** (sem args). O **backfill** é manual,
fatiado por ano (ver abaixo).

## A lógica de tempo (o que você perguntou)

- O `sync_occurrences` **não tem estado**: não guarda "até onde já sincronizei".
  Cada execução re-busca a janela e re-faz upsert. Como o upsert é **idempotente**
  (chave `external_id`), re-buscar a sobreposição é inofensivo.
- As datas vão **direto** como `initialdate`/`finaldate` para a API da Fogo
  Cruzado. `--final-date` omitido = aberto até agora.
- **Por que janela fixa em vez de cursor incremental?** Decisão ponytail: no
  volume do RJ (<100k linhas no total), re-buscar os últimos 3 dias toda hora é
  mais simples e robusto (cobre correções/atrasos da fonte) do que manter e
  versionar um cursor de "última data sincronizada". Ver
  [decisions.md](decisions.md#adr-007). Gatilho de upgrade: se a janela recente
  ficar cara (muitos dados/dia), passar a guardar o último `occurred_at`.

## Paginação e o teto de 50k

`client.py` pagina a API:
- `PER_PAGE = 1000` registros por requisição (rápido o suficiente p/ evitar 502).
- `MAX_PAGES = 50` → teto de **50.000 registros por execução**.
- Segue `pageMeta.hasNextPage` até acabar ou bater no teto.

**Implicação:** uma execução não pode trazer mais de 50k. Por isso o backfill
histórico é **fatiado por ano** — cada ano do RJ cabe folgado abaixo de 50k.

## Backfill histórico (a partir de 2020)

```sh
for y in 2020 2021 2022 2023 2024 2025; do
  docker compose run --rm web python manage.py sync_occurrences \
    --initial-date $y-01-01 --final-date $y-12-31
done
```

Rodar duas vezes não duplica: a segunda passada marca tudo como `updated`.

## Cron incremental (produção)

```cron
0 * * * * cd /caminho/do/projeto && /usr/bin/docker compose run --rm web \
  python manage.py sync_occurrences >> /var/log/cz-ingest.log 2>&1
```

Sem args → últimos 3 dias. Idempotente, então rodar de hora em hora só atualiza.

## Idempotência

`ingest.upsert_occurrence()` usa `Occurrence.objects.update_or_create(external_id=...)`.
A constraint `unique` em `external_id` (nível de banco) garante que **nunca** há
registro externo duplicado, mesmo com execuções concorrentes. Retorna `True` se
criou, `False` se atualizou — é o que alimenta as contagens do `IngestionRun`.

## Isolamento da API externa

- `client.py`: **só** fala HTTP. Nenhum import de models/Django ORM. Faz login,
  cacheia o token em memória pela duração do run e renova uma vez em caso de 401.
- `normalize.py`: **funções puras**, sem Django. Por isso são testáveis sem
  banco, sem GDAL e sem rede (ver [`api/tests/test_normalize.py`](../api/tests/test_normalize.py)).
- `ingest.py` é o **único** ponto que liga as duas coisas ao ORM.

Esse isolamento é o que permite testar cada transformação e trocar o provedor
sem tocar no resto.

## Falha parcial (nunca silenciosa)

Se uma página falhar no meio da paginação:
- O que já foi gravado **permanece** (não descarta o run inteiro).
- O `IngestionRun` é marcado `partial` (ou `failed` se nada foi obtido) com a
  mensagem de erro.
- Nada de `except: return []` mascarando o problema.

## Auditoria (`IngestionRun`)

Cada execução grava: `started_at`, `finished_at`, `status`
(`success`/`partial`/`failed`), `fetched`, `created`, `updated`, `error`.
Visível em `/admin/` e resumido em `/health/` (idade da última ingestão).
A API responde **503** se a última ingestão estiver mais velha que
`INGESTION_MAX_AGE_HOURS` (default 6h) — falha honesta em vez de dados velhos.

## Variáveis de ambiente relevantes

| Env | Default | Efeito |
|---|---|---|
| `FOGO_CRUZADO_EMAIL` / `_PASSWORD` | — | credenciais do provedor |
| `FOGO_CRUZADO_STATE_ID` | UUID do RJ | estado ingerido (restringe ao RJ) |
| `INGESTION_DEFAULT_DAYS` | `3` | janela do modo incremental |
| `INGESTION_MAX_AGE_HOURS` | `6` | idade máxima antes de `/health` e endpoints reportarem 503 |
