#!/bin/bash
# Start a sealed trial copy of v2 from the work copy against a copy of the database.
set -u; umask 077; T=/root/felo-v2-runtime/trial; rm -rf $T; mkdir -p $T
docker inspect felo-codex-preview-app --format '{{json .Config.Env}}' | python3 -c "
import json,sys
out=[]
for e in json.load(sys.stdin):
    k,v=e.split('=',1)
    if k in ('PATH','NODE_VERSION','YARN_VERSION'): continue
    if k in ('DATABASE_URL','FELO_LEGACY_DATABASE_URL'): v='postgresql://felo:t@trial-db:5432/felo_preview'
    out.append(k+'='+v)
out.append('FELO_EMAIL_CALENDAR_SCHEDULE=0')
open('$T/env','w').write('\n'.join(out)+'\n')"
docker exec felo-codex-preview-db sh -c 'pg_dump -U "$POSTGRES_USER" -d felo_preview' > $T/v2.sql
docker network create --internal felo-v2-trial >/dev/null
docker run -d --rm --name trial-db --network felo-v2-trial -e POSTGRES_USER=felo -e POSTGRES_PASSWORD=t -e POSTGRES_DB=felo_preview postgres:16 >/dev/null
for i in $(seq 1 30); do docker exec trial-db pg_isready -U felo -q 2>/dev/null && break; sleep 1; done; sleep 2
docker exec -i trial-db psql -q -U felo -d felo_preview < $T/v2.sql >/dev/null 2>&1
docker run -d --rm --name trial-app --network felo-v2-trial --read-only --env-file $T/env -v /root/felo-v2-work/app:/repair:ro -w /repair felo-v2-runtime:current node /repair/preview.js >/dev/null
for i in $(seq 1 30); do sleep 2; docker logs trial-app 2>&1 | grep -qE "preview is ready|initialization failed" && break; done
echo "--- trial log:"; docker logs trial-app 2>&1 | tail -4
echo "--- new tables: $(docker exec trial-db psql -U felo -d felo_preview -At -c "select string_agg(table_name,', ') from information_schema.tables where table_name like 'felo_calendar_%'")"
echo "--- answers: $(docker run --rm --network felo-v2-trial node:20-alpine wget -qO- http://trial-app:8080/hq 2>&1 | grep -c 'Felo owner access') owner-gate page"
docker stop trial-app trial-db >/dev/null; docker network rm felo-v2-trial >/dev/null; rm -rf $T; echo "trial removed"
