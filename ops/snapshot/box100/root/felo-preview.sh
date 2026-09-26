#!/bin/bash
set -u
cd /root/felo-orchestrator || exit 0
R=/root/git/felo.git
Q(){ docker compose exec -T db psql -U felo -d felo_orchestrator -tAc "$1" 2>/dev/null; }
[ -n "$(Q "SELECT 1 FROM felo_drops WHERE state='preview' LIMIT 1")" ] && exit 0
[ -f app/hq-preview.html ] && exit 0
BEST=""; BESTT=0
for B in $(git -C $R for-each-ref --format='%(refname:short)' refs/heads | grep -v '^master$'); do
  git -C $R merge-base --is-ancestor $B master && continue
  [ "$(git -C $R diff --name-only master $B)" = "app/hq.html" ] || continue
  T=$(git -C $R log -1 --format=%ct $B)
  [ "$T" -gt "$BESTT" ] && { BEST=$B; BESTT=$T; }
done
[ -z "$BEST" ] && exit 0
git -C $R show $BEST:app/hq.html > /tmp/prev.html 2>/dev/null || exit 0
[ -s /tmp/prev.html ] || exit 0
cmp -s /tmp/prev.html app/hq.html && exit 0
NEW=$(sha256sum /tmp/prev.html | cut -c1-16)
[ -n "$(Q "SELECT 1 FROM felo_drops WHERE sha='$NEW' LIMIT 1")" ] && exit 0
NOTE=$(git -C $R log -1 --format=%s $BEST | tr -d "'\"" | head -c 300)
cp /tmp/prev.html app/hq-preview.html
docker compose up -d --build --force-recreate orchestrator >/dev/null 2>&1
Q "INSERT INTO felo_drops(name,note,sha) VALUES ('$BEST','$NOTE','$NEW')"
Q "INSERT INTO felo_actions(kind,summary,ok) VALUES ('preview','a new interface is waiting for you - open /hq/preview',true)"
