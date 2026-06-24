# CLAUDE.md — instruções para agentes neste repositório

ConflictZone API: camada de **ingestão + persistência + analytics** sobre os
dados da Fogo Cruzado (escopo: Rio de Janeiro). Django + DRF + PostgreSQL/PostGIS,
rodando 100% em free tier. A API **lê do banco** (nunca chama o provedor no
request); a ingestão roda em background.

## 📌 Política de documentação (OBRIGATÓRIA)

**Atualizar a documentação faz parte de toda tarefa que mexe neste repo.** Um PR
que muda comportamento e não atualiza os docs está incompleto. Antes de concluir:

- Mudou **endpoint / parâmetro / contrato de resposta** → atualize `docs/api.md`.
- Mudou **modelo / índice / migration** → atualize `docs/data-model.md`.
- Mudou **ingestão** (job, agendamento, lógica de tempo) → `docs/ingestion.md`.
- Mudou **deploy / infra / env** → `docs/deployment.md`.
- Tomou uma **decisão de arquitetura / trade-off** → adicione um ADR em
  `docs/decisions.md`.
- Concluiu ou adiou algo → reflita em `docs/roadmap.md` (feito / não feito /
  atalho com gatilho).

Mantenha o índice `docs/README.md` coerente. Docs desatualizados = bug.

## Como trabalhar aqui

- **Doutrina ponytail:** a solução mais simples que satisfaz o contrato; atalhos
  deliberados levam comentário `# ponytail:` com o teto e o caminho de upgrade.
- **Custo R$0 recorrente** é restrição dura — nada de serviço pago/managed.
- **Camadas:** `client.py` (só HTTP) → `normalize.py` (puro, sem Django) →
  `ingest.py` (único ponto que toca o ORM) → `selectors.py` (query/agregação) →
  views finas. Sem lógica de negócio em view; sem `print` (use `logging`).
- **Testes** para cada transformação em `api/tests/` (sem rede).

## Mensagens de commit e PR

Diretas, concisas, explícitas. Dizem **o que** foi feito e **onde** mudou; o
**porquê** só quando não for óbvio. Nada além disso — o histórico é público.

- Assunto: `<área>: <o que foi feito>` — imperativo, conciso, sem ponto final
  (ex.: `api: add bbox filter to /occurrences/`).
- Corpo (se necessário): bullets diretos do que mudou e onde. **Sem** narrativa,
  contexto de conversa, status ("pronto para…", "para um novo agente") ou tom.
- **Nunca vaze**: referências a arquivos locais/gitignored, planos internos,
  nomes de agentes, `.env`, dumps — nada que não seja a própria mudança.
- Sem trailer `Co-Authored-By`. Não commitar `.env` nem `*.dump`.

## Orientação

Comece por `docs/README.md` (índice). Detalhes operacionais e armadilhas
conhecidas em `docs/agents.md` (se presente localmente — é gitignored).
