# Handoff — finish-line #6: client websites on Felo core with one-tap Launch (built 2026-10-03)

Workflow (Daniel): build on Proxmox with Felo → run on Felo core → keep the release on Proxmox.

## Pieces
- **App** (branch `site-launch-all` e24098d = Nextcloud fix 1a3e543 + Launches; deploy #5573, waiting for Daniel's tap):
  `app/lib/launches.js` — table felo_launches (pending → approved → building → live | failed | rejected;
  live → rollback_requested → live on previous; older live rows → replaced). Page **/launch** (rocket icon in HQ menu):
  Launch / Skip, "look at it first" preview, first-launch Cloudflare instructions until the address answers, Roll back.
  Tools: `felo_request_launch` (Level 3, only asks), `felo_launches`. 33 tools. Tests 391 pass.
- **Host** `/usr/local/sbin/felo-site-launch [--rollback] <project> <hostname>`:
  box 101 collects public files only (html/css/js/images/fonts/pdf/txt/xml/json; no dotfiles, node_modules, tests,
  proposal/, .md) → box 100 builds `site-<project>:<YYYY.MM.DD-n>` FROM store nginx:1.30.5-alpine (sample files removed,
  security headers, /__felo_health, gzip, 1 h asset cache) → keeps `/root/felo-core/sites/<project>/<release>.tar.gz`
  (newest 5) → pushes to the store → core: service `site-<project>` 2 replicas, nodes only, felo-edge, health check,
  stop-first, auto-rollback (update-monitor 20 s) → checks inside the cluster (/__felo_health + index) and the public
  address. Prints JSON.
- **Host** `/usr/local/sbin/felo-launch-watch` (cron every minute, flock, felo-ran → Automations "Website launches"):
  carries out approved / rollback_requested, marks route_ok when https://<hostname>/__felo_health answers,
  stale "building" > 40 min → failed. Phone alert (ntfy) on every result.
- Store now also holds `nginx:1.30.5-alpine` (base for all sites).

## Tests (all on the real oil-equipment-site project, address launch-test.felostudio.com with no route = not public)
1st launch 52 s (2/2) · update -2 (stop-first) · rollback → -1 · project without index.html refused ·
deliberately broken image → swarm **rolled back by itself** to -1 (2/2 throughout) · full loop through the DB with the
watcher: approved → live -3 (prev -1) → rollback_requested → live -1. Published files checked: pages/fonts/images only;
BRIEF.md and .git → 404. Everything removed afterwards (service, store tags + empty repos, kept copies, test row).
Daniel's phone got 2 test alerts ("oil-equipment-site is live", "rolled back").

## First real launch of a client address
Daniel adds a Published application route in Cloudflare (felo-core tunnel): hostname → `http://site-<project>:80`.
A client domain must first be in Daniel's Cloudflare account (nameservers moved at the client's registrar).
Updates afterwards: one tap.

## After the Deploy tap (Claude)
- Restart Hermes (loads the 2 new tools); run `ops/skills-after-launch.py` on box 101 (felo-delivery go-live step →
  felo_request_launch; website playbook → hosted on Felo core). Backups *.before-launch-*.
- Live Nextcloud re-test (team-test → /Felo/Projects/team-test).
- Check /launch renders.

## Known / later
- Only one rollback step via Roll back (swarm keeps one previous spec); older releases stay in the store (5) and can
  be relaunched by hand if ever needed.
- Sites with server code (forms, databases) are not covered yet: static sites only. Forms can post to felo-leads.

## 2026-10-04 after the Deploy tap (done)
Deploys #5573 site-launch-all + #1028 nextcloud-projects live. Hermes restarted: 33 tools; #3 start check status 0.
Playbooks updated (ops/skills-after-launch.py). Live tool test: Nextcloud create/save/list in /Felo/Projects/team-test OK,
second save refused (no overwrite), path outside refused; felo_launches OK (empty). /launch behind owner login.
Test PDF removed from the workroom; Nextcloud /Felo/Projects/team-test (1 test PDF) left for Daniel to delete.
**Felo roots complete** (WhatsApp skipped by Daniel).
