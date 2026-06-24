# ConflictZone API — Documentação

Camada de **ingestão + persistência + analytics** sobre os dados de violência
armada da [Fogo Cruzado](https://fogocruzado.org.br/), restrita ao **Rio de
Janeiro**. A API não é mais um proxy: ela lê de um PostgreSQL+PostGIS próprio,
populado por um job idempotente e auditável.

> **Para agentes de IA:** comece por [`agents.md`](agents.md) — convenções,
> doutrina ponytail, como rodar/testar e armadilhas conhecidas. Depois leia o
> doc relevante à sua tarefa abaixo.

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
| [agents.md](agents.md) | Guia para agentes/devs que vão continuar o projeto |
| [reference/](reference/) | Fontes originais: contrato de engenharia e o plano de implementação |

## Princípios (não-negociáveis)

Confiabilidade > esperteza · ingestão idempotente · isolamento da API externa ·
contratos de dados explícitos · jobs auditáveis · timezone correto · modelagem
geoespacial · falhas observáveis · testes para cada transformação. Detalhes em
[reference/backend-engineer-contract.md](reference/backend-engineer-contract.md).

## Restrição de custo

O projeto roda **100% em free tier** (Oracle Cloud Always Free, sem DB
gerenciado/cobrado). Toda decisão respeita "R$0 de custo recorrente". Ver
[decisions.md](decisions.md).
