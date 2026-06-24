#!/bin/sh
# Backup rolável (pg_dump) do banco ConflictZone.
#
# Sobrescreve o dump anterior só após um dump válido e não-vazio: escreve num
# temp, confere o tamanho e move atomicamente. Dump falho/vazio nunca destrói o
# último backup bom.
#
# ponytail: um arquivo rolável + cron resolve; rotação datada / upload off-site
# (Object Storage / B2) quando uma cópia local deixar de bastar.
#
# Uso (na raiz do projeto): ./scripts/backup.sh
# Envs: CZ_BACKUP_FILE, CZ_BACKUP_MIN_BYTES, POSTGRES_USER, POSTGRES_DB
set -u

cd "$(dirname "$0")/.." || exit 1

OUT="${CZ_BACKUP_FILE:-cz-latest.dump}"
TMP="${OUT}.tmp"
DB_USER="${POSTGRES_USER:-conflictzone}"
DB_NAME="${POSTGRES_DB:-conflictzone}"
MIN_BYTES="${CZ_BACKUP_MIN_BYTES:-100000}"   # piso ~100 KB; protege contra dumps vazios

if ! docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$TMP"; then
    echo "$(date -Is) backup FAILED: pg_dump error; kept previous $OUT" >&2
    rm -f "$TMP"
    exit 1
fi

size=$(wc -c < "$TMP")
if [ "$size" -lt "$MIN_BYTES" ]; then
    echo "$(date -Is) backup ABORTED: dump too small ($size bytes); kept previous $OUT" >&2
    rm -f "$TMP"
    exit 1
fi

mv -f "$TMP" "$OUT"
echo "$(date -Is) backup OK: $OUT ($size bytes)"
