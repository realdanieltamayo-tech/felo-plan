#!/bin/bash
# Ask Google whether a client secret is accepted, using a deliberately fake one-time code.
# "invalid_grant" = secret accepted (only the fake code was rejected); "invalid_client" = secret wrong.
CID=$(sed -n 's/^GMAIL_CLIENT_ID=//p' /root/felo-v2-runtime/app.run.env)
probe(){ curl -s https://oauth2.googleapis.com/token --data-urlencode "client_id=$CID" --data-urlencode "client_secret@$1" \
  -d grant_type=authorization_code -d code=felo-probe-not-a-real-code -d redirect_uri=https://felo-orchestrator.tail0ff06a.ts.net:8443/callback \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("error"))'; }
umask 077; sed -n 's/^GMAIL_CLIENT_SECRET=//p' /root/felo-v2-runtime/app.run.env | tr -d '\n' > /root/felo-v2-runtime/pending/.old
echo "old secret: $(probe /root/felo-v2-runtime/pending/.old)"; echo "new secret: $(probe /root/felo-v2-runtime/pending/gmail-secret)"; rm -f /root/felo-v2-runtime/pending/.old
V1=$(sed -nE 's/^[[:space:]]*GMAIL_CLIENT_ID:[[:space:]]*//p' /root/felo-orchestrator-backups/v1-retire-*/docker-compose.yml | head -1 | tr -d "'\" ")
[ "$V1" = "$CID" ] && echo "v1 used the SAME Google app (web)" || echo "v1 used a DIFFERENT Google app: id starts ${V1%%-*}-${V1#*-}" | cut -c1-80
