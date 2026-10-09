# Handoff — tyxcrm (app + database) running on Felo core (2026-10-05)

Daniel: "do this set up in our servers" (Felo's Launch failed: tyxcrm is an app, not a static site).

## What runs
- **tyxcrm-db**: Postgres 16.15 (store image), 1 replica pinned to **felo-node-1**, data `/srv/tyxcrm/pgdata` (bind),
  network **tyxcrm-net** (overlay, encrypted, **internal** = no outside access), owner password = secret tyxcrm_owner_pw.
- **tyxcrm-app**: 1 replica on felo-node-1 (documents in `/srv/tyxcrm/uploads`), networks felo-edge + tyxcrm-net,
  port 3000, /health, start-first updates with auto-rollback. Gets ONLY tyxcrm_app_pw, tyxcrm_jwt, tyxcrm_jobs_token.
  Settings (app.json): production; EMAIL/SMS console, AI mock, billing mock, listings stub (all safe test mode).
- Secrets generated on core with openssl, never shown: tyxcrm_owner_pw, tyxcrm_app_pw, tyxcrm_jwt, tyxcrm_jobs_token.
- Verified: app role tyxcrm_app not superuser, no BYPASSRLS, owns no tables; 13/14 tables FORCE row-level security
  (14th = schema_migrations, app has no access); React screens served from the backend (same origin /api/v1).
- **v1 limit:** one machine (felo-node-1). If it fails, tyx is down until restored. HA Postgres = later project.

## Release recipe (owned by Felo core, not the project): box 100 `/root/felo-core/apps/tyxcrm/`
Dockerfile (stage 1 builds frontend/ with Vite; stage 2 backend npm ci --omit=dev --ignore-scripts, public = built
screens, USER node), felo-entry.sh (builds DATABASE_URL etc. from /run/secrets), app.json (service, networks, mounts,
secrets, env, migrate cmd, exclude list). Releases kept in apps/tyxcrm/releases/ (newest 5) + store `tyxcrm:<tag>`.

## Launch for apps
`/usr/local/sbin/felo-app-launch [--rollback] <project> <hostname>`: copy source (no .git/node_modules/dist/uploads/
tests/.env*) → build on box 100 → push → **migrations as a one-time swarm job** (replicated-job, owner + app secrets,
tyxcrm-net only) → if OK update the app (start-first, auto-rollback) → check inside + public /health.
felo-launch-watch now uses felo-app-launch when box 100 has apps/<project>/app.json. First release **2026.10.05-1** live.
Rollback never undoes database changes.

## Backups
`/usr/local/sbin/felo-core-app-backup` (host cron 04:10, Automations "Felo core app data backup"): pg_dump -Fc (checked
with pg_restore --list) + uploads tar → `/var/lib/felo-core-backups/tyxcrm/`, 14 days. felo-offsite-backup step
`core-apps` sends that folder off-site (first snapshot made). Restore tested into a scratch DB: 14 tables, then dropped.

## Not done / for Daniel
- **Address:** Felo asked for staging.tyxcrm.com, but tyxcrm.com DNS is at **lyttix.com** (A 209.126.82.19 — likely
  the old tyx host), not Cloudflare. Options: move tyxcrm.com nameservers to Cloudflare (Daniel at the registrar), or
  test now on a felostudio.com address. Cloudflare route (felo-core tunnel → Published application routes):
  hostname → `http://tyxcrm-app:3000`.
- Writing a "live" row into felo_launches was blocked (Felo's DB) — Felo makes a new felo_request_launch; Daniel taps.
- **Open sign-up** (/api/v1/auth/signup): anyone reaching the address can create a tenant. Daniel signs up first; Felo
  should add a switch to close sign-up before tyx is public.
- Follow-up job (POST /api/v1/jobs/run-followups with JOBS_TOKEN) has no scheduler yet (and sends are console-only).
- Demo seed NOT run in production.

## 2026-10-08 "I cant find tyx anywhere"
- Our tyx has **no working address**: staging.tyxcrm.com (DNS lyttix.com → 209.126.82.19) is the OLD tyx ("Invalid Tenant");
  tyxcrm.app (Hostinger parking DNS → 168.231.66.195) also old. Neither is on Cloudflare.
- Bug 1 (mine): the address check accepted ANY 200 → Launches row #3 shows "answering" because the OLD server answered.
  Fixed: felo-app-launch, felo-site-launch, felo-launch-watch count an address only if the answer comes through Cloudflare
  (cf-ray + server cloudflare) and send User-Agent felo-launch-check/1.0 (Cloudflare 403s Python's default UA).
  Row #3 still says route_ok=true (writing Felo's DB was blocked); the next launch corrects it.
- Bug 2 (mine): Felo's launch #4 (2026.10.08-1, same code as -2) "failed" at the database step: swarm replicated-job mode
  ran several copies at once → "tuple concurrently updated"; the launcher read one failed attempt. Fixed: migrations run as
  a plain 1-replica service with restart none (exactly one run); tested 3×. DB untouched (8 migrations, all from 2026-10-05).
- Backups: felo-*.before-cfcheck-202610082300, felo-app-launch.before-migrate-fix-202610082320.

## 2026-10-08 tyxcrm.app live
Daniel moved **tyxcrm.app** DNS to Cloudflare (nameservers rudy/zita.ns.cloudflare.com; registrar stays Hostinger). Kept: MX
mx1/mx2.hostinger.com, SPF, DMARC, autoconfig/autodiscover + 3 hostingermail DKIM CNAMEs (all DNS only). Deleted: apex A
168.231.66.195 (old tyx). Route felo-core → Published application routes: tyxcrm.app → http://tyxcrm-app:3000.
Verified: https://tyxcrm.app/health ok and / = tyxcrm screens, through Cloudflare. Felo's launches should use hostname tyxcrm.app.
