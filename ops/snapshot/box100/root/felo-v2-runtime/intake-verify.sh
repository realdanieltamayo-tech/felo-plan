#!/bin/bash
# Prove what felo_website_intake can and cannot do on the live v2 DB. Nothing is kept.
set -u
PW=$(sed -nE 's#^DATABASE_URL=postgres://felo_website_intake:([^@]+)@.*#\1#p' /root/felo-v2-runtime/intake.env)
Q() { docker exec -i -e PGPASSWORD="$PW" felo-codex-preview-db psql -XqAt -h 127.0.0.1 -U felo_website_intake -d felo_preview 2>&1 <<< "$1" | grep -v '^$' | head -1 | cut -c1-70; }
echo "read contacts:        $(Q 'SELECT count(*) FROM crm_contacts;')"
echo "insert a lead:        $(Q "INSERT INTO crm_leads(title) VALUES('x');")"
echo "old v1 import func:   $(Q "SELECT felo_import_website_leads('{}'::jsonb);")"
echo "memory table:         $(Q 'SELECT count(*) FROM felo_owner_memory;')"
echo "intake func (undone): $(Q "BEGIN; SELECT (felo_website_intake('{\"name\":\"Verify Only\",\"email\":\"verify@example.invalid\"}'::jsonb,'99999999-9999-4999-8999-999999999999'))->>'newContact'; ROLLBACK;")"
echo "heartbeat (undone):   $(Q 'BEGIN; SELECT felo_website_intake_heartbeat(); ROLLBACK;' ; echo ok)"
