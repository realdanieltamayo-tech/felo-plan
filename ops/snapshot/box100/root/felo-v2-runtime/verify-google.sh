#!/bin/bash
# Confirm the old Google secret is dead and the new one works; then destroy the old copy.
R=/root/felo-v2-runtime; umask 077
CID=$(sed -n 's/^GMAIL_CLIENT_ID=//p' $R/app.run.env)
OLDF=$(ls -t $R/app.run.env.before-gmail-secret-* 2>/dev/null | head -1)
probe(){ curl -s https://oauth2.googleapis.com/token --data-urlencode "client_id=$CID" --data-urlencode "client_secret@$1" \
  -d grant_type=authorization_code -d code=felo-probe-not-a-real-code -d redirect_uri=https://felo-orchestrator.tail0ff06a.ts.net:8443/callback \
  | python3 -c 'import json,sys; e=json.load(sys.stdin).get("error"); print({"invalid_client":"REJECTED by Google (dead)","invalid_grant":"accepted by Google"}.get(e,e))'; }
sed -n 's/^GMAIL_CLIENT_SECRET=//p' "$OLDF" | tr -d '\n' > $R/pending/.old; sed -n 's/^GMAIL_CLIENT_SECRET=//p' $R/app.run.env | tr -d '\n' > $R/pending/.new
echo "old secret: $(probe $R/pending/.old)"; echo "new secret: $(probe $R/pending/.new)"
shred -u $R/pending/.old $R/pending/.new
