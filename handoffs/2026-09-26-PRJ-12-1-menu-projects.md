# Handoff — PRJ-12 phase 1: working menu + Projects & jobs (built 2026-09-26, branch dashboard-phase1 e4a1971)

## What changed (felo-v2)
- app/hq.html menu: Home, Chat, Waiting (/questions, count from /api/hq/waiting), Projects & jobs (/projects, count),
  Clients (/crm), Inbox (/email), Calendar (/calendar), Shares (/share), Memory (/memory), System (/servers),
  Updates (/deploy), Settings (modal). Removed 9 empty placeholders (Agents, Files, Automations, Knowledge, Apps,
  Analytics, Integrations, "SOON" items). Removed the /api/hq/agents counter.
- Home right column: "Projects & jobs →" card now reads /api/hq/workroom (5 newest projects + running count);
  "The Brain" card = Sonnet everyday · Gemma local · Opus advisor (on call) · Claude Code coder (ready).
- app/preview.js: dropped 3 serve-time injections (Projects→/workbench link, Templates link, Waiting/Shares/Servers links);
  gate: GET /projects, /api/hq/workroom; mounts app/lib/workroom.js; table felo_workroom created at start.
- app/lib/workroom.js: /projects page (Running now · project cards with stage, last change, jobs done, links to
  preview/proposal/PDF/brief/plan on :8900, live client share links · Finished work with each job's task + summary).
- Old pages still reachable by address (not in the menu): /workbench (old builder, has the old Dogo project), /templates,
  /briefings, /updates, /crm-workspace, /model-settings, /existing-records, /migration-review.
- Tests: tests/workroom.test.cjs (data + page + gate + "every menu item is real"); 346 pass.

## Host (Proxmox)
- /usr/local/sbin/felo-workroom-sync, cron /etc/cron.d/felo-workroom-sync every minute: reads CT101 workroom
  (projects: stage/files/last commit/jobs done; jobs: status/times/task 400 chars/summary 1500 chars) via pct exec,
  writes felo_workroom id=1 in the v2 DB (dollar-quoted JSON). Stage rule: running job > proposal.pdf > index.html >
  PLAN.md > BRIEF.md > Started.

## Next (PRJ-12)
Phase 2 Clients hub; then Proactive Felo (agreed order: dashboard 1 -> proactive -> voice), later phases 3-7.
