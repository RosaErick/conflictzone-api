# Guia para agentes (e devs novos)

Leia isto antes de tocar no código. Depois vá ao doc da sua tarefa pelo
[índice](README.md).

## Doutrina

- **ponytail**: a solução mais simples que satisfaz o contrato. Antes de
  adicionar dep/abstração, suba a escada: já existe? stdlib? feature nativa? dep
  já instalada? uma linha? Atalhos deliberados levam comentário `# ponytail:`
  nomeando o teto e o caminho de upgrade. Ver [decisions.md](decisions.md).
- **Contrato é lei**: os não-negociáveis e proibidos em
  [reference/backend-engineer-contract.md](reference/backend-engineer-contract.md)
  decidem *se*; o ponytail decide *como*.
- **Custo R$0 recorrente** é uma restrição dura. Nada de serviço pago/managed.

## Convenções deste repo

- **Camadas**: `client.py` (só HTTP, sem ORM) → `normalize.py` (puro, sem Django)
  → `ingest.py` (único ponto que toca o ORM) → `selectors.py` (query/agregação) →
  `views.py` (finas: validam e chamam selectors). Não misture.
- **Sem `print`**: use `logging`.
- **Sem lógica de negócio em view**: vai para `selectors.py`/`services/`.
- **Toda transformação não-trivial tem teste** em `api/tests/` (sem rede).
- **`normalize.py` é puro de propósito** — não importe Django lá, senão quebra a
  testabilidade local sem GDAL.

## Ambiente: o que roda onde

| Onde | O quê |
|---|---|
| **venv local** | só funções puras (`python api/services/fogo_cruzado/normalize.py`), ruff. **Não tem GDAL/Postgres** — GeoDjango e DB **não** rodam local. |
| **Docker Compose** | tudo que toca DB/GeoDjango: migrate, sync, testes, endpoints. |

## Comandos

```sh
# Lint (local)
./venv/bin/ruff check .

# Subir a stack
docker compose up -d --build

# Testes (runner do Django; a imagem tem GDAL+DB, mas não pytest)
docker compose run --rm -v "$PWD":/app --entrypoint python web manage.py test api

# Ingestão incremental (últimos 3 dias)
docker compose run --rm web python manage.py sync_occurrences

# Backfill de um ano
docker compose run --rm web python manage.py sync_occurrences \
  --initial-date 2020-01-01 --final-date 2020-12-31
```

> Na **CI** (GitHub Actions) os testes rodam com **pytest** + serviço PostGIS;
> os testes são `TestCase`/`SimpleTestCase`, então rodam nos dois runners.

## Armadilhas conhecidas (já custaram tempo)

1. **A imagem `web` "congela" o código no build.** Para rodar código novo num
   one-off sem rebuildar, monte o projeto: `-v "$PWD":/app`. Para valer no
   container que serve HTTP, **rebuilde** (`docker compose up -d --build`).
2. **`makemigrations` precisa de GDAL** (por causa do `PointField`) → gere dentro
   da imagem, montando o projeto para o arquivo cair no host:
   `docker run --rm -v "$PWD":/app --entrypoint python web manage.py makemigrations api`.
   Não precisa de DB para gerar; precisa para aplicar.
3. **A extensão PostGIS** é criada por `0001_enable_postgis` (`CREATE EXTENSION`)
   **antes** das tabelas. Não reordene migrations.
4. **Comandos de management rodam system checks** → carregam URLs/views. Se as
   views estiverem quebradas, até `sync_occurrences` falha.
5. **Antes do primeiro backfill, endpoints de dados dão 503** de propósito (falha
   honesta). Rode a ingestão para popular.
6. **Timezone**: persistir UTC; agrupar séries em `America/Sao_Paulo`. Não use
   `__date` ingênuo — ver `selectors.filtered_occurrences` (range half-open local).

## Git / commits

- O dono pediu para **não** incluir trailers `Co-Authored-By` nos commits.
- Não commitar `.env` (tem credenciais reais; está no `.gitignore`).
- Trabalho desta refatoração está na branch `feat/ingestion-analytics-rewrite`.

## Estado atual

Ver [roadmap.md](roadmap.md) para o que está feito, o que falta e os atalhos com
gatilho. Pendência nº1 antes de "produção": **backup automatizado**.
