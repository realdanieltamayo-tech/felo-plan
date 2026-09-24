# Felo projects

Rule: **one phase of one project at a time.** A phase ends with a handoff in `handoffs/`.
Ideas Daniel pitches go to `IDEAS.md` — they are not worked on until they become a phase here.

| ID | Project | Status | Active phase |
|---|---|---|---|
| PRJ-00 | Move from v1 to v2 + memory upgrade | **Done** (memory deploys waiting on Daniel's tap) | — |
| PRJ-01 | Platform safety & reliability | **Active** | 1.2 |
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
- **1.1 Lock down** — **done 2026-09-24.** Handoff: `handoffs/2026-09-24-PRJ-01-1.1-lock-down.md`.
- **1.2 Off-site & recovery** — *in progress (started 2026-09-24)*
  - [x] Codex snapshot preserved as tag `archive-codex-snapshot-2026-09-24` in `/root/git/felo-v2.git` (was only in a temp folder).
  - [x] Keys made: GitHub deploy keys on CT100 (`~/.ssh/felo_v2_github`, `~/.ssh/felo_plan_github`, one repo each, write); off-site key on the Proxmox host (`/root/.ssh/felo_offsite_backup`).
  - [x] GitHub: private `realdanieltamayo-tech/felo-v2` + `felo-plan`, one write deploy key each; copied automatically after every push (post-receive hooks) + nightly 03:40; phone alert on failure. Whole history scanned first: 0 secrets.
  - [x] Off-site: encrypted restic store on the Hostinger VPS in a locked SFTP-only account (`felo-backup`, chroot `/srv/felo-backup`, cannot see core's backups). Nightly 04:30 from the Proxmox host (`/usr/local/sbin/felo-offsite-backup`): database, box 100 settings/keys/repos/plan, box 101 settings/code, host settings; Sundays full container copies + keep policy (14 daily / 8 weekly / 6 monthly) + integrity check. Phone alert on failure.
  - [x] Hostinger VPS hardened: root keys only, fail2ban (office IP exempt), Felo's root key removed (only `core-backup` left).
  - [x] Test restore passed (`felo-restore-test`): 39/39 tables, 616/616 rows identical to live; Felo started from restored code + settings.
  - [ ] Daniel saves the backup password in his password manager (`felo-backup-key` on the Proxmox shell) and deletes the `felo-offsite-backup@proxmox` key from the Hostinger panel.
- **1.3 Reliability** — optional: self-hosted alert server with a login instead of public ntfy.sh (lead alerts contain names and emails); chat backup brain when the work PC is off (needs Daniel's privacy decision); phone alert when a server on the Servers page goes down; put box 101 services (Gemma worker, supervisor, bridge) in git.
- **1.4 Clean up** — clear/archive the 7 waiting test projects; remove the 7 old stopped `felo-codex-preview-pre-*` containers (hold old settings); remove v1 leftovers after 2026-10-24.

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
