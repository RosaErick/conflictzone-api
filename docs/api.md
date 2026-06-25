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
| GET | `/occurrences/density/` | grid de densidade (PostGIS) em GeoJSON — fonte do heatmap |
| GET | `/occurrences/stats/` | totais agregados |
| GET | `/occurrences/monthly/` | série mensal (alias de `timeseries?granularity=month`) |
| GET | `/occurrences/timeseries/` | série por `day`/`week`/`month` |
| GET | `/occurrences/by-city/` | breakdown por cidade |
| GET | `/occurrences/by-neighborhood/` | breakdown por bairro (mesmo shape do by-city) |
| GET | `/occurrences/filters/` | tipos/cidades disponíveis para dropdowns |

## Parâmetros de filtro (validados na fronteira)

`initialdate`, `finaldate` (YYYY-MM-DD) · `type` (repetível, multi-select) ·
`mainReason` · `city` · `policePresent` (bool) · `victimStatus`
(`fatalities`/`injuries`/`none`/`all`) · `bbox`. Paginação: `page`, `take` (máx 5000).

`bbox=minLng,minLat,maxLng,maxLat` recorta pela **viewport** do mapa (4 floats;
`minLng<maxLng`, `minLat<maxLat`, ranges válidos). Usa o índice **GiST** de
`location` (`location__intersects`). Vale para todos os endpoints de ocorrência.

Input inválido → **400** com os erros do serializer (nunca ignorado em silêncio).

## `GET /occurrences/density/`

Agrega os pontos num **grid quadrado** (`ST_SnapToGrid`, PostGIS puro) e devolve
um GeoJSON `FeatureCollection` de pontos-centro de célula com `properties.count`
— pronto pro peso (`weight`) de um heatmap MapLibre. Pensado pra zoom baixo:
agrega tudo num payload pequeno em vez de baixar todos os pontos.

Aceita os filtros comuns + `bbox` (recorta a área) + `cell` (lado da célula em
graus; default `0.005` ≈ 500 m; limitado a `0.001`–`0.05`). Mesma semântica de
erro (400/503) dos demais.

```json
{ "type": "FeatureCollection",
  "features": [ { "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [-43.2575, -22.8925] },
    "properties": { "count": 42 } } ] }
```

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
| **400** | parâmetro inválido (data malformada, range invertido, `take` acima do máx, granularity inválida, `bbox`/`cell` fora do contrato) |
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
