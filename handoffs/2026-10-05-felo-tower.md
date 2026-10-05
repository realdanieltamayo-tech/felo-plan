# Handoff — Felo Tower: live view of the AI team at work (built 2026-10-05, branch factory)

Daniel: "a dashboard where I can see all agents working, like animated workers in a factory or building, and on what they are working."

- **Page /factory** (menu item "Tower", also linked from Team): cross-section of "Felo Tower", one floor per team, CSS-animated
  workers (type when busy, rest with "z z" when idle, red lamp on a problem), speech bubble = what it is doing; an elevator moves
  to the busiest floor. Floors: 6 Felo's office (open Hermes turns from Felo HQ/Telegram: chat title, current tool, steps, time),
  5 Senior advisor (open subagent turns), 4 Dev workshop (running Claude Code jobs: project, task line, time), 3 Business
  supervisors (felo_automations supervisor-* + latest felo_supervisor_reports), 2 Watch room (felo-events, morning briefing),
  1 Maintenance robots (every other automation). Plus "Latest work" (felo_actions). Polls /api/hq/factory every 20 s.
- **Data:** CT101 `/usr/local/sbin/felo-live-activity` (read-only: agent.log tail for open turns + last tool, state.db titles,
  workroom jobs/*/job.json + task.txt first line; no message text) → host `/usr/local/sbin/felo-live-sync` every minute
  (`/etc/cron.d/felo-live-sync`, via felo-ran key live-sync) → table felo_live in the v2 DB.
  An open turn with no log line for 20 min counts as finished.
- App: `app/lib/factory.js`, owner gate GET /factory + /api/hq/factory. Tests: tests/factory.test.cjs; 400 pass.
- Ideas for later: click a worker to open its chat/job; add live-sync to the Automations page registry; Gemma/work-PC desk.
