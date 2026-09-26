#!/bin/sh
# Daily Felo database backup (felo-backup.timer, 03:30). Keeps the last 14.
# Only v2 (the live Felo). v1 was retired on 2026-09-24; its final dumps are in
# /root/felo-orchestrator-backups/v1-retire-* and older felo-2*.sql.gz files here.
set -e
umask 077
D=/root/backups
STAMP=$(date +%Y%m%d-%H%M)
docker exec felo-codex-preview-db sh -c "pg_dump -U \"\$POSTGRES_USER\" -d felo_preview" | gzip > "$D/felo-v2-$STAMP.sql.gz"
ls -1t $D/felo-v2-*.sql.gz | tail -n +15 | xargs -r rm --
echo "backup done: $D/felo-v2-$STAMP.sql.gz"
