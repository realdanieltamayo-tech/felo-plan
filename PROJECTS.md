# Felo projects

Rule: **one phase of one project at a time.** A phase ends with a handoff in `handoffs/`.
Ideas Daniel pitches go to `IDEAS.md` — they are not worked on until they become a phase here.

| ID | Project | Status | Active phase |
|---|---|---|---|
| PRJ-00 | Move from v1 to v2 + memory upgrade | **Done** (memory deploys waiting on Daniel's tap) | — |
| PRJ-01 | Platform safety & reliability | **Active** | 1.1 |
| PRJ-02 | Build Studio — the Developer department | Planned | — |
| PRJ-03 | Pilot client: oil, energy & mining equipment website | Planned (built with PRJ-02) | — |
| PRJ-04 | Separate departments into dedicated agents | Planned | — |
| PRJ-05 | Daily operations (email, calendar, CRM, files) | Planned | — |
| PRJ-06 | Growth (sales, marketing, social, design, finance) | Planned | — |
| PRJ-07 | Leadership & autonomy (chief of staff, strategist, analytics) | Planned | — |
| PRJ-08 | Client: Odalyake | On hold | — |

Order: PRJ-01 → PRJ-02 (PRJ-03 is its pilot) → PRJ-04 → PRJ-05 → PRJ-06 → PRJ-07. PRJ-08 when Daniel says.

---

## PRJ-01 Platform safety & reliability
Why first: professional clients will trust Felo with their data.
- **1.1 Lock down** — *in progress (started 2026-09-24)*
  - [x] Box 101 Hermes bridge (port 8000, no password, root, office Wi-Fi) switched off — unused since 2026-09-11.
  - [x] Box 100 git daemon (port 9418, anyone on Wi-Fi/Tailscale could read AND push every repo) switched off — nothing used it.
  - [x] Proxmox host rpcbind (port 111, open on Wi-Fi) switched off — no network file sharing in use.
  - [x] Only the deployer can move v2 `master`/`deployed` (pre-receive hook, tested). Repo copy of the deployer waiting for Deploy tap (branch `deployer-identity`).
  - [x] Calendar-suggestion phone alerts switched on (`/root/felo-v2-notify.py`, cron).
  - [ ] New private alert channel: prepared on box 100 (`/root/felo-v2-runtime/ntfy.env`); Daniel runs `felo-alerts-qr` on the Proxmox shell and subscribes → test alert → switch intake + watcher + notifier to it.
  - [ ] Nextcloud app password: Daniel creates a new one (needs core online) → `felo-set-secret nextcloud` → Claude applies + verifies → Daniel deletes the old one.
  - [ ] Google client secret: Daniel adds a new secret in Google Cloud Console → `felo-set-secret gmail-secret` → Claude applies + verifies Gmail → Daniel disables the old secret (this also makes the leaked v1 refresh token useless).
  - [ ] Decision: the Proxmox host allows root SSH login with a password from the office Wi-Fi — switch to key-only? (Daniel: how do you log in today?)
  - Note: core went offline 2026-09-24 15:30 UTC (felostudio.com, cloud, office = Cloudflare 530). Not caused by this phase (first change 15:31:28). Log: `/root/felo-plan-lockdown-*.log` on the Proxmox host.
- **1.2 Off-site & recovery** — v2 code to GitHub (repo `felo-codex-preview`/`felo-v2`, Daniel creates it); off-site database backup; one test restore.
- **1.3 Reliability** — optional: self-hosted alert server with a login instead of public ntfy.sh (lead alerts contain names and emails); chat backup brain when the work PC is off (needs Daniel's privacy decision); phone alert when a server on the Servers page goes down; put box 101 services (Gemma worker, supervisor, bridge) in git.
- **1.4 Clean up** — clear/archive the 7 waiting test projects; remove v1 leftovers after 2026-10-24.

## PRJ-02 Build Studio — the Developer department
Goal: websites and software good enough for professional clients, proven before Daniel sees them.
- **2.1 Foundations** — standard stack; Felo design system (tokens, fonts, polished page sections); spec template (pages, features, acceptance per page); reference-site intake; per-project workspace isolation.
- **2.2 The team** — separate agents: Architect (spec), Designer, Frontend dev, Backend dev on a top cloud model (Claude API); each with its own instructions, tools and project memory.
- **2.3 QA reviewer** — real browser screenshots at phone/tablet/desktop, performance/accessibility/SEO scores with minimums, tests + key flows, compare with references; failures go back to the developer automatically before Daniel sees anything.
- **2.4 Delivery** — private client preview link; Daniel approves; **push the finished project to its hosting place on Daniel's servers** (all servers are Daniel's; client sites get their own container/machine, separate from Felo's own boxes 100/101 — which machine is still to decide) with rollback.
- **2.5 Measure** — rounds to approval, quality scores, cost per project; tune.

## PRJ-03 Pilot client — oil, energy & mining equipment website
Client: a friend of Daniel who sells equipment to the oil, energy and mining industry. Not yet signed.
- **3.1 Discovery** — company info, products/catalogue, brand (logo, colours), 2–3 reference sites, pages, contact/quote flow, domain, and which of Daniel's machines hosts it (open question: new container on the Felo Proxmox host, core, or felo-node-1/2).
- **3.2 Design** — through PRJ-02 designer + Daniel review.
- **3.3 Build + QA** — through PRJ-02 team and QA reviewer.
- **3.4 Launch** — push to Daniel's server, domain, SSL, handover.
Depends on PRJ-02 2.1–2.3. Discovery (3.1) can be prepared early as the first real spec.

## PRJ-04 Separate departments into dedicated agents
Each department gets its own: instructions, AI model, tool access, memory scope, work queue. A front desk routes requests as handoff tickets; departments never share a conversation.
- 4.1 Ticket + routing layer · 4.2 Per-department memory scopes · 4.3 Tool allowlists · 4.4 Model per department (small local for sorting, larger local for private work, cloud for code/design/judgment).

## PRJ-05 → PRJ-07
See ROADMAP.md (phases P2–P4 of the published roadmap).
