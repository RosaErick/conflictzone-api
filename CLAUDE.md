# CLAUDE.md — instruções para agentes neste repositório

ConflictZone API: camada de **ingestão + persistência + analytics** sobre os
dados da Fogo Cruzado (escopo: Rio de Janeiro). Django + DRF + PostgreSQL/PostGIS,
100% free tier. A API **lê do banco** (nunca chama o provedor no request); a
ingestão roda em background.

> Resumo vinculante. O *porquê*, o detalhe e o glossário estão em
> [`docs/engineering.md`](docs/engineering.md). Comece pelo índice
> [`docs/README.md`](docs/README.md).

## Invariantes (nunca quebre)

1. Request público **lê do banco** — nunca chama o provedor externo.
2. Datetime **tz-aware UTC**; séries agregadas em `America/Sao_Paulo`.
3. Ingestão **idempotente** (upsert por `external_id`).
4. Endpoint de lista **sempre paginado** (sem lista ilimitada).
5. Query analítica **sobre coluna indexada** (sem seq scan em volume).
6. **Falha honesta** (400 input inválido / 503 dado ausente/defasado); nunca `[]`
   mascarando erro.
7. **Isolamento de camadas**: `client.py`/`normalize.py` não importam o ORM.

## Definition of Done (antes de "pronto")

- [ ] Testes verdes (`manage.py test api`; pytest na CI).
- [ ] `ruff check .` limpo.
- [ ] Docs atualizados (ver política abaixo).
- [ ] Migration criada se mudou modelo.
- [ ] Contrato de endpoint preservado (ou versionado de propósito).
- [ ] Nenhum segredo em código, commit ou log.
- [ ] PR pequeno, um concern só.

## Pare e pergunte (não decida sozinho)

Deleção/irreversível (`down -v`, `DROP`, prune de volume) · mudar contrato público
de endpoint · adicionar dependência nova ou serviço pago · migration destrutiva ·
expor/rotacionar segredo.

## Como trabalhar

- **Ponytail:** a solução mais simples que satisfaz o contrato; atalhos deliberados
  levam comentário `# ponytail:` com o teto e o caminho de upgrade.
- **Custo R$0 recorrente** é restrição dura — nada pago/managed.
- **Camadas:** `client.py` (só HTTP) → `normalize.py` (puro, sem Django) →
  `ingest.py` (único que toca o ORM) → `selectors.py` (query) → views finas.
  Sem lógica de negócio em view; sem `print` (use `logging`).

## Mensagens de commit e PR

Diretas: **o que** foi feito e **onde** mudou; o **porquê** só quando não óbvio.
O histórico é público.

- Idioma: **português**.
- Assunto: `<área>: <o que foi feito>` — imperativo, conciso, sem ponto final
  (ex.: `api: adiciona filtro bbox em /occurrences/`).
- Corpo (se preciso): bullets do que/onde mudou. **Sem** narrativa, contexto de
  conversa, status ("pronto para…", "para um novo agente") ou tom.
- **Nunca vaze**: arquivos locais/gitignored, planos internos, nomes de agentes,
  `.env`, dumps. Sem trailer `Co-Authored-By`.

## Política de documentação (OBRIGATÓRIA)

Atualizar os docs faz parte de toda tarefa. Doc desatualizado = bug.

- Endpoint/parâmetro/contrato → `docs/api.md`
- Modelo/índice/migration → `docs/data-model.md`
- Ingestão (job/agendamento/tempo) → `docs/ingestion.md`
- Deploy/infra/env → `docs/deployment.md`
- Decisão de arquitetura → ADR em `docs/decisions.md`
- Concluiu/adiou algo → `docs/roadmap.md`

Mantenha `docs/README.md` coerente. Detalhes operacionais e armadilhas locais em
`docs/agents.md` (gitignored, se presente).
