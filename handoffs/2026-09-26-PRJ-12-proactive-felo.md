# Handoff — Felo speaks first (proactive Felo), DONE 2026-09-26

## What exists (CT101 Hermes cron, delivers to Daniel's Telegram DM)
- config.yaml: `timezone: America/Chicago` (cron times = Daniel's time, DST handled). Backup config.yaml.before-proactive-*.
- Tools for the cron platform trimmed to: terminal, file, skills, todo + MCP felo (web, browser, code, vision, image,
  tts, memory, session search, clarify, delegation, cronjob, computer use OFF).
- Job `morning-briefing` (10c91cfe250f): 07:30 daily, Sonnet, skill felo-dev-team, prompt /root/.hermes/scripts/prompt-briefing.txt
  (today's calendar, needs you, urgent account emails, follow-ups 3+ days, work done/running, one suggestion; <= 14 lines).
  Failure notices also to Telegram. Trial (via API, not sent): accurate and short.
- Job `felo-events` (a2145a136369): every 5 min, MONITOR mode: /root/.hermes/scripts/felo-events.py (no AI) prints the open
  list: LEAD (new website leads), EMAIL (unread Primary inbox, 2 days; automatic senders skipped unless the subject looks
  urgent: suspension, failed/declined payment, security, overdue...), JOB (coding jobs finished in 2 days). Felo's brain runs
  ONLY when the list changes; prompt /root/.hermes/scripts/prompt-events.txt: act only on new (+) lines — lead: draft a reply
  (not for tests/spam) + tell Daniel; email: say what the person wants, draft simple replies, flag urgent account problems;
  job: one line. Otherwise [SILENT]. First run (baseline) = [SILENT].
- Quiet hours 22:00–07:00 Central: the watcher repeats the last daytime list (state /root/.hermes/scripts/felo-events.last),
  so nothing wakes Felo at night. If Felo tools are unreachable, it also repeats the last list (no false alarms).
- Seeded the starting list (11 items) so 07:00 does not announce old items.

## Cost
Watcher: free every 5 minutes; Sonnet only on real changes (a few per day, ~2-5 cents each). Briefing ~5-10 cents/day.

## Manage
`hermes cron list | pause <id> | resume <id> | runs <id>` (run with /usr/local/lib/hermes-agent/venv/bin/python hermes ... on CT101).
Daniel can reply to Felo on Telegram (Telegram is its own conversation; HQ chat is another).

## Next
Voice (agreed order). Later: show proactive messages on HQ Home too; events for client-email replies from CRM contacts
could get their own rule; per-business supervisors reuse this pattern.
