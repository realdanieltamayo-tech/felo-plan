# Handoff — business threads, voice outage, "Hey Felo" wake word (2026-10-25/26)

## 1. "I click Studio and nothing shows"
Cause: every business chat thread was empty (0 messages; all 299 turns in General); supervisor reports only went to the
Products page; new businesses had no thread. Branch **business-view** (eb0f61a, Deploy page): threads synced to Products
(live/building/planned); status card above the chat (today's check, numbers, sites up/DOWN, next step, last 7 checks;
text nodes only); each saveReport posts "Daily check: …" into the business thread (unread); chatting there gives Felo the
latest check as context (threads.input context). Tests 420 pass. Note: product "tyx" is still status retired although
tyxcrm is live — Felo can fix with felo_product_update (status building) so it gets a thread.

## 2. Felo's voice broken (found while testing)
Microsoft started refusing edge-tts < 7.3.x (403 WSServerHandshakeError) after the 7:30 briefing on 2026-10-25.
- box 101 Hermes venv: edge-tts 7.3.1 installed (briefing voice + Telegram voice OK). felo-hermes-fixes now also guards
  edge-tts >= 7.3.1 (Hermes pins 7.2.7 as an optional extra). Backup felo-hermes-fixes.before-edgetts.
- box 100 felo-voice sidecar (Felo HQ voice + Talk mode): branch **voice-fix** (59f7980) requires edge-tts>=7.3.1. The
  deployer does NOT rebuild the sidecar: after the Deploy tap run on box 100: `sh /root/felo-codex-preview/voice/run.sh`
  (rebuilding it directly was blocked by the safety guard as a production deploy — Daniel's step or explicit OK).

## 3. "Always on, wake word" (camera not used yet)
Whisper as wake detector tested on synthetic speech: 6/10 full phrase, 8/13 first-1.3 s (drops "Hey Felo", hallucinates
"Felo" from "fellows") → not usable. Daniel chose: train our own openWakeWord model.
- Training: felo-node-2, container wakeword-train (python:3.10-slim, --cpus 3, 9 GB, cpu-shares 128), /srv/wakeword/work
  (run.sh resumable; log train.log). Phrases "hey felo", "hey fello", "oye felo"; 18 negative look-alikes; n_samples
  15000, steps 40000; ACAV100M features (17 GB) + MIT RIR + AudioSet bal_train08/09 + 3 h FMA. Output
  my_custom_model/hey_felo.onnx. Delete /srv/wakeword/work data afterwards (keep the .onnx in the plan/ops).
- Program (scratch → to deliver): felo-listener/ felo_listener.py (openWakeWord onnx on the PC; after "Hey Felo" →
  /api/hq/listen → /api/hq/ask thread general voice:true → /api/hq/speak; follow-up 8 s; stop words; "Hey Felo, stop/start
  listening"), requirements.txt, install.ps1 (Python 3.12 via winget if missing, venv in %LOCALAPPDATA%\FeloListener,
  scheduled task at log-on, hidden). Auth = Tailscale identity + Origin header (verified the voice endpoints from the
  Proxmox host as Daniel). Delivery idea: Taildrop (`tailscale file cp … desktop-89vcnqk:`).

## 2026-10-26 Hey Felo model + listener delivered
Trained hey_felo.onnx (205 KB, felo-node-2, ~2 h). Training metrics: accuracy 0.65, recall 0.31, 0.71 false positives/h (harsh augmented test). Own test with unseen Microsoft voices: clean 41/60 caught (misses mostly full sentences in one breath), noisy 22/60; false wakes only "Hey fellow" (4/82 clean). Threshold 0.3. Package ops/felo-listener/ (also sent to desktop-89vcnqk by Taildrop). Fixes needed on the way: torch index, pyarrow 14, AudioSet now parquet, piper-sample-generator v2.0.0, DeepPhonemizer S3 403 (custom negatives only), --shm-size 2g. Next: record Daniel saying Hey Felo ~20x and retrain/verify for his voice. Container image felo-wakeword:env and /srv/wakeword/work (~20 GB) still on felo-node-2.
