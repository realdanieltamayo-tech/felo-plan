# Handoff — finish-line #3: Hermes update safety (built 2026-09-30)

Problem: a Hermes update can drop Felo's two local fixes. (1) Opus 5.5 patch: `_MANDATORY_THINKING_CLAUDE_SUBSTRINGS` in
`/usr/local/lib/hermes-agent/agent/anthropic_adapter.py` must include claude-opus-5-5 (Opus 5.5 refuses thinking disabled).
Hermes' updater stashes/restores local edits, but can park the stash on conflict. (2) faster-whisper in the Hermes venv: an
optional extra (`voice`, pinned in pyproject.toml), so the updater's dependency sync can remove it. Neither was checked after updates.

Built (box 101, ops files, no Felo app change so no Deploy tap needed):
- `/usr/local/sbin/felo-hermes-fixes` (system python3, not the Hermes venv): checks both fixes, puts back what is missing
  (patch: adds the Opus names to the tuple, compiles, restores the file if compile fails; whisper: `/root/.hermes/bin/uv pip
  install --python venv/bin/python faster-whisper==<pin from pyproject>`). Restarts hermes-gateway only if it changed something
  (drain drop-in lets running jobs finish). Exit 1 + log `/var/log/felo-hermes-fixes.log` if a fix cannot be put back, e.g.
  Hermes renamed the list -> check by hand whether Opus 5.5 still needs it.
- `/etc/systemd/system/hermes-gateway.service.d/felo-fixes.conf`: `ExecStartPre=-felo-hermes-fixes --no-restart`,
  TimeoutStartSec=300. Every update restarts Hermes, so the fixes are in before Hermes loads. "-" = Hermes starts even if a fix fails.
- `/etc/cron.d/felo-hermes-fixes`: every 15 min via felo-ran -> Automations page row "Hermes update safety" (host watchdog
  AUTOMATIONS list; backup `felo-watchdog.before-hermes-fixes-202609301730`). A failure = phone alert (existing watchdog logic).
- All three files are picked up by the nightly ops snapshot (globs felo-*, hermes-gateway.service*).

Tests: copy with the stock adapter + empty venv -> both put back in ~2 s, exit 0; second run "all fixes in place"; renamed list
-> exit 1 with message. Live run: all fixes in place; Automations row shows ok.
Test on copies: `HERMES_DIR=/copy HERMES_PY=/copy/venv/bin/python felo-hermes-fixes --no-restart`.

Adding a future local fix: add a fix_* function in felo-hermes-fixes and list it in main().
Not done: the start hook itself was not exercised with a real Hermes restart (to avoid cutting chats); it runs at the next restart.
