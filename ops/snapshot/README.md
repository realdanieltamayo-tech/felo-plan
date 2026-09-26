# Felo setup snapshot (automatic, nightly)

Copied by `felo-ops-snapshot` on the Proxmox host every night at 03:20 (then mirrored to GitHub at 03:40).
- `host/`   Proxmox host: felo-* commands, cron jobs (share watcher, off-site backup)
- `box100/` Felo app box: runtime helpers, deploy / backup / mirror scripts, firewall, services, crontab
- `box101/` Hermes box: Hermes config, SOUL.md (Felo's identity), Felo's own skills, dev team (felo-team.py),
  share + preview services, old builder code, crontab
Secrets are never copied (*.env files are excluded and every file is scanned; see SKIPPED.md).
The Felo app code itself lives in the felo-v2 repo; plans and handoffs in the rest of this repo.
