#!/bin/bash
# Runs on box 100. Uses /root/felo-v2-runtime/hermes.env; never prints the key.
set -u
. /root/felo-v2-runtime/hermes.env
H=(-H "Authorization: Bearer $HERMES_API_KEY")
echo "health with key:    HTTP $(curl -s -o /dev/null -w %{http_code} --max-time 15 "${H[@]}" $HERMES_API_URL/v1/health)"
echo "health without key: HTTP $(curl -s -o /dev/null -w %{http_code} --max-time 15 $HERMES_API_URL/v1/health)  (401 = locked)"
echo "models: $(curl -s --max-time 15 "${H[@]}" $HERMES_API_URL/v1/models | python3 -c 'import json,sys;print([m["id"] for m in json.load(sys.stdin).get("data",[])])')"
T0=$(date +%s)
curl -s --max-time 180 "${H[@]}" -H 'Content-Type: application/json' $HERMES_API_URL/v1/chat/completions \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"This is a connection test from the Felo app on box 100. In one short sentence: who are you and which company do you work for?"}]}' \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print("answer: "+(d.get("choices",[{}])[0].get("message",{}).get("content","") or str(d)[:300]).strip()[:300])'
echo "answer time: $(( $(date +%s)-T0 ))s"
