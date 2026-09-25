# Felo projects

Rule: **one phase of one project at a time.** A phase ends with a handoff in `handoffs/`.
Ideas Daniel pitches go to `IDEAS.md` — they are not worked on until they become a phase here.

| ID | Project | Status | Active phase |
|---|---|---|---|
| PRJ-00 | Move from v1 to v2 + memory upgrade | **Done** (memory deploys waiting on Daniel's tap) | — |
| PRJ-01 | Platform safety & reliability | **Active** | 1.3 (waiting for Daniel's go) |
| PRJ-02 | Build Studio — the Developer department | Planned | — |
| PRJ-03 | Pilot client: oil, energy & mining equipment website | Planned (built with PRJ-02) | — |
| PRJ-04 | Separate departments into dedicated agents | Planned | — |
| PRJ-05 | Daily operations (email, calendar, CRM, files) | Planned | — |
| PRJ-06 | Growth (sales, marketing, social, design, finance) | Planned | — |
| PRJ-07 | Leadership & autonomy (chief of staff, strategist, analytics) | Planned | — |
| PRJ-08 | Client: Odalyake (paralegal office, immigration) | On hold | — |
| PRJ-09 | Printing & artwork store (new business) | Planned | — |
| PRJ-10 | THE REBUILD: real estate website + CRM | Planned | — |
| PRJ-11 | Business supervisors: one Felo agent per business, reporting to Felo | Planned | — |

Order: PRJ-01 → PRJ-02 (PRJ-03 is its pilot) → PRJ-04 → PRJ-05 → PRJ-06 → PRJ-07. PRJ-08 when Daniel says.

---

## PRJ-01 Platform safety & reliability
Why first: professional clients will trust Felo with their data.
- **1.1 Lock down** — **done 2026-09-24.** Handoff: `handoffs/2026-09-24-PRJ-01-1.1-lock-down.md`.
- **1.2 Off-site & recovery** — **done 2026-09-24.** Handoff: `handoffs/2026-09-24-PRJ-01-1.2-offsite-recovery.md`.
- **1.3 Reliability** — put box 101 code (Gemma worker, supervisor, gateway, bridge) into git — today it is only in the off-site backups; phone alert when a service on the Servers page goes down; optional: self-hosted alert server with a login instead of public ntfy.sh (lead alerts contain names and emails). *Decided 2026-09-24: the assistant brain stays on Gemma — no Claude backup brain. When the work PC is off, chat is down; the Servers page and the down-alert make that visible.*
- **1.4 Clean up** — clear/archive the 7 waiting test projects; remove the 7 old stopped `felo-codex-preview-pre-*` containers (hold old settings); remove v1 leftovers after 2026-10-24.

## PRJ-02 Build Studio — the Developer department
Goal: websites and software good enough for professional clients, proven before Daniel sees them.
- **2.1 Foundations** — standard stack; Felo design system (tokens, fonts, polished page sections); spec template (pages, features, acceptance per page); reference-site intake; per-project workspace isolation.
- **2.2 The team** — separate agents, each with its own instructions, tools and project memory. **Decided by Daniel 2026-09-24: backend coding = Claude Code; frontend and images = Codex.** Architect/spec and QA roles still to assign (propose when 2.2 starts).
  - *Existing piece found 2026-09-24 (read-only check):* **Codex bridge** already runs on Daniel's Windows work PC (100.109.89.77:8766, Windows task `Felo-Codex-Correction-Preview`, starts at logon). Uses the installed Codex CLI with Daniel's ChatGPT subscription (model `gpt-6-astra`, never paid API). Endpoints `/health`, `/correct` (bearer token; token DPAPI-protected on Windows). Strict: returns complete files only; no shell/browser/plugins; one job at a time; 10-min limit; box 101 re-validates. Used today only as the **repair** step after Gemma fails twice (worker `generate_codex`, `FELO_CODEX_URL` in `/root/felo-codex-preview/gemma-worker/worker.env` on CT101). Healthy; 13 successful corrections. Docs: `docs/codex-subscription-fallback.md`, `docs/windows-bridge-recovery.md`.
  - Gaps for Daniel's plan: no image generation; Codex (like Gemma) is down when the work PC is off; the Windows bridge is **not** in Felo's off-site backups (only a same-disk copy on Windows). Idea: a matching bridge for **Claude Code** (backend) on Daniel's Claude subscription, same limits.
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

## PRJ-09 Printing & artwork store
Website selling printing services (business cards etc.) and artworks. Order flow (Daniel): client orders → order on our dashboard → email design + measurements to the printing warehouse (never our price) → warehouse emails our cost → we pay → pick up → ship → client gets tracking → repeat. Daniel has a basic structure. Built by the Build Studio (step 7); Felo's printing supervisor runs the order flow.

## PRJ-10 THE REBUILD
Daniel's real estate business (realtamayo.com): website now, CRM later; a Felo supervisor for it.

## PRJ-11 Business supervisors
One supervising agent per business (Studio agency, Cloud, Zubaloop, THE REBUILD, printing store), each reporting to Felo, each tracking its income. Needs step 2.6 action tools + step 7 department agents first.
