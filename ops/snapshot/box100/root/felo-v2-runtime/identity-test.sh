#!/bin/bash
# Step 2.4 checks: ask Felo (Hermes) four questions in a test conversation. Runs on box 100.
. /root/felo-v2-runtime/hermes.env
ask(){ curl -s --max-time 300 -H "Authorization: Bearer $HERMES_API_KEY" -H "Content-Type: application/json" $HERMES_API_URL/v1/responses \
  -d "$(python3 -c 'import json,sys;print(json.dumps({"model":"hermes-agent","input":sys.argv[1],"conversation":"felo-identity-check","store":True}))' "$1")" \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);o=d.get("output",[]);t=[x.get("name") for x in o if x.get("type")=="function_call"];print("   tools:",t or "-");print("   "+" ".join(c.get("text","") for x in o if x.get("type")=="message" for c in x.get("content",[])).strip()[:420])'; }
for q in "Who are you, in one sentence?" \
         "A 20-person law office asks what our private cloud costs per month. One line." \
         "What kind of business is Odalyake, and what did we quote them? Two lines max." \
         "¿Qué negocios manejas para mí? Responde en una línea."; do
  echo "Q: $q"; T0=$(date +%s); ask "$q"; echo "   ($(( $(date +%s)-T0 ))s)"; done
