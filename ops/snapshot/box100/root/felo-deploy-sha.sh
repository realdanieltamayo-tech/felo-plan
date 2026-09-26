#!/bin/bash
set -u
R=/root/felo-orchestrator
G=/root/git/felo.git
SHA="$1"
cd "$R" || { echo "no repo at $R"; exit 1; }
PREV=$(git rev-parse HEAD)
git fetch origin --quiet
if ! git merge --no-edit "$SHA" >/dev/null 2>&1; then
  git merge --abort >/dev/null 2>&1
  echo "CONFLICT: $SHA will not merge cleanly onto current master - the branch must be rebuilt from origin/master and the work redone. Nothing was changed."
  exit 1
fi
docker compose up -d --build orchestrator >/dev/null 2>&1
sleep 12
H=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 localhost:8080/hq || echo 000)
S=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 localhost:8080/api/hq/state || echo 000)
C=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 localhost:8080/api/hq/crm/leads || echo 000)
if [ "$H" = "200" ] && [ "$S" = "200" ] && [ "$C" = "200" ]; then
  git push -q origin HEAD:refs/heads/deployed --force >/dev/null 2>&1
  git --git-dir=$G update-ref refs/heads/master "$(git rev-parse HEAD)"
  echo "DEPLOYED $(git rev-parse --short HEAD)  (hq $H, state $S, crm $C)"
  exit 0
fi
git reset --hard "$PREV" >/dev/null 2>&1
docker compose up -d --build orchestrator >/dev/null 2>&1
echo "ROLLED BACK - health was hq $H, state $S, crm $C"
exit 1
