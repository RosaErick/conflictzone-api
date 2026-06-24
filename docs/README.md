# ConflictZone API — Documentação

Camada de **ingestão + persistência + analytics** sobre os dados de violência
armada da [Fogo Cruzado](https://fogocruzado.org.br/), restrita ao **Rio de
Janeiro**. A API não é mais um proxy: ela lê de um PostgreSQL+PostGIS próprio,
populado por um job idempotente e auditável.

> **Para agentes de IA:** as regras obrigatórias estão no [`CLAUDE.md`](../CLAUDE.md)
> da raiz (carregado automaticamente). Convenções e armadilhas detalhadas estão em
> `agents.md` (local/gitignored, se presente). Depois leia o doc relevante abaixo.

> **📌 Política de documentação (obrigatória):** atualizar os docs faz parte de
> toda tarefa que mexe neste repo — mudou comportamento, atualize o doc
> correspondente (ver mapa abaixo). Doc desatualizado conta como bug. Detalhe em
> [`CLAUDE.md`](../CLAUDE.md).

## Mapa da documentação

| Doc | Para quê |
|---|---|
| [overview.md](overview.md) | O que é o app, arquitetura, fluxo de dados, stack |
| [ingestion.md](ingestion.md) | Como a ingestão funciona: tempo, backfill, incremental, idempotência, auditoria |
| [data-model.md](data-model.md) | Modelos, PostGIS, índices, timezone |
| [api.md](api.md) | Endpoints, contratos de resposta, erros (400/503), paginação |
| [deployment.md](deployment.md) | Deploy na Oracle Cloud (free tier) + Postgres + cron |
| [decisions.md](decisions.md) | Decisões de arquitetura (ADRs) e questões debatidas, com o porquê |
| [roadmap.md](roadmap.md) | O que foi feito, o que não foi, e os atalhos deliberados com gatilho |
| `agents.md` | Guia detalhado para agentes (local/gitignored — regras obrigatórias no `CLAUDE.md`) |
| `reference/` | Fontes originais: contrato de engenharia e plano (local/gitignored) |

## Princípios (não-negociáveis)

Confiabilidade > esperteza · ingestão idempotente · isolamento da API externa ·
contratos de dados explícitos · jobs auditáveis · timezone correto · modelagem
geoespacial · falhas observáveis · testes para cada transformação. Detalhes em
[reference/backend-engineer-contract.md](reference/backend-engineer-contract.md).

## Restrição de custo

O projeto roda **100% em free tier** (Oracle Cloud Always Free, sem DB
gerenciado/cobrado). Toda decisão respeita "R$0 de custo recorrente". Ver
[decisions.md](decisions.md).
