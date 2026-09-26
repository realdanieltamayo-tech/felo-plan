# Handoff — PRJ-12 phase 5b: business supervisors (built 2026-09-26/27, branch supervisors f33bd06)

- One Hermes scheduled agent per active business, fresh session each run (no mixing), Sonnet, deliver local (no Telegram):
  supervisor-felo-studio (a27d80084bf7) 07:00 · supervisor-felo-studio-cloud (4080df7298d9) 07:04 ·
  supervisor-zubaloop (fbdbc54902e1) 07:08 · supervisor-the-rebuild (6db596220b39) 07:12 (Central).
  Prompts: CT101 /root/.hermes/scripts/supervisors/<key>.txt (business key + focus list). Skills: felo-supervisor
  (/root/.hermes/skills/productivity/felo-supervisor/SKILL.md) + felo-dev-team.
- Supervisor playbook: read own last 3 reports -> gather facts for its business only (felo_money, felo_websites, CRM,
  jobs) -> compare -> Level 1 actions only (CRM follow-up task, product next step) -> felo_supervisor_report
  (status ok|attention, summary 3-6 sentences incl. ONE next action, numbers, actions). Never contacts customers.
- Felo app (deploy f33bd06): felo_supervisor_reports table; tools felo_supervisor_report / felo_supervisor_reports;
  Products cards show the latest report.
- Morning briefing prompt: step 5b mentions only businesses with status "attention" (else "All businesses OK" + MRR).
- Watchdog AUTOMATIONS: 4 supervisor entries (alert if a supervisor fails or stops running).
- Printing store: supervisor added when the store exists (same pattern: prompt file + cron create + AUTOMATIONS row).

## Changed the same day (Daniel): LITE supervisors for businesses without real income; FULL (Sonnet) for income businesses
- LITE (now: felo-studio, felo-studio-cloud, zubaloop, the-rebuild): Hermes jobs supervisor-<key> 07:00/04/08/12, MONITOR
  mode with /root/.hermes/scripts/supervise-<key>.py (wrapper -> felo-supervise.py, business via FELO_SUPERVISE env).
  The script (no AI): collects facts via Felo tools (felo_money, felo_websites, felo_new_leads, workroom jobs), compares
  with the last report, finds problems (site down/slow/cert < 14 d, failed payment, income drop, real lead waiting 2+ days,
  failed coding job), has Gemma (work PC) write the summary (template if Gemma is off), SAVES the report, and prints stable
  "ATTENTION <key> | ..." lines. Hermes wakes Sonnet only when those lines change (new problem) -> prompt
  /root/.hermes/scripts/supervisors/lite-prompt.txt: investigate, Level 1 actions, improved report; else [SILENT].
- FULL (for businesses producing income, e.g. printing store when live): Sonnet daily job with the full prompt
  (/root/.hermes/scripts/supervisors/<key>.txt, skill felo-supervisor):
  hermes cron create "16 7 * * *" "$(cat .../<key>.txt)" --name supervisor-<key> --deliver local --failure-deliver local --skill felo-supervisor --skill felo-dev-team
  (+ AUTOMATIONS row in felo-watchdog).
- First run 2026-09-26 (manual): felo-studio attention (Sandro #19 and Lucas #25 leads still stage "new"), cloud ok, rebuild ok,
  zubaloop attention (failed $9.99 payment Sep 22 from "Daniel A Tamayo" — probably Daniel's own/test subscription).
