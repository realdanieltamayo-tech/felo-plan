# MASTER HANDOFF — Felo, everything so far (2026-09-30)

Written for Daniel and for any fresh session. The detail of each phase is in its own handoff in this folder; this file is the
whole picture in one place. Page version: see ROADMAP.md header for the published links.

## 1. Where we are today (2026-09-30)

- **Felo works.** Hermes (box 101) is the one assistant, Felo HQ (box 100) is its screens and tools. Daniel talks to Felo
  directly in Felo HQ, the Felo app on his iPhone, and Telegram.
- **All of PRJ-12 is built and deployed** (business dashboard, proactive Felo, voice, neural look) and finish-line #1
  (chat threads + late answers) and #2 (installable app).
- **Talk mode (hands-free voice conversation) is deployed** (last deploy a751fa0). Hearing in English is correct.
- **Daniel tested Talk mode (2026-09-30):** "works, not excellent but it does the job" — polish later (IDEAS.md).
- **#3 Hermes update safety: built 2026-09-30** (handoffs/2026-09-30-finish-3-hermes-update-safety.md).
- **#4 last playbooks: built 2026-09-30** (handoffs/2026-09-30-finish-4-playbooks.md); Felo test pending (API limit hit today).
- **#5 last tools: live 2026-09-30** (deploy #790; follow-up branch felo-calendar-only waits for a Deploy tap) (branch last-tools, handoffs/2026-09-30-finish-5-last-tools.md).
- **Next build step:** #6 waits for the Felo core cluster (core + felo-node-1/2). Felo roots #1-#5 done; #7 WhatsApp skipped. Daniel wants the Felo roots finished before a personal project. WhatsApp (#7) skipped for now (Daniel, 2026-09-30).

**How client work flows (Daniel, 2026-10-01):** build on Proxmox with Felo (workroom, box 101) → push ready sites and
software to Felo core (the swarm) → always keep the released copy on Proxmox as the backup and the base for updates.
Each release is a versioned copy (git tag + image) so a bad update rolls back. Data created live on core (form entries,
app databases, uploads) is NOT on Proxmox: it needs its own backup from core (to Proxmox + off-site).

## 2. The system

| Part | Where | What it does |
|---|---|---|
| Proxmox host "proxmox" | Dell, Xeon X5670, 24 threads, 62 GB | Runs box 100 + box 101, nightly vzdump 04:00, off-site backup 04:30, host automations |
| Box 100 (CT100 felo-orchestrator) | 8 cores | Felo v2 app `felo-codex-preview-app` (Felo HQ + all pages + Felo tools MCP :8090), Postgres `felo-codex-preview-db`, website lead intake `felo-v2-intake` (:8080), voice service `felo-voice` (speak + listen), plan repo `/root/felo-plan` |
| Box 101 (CT101 felo-hermes) | | Hermes Agent v0.21 (`/root/.hermes`): Felo's brain harness, Telegram, cron jobs, API server :8642 (only box 100), sandbox `hermes-840bd48b` where Felo's dev team and workroom live |
| Work PC 100.109.89.77 | Windows | Ollama `gemma4:e4b` (free local model for small jobs), Codex bridge (not used now) |
| Core server | office | felostudio.com, cloud.felostudio.com, office.felostudio.com via Cloudflare. **Read-only for us** unless Daniel says yes. On Wi-Fi (went down once) |
| Hostinger VPS 168.231.66.195 | | Off-site encrypted backups (account felo-backup), retired tyx/Postiz/Temporal |
| GitHub realdanieltamayo-tech | | Private mirrors: felo-v2, felo-plan |

**Addresses:** Felo HQ `https://felo-orchestrator.tail0ff06a.ts.net:8443` (Tailscale only) · private previews
`felo-hermes…:8900` · public share links through Tailscale Funnel :443 → share server 127.0.0.1:8096 (Daniel turned it on).

**Brains (tiers, to save money):** everyday Felo = Claude Sonnet 5 (medium reasoning) · senior advisor = Opus 5.5 (only via
delegation, important work) · chat compression = Haiku 4.5 · titles, supervisor reports, long reading = Gemma (free) ·
ALL coding = Claude Code on Daniel's Claude subscription (Codex later, in IDEAS).

**Permission levels for Felo's actions:** L1 just do (internal, undoable) · L2 do and tell · L3 ask first (client emails,
posts, payments, going live, deleting, public links).

## 3. How work is done (rules that still apply)

- One phase of one project at a time; a handoff in `handoffs/` after each phase. Ideas Daniel pitches go to IDEAS.md, not built.
- Nothing goes live on Felo v2 without Daniel's **Deploy** tap: work in `/root/felo-v2-work` (box 100) on a branch → push to
  `/root/git/felo-v2.git` → it appears on `/deploy` → Daniel taps → tests run sealed → live copy `/root/felo-codex-preview`
  (never hand-edit it; `.gitignore` is an allowlist — new folders must be added).
- Tests: `docker run --rm --network none -e NODE_PATH=/app/node_modules -v $PWD:/w:ro -w /w felo-v2-runtime:current sh -c "node --test tests/*.test.cjs"`.
- Secrets: never printed, never pasted in chat. Daniel sets them with `felo-set-secret <name>` over **SSH** (the Proxmox web
  console scrambles pastes). Claude does not move logins/credentials and does not open public tunnels; Daniel runs those.
- Only Daniel instructs Felo on business work (he talks to Felo himself). Claude builds Felo itself.
- Daniel is not a developer: give exact taps and say which machine; no code for him to edit. Keep it simple; watch token cost.

## 4. Everything built (by Daniel's 9 steps)

**Step 1 Home (server)** — PRJ-01, done 2026-09-24/26
- Lock-down: bridge off, git daemon off, rpcbind off, fail2ban on SSH, master protected by a pre-receive hook, all leaked secrets rotated, phone alerts (ntfy).
- Off-site: nightly encrypted restic backup to the VPS (Daniel holds the password), test restore passed, GitHub mirrors.
- Reliability: nightly setup snapshot into `ops/snapshot`, `felo-watchdog` down-alerts every 5 min, fixed silent cron failures, every host job wrapped by `felo-ran` (logs result for the Automations page).
- Clean-up: test projects and old app copies removed. v1 retired (only v2 left; v1 files deleted after 2026-10-24).

**Step 2 Harness (Hermes)** — done 2026-09-24
- 2.1 Hermes API server, key, firewall (only box 100). 2.2 Felo HQ chat goes through Hermes. 2.3 Felo tools MCP server (now 28 tools). 2.4 one identity (`identity/FELO.md` → SOUL.md) + one memory (Felo memory; Hermes' own off). 2.5 dev team (Claude Code, restricted). 2.6 action tools with permission levels.

**Step 3 Brain** — 2026-09-26: the tiers above. Cost fix after ~$20 on day one: compression at ~80k tokens, background review off, Sonnet everyday.

**Step 4 Who it is** — SOUL.md = FELO.md: businesses, prices, rules. 2026-09-30: language rule "answer in the language of Daniel's LATEST message; Spanish = neutral Latin American with tú".

**Step 5 Memory** — v2 memory (103 facts from v1) used in every answer; Keep/Drop suggestions.

**Step 6 Skills** — website-build playbook + check-site checker + private previews; 42 unused skills off (prompt 19.3k → 15.8k tokens); quotes & proposals playbook (Felo Studio PDF, advisor review; terms 50% start / 50% launch, valid 30 days, 2 revision rounds).

**Step 7 Tools** — CRM create/update, calendar, Gmail read + email drafts (Daniel sends), share preview links + Share button, websites, automations, money (Stripe read-only, one account for Zubaloop + Cloud), project links, supervisor reports.

**Step 8 Channels** — Telegram (text + voice notes both ways), phone alerts, website form → CRM, morning briefing 7:30 (text + voice), `felo-events` every 5 min (Felo speaks first when something happens; quiet 22–07).

**Step 9 Interface** — Felo HQ organized like the corporation (PRJ-12): Home command center, Projects & jobs, Clients hub, Websites, Automations, Products & Money, Team, Inbox & calendar, System. Neural look (violet core, rings, neurons). Chat threads per business with unread badges; late answers from the advisor appear by themselves. Installable app (iPhone "Add to Home Screen"). Voice: spoken answers + Talk mode (tap once, talk naturally, Felo answers aloud and listens again; say "stop"/"bye" to end).

**Businesses supervised (PRJ-11):** lite supervisors (script + Gemma, Sonnet only on new ATTENTION) for the slow businesses at 7:00–7:12; the full Sonnet supervisor is reserved for income businesses such as the future printing store.

**Client work:** PRJ-03 Dogo Group (Lucas Osorio, oil/energy/mining equipment): pitch preview built and shared, proposal FGC-2026-0926-DGO started — paused ("don't worry about Dogo now"). Lucas **Tamayo** is the test contact.

## 5. What we learned from errors (read before changing anything)

**Safety and secrets**
- Never print settings/env files, even "masked" — masking failed twice. Compare hashes or list key names only. A secret check once printed FELO_MCP_KEY → it was rotated on both boxes.
- When the safety guard blocks an action (moving login tokens, a no-permissions coder, opening a public tunnel), redesign so Daniel does the step himself; never work around it.
- Proxmox web console scrambles pasted secrets → use SSH; `felo-set-secret` cleans input and checks the key type (Stripe must be `rk_live_` restricted, tested read-only).

**Scheduled jobs**
- Host cron has no `/usr/sbin` in PATH (`pct` lives there) → backups and the share watcher failed silently. Every cron file now has a PATH line and runs through `felo-ran`.
- ntfy headers must be latin-1: an em dash made alerts fail silently.
- Restarting Hermes kills a running cron job (the morning briefing was cut) → `cron_drain_timeout 240` + systemd `TimeoutStopSec=300`. Restart Hermes only when no job is running.

**Hermes**
- **A Hermes API conversation keeps the instructions (SOUL.md) it started with.** After changing SOUL.md, run `felo-fresh-chats` on box 101 (backs up, gives every Felo HQ thread a fresh start; screen history stays). This is why Felo kept answering in Spanish.
- Advisor (async delegation) results land as a user message and Hermes doesn't answer until the next message → `felo-late-answers` (host, every minute) makes Felo report them and saves an unread turn.
- **2026-10-04:** Hermes stores those results as display-only rows the model does NOT see, so Felo only got "task finished" (tyx DB advice got stuck). Fix: felo-late-answers now pipes the stored TEXT into app/scripts/late-answer.js (lib/late-answer.js puts it in Felo's message), and scans every result of the last 2 h, not just the newest message. App branch late-answers-text (Deploy tap). Backup: felo-late-answers.before-text-202610041530.
- Local fixes are lost when Hermes updates: the Opus 5.5 mandatory-thinking patch (`agent/anthropic_adapter.py`) and faster-whisper in the Hermes venv (install with `/root/.hermes/bin/uv`). Since 2026-09-30 `felo-hermes-fixes` (box 101) puts them back at every Hermes start and every 15 min.
- Cost: long chats re-read 100k+ tokens per call and cache writes happen after every 5-minute pause. Keep compression low, use tiers, Gemma for reading/reports.

**Code and files**
- Shell heredocs with apostrophes broke repeatedly → write scripts to files and run them.
- Some files use CRLF line endings → edit single anchored lines and keep the line endings.
- `.gitignore` is an allowlist → a new folder (e.g. `voice/`) is silently left out of the deploy until added.
- Test harness needs every new `./lib/*` module passed through in `tests/helpers.cjs`; the fake DB must learn new queries.

**Voice on iPhone**
- The browser's speech recognition doesn't work in the iPhone app → record audio and transcribe on box 100 (faster-whisper `base`).
- STT took 12 s on 2 cores → box 100 raised to 8 cores, 8 threads → ~5 s.
- Forcing the EN/ES toggle language turned English into Spanish → only compare en vs es for short (≤3 s) phrases, keep the clearer one.
- iPhone switches the mic off after an `<audio>` element plays → in Talk mode Felo's voice plays through Web Audio (same session as the mic), and a muted/ended mic is replaced automatically.
- Docker build failed because Debian already has a group "voice" → the service user is `felovoice`.

**Data and people**
- Don't "correct" business facts from guesses: Lucas Osorio is the real client (Dogo), Lucas Tamayo is the test contact. The Sandro lead (sandro@test.com) is test data.

## 6. What's left

**Verify now (Daniel):** Talk mode on iPhone — English answers, keeps listening without tapping.

**Finish line (one at a time):**
3. Hermes update safety — **built 2026-09-30** (`felo-hermes-fixes`, box 101).
4. Last playbooks — **built 2026-09-30** (felo-client-onboarding, felo-delivery, felo-studio-voice).
5. Last tools — **live 2026-09-30** (PDF in drafts, Nextcloud folders). **Decision (Daniel, 2026-09-30): the calendar is the Felo calendar; Daniel has never used Google Calendar — do not connect or suggest it.**
6. Where client sites live + one-tap launch — **live 2026-10-04** (handoffs/2026-10-03-finish-6-site-launch.md). Was: waits for "Felo core" (Daniel, 2026-09-30): Felo core = core server +
   felo-node-1 + felo-node-2, not connected together yet; Daniel may do that in another chat. Client sites go there.
   Status 2026-09-30 evening: 3-node Docker Swarm, 3 managers, **failover proven** (worker and leader down: 0 failed requests).
   handoffs/2026-09-30-felo-core-cluster.md. felo-leads secrets fix done 2026-10-01 (runs on the swarm, not live yet). Release store done 2026-10-02. Cloudflare tunnel felo-core done 2026-10-03: **leads.felostudio.com runs on the swarm**. Next: #6.
7. WhatsApp — **skipped for now** (Daniel, 2026-09-30); needs a phone number.
Optional: Instagram/Facebook, ElevenLabs voice, QA reviewer.

**Dated:** stop old felo-leads container on core after 2026-10-10 · remove v1 leftovers after 2026-10-24 · check the real API cost around 2026-10-10.

**Daniel's to-dos:** core server on ethernet · Anthropic monthly spending limit · Google OAuth out of testing mode ·
tell us where Zubaloop is hosted · dismiss test leads (Felo offered) · one real felostudio.com form test.

**Later projects (planned):** PRJ-04 separate department agents · PRJ-05 daily operations · PRJ-06 growth · PRJ-07 leadership ·
PRJ-08 Odalyake (on hold) · PRJ-09 printing & artwork store · PRJ-10 THE REBUILD website + CRM.

## 7. Where things are

| What | Where |
|---|---|
| Plan of record | box 100 `/root/felo-plan` (ROADMAP.md, PROJECTS.md, IDEAS.md, handoffs/, identity/FELO.md, ops/snapshot) |
| Roadmap page | https://claude.ai/artifact/A83xso7kLPuiFB4pjMbWXQ |
| Felo v2 code | box 100 work copy `/root/felo-v2-work`, repo `/root/git/felo-v2.git`, live `/root/felo-codex-preview` (read-only) |
| App settings | box 100 `/root/felo-v2-runtime/` (`apply-app-env.sh KEY=VAL`) — never print |
| Hermes | box 101 `/root/.hermes` (config.yaml, SOUL.md, cron/jobs.json, state.db, response_store.db, scripts) |
| Felo's workroom + dev team | box 101 sandbox home/workspace; `felo-team.py` (build, review, check-site, local, proposal-start/pdf, jobs) |
| Host helpers | `felo-set-secret`, `felo-share-public`, `felo-watchdog`, `felo-late-answers`, `felo-offsite-backup`, `felo-restore-test`, `felo-ran` |
| Box 101 helper | `felo-fresh-chats` (after any SOUL.md change) |

## 8. How a new session starts

Read this file, then ROADMAP.md "Finish line", PROJECTS.md and the newest handoff. Confirm with Daniel the one active phase,
then work on it only, and write its handoff when done.

- **2026-10-05 watchdog:** Hermes reaps a finished cron worker before it records done, so delivered briefings showed "Interrupted by shutdown" (Oct 3 + 4) and alerted Daniel. The watchdog now checks Hermes' delivery record (cron/executions.db → deliveries.db) for that error and treats a delivered run as OK (hermes_delivered()). Backup felo-watchdog.before-delivered-202610050130.
- **2026-10-04 Gmail disconnected** ("authorization is no longer accepted") — Google testing mode ends tokens after ~7 days. Daniel: Email → Reconnect Gmail; publish the OAuth app to stop it.
- The morning-briefing job loads the felo-dev-team skill every run (not needed; extra tokens). Clean up later.

- **2026-10-05 three fixes (Daniel):**
  (a) Watchdog check `anthropic` ("Felo's AI account"): reads Hermes errors.log/agent.log on box 101; alerts when the last Anthropic answer was a block (credits / usage limit / key) with no success since; clears on the next success. Backup felo-watchdog.before-anthropic-202610050215. Fired at once: **credits ran out 2026-10-04 22:48 UTC** — Felo down until Daniel adds credits.
  (b) Felo HQ long jobs: Node fetch has a hidden 5-min first-byte limit → "Hermes is not reachable" during Felo's 26-min build. hermes-chat now uses plain http (1 h cap); after 4 min the screen says "still working", the real answer is saved later as unread (branch still-working, Deploy tap).
  (c) Dev team may install npm packages: felo-team.py ALLOWED + npm install/ci/view/ls; NPM_ENV = official registry only, ignore-scripts on (enforced by Claude Code allowlist + npm config, not a firewall). Backup felo-team.py.before-npm-202610050200. Verified: tyxcrm installs; its 24 tests fail because embedded-postgres refuses root (needs createPostgresUser: true) — Felo's dev team to fix.
