# API

Views em [`api/views.py`](../api/views.py) (finas), query em
[`api/selectors.py`](../api/selectors.py), validação/contrato em
[`api/serializers.py`](../api/serializers.py). Docs OpenAPI em `/documentation/`.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health/` | status + idade da última ingestão |
| GET | `/health/fogo-cruzado/` | probe do provedor externo (operacional) |
| GET | `/occurrences/` | lista paginada de ocorrências |
| GET | `/occurrences/stats/` | totais agregados |
| GET | `/occurrences/monthly/` | série mensal (alias de `timeseries?granularity=month`) |
| GET | `/occurrences/timeseries/` | série por `day`/`week`/`month` |
| GET | `/occurrences/by-city/` | breakdown por cidade |
| GET | `/occurrences/filters/` | tipos/cidades disponíveis para dropdowns |

## Parâmetros de filtro (validados na fronteira)

`initialdate`, `finaldate` (YYYY-MM-DD) · `type` (repetível, multi-select) ·
`mainReason` · `city` · `policePresent` (bool) · `victimStatus`
(`fatalities`/`injuries`/`none`/`all`). Paginação: `page`, `take` (máx 5000).

Input inválido → **400** com os erros do serializer (nunca ignorado em silêncio).

## Contrato de resposta (mantido idêntico ao frontend antigo)

`/occurrences/` devolve cada item com exatamente estes campos:

```json
{ "id", "lat", "lng", "address", "date", "type",
  "fatalities", "injuries", "policePresent", "neighborhood", "city", "weight" }
```

`lat`/`lng` vêm de `location` (PostGIS Point). `id` = `external_id`.
`date` = `occurred_at`. `type` = `main_reason`.

## Semântica de erro (falhas honestas)

| Código | Quando |
|---|---|
| **400** | parâmetro inválido (data malformada, range invertido, `take` acima do máx, granularity inválida) |
| **503** | sem ingestão bem-sucedida ainda, **ou** última ingestão mais velha que `INGESTION_MAX_AGE_HOURS` |
| **200** | dados frescos |

> Nunca devolvemos lista vazia para mascarar pipeline quebrado. Antes do primeiro
> backfill, os endpoints de dados respondem **503** de propósito.

## Paginação

`/occurrences/` é **sempre** paginado (LIMIT/OFFSET em SQL), `take` com teto rígido
de 5000. Formato preservado do contrato:

```json
{ "data": [ ... ], "pagination": { "page", "take", "total", "pages" } }
```

## Observabilidade

`api/middleware.py` loga cada request: `GET /occurrences/stats/ -> 200 8.1ms`.
`/health/` expõe a idade da última ingestão.
