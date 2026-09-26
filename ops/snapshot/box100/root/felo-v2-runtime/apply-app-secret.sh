#!/bin/bash
# Put a new secret into Felo v2's settings and restart the app safely.
#   apply-app-secret.sh <pending-name> <ENV_KEY>
# Keeps the previous container (renamed *-prev) and switches back if the new one is not healthy.
set -u
NAME=$1; KEY=$2; R=/root/felo-v2-runtime; E=$R/app.run.env; P=$R/pending/$NAME; APP=felo-codex-preview-app
[ -s "$P" ] || { echo "no pending secret $NAME"; exit 1; }
umask 077
cp -p "$E" "$E.before-$NAME-$(date -u +%Y%m%d%H%M)"
python3 - "$E" "$KEY" "$P" <<'PY'
import sys
env,key,p=sys.argv[1:]; val=open(p).read().strip()
lines=open(env).read().splitlines(); hit=0
for i,l in enumerate(lines):
    if l.startswith(key+"="): lines[i]=key+"="+val; hit+=1
assert hit==1, "key not found exactly once"
open(env,"w").write("\n".join(lines)+"\n")
PY
docker rm -f ${APP}-prev >/dev/null 2>&1
docker rename $APP ${APP}-prev && docker stop ${APP}-prev >/dev/null
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker run -d --name $APP --network felo-codex-preview -p 127.0.0.1:8081:8080 -p 8090:8090 --read-only --restart unless-stopped \
  --env-file "$E" -v /root/felo-codex-preview/app:/repair:ro -w /repair felo-v2-runtime:current node /repair/preview.js >/dev/null
ok=0; for i in $(seq 1 30); do sleep 2
  curl -s --max-time 5 http://127.0.0.1:8081/hq | grep -q "Felo owner access" && docker logs --since $START $APP 2>&1 | grep -q "preview is ready" && { ok=1; break; }; done
if [ $ok = 1 ]; then
  docker update --restart no ${APP}-prev >/dev/null; shred -u "$P" 2>/dev/null || rm -f "$P"
  echo "APPLIED $KEY: new container healthy after $((i*2))s; pending copy destroyed; previous container kept as ${APP}-prev"
else
  echo "NOT HEALTHY - switching back"; docker logs --since $START $APP 2>&1 | tail -4
  docker rm -f $APP >/dev/null; cp -p "$(ls -t $E.before-$NAME-* | head -1)" "$E"; docker rename ${APP}-prev $APP; docker start $APP >/dev/null
  echo "previous version restored"; exit 1
fi
