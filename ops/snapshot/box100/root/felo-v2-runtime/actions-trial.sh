#!/bin/bash
# Sealed trial of the 2.6 action tools on a COPY of the v2 database. Nothing live is touched.
set -u; umask 077; T=/root/felo-v2-runtime/atrial; rm -rf $T; mkdir -p $T
KEY=$(head -c 48 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 40)
docker inspect felo-codex-preview-app --format '{{json .Config.Env}}' | python3 -c "
import json,sys
out=[]
for e in json.load(sys.stdin):
    k,v=e.split('=',1)
    if k in ('PATH','NODE_VERSION','YARN_VERSION'): continue
    if k in ('DATABASE_URL','FELO_LEGACY_DATABASE_URL'): v='postgresql://felo:t@at-db:5432/felo_preview'
    if k=='FELO_MCP_KEY': v='$KEY'
    out.append(k+'='+v)
out.append('FELO_EMAIL_CALENDAR_SCHEDULE=0'); out.append('FELO_MCP_PORT=18090')
open('$T/env','w').write('\n'.join(out)+'\n')"
docker exec felo-codex-preview-db sh -c 'pg_dump -U "$POSTGRES_USER" -d felo_preview' > $T/db.sql
docker network create --internal felo-at >/dev/null
docker run -d --rm --name at-db --network felo-at -e POSTGRES_USER=felo -e POSTGRES_PASSWORD=t -e POSTGRES_DB=felo_preview postgres:16 >/dev/null
for i in $(seq 1 40); do docker exec at-db pg_isready -U felo -q 2>/dev/null && break; sleep 1; done; sleep 2
docker exec -i at-db psql -q -U felo -d felo_preview < $T/db.sql >/dev/null 2>&1; shred -u $T/db.sql
docker run -d --rm --name at-app --network felo-at --read-only --env-file $T/env -v /root/felo-v2-work/app:/repair:ro -w /repair felo-v2-runtime:current node /repair/preview.js >/dev/null
for i in $(seq 1 30); do sleep 2; docker logs at-app 2>&1 | grep -q "Felo tools for Hermes listening" && break; done
docker logs at-app 2>&1 | grep -E "preview is ready|\[tools\] Felo tools" | sed 's/^/  /'
cat > $T/c.cjs <<'EOF'
const K=process.env.K,U='http://at-app:18090/mcp';let id=0;
const call=async(name,args)=>{const r=await fetch(U,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+K},body:JSON.stringify({jsonrpc:'2.0',id:++id,method:'tools/call',params:{name,arguments:args}})});const d=await r.json();const t=d.result.content[0].text;return {err:d.result.isError,v:d.result.isError?t:JSON.parse(t)};};
(async()=>{
 const c=await call('felo_crm_create',{kind:'contacts',fields:{name:'Trial Contact',email:'trial@example.invalid',source:'trial'}});console.log('create contact:',c.err?c.v:'#'+c.v.record.id+' v'+c.v.record.version);
 const l=await call('felo_crm_create',{kind:'leads',fields:{contact_id:c.v.record.id,title:'Trial lead',stage:'new'}});console.log('create lead:',l.err?l.v:'#'+l.v.record.id);
 const u=await call('felo_crm_update',{kind:'leads',id:l.v.record.id,fields:{stage:'contacted',next_step:'Call Friday'}});console.log('update lead:',u.err?u.v:'stage='+u.v.record.stage+' v'+u.v.record.version);
 const t=await call('felo_crm_create',{kind:'tasks',fields:{title:'Trial task',due_date:'2026-10-01'}});console.log('create task:',t.err?t.v:'#'+t.v.record.id);
 const d=await call('felo_crm_update',{kind:'tasks',id:t.v.record.id,fields:{done:true}});console.log('task done:',d.err?d.v:d.v.record.done);
 const e=await call('felo_calendar_add_event',{title:'Trial meeting',start:new Date(Date.now()+86400000).toISOString(),why:'trial'});console.log('calendar add:',e.err?e.v:'#'+e.v.id);
 const bad=await call('felo_crm_create',{kind:'notes',fields:{contact_id:999999,body:'x'}});console.log('bad contact refused:',bad.err,'-',bad.v);
})();
EOF
docker run --rm --network felo-at -e K=$KEY -v $T/c.cjs:/c.cjs:ro node:20-alpine node /c.cjs | sed 's/^/  /'
Q(){ docker exec at-db psql -U felo -d felo_preview -At -c "$1"; }
echo "  change history rows by agent:felo: $(Q "select count(*) from felo_crm_audit where actor='agent:felo'")"
echo "  activity feed entries by Felo: $(Q "select count(*) from felo_actions where kind='felo'")"
echo "  confirmed Felo calendar events: $(Q "select count(*) from felo_calendar_items where decided_by='agent:felo' and status='confirmed'")"
docker stop at-app at-db >/dev/null; docker network rm felo-at >/dev/null; shred -u $T/env; rm -rf $T; echo "  trial removed"
