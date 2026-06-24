# Deploy — Oracle Cloud Always Free + Docker Compose

Roda a API ConflictZone num VM **Always Free** da Oracle, com `gunicorn` atrás de
`nginx`, orquestrado por Docker Compose. Custo: **R$ 0**. Ambiente persistente
(sem cold start, cache em memória funciona).

> Stack: `nginx` (porta 80) → `gunicorn` (porta 8000) → Django → **PostgreSQL +
> PostGIS** (serviço `db` no compose, dados num volume nomeado `pg_data`). A API
> lê **do banco**; os dados entram por um job de ingestão agendado (passo 7).

---

## 1. Criar a conta e o VM

1. Crie a conta gratuita em <https://www.oracle.com/cloud/free/> (pede cartão para
   verificação, mas os recursos **Always Free** não são cobrados).
2. Console → **Compute → Instances → Create instance**.
3. **Image and shape:**
   - Image: **Canonical Ubuntu 22.04**.
   - Shape: **Ampere (VM.Standard.A1.Flex)** — ARM, Always Free (até 4 OCPU / 24 GB).
     Use **1 OCPU / 6 GB** (sobra). Alternativa x86: **VM.Standard.E2.1.Micro**.
   - Se aparecer "Out of host capacity" (comum no Ampere), troque o
     *Availability Domain* ou tente mais tarde / outra região.
4. **Add SSH keys:** gere localmente e cole a pública:
   ```sh
   ssh-keygen -t ed25519 -C "oracle-conflictzone" -f ~/.ssh/oracle_conflictzone
   cat ~/.ssh/oracle_conflictzone.pub   # cole no campo "Public key"
   ```
5. Crie a instância e anote o **Public IP**.

---

## 2. Liberar a porta 80 (duas camadas de firewall!)

A Oracle bloqueia tudo por padrão **e** o Ubunto dela tem iptables próprio.

**a) Security List (rede):** VCN da instância → **Subnet → Security List default →
Add Ingress Rules:**
- Source CIDR: `0.0.0.0/0`
- IP Protocol: `TCP`
- Destination Port: `80` (e `443` se for usar HTTPS depois)

**b) Firewall do host (depois de logar via SSH — passo 3):**
```sh
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save
```

---

## 3. Conectar e instalar o Docker

```sh
ssh -i ~/.ssh/oracle_conflictzone ubuntu@SEU_PUBLIC_IP

# Docker + plugin compose (script oficial)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # aplica o grupo sem relogar
docker version && docker compose version
```

---

## 4. Clonar o projeto e configurar o ambiente

```sh
git clone https://github.com/RosaErick/conflictzone-api.git
cd conflictzone-api

cp .env.production.example .env
nano .env
```
Preencha o `.env`:
- `DJANGO_SECRET_KEY` → gere com
  `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
  (obrigatório quando `DJANGO_DEBUG=False` — o app recusa subir sem ele).
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=SEU_PUBLIC_IP` (adicione o domínio depois, separado por vírgula)
- `CORS_ALLOWED_ORIGINS=https://seu-frontend` (em prod; sem isso o CORS fica fechado)
- `FOGO_CRUZADO_EMAIL` / `FOGO_CRUZADO_PASSWORD`
- `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` (use uma senha forte; o
  serviço `web` aponta para o host `db` automaticamente via compose)

---

## 5. Subir

```sh
docker compose up -d --build
```
O build roda **nativo no ARM** do VM (sem cross-build). O entrypoint aplica
migrations e coleta os estáticos automaticamente.

Verifique:
```sh
docker compose ps
docker compose logs -f web    # Ctrl+C para sair
```

Teste no navegador / curl:
- `http://SEU_PUBLIC_IP/health/` → `{"status":"ok","lastIngestion":{...}}`
- `http://SEU_PUBLIC_IP/health/fogo-cruzado/` → `{"status":"online",...}`
- `http://SEU_PUBLIC_IP/documentation/` → docs (Redoc)
- `http://SEU_PUBLIC_IP/occurrences/?initialdate=2024-05-01&finaldate=2024-05-31`

> Antes da primeira ingestão os endpoints de dados respondem **503** (`data
> unavailable`) — isso é proposital (falha honesta, nunca lista vazia). Rode o
> job do passo 7 ao menos uma vez para popular o banco.

---

## 6. Operação

```sh
# Ver logs
docker compose logs -f

# Atualizar após um git push
git pull && docker compose up -d --build

# Reiniciar / parar
docker compose restart
docker compose down

# Criar superuser do admin (opcional)
docker compose exec web python manage.py createsuperuser
```

---

## 7. Ingestão: backfill + cron incremental

A API só lê do banco; quem popula é o command `sync_occurrences`. Ver
[`docs/ingestion.md`](ingestion.md) para a lógica completa. Resumo operacional:

**a) Carga histórica (uma vez), fatiada por ano** — o teto é ~50k registros por
execução, então um ano por vez fica folgado para o volume do RJ:

```sh
for y in 2020 2021 2022 2023 2024 2025; do
  docker compose run --rm web python manage.py sync_occurrences \
    --initial-date $y-01-01 --final-date $y-12-31
done
```

**b) Cron incremental (1x/hora)** — sem datas, o command sincroniza só os
**últimos 3 dias** (`INGESTION_DEFAULT_DAYS`); o upsert idempotente cobre
sobreposições e atrasos da fonte:

```sh
crontab -e
# Sincroniza os últimos 3 dias toda hora; ajuste o caminho do projeto.
0 * * * * cd /home/ubuntu/conflictzone-api && /usr/bin/docker compose run --rm web \
  python manage.py sync_occurrences >> /var/log/cz-ingest.log 2>&1
```

> ponytail: cron do SO + management command cobre o agendamento sem Celery/Redis,
> e uma **janela fixa recente** evita guardar cursor de sincronização. Migrar para
> **Celery beat** só quando precisar de retry automático/concorrência. O
> `IngestionRun` (visível no `/admin/` e em `/health/`) já dá auditoria:
> status `success`/`partial`/`failed` e contagens.

## 8. Backup automático do banco

O banco é a fonte de verdade e o backfill custou esforço — não deixe sem backup.
O script [`scripts/backup.sh`](../scripts/backup.sh) faz um `pg_dump` **rolável**:
escreve num temp, valida o tamanho e só então sobrescreve atomicamente o dump
anterior. Um dump que falhe ou venha vazio **nunca** destrói o último backup bom.

Rodar manualmente (da raiz do projeto):
```sh
./scripts/backup.sh            # gera/atualiza cz-latest.dump
```

**Agendamento é opcional** — o script roda sob demanda. Quando/se quiser backup
diário automático, adicione esta linha ao `crontab -e` (diário às 04:00):
```cron
0 4 * * * cd ~/conflictzone-api && ./scripts/backup.sh >> /var/log/cz-backup.log 2>&1
```

Restaurar, se algum dia precisar:
```sh
docker compose exec -T db pg_restore -U conflictzone -d conflictzone --clean < cz-latest.dump
```

> ponytail: um arquivo rolável local + cron cobre o essencial. Suba para **cópias
> datadas com retenção** e **upload off-site** (Oracle Object Storage / Backblaze
> B2, ambos free tier) quando uma cópia local na mesma VM deixar de ser suficiente.
> Os `*.dump` estão no `.gitignore` (binário com dados — nunca versionar).

## 9. Próximos passos (opcionais)

- **HTTPS + domínio:** aponte um domínio (ou DuckDNS grátis) para o IP, abra a
  porta 443 e troque o `nginx` por **Caddy** (TLS automático via Let's Encrypt) ou
  adicione `certbot`. Inclua o domínio em `DJANGO_ALLOWED_HOSTS`.
- **Frontend:** o `fogo-cruzado-insights` (Vite estático) pode ir para Cloudflare
  Pages / Vercel grátis, com `VITE_API_URL=http://SEU_PUBLIC_IP` (ou o domínio https).
- **Upgrades com gatilho (ver [`docs/roadmap.md`](roadmap.md)):** Redis (cache/
  token) quando medir lento; Celery beat quando precisar de retry/concorrência;
  tabela `Victim` normalizada no primeiro filtro por atributo de vítima.
