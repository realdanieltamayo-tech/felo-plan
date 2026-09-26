#!/bin/bash
# Move every Felo alert sender to the new private ntfy channel in /root/felo-v2-runtime/ntfy.env.
# Never prints the channel name. PRJ-01 1.1, 2026-09-24.
set -u; umask 077
R=/root/felo-v2-runtime; NEW=$(sed -n 's/^NTFY_TOPIC=//p' $R/ntfy.env); [ -n "$NEW" ] || { echo "no new channel"; exit 1; }
h(){ printf %s "$1" | sha256sum | cut -c1-10; }

echo "== 1. host scripts read the channel from ntfy.env"
for f in /root/felo-v2-deploy-watch.py /root/felo-v2-notify.py /root/felo-v2-work/ops/felo-v2-deploy-watch.py /root/felo-v2-work/ops/felo-v2-notify.py; do
  cp -p $f $R/$(basename $f).before-channel 2>/dev/null
  sed -i 's#^TOPIC_FROM = "/root/felo-orchestrator/docker-compose.yml"#TOPIC_FROM = "/root/felo-v2-runtime/ntfy.env"#' $f
  sed -i "s#re.match(r\"\\\\s\*NTFY_TOPIC:\\\\s\*#re.match(r\"\\\\s*NTFY_TOPIC[:=]\\\\s*#" $f
  python3 -m py_compile $f && echo "  $(basename $(dirname $f))/$(basename $f): $(grep -c 'felo-v2-runtime/ntfy.env' $f) path, $(grep -c 'NTFY_TOPIC\[:=\]' $f) pattern"
done
for f in /root/felo-v2-deploy-watch.py /root/felo-v2-notify.py; do
  got=$(cd /root && python3 -c "import importlib.util as u;s=u.spec_from_file_location('m','$f');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.topic() if hasattr(m,'topic') else m.ntfy_topic())")
  [ "$(h "$got")" = "$(h "$NEW")" ] && echo "  $(basename $f) now uses the new channel" || { echo "  $(basename $f) MISMATCH"; exit 1; }
done

echo "== 2. website lead service"
cp -p $R/intake.env $R/intake.env.before-channel
python3 - $R/intake.env "$NEW" <<'PY'
import sys
p,new=sys.argv[1:]; lines=open(p).read().splitlines(); hit=0
for i,l in enumerate(lines):
    if l.startswith("NTFY_TOPIC="): lines[i]="NTFY_TOPIC="+new; hit+=1
assert hit==1; open(p,"w").write("\n".join(lines)+"\n")
PY
docker rm -f felo-v2-intake-prev >/dev/null 2>&1
docker rename felo-v2-intake felo-v2-intake-prev && docker stop felo-v2-intake-prev >/dev/null
docker run -d --name felo-v2-intake --network felo-codex-preview -p 8080:8080 --read-only --restart unless-stopped \
  --env-file $R/intake.env -v /root/felo-codex-preview/intake:/intake:ro -w /intake felo-v2-runtime:current node /intake/intake.js >/dev/null
ok=0; for i in $(seq 1 20); do sleep 1; curl -s --max-time 3 http://127.0.0.1:8080/health | grep -q '"ok":true' && { ok=1; break; }; done
if [ $ok = 1 ]; then
  docker update --restart no felo-v2-intake-prev >/dev/null
  inside=$(docker exec felo-v2-intake sh -c 'printf %s "$NTFY_TOPIC"')
  [ "$(h "$inside")" = "$(h "$NEW")" ] && echo "  lead service healthy after ${i}s and uses the new channel" || echo "  lead service healthy but channel MISMATCH"
else
  echo "  lead service NOT healthy - switching back"; docker rm -f felo-v2-intake >/dev/null; cp -p $R/intake.env.before-channel $R/intake.env
  docker rename felo-v2-intake-prev felo-v2-intake; docker start felo-v2-intake >/dev/null; exit 1
fi

echo "== 3. retired v1 settings no longer hold the old channel"
sed -i "s#^\([[:space:]]*\)NTFY_TOPIC:.*#\1\# NTFY_TOPIC moved to /root/felo-v2-runtime/ntfy.env on 2026-09-24 (old channel retired)#" /root/felo-orchestrator/docker-compose.yml
grep -c "moved to /root/felo-v2-runtime/ntfy.env" /root/felo-orchestrator/docker-compose.yml | sed 's/^/  v1 compose lines updated: /'
shred -u $R/intake.env.before-channel 2>/dev/null; echo "  old-channel copy of intake settings destroyed"
