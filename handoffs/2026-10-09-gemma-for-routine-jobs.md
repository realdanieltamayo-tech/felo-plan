# Handoff — routine jobs moved to the free local Gemma (night of 2026-10-08/09)

Daniel: "move whatever Gemma can handle so the Claude API only takes care of the important stuff like coding and the
senior advisor." October API spend Oct 1-8 ≈ $27 (Sonnet ≈ $20.5, Opus ≈ $6.8); ~75% of it cache WRITES.

## Finding: Gemma cannot drive Felo as an agent
Test: morning briefing run by Hermes with Gemma (provider workpc-gemma) → it made 1 of ~6 tool calls (Felo's tools are
deferred behind tool_search, which Sonnet uses and Gemma does not) and then CLAIMED the others "failed". So: no Gemma
agents. Pattern used instead (same as the supervisors): a SCRIPT collects every fact deterministically, Gemma only
WRITES (and classifies one email at a time YES/NO). Plain gemma4:e4b via the OpenAI endpoint gets only a 4k window;
scripts call Ollama's native /api/chat with num_ctx (16k) — or the felo-gemma-worker model (65k) via Hermes.

## What changed (box 101)
- config.yaml: providers.workpc-gemma (http://100.109.89.77:11434/v1, felo-gemma-worker:latest, 65k). Not used by any
  job now; kept for tests. Backup config.yaml.before-gemma-*.
- Scheduled jobs (backup cron/jobs.json.before-gemma-*): ALL six now no_agent (script = the job, zero Claude):
  - felo-events (every 5 min) → scripts/felo-events-gemma.py: detection = felo-events.py (unchanged, quiet hours),
    new lines vs felo-events-gemma.seen (first run = baseline), facts per item (lead details, email text, job summary),
    test data skipped (test.com/example/Sandro/Lucas Tamayo), Gemma YES/NO per email (7/7 correct on real subjects),
    Gemma writes ≤8 lines. **No email drafting** (stays on Claude: "Want a reply drafted? Ask me in Felo HQ").
    Gemma down → plain message (nothing missed). Dry-run: `felo-events-gemma.py --dry "<fact>"`, `--triage`.
  - morning-briefing (7:30) → scripts/felo-briefing-gemma.py: calendar, waiting, emails (triaged), leads (test skipped),
    jobs, supervisor reports + income; Gemma writes ≤14 lines + a ≤90-word spoken version; edge-tts
    en-US-AvaMultilingualNeural → MEDIA:…mp3 + [[audio_as_voice]]. Gemma down → plain facts, no voice. `--facts` test.
  - supervisor-* (4) → their existing supervise-*.py (script + Gemma report) as the whole job; the Sonnet follow-up on
    new problems is gone. felo-supervise.py now skips test leads by email/summary/known names too (Sandro false alarm
    fixed). Backup felo-supervise.py.before-gemma-only.
  - All: dev-team / supervisor skills removed from the jobs (were loaded every run, unused).

## Still on Claude (by design)
Felo HQ / Telegram chats (Sonnet 5: orchestration, tools, dev team, advisor calls), the senior advisor (Opus 5.5),
chat compression (Haiku 4.5, small), late answers (a chat turn). Coding = Claude Code on the subscription.
Not changed: cache_ttl 5m (1h makes one-shot advisor writes 2x; net unclear without a week of chat-only data).
Ideas: Sonnet 5.5 for chats (same price); measure chat cost for a week, then decide on cache_ttl 1h.

## Check in the morning
07:00-07:12 supervisors and 07:30 briefing are the first real Gemma runs (voice note included). felo-events baseline
taken 00:05 (8 lines), runs every 5 min, silent at night.
