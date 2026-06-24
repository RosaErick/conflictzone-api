# Decisões de arquitetura (ADRs)

Cada decisão importante, com o **contexto**, a **escolha** e o **gatilho** que a
reverteria. Doutrina: ponytail (a solução mais simples que satisfaz o contrato)
+ custo recorrente **R$0**.

---

## ADR-001 — Banco: PostgreSQL+PostGIS self-hosted na Oracle Always Free

**Contexto.** Restrição absoluta: não pagar por DB. Medo inicial de "cobrança por
uso de banco".

**Análise.** Não há DB gerenciado: o Postgres roda como **container na VM Oracle
Always Free**, gravando num disco que já é grátis. Logo, **não existe cobrança por
uso** — só o teto da VM. Conta de volume (RJ): ~3–10k ocorrências/ano × ~9 anos
≈ **<100k linhas**; o peso é a coluna `raw` (~2–4 KB/linha) → **~0,5 GB total**.
Boot volume de 47 GB e até 24 GB de RAM (A1.Flex) → storage usa ~1%.

**Decisão.** Manter Postgres+PostGIS self-hosted na A1.Flex Always Free.

**Riscos reais (não são custo):** (1) Oracle pode reclamar instância ociosa; (2)
backup é por sua conta — resolver com `pg_dump` → Object Storage grátis; (3) RAM
se a shape for pequena. **Gatilho de fuga:** só sair p/ managed (Supabase/Neon
free, ambos com PostGIS mas teto ~500 MB e auto-pause) se a VM virar problema.

> ⚠️ Shapes pagas (VM.Standard2.x, E2.x não-micro, E3.Flex) **não** são free. As
> Always Free são **VM.Standard.A1.Flex** (ARM, até 4 OCPU/24 GB) e
> **E2.1.Micro** (1 GB). Confirme o selo "Always Free-eligible".

---

## ADR-002 — Escopo: só Rio de Janeiro

**Contexto.** A Fogo Cruzado cobre vários estados; isso multiplica volume.

**Decisão.** Ingerir só o RJ (`FOGO_CRUZADO_STATE_ID`). Mantém o volume em <100k
linhas e simplifica tudo. **Gatilho:** adicionar estados quando houver demanda —
basta tornar o estado um parâmetro do job (já é env).

---

## ADR-003 — Jobs: cron do SO + management command, não Celery/Redis

**Contexto.** O contrato pede "jobs de background auditáveis". Celery+Redis seria
o padrão "enterprise".

**Decisão.** `management command` + cron do SO, auditado em `IngestionRun`. Zero
dependência nova, zero serviço extra consumindo RAM.

**Gatilho de upgrade:** retry automático, concorrência ou agendamento gerenciado
dentro do app → Celery beat (+ Redis).

---

## ADR-004 — Cache de agregações: adiado (YAGNI)

**Contexto.** O plano previa cache em DB-backend (e Redis depois).

**Decisão.** **Não cachear ainda.** O contrato não exige cache; as agregações são
indexadas e respondem em ~8 ms neste volume. Cache de 60 s introduz staleness por
ganho marginal.

**Gatilho:** quando um profiler mostrar agregação quente → cache em DB-backend
(compartilhado entre workers) → Redis (Upstash free) se medir lento.

---

## ADR-005 — Vítimas: contagem derivada, sem tabela `Victim`

**Decisão.** Guardar `fatalities`/`injuries` + `raw`, em vez de normalizar
`Victim`. Cobre os dashboards atuais. **Gatilho:** primeiro filtro por atributo
de vítima (idade/raça/sexo) → criar a tabela `Victim` (o `raw` permite
reprocessar o histórico).

---

## ADR-006 — Cutover sem flag `READ_FROM_DB`

**Contexto.** O plano sugeria uma flag para rollback ao proxy.

**Decisão.** **Sem flag.** O proxy foi removido por inteiro; manter uma flag
exigiria preservar dois code paths permanentes — exatamente a complexidade que o
plano e o ponytail evitam. O cutover foi validado ponta a ponta. **Gatilho:** se
um rollback rápido virar requisito, reintroduzir o proxy atrás de flag — mas a
aposta é que o caminho de DB é estável.

---

## ADR-007 — Ingestão: janela fixa recente, não cursor incremental

**Contexto.** Manter o banco atualizado sem re-varrer tudo toda hora.

**Decisão.** O cron incremental busca os **últimos 3 dias** (`INGESTION_DEFAULT_DAYS`)
e faz upsert idempotente. Sem guardar "última data sincronizada".

**Porquê.** No volume do RJ, re-buscar 3 dias é trivial e cobre correções/atrasos
da fonte. Um cursor seria mais código e mais estado para versionar.
**Gatilho:** se a janela recente ficar cara (muitos dados/dia) → guardar o último
`occurred_at` e buscar a partir dele.

---

## ADR-008 — Reset de migrations (SQLite → PostGIS)

**Contexto.** As migrations antigas eram do modelo SQLite, e o `Occurrence` nem
era persistido em produção (era proxy).

**Decisão.** Apagar as migrations 0001–0007 e gerar `0001_enable_postgis` +
`0002_initial`. Sem dados de produção a preservar, é o caminho limpo.

---

## ADR-009 — Contagem só de vítimas humanas (correção de bug)

**Contexto.** O código antigo contava **todas** as vítimas, incluindo animais,
como mortos/feridos.

**Decisão.** Contar só `type == 'People'`. Corrige uma superestimativa real de
casualidades. Coberto por teste (`test_normalize.py::VictimCountTests`).
