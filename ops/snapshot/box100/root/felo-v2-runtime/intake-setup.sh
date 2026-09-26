#!/bin/bash
# Create the felo_website_intake role (fresh password, never printed) and apply scripts/website-intake.sql.
set -euo pipefail
umask 077
E=/root/felo-v2-runtime/intake.env
PSQL=(docker exec -i felo-codex-preview-db sh -c 'psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d felo_preview')
if [ -n "$("${PSQL[@]}" <<< "SELECT 1 FROM pg_roles WHERE rolname='felo_website_intake';")" ]; then
  echo "role already exists - stopping so nothing is overwritten"; exit 1
fi
PW=$(head -c 48 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 32)
TOPIC=$(sed -nE "s/^[[:space:]]*NTFY_TOPIC:[[:space:]]*['\"]?([^'\" ]+).*/\1/p" /root/felo-orchestrator/docker-compose.yml)
printf 'DATABASE_URL=postgres://felo_website_intake:%s@felo-codex-preview-db:5432/felo_preview\nNTFY_TOPIC=%s\nPORT=8080\nNODE_PATH=/app/node_modules\n' "$PW" "$TOPIC" > "$E"
"${PSQL[@]}" > /dev/null 2>&1 <<< "CREATE ROLE felo_website_intake LOGIN PASSWORD '$PW' CONNECTION LIMIT 3;" || { echo "could not create role"; exit 1; }
unset PW
"${PSQL[@]}" < /root/felo-codex-preview/scripts/website-intake.sql
echo "role created, functions + grants applied; env keys: $(cut -d= -f1 "$E" | tr '\n' ' ')"
