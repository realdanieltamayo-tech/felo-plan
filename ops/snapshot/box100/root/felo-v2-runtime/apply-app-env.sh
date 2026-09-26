#!/bin/bash
# Set several Felo v2 app settings at once and restart safely (switch back if unhealthy).
#   apply-app-env.sh KEY=VALUE ... [--from FILE]   (FILE lines KEY=VALUE are merged too; values never printed)
set -u; umask 077
R=/root/felo-v2-runtime; E=$R/app.run.env; APP=felo-codex-preview-app
TS=$(date -u +%Y%m%d%H%M); BK=$E.before-env-$TS; cp -p $E $BK
python3 - "$E" "$@" <<'PY'
import sys
env=sys.argv[1]; args=sys.argv[2:]; kv={}
i=0
while i<len(args):
    if args[i]=="--from":
        for l in open(args[i+1]).read().splitlines():
            if "=" in l: k,v=l.split("=",1); kv[k]=v
        i+=2; continue
    k,v=args[i].split("=",1); kv[k]=v; i+=1
lines=open(env).read().splitlines(); seen=set()
for n,l in enumerate(lines):
    k=l.split("=",1)[0]
    if k in kv: lines[n]=k+"="+kv[k]; seen.add(k)
lines+=[k+"="+v for k,v in kv.items() if k not in seen]
open(env,"w").write("\n".join(lines)+"\n")
print("settings changed:", ", ".join(sorted(kv)))
PY
docker rm -f ${APP}-prev >/dev/null 2>&1
docker rename $APP ${APP}-prev && docker stop ${APP}-prev >/dev/null
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker run -d --name $APP --network felo-codex-preview -p 127.0.0.1:8081:8080 -p 8090:8090 --read-only --restart unless-stopped \
  --env-file "$E" -v /root/felo-codex-preview/app:/repair:ro -w /repair felo-v2-runtime:current node /repair/preview.js >/dev/null
ok=0; for i in $(seq 1 30); do sleep 2
  curl -s --max-time 5 http://127.0.0.1:8081/hq | grep -q "Felo owner access" && docker logs --since $START $APP 2>&1 | grep -q "preview is ready" && { ok=1; break; }; done
if [ $ok = 1 ]; then
  docker rm ${APP}-prev >/dev/null; echo "APPLIED: app healthy after $((i*2))s (previous settings: $(basename $BK))"
else
  echo "NOT HEALTHY - switching back"; docker logs --since $START $APP 2>&1 | tail -4
  docker rm -f $APP >/dev/null; cp -p $BK $E; docker rename ${APP}-prev $APP; docker start $APP >/dev/null; echo "previous version restored"; exit 1
fi
