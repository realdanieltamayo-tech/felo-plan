# Ideas inbox

Daniel's ideas land here first. They are **not** worked on until they are turned into a project phase in `PROJECTS.md`.
Format: date · idea in Daniel's words (short) · where it probably fits · status.

| Date | Idea | Fits | Status |
|---|---|---|---|
| 2026-09-24 | Each department gets a dedicated agent/model so ideas, memories and information never mix | PRJ-04 | Planned |
| 2026-09-24 | Software and frontend developers must be excellent: modern, high-performance sites for professional clients | PRJ-02 | Planned |
| 2026-09-24 | All servers are Daniel's. Felo must push finished client projects to where they are hosted, kept separate from Felo's own boxes (host machine to decide) | PRJ-02 · 2.4 | Planned |
| 2026-09-24 | Pilot: website for a friend selling oil, energy & mining equipment | PRJ-03 | Planned |
| 2026-09-24 | Felo proposes improvements to itself through the Deploy queue | PRJ-07 | Idea |
| 2026-09-24 | SSH keys instead of the root password for the terminal login (laptop in the car + home work PC; one key each, then passwords off). fail2ban covers guessing for now | PRJ-01 (optional) | Idea |
| 2026-09-24 | tyx production server (Hostinger VPS 168.231.66.195, also holds core's restic store /opt/felo-restic) allows root SSH with a password from the whole internet and has no fail2ban. Harden (fail2ban + keys) — needs Daniel's OK, tyx is 'read, never change' | Security (new item) | Found, not started |
| 2026-09-24 | tyx is a failed product (Daniel's words). Later: build a new, better real-estate/CRM product on Daniel's own servers instead of tyx | New product (future project) | Idea - not scheduled |
| 2026-09-24 | tyx, Postiz and Temporal still run on the Hostinger VPS although tyx is retired. Shutting them down would shrink the attack surface next to the backups and free resources | Clean-up (after Daniel decides) | Idea |
| 2026-09-24 | Build Studio models: backend coding with Claude Code, frontend and images with Codex (Daniel believes Codex is best at that) | PRJ-02 · 2.2 | Decided |
| 2026-09-24 | Assistant brain stays Gemma; no Claude backup brain for chat | PRJ-01 · 1.3 | Superseded same day: brain = Claude |
| 2026-09-24 | Back up the Windows Codex bridge (code, settings, task) off-site too — today only a same-disk copy on the work PC | PRJ-01 1.3 or PRJ-02 | Idea |
| 2026-09-24 | Hermes is the only assistant and boss of the other agents; brain = Claude ("use you, you are the best at coding") | Steps 2–3 | Decided — being built (2.1) |
| 2026-09-24 | Felo must DO work, not just read: it manages a corporation with multiple products, services and future add-ons; main job = take workload off Daniel | Step 2.6 (permission levels) | Decided |
| 2026-09-24 | Felo supervises every business under FGC with one agent per business (Zubaloop, Cloud, agency, printing income, THE REBUILD) | PRJ-11 | Planned |
| 2026-09-24 | New business: printing & artwork store (order → warehouse → pay → pick up → ship → tracking) | PRJ-09 | Planned |
| 2026-09-24 | THE REBUILD real estate: website + CRM managed by Felo | PRJ-10 | Planned |
| 2026-09-24 | Research the best option/prices to get Felo Studio clients now | Task for Felo | Open |
| 2026-09-24 | Felo can open a workbench project's details (e.g. the Dogo Group LLC plan) and turn a roadmap into a checklist/task page with progress by phase (Daniel asked Felo for this; it could not yet) | Next small tools after 2.6 | Idea |

- **2026-09-24 — Codex for frontend/images (later).** Daniel: Claude is the main brain and does backend AND frontend for now. The Codex bridge on the work PC stays as-is; add a Codex frontend command to Felo's dev team only when Daniel says so.

- **2026-09-25 — Jobs panel on Felo HQ (step 9).** Live list of Felo's build jobs (project, running/done/failed, started, summary, preview link) so Daniel can see work in progress without asking in chat. Data: felo-team jobs in Felo's workroom (/workspace/jobs/*/job.json).
- **2026-09-25 — One chat thread per project/business (steps 5 + 9).** Today Felo HQ is one long conversation (felo-hq) for everything. Split into threads (Dogo Group, Zubaloop, Cloud, THE REBUILD, printing store, general) so topics do not mix; each thread starts with that project's brief/plan/memory. Pairs with the business supervisors (PRJ-11).

- **2026-09-25 — Branded preview address.** Client share links use felo-hermes.tail0ff06a.ts.net today; later preview.felostudio.com (needs DNS on core + a route).

- **2026-09-25 — Share approvals as a button in Felo HQ (step 9).** ✅ BUILT 2026-09-26 (deploy 4c8bf39). Daniel asked for an easy button instead of the Proxmox command. Design: Felo asks to share -> request shows on the Waiting page (project, who, days, preview) -> Daniel taps Approve -> link goes live; list of live links with a Turn off button. Same pattern as Deploy approvals (host-side watcher runs the action). Replaces felo-share-public for daily use.

- **2026-09-26 — Late answers appear in the HQ chat.** Advisor (Opus) answers and finished jobs re-enter Felo's conversation, but the HQ chat only shows them after Daniel writes again. Show them as they arrive (poll or push).
