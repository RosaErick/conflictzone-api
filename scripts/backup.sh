#!/bin/sh
# Rolling pg_dump backup of the ConflictZone database.
#
# Overwrites the previous dump, but ONLY after a successful, non-empty dump:
# it writes to a temp file, sanity-checks the size, then atomically moves it
# over the target. A failed/empty dump therefore never clobbers the last good
# backup.
#
# ponytail: single rolling file + cron covers it; add dated rotation or an
# off-site upload (Object Storage / B2) when one local copy stops being enough.
#
# Usage (from the project root, where docker-compose.yml lives):
#   ./scripts/backup.sh
# Env overrides: CZ_BACKUP_FILE, CZ_BACKUP_MIN_BYTES, POSTGRES_USER, POSTGRES_DB
set -u

cd "$(dirname "$0")/.." || exit 1

OUT="${CZ_BACKUP_FILE:-cz-latest.dump}"
TMP="${OUT}.tmp"
DB_USER="${POSTGRES_USER:-conflictzone}"
DB_NAME="${POSTGRES_DB:-conflictzone}"
MIN_BYTES="${CZ_BACKUP_MIN_BYTES:-100000}"   # ~100 KB floor; guards against empty dumps

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
