# Handoff — PRJ-12 phase 4: Automations (built 2026-09-26, branch automations)

- /usr/local/bin/felo-ran <name> <cmd...> on host, box 100, box 101: runs a scheduled job and writes
  /var/lib/felo-automations/<name>.json {start,end,exit}. Wrapped: host cron.d (watchdog, share-watch, workroom-sync,
  ops-snapshot, offsite-backup; backup /root/.felo-backup/cron.d.before-ran), box 100 root crontab (deploy-watch, notify,
  github-mirror; backup /root/crontab.before-ran), box 101 cron.d (share-expire).
- Watchdog collect_automations() (backup /root/.felo-backup/felo-watchdog.before-automations): registry AUTOMATIONS (13:
  key, title, plain description, where, schedule, expected minutes, source) -> felo_automations (upsert; stale keys
  deleted). Sources: felo-ran records; offsite-backup also /root/.felo-backup/last-status; vzdump via
  `pvesh get /nodes/<node>/tasks --typefilter vzdump --limit 1`; box 100 felo-backup.service/timer via systemctl show;
  Hermes jobs via /root/.hermes/cron/jobs.json (last_run_at, last_status, next_run_at). Alerts: last run failed, or
  overdue (> max(3x interval, interval+30 min)), and "working again".
- To add an automation: wrap its cron line with felo-ran <key> and add a row to AUTOMATIONS in felo-watchdog.
- app/lib/automations.js: /automations page + /api/hq/automations; Felo tool felo_automations (read). Menu "Automations".
- Tests: 358 pass.
