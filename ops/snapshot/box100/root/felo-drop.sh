#!/bin/bash
set -u
cd /root/felo-orchestrator || exit 0
Q(){ docker compose exec -T db psql -U felo -d felo_orchestrator -tAc "$1" 2>/dev/null; }
NC(){ docker compose exec -T orchestrator node -e '
const u=process.env.NEXTCLOUD_URL,n=process.env.NEXTCLOUD_USER,p=process.env.NEXTCLOUD_PASS;
fetch(u+"/remote.php/dav/files/"+n+"/Felo/Drop/"+process.argv[1],
{headers:{Authorization:"Basic "+Buffer.from(n+":"+p).toString("base64")}})
.then(r=>{if(!r.ok)process.exit(3);return r.text()})
.then(t=>process.stdout.write(t)).catch(()=>process.exit(3));' "$1" 2>/dev/null; }
BUILD(){ docker compose up -d --build --force-recreate orchestrator >/dev/null 2>&1; }

NC hq-preview.html > /tmp/drop.html
if [ -s /tmp/drop.html ]; then
  NEW=$(sha256sum /tmp/drop.html | cut -c1-16)
  SEEN=$(Q "SELECT 1 FROM felo_drops WHERE sha='$NEW' LIMIT 1")
  if [ -z "$SEEN" ]; then
    NOTE=$(NC note.md | head -c 800 | tr -d "'\"" | tr '\n' ' ')
    cp /tmp/drop.html app/hq-preview.html
    BUILD
    Q "UPDATE felo_drops SET state='superseded' WHERE state='preview'"
    Q "INSERT INTO felo_drops(name,note,sha) VALUES ('hq-preview.html','$NOTE','$NEW')"
    Q "INSERT INTO felo_actions(kind,summary,ok) VALUES ('preview','a new preview arrived - open /hq/preview',true)"
  fi
fi

ACT=$(Q "SELECT action FROM felo_preview WHERE done_at IS NULL ORDER BY id LIMIT 1")
[ -z "$ACT" ] && { /root/felo-preview.sh; exit 0; }
R="none"
if [ "$ACT" = "promote" ] && [ -f app/hq-preview.html ]; then
  cp app/hq.html app/hq.html.rollback
  cp app/hq-preview.html app/hq.html
  rm -f app/hq-preview.html
  BUILD; sleep 12
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:8080/hq || echo 000)
  if [ "$CODE" = "200" ]; then
    Q "UPDATE felo_drops SET state='live' WHERE state='preview'"
    Q "INSERT INTO felo_actions(kind,summary,ok) VALUES ('preview','made the preview live',true)"
    /root/felo-publish.sh "promote preview to live" >/dev/null 2>&1
    R="live"
  else
    cp app/hq.html.rollback app/hq.html; BUILD
    Q "INSERT INTO felo_actions(kind,summary,ok) VALUES ('preview','promote failed the health check - rolled back',false)"
    R="rolled back"
  fi
elif [ "$ACT" = "discard" ]; then
  rm -f app/hq-preview.html; BUILD
  Q "UPDATE felo_drops SET state='discarded' WHERE state='preview'"
  Q "INSERT INTO felo_actions(kind,summary,ok) VALUES ('preview','discarded the preview',true)"
  R="discarded"
fi
Q "UPDATE felo_preview SET done_at=now(), result='$R' WHERE done_at IS NULL"
