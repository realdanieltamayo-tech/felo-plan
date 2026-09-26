#!/bin/bash
set -e
B="${1:?usage: felo-deploy.sh <branch>}"
cd /root/felo-orchestrator
PREV=$(git rev-parse HEAD)
git fetch -q /root/git/felo.git "$B"
echo "--- changes in $B ---"
git --no-pager diff --stat HEAD FETCH_HEAD
read -p "merge and deploy? (yes/no) " OK
[ "$OK" = "yes" ] || { echo aborted; exit 1; }
git merge --no-edit FETCH_HEAD
docker compose up -d --build --force-recreate orchestrator
sleep 12
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:8080/api/hq/state || echo 000)
BRAIN=skipped
if [ "$CODE" = "200" ]; then
  echo "state ok - asking felo a question..."
  BRAIN=$(docker compose exec -T orchestrator node -e '
const t=process.env.AUTH_TOKEN;
fetch("http://localhost:8080/api/hq/ask",{method:"POST",
 headers:{"content-type":"application/json",authorization:"Bearer "+t},
 body:JSON.stringify({text:"deployment check - reply with one short sentence"}),
 signal:AbortSignal.timeout(60000)})
.then(r=>r.json()).then(j=>process.stdout.write(JSON.stringify(j).length>40?"ok":"empty"))
.catch(e=>process.stdout.write("fail"));' 2>/dev/null || echo fail)
fi
if [ "$CODE" = "200" ] && [ "$BRAIN" = "ok" ]; then
  echo "HEALTHY - deployed $(git rev-parse --short HEAD) - brain answered"
else
  echo "UNHEALTHY (state $CODE, brain $BRAIN) - rolling back to $PREV"
  git reset --hard "$PREV"
  docker compose up -d --build --force-recreate orchestrator
  sleep 12
  curl -s -o /dev/null -w 'health after rollback: %{http_code}\n' http://localhost:8080/api/hq/state
  exit 1
fi
