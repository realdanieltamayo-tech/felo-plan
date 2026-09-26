#!/bin/bash
# Hand port 8080 from the v1 lead inbox to the v2 website intake service.
set -u
sync_once() { systemctl start felo-website-lead-sync.service; journalctl -u felo-website-lead-sync -n 1 --no-pager -o cat; }
echo "final sync before switch: $(sync_once)"
cd /root/felo-orchestrator
docker compose stop orchestrator >/dev/null 2>&1 && echo "v1 lead inbox stopped"
docker run -d --name felo-v2-intake --network felo-codex-preview -p 8080:8080 --read-only --restart unless-stopped \
  --env-file /root/felo-v2-runtime/intake.env -v /root/felo-codex-preview/intake:/intake:ro -w /intake \
  felo-v2-runtime:current node /intake/intake.js >/dev/null
ok=0
for i in $(seq 1 20); do sleep 1; curl -s --max-time 3 http://127.0.0.1:8080/health | grep -q '"ok":true' && { ok=1; break; }; done
if [ $ok = 1 ]; then
  echo "v2 intake healthy after ${i}s: $(curl -s http://127.0.0.1:8080/health)"
  echo "sync after switch (catches anything that reached v1 in between): $(sync_once)"
  systemctl disable --now felo-website-lead-sync.timer 2>&1 | tail -1
  echo "sync timer: $(systemctl is-active felo-website-lead-sync.timer)"
else
  echo "v2 intake NOT healthy - putting v1 inbox back"; docker logs felo-v2-intake 2>&1 | tail -5
  docker rm -f felo-v2-intake >/dev/null; docker compose start orchestrator >/dev/null 2>&1
  sleep 3; echo "v1 inbox: $(curl -s http://127.0.0.1:8080/health)"; exit 1
fi
