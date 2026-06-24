# Modelo de dados

Definido em [`api/models.py`](../api/models.py). Migrations em
[`api/migrations/`](../api/migrations/).

## `Occurrence`

Contrato explícito e tipado — **não** o payload cru. O JSON original fica em
`raw` para auditoria/reprocessamento.

| Campo | Tipo | Notas |
|---|---|---|
| `external_id` | `UUIDField(unique=True)` | UUID do provedor; **chave de dedup** |
| `occurred_at` | `DateTimeField(db_index=True)` | tz-aware (UTC); indexado |
| `location` | `PointField(geography=True, srid=4326)` | PostGIS; índice **GiST** automático |
| `address` | `TextField` | endereço |
| `neighborhood` | `CharField(255)` | bairro (indexado) |
| `city` | `CharField(255)` | cidade (indexado) |
| `main_reason` | `CharField(255)` | tipo da ocorrência (indexado) |
| `police_action` | `BooleanField` | |
| `agent_presence` | `BooleanField` | |
| `fatalities` | `PositiveIntegerField` | mortos **humanos** (`type=='People'`, `situation=='Dead'`) |
| `injuries` | `PositiveIntegerField` | feridos **humanos** (`situation=='Wounded'`) |
| `weight` | `FloatField` | score de severidade (heurística) |
| `raw` | `JSONField` | payload original completo |
| `ingested_at` | `DateTimeField(auto_now=True)` | quando foi gravado |

Propriedade `police_present` = `police_action or agent_presence` (usada na
serialização, não é coluna).

### Vítimas: contagem derivada, sem tabela `Victim`

Decisão ponytail: guardamos as **contagens** (`fatalities`/`injuries`) + o `raw`,
em vez de uma tabela `Victim` normalizada. Cobre todos os dashboards atuais.
**Gatilho de upgrade:** criar `Victim` no primeiro filtro por atributo de vítima
(idade, raça, sexo). Ver [decisions.md](decisions.md#adr-005).

## `IngestionRun`

Auditoria de cada execução do job. Ver [ingestion.md](ingestion.md#auditoria-ingestionrun).

| Campo | Tipo |
|---|---|
| `started_at` / `finished_at` | `DateTimeField` |
| `status` | `success` / `partial` / `failed` |
| `fetched` / `created` / `updated` | `PositiveIntegerField` |
| `error` | `TextField` |

## Índices

Confirmados no banco (`\d api_occurrence`):

```
gist  (location)          -- consultas geográficas (raio, bbox, clustering)
btree (occurred_at)       -- filtros e séries por data
btree (city)              -- breakdown/filtro por cidade
btree (main_reason)       -- filtro por tipo
btree (neighborhood)      -- breakdown/filtro por bairro
unique(external_id)       -- dedup idempotente
```

> Verificar "sem seq scan" em `EXPLAIN` só faz sentido **com volume**: em tabela
> pequena o planner do Postgres prefere seq scan de propósito. Os índices existem
> desde a modelagem; a verificação com `EXPLAIN` é uma tarefa de escala.

## Timezone (não-negociável)

- `USE_TZ=True`; tudo persistido em **UTC tz-aware**.
- Séries (dia/semana/mês) são agrupadas em **America/Sao_Paulo**
  (`Trunc*(tzinfo=...)` em `selectors.py`), senão a "virada de dia" sai errada.
- Coberto por teste: `api/tests/test_selectors.py::TimeseriesTzTests`.

## PostGIS

A primeira migration (`0001_enable_postgis`) roda `CREATE EXTENSION postgis`
antes de qualquer coluna geométrica. O `location` é `geography` (distâncias em
metros). Recursos disponíveis sem custo extra (é CPU da VM, não cobrança):
clustering server-side (`ST_ClusterDBSCAN`), grid de heatmap (`ST_SnapToGrid`),
vector tiles (`ST_AsMVT`). Ver ideias em [roadmap.md](roadmap.md).
