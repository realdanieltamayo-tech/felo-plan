# Handoff · PRJ-00 · v1 → v2 move + memory upgrade · 2026-09-24

**Status: done.** Two memory updates are built and waiting for Daniel's Deploy tap.
**Next phase: PRJ-01 · 1.1 Lock down** (see PROJECTS.md). Nothing else is in progress.

## Read first
- Daniel is the owner, not a developer. Short answers, plain words, say which machine a command runs on.
- Work rules: `PROJECTS.md` top · one phase at a time · ideas go to `IDEAS.md`, not into code.
- Machines: Proxmox host → CT100 `felo-orchestrator` (100.81.117.27) and CT101 `felo-hermes` (100.94.252.30). Core server (100.87.6.99) is off-limits for changes. Work PC 100.109.89.77 runs Ollama `gemma4:e4b`.

## What exists now (all on CT100 unless noted)
| Piece | Where | Notes |
|---|---|---|
| Felo v2 app (the only Felo) | container `felo-codex-preview-app`, image `felo-v2-runtime:current`, served at https://felo-orchestrator.tail0ff06a.ts.net:8443 | Owner-only (Tailscale login). Code bind-mounted read-only from the **live copy** `/root/felo-codex-preview/app`. Env: `/root/felo-v2-runtime/app.run.env` (600). Old container `felo-codex-preview-app-old` kept stopped. |
| Live copy (git) | `/root/felo-codex-preview` | **Never hand-edit** — the deployer refuses. Allowlist `.gitignore`. |
| Work copy | `/root/felo-v2-work` | Branch off `origin/master`, push to `/root/git/felo-v2.git`. |
| Deploys | cron `/root/felo-v2-deploy-watch.py` → `/deploy` page + ntfy; Daniel taps Deploy → `/root/felo-v2-deploy.sh` runs all tests in a sealed container, fast-forwards, restarts, health-checks, rolls back | Guide: `DEPLOY.md` in the repo. Copies in `ops/`. |
| Website lead intake | container `felo-v2-intake` on port 8080 (same address v1 used) → `felo_website_intake()` in the v2 DB (role `felo_website_intake`, EXECUTE only) | Env `/root/felo-v2-runtime/intake.env` (600). Docs `docs/website-intake.md`. Not yet proven with a real felostudio.com form submission. |
| Status pages | `/servers`, `/questions` ("Waiting for you") | `app/lib/status-pages.js` |
| Meetings from email | `/calendar` Felo calendar section; Gemma reads new inbox mail every 2 h 7am–9pm Central + button | `app/lib/email-calendar.js`, `docs/email-calendar.md`. Phone alert script `ops/felo-v2-notify.py` **not installed yet** (needs Daniel's OK; PRJ-01 1.1). |
| Memory | `felo_owner_memory` — 103 entries copied from v1 (74 active, 29 archived) | Waiting deploys: `3acf344` memory in every answer, `9f3d5a2` Keep/Drop suggestions (includes 3acf344). Deploy older first. Docs `docs/memory.md`. |
| Backups | `/root/backup-felo.sh` daily 03:30 (v2 DB only, keeps 14) + Proxmox vzdump nightly of CT100/101 | Final v1 dumps: `/root/felo-orchestrator-backups/v1-retire-20260924T124921Z/`. |
| v1 (retired) | `/root/felo-orchestrator` containers stopped, files kept; LAN block on 8080 via `felo-lan-block.service` | Delete leftovers after 2026-10-24. GitHub `felo-orchestrator` holds its history (`live-master` branch). |

## Tests
`docker run --rm --network none -e NODE_PATH=/app/node_modules -v $PWD:/w -w /w felo-v2-runtime:current sh -c "node --test tests/*.test.cjs"` in the work copy — 316 passing at `9f3d5a2`.

## Known problems / open items (carry into PRJ-01)
1. **Box 101 bridge `0.0.0.0:8000` — no auth, runs `hermes --yolo` as root, reachable from the office LAN.** Most serious open risk.
2. **Secrets printed in the 2026-09-24 session** must be rotated: Nextcloud app password (shared by v2), Gmail client secret (shared by v2) + v1 refresh token, ntfy topic `NTFY_TOPIC` (in `/root/felo-orchestrator/docker-compose.yml`, used by intake + notifiers), v1 AUTH_TOKEN and DB password (v1 stopped). Also a never-used intake password printed once (discarded).
3. v2 `HERMES_URL` points to `100.94.252.30:8001` where nothing listens; chat runs only on Gemma, so **chat stops when the work PC is off**.
4. The Codex snapshot for GitHub is staged but not pushed — Daniel must create an empty private repo (token can't create repos).
5. CT101 services (Gemma worker, supervisor, project gateway, bridge) are not in git.
6. Codex left an unfinished "candidate" release in `/root/felo-codex-preview/release-preparation/` — archived reference only; **do not deploy it**.

## Decisions Daniel made
- v2 is the keeper; Claude (not Codex) builds v2 from now on.
- Felo calendar (not Google write), local Gemma for email reading, button + every 2 hours.
- Memory: automatic use in answers; new memories only through Keep/Drop.
- Roadmap order: safety → Build Studio (with pilot) → department agents → daily ops → growth → leadership.
