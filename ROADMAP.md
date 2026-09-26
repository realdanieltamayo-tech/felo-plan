# Felo roadmap — Daniel's 9 steps

Published page: https://claude.ai/artifact/A83xso7kLPuiFB4pjMbWXQ (keep in step with this file).
Rule: one step at a time; each step ends with something Daniel can see and use; handoff after each.

## Decided 2026-09-24 (Daniel)
- **Hermes is the only assistant and the boss of the other agents.** Felo v2 becomes the screens (step 9) + business tools Hermes uses (CRM, leads, calendar, deploy approvals). Both boxes stay.
- **Brain = Claude** (replaces "assistant = Gemma"). Hermes already signs in with Daniel's Claude subscription (not pay-per-use). Coding: Claude Code (backend), Codex (frontend + images).
- The link: Hermes' built-in API server (key-protected; chat, sessions, runs with approvals, skills, toolsets), locked so only box 100 can reach it.

## Hermes' brain (decided 2026-09-24)
- Anthropic **API key** (Daniel's Console account, prepaid credits, monthly limit), not the subscription login. Old login kept only in CT101 `/root/.hermes/.env.before-api-key-*`.
- Model **claude-opus-5-5** (the strongest for complex coding/multi-step jobs; ~2x Sonnet price), `reasoning_effort: high`. Backups: `config.yaml.before-opus-*`.
- Local fix in Hermes: Opus 5.5 added to `_MANDATORY_THINKING_CLAUDE_SUBSTRINGS` (agent/anthropic_adapter.py; backup `/root/.hermes/anthropic_adapter.py.before-opus-*`). **Re-apply after any Hermes update.**
- Working 2026-09-24: Hermes answers on claude-opus-5-5 via the API key (9 s, ~18k input tokens per message ≈ 7 cents before caching). Still introduces itself as "Hermes Agent by Nous Research" → fix in step 4. Base prompt size → trim in step 6. Note: the $100 Claude app credit does not apply to the API.
- Later (step 7): heavy coding through Claude Code itself, which may use Daniel's Claude subscription legitimately (it is Anthropic's own app).

## Order of work for steps 2–3 (one sub-step at a time, each visible)
- 2.1 Turn on Hermes' API server — **done 2026-09-24.** Port 8642 on CT101, key in CT101 `/root/.hermes/.env` (API_SERVER_*) and CT100 `/root/felo-v2-runtime/hermes.env`; firewall `felo-hermes-api-guard` (systemd) drops 8642 from everything except box 100 (100.81.117.27). Tested: answers with key in ~7 s; no key / wrong key = 401; Wi-Fi and other Tailscale devices blocked; Telegram reconnected. Settings backup: CT101 `/root/.hermes/.env.before-api-server-*`. (Servers page still points at the old dead address — fixed in 2.2.)
- 2.2 Felo chat screen talks to Hermes — **done 2026-09-24** (deploy c923234 + settings FELO_CHAT_PROVIDER=hermes, HERMES_API_URL, HERMES_API_KEY in app.run.env). Tested over Tailscale: top bar Claude online, Servers page all working, chat answered by Hermes in 7 s. Same assistant/memory/skills as Telegram; separate conversation (Hermes can search past sessions). Switch back = FELO_CHAT_PROVIDER=ollama via /root/felo-v2-runtime/apply-app-env.sh. Until 2.3 the chat cannot use Felo tools (CRM, Felo calendar/memory, email/file commands); their pages still work.
- 2.3 Hermes gets Felo tools — **done 2026-09-24** (deploy 8724624). MCP server inside the app on port 8090 (`app/lib/felo-tools.js`), key FELO_MCP_KEY (`/root/felo-v2-runtime/tools.env` → app.run.env), firewall `felo-tools-guard` on box 100 (only 100.94.252.30), Hermes `mcp_servers.felo` in CT101 config.yaml (backup `config.yaml.before-felo-tools-*`). 12 tools: 10 read (waiting, servers, new leads, CRM search/get, calendar, email search/read, memory search, projects) + 2 propose (memory → Keep/Drop, calendar event → Confirm). No send/delete/pay/CRM writes. Tested: Wi-Fi + other devices blocked; Hermes answered a real question with felo_new_leads + felo_waiting in 14 s. Not yet: Nextcloud files tool.
- 2.4 One identity + one memory — **done 2026-09-24.** Identity `identity/FELO.md` (Daniel reviewed; his answers + felostudio.com published prices) installed as Hermes SOUL.md (backup `SOUL.md.before-felo-*`). Felo memory corrected (23 audited changes: Odalyake = paralegal/immigration, Stripe live for Cloud + Zubaloop, tyx retired, Zubaloop awaiting Meta, Artiria/Ledger paused, printing store, THE REBUILD, prices, Hermes-note facts). Hermes' separate memory switched off (`memory_enabled: false`, `user_profile_enabled: false`; old notes in CT101 `/root/.hermes/memories/archive-*`). Tested: answers as Felo, correct Office price, correct Odalyake, Spanish.
- 2.5 ✅ DONE 2026-09-24 — Hermes delegates ALL coding (backend + frontend) to Claude Code on Daniel's Claude subscription, checks it, reports. Codex later (IDEAS). Handoff: handoffs/2026-09-24-PRJ-02-2.5-dev-team.md
- 2.6 **Action tools with permission levels** — **done 2026-09-24** (deploy 169dc2c). Level 1: felo_crm_create / felo_crm_update (contacts, leads, notes, tasks) as actor agent:felo through the normal CRM save path (version check, audit); Level 2: felo_calendar_add_event (confirmed + activity feed). No send/post/pay/delete (Level 3 = draft and ask). Identity updated. Real test: Felo created follow-up task #3 for the oil-company lead (Lucas Osorio, due 2026-09-28), verified it itself; audit + Home activity recorded.

## 1. Home — the server
Made: Proxmox (Dell) with CT100 (Felo v2, DB, lead intake) and CT101 (Hermes, builder); work PC runs Gemma + Codex bridge; lock-down done (PRJ-01 1.1); nightly encrypted off-site backups, GitHub mirror, tested restore (1.2).
To do: CT101 code into git; down-alerts; Windows Codex bridge off-site backup; cleanup (1.3/1.4). Keep in mind: brain + Codex are down when the work PC is off.

## 2. Harness — Hermes
Made: Hermes running on CT101, Telegram gateway, built-in skills/memory/cron/kanban/browser/web/tts.
Done (2.1–2.6): Hermes is the one assistant; locked link v2 ⇄ Hermes; v2 chat goes through Hermes; Felo tools (read, propose, act L1/L2); dev team (Claude Code).

## 3. Brain
Done 2026-09-26 (brains work together): Felo everyday = Sonnet 5; senior advisor = Opus 5.5 (delegation, important work only); chat summaries = Haiku 4.5; titles + long reading = Gemma on the work PC (free); coding = Claude Code. Handoff: handoffs/2026-09-26-PRJ-07-3.1-brain-tiers.md
Before: brain = Claude Opus 5.5 via API key (Hermes); ALL coding = Claude Code on Daniel's Claude subscription (2.5). Codex later (IDEAS). Gemma stays only for small local jobs if useful.
To do: check real daily cost after a few days; watch Claude subscription limits (Claude Code).

## 4. Who it is
Made: Hermes SOUL.md (2 KB, mostly safety); 74 facts in v2 memory; Felo Studio voice/design rules as memories.
Done (2.4): identity/FELO.md installed as Hermes SOUL.md; Daniel reviewed.

## 5. Long-term memory
Made: v2 memory (103, used in every answer, Keep/Drop suggestions); Hermes has separate MEMORY.md/USER.md.
Done (2.4): one memory (Felo memory; Hermes' own memory off). Later: memory per client/project/department.

## 6. Skills
Made: 61 generic Hermes skills; v2 project templates.
Done 2026-09-24: website-build playbook skill + check-site quality checker + private previews (:8900). Handoff: handoffs/2026-09-24-PRJ-07-6.1-website-playbook.md
To do: proposals/quotes, Felo Studio voice, client onboarding, deploy process; prune unused.

## 7. Tools
Made (in v2): Gmail read-only; Felo calendar + meetings from email; CRM + direct website leads; Nextcloud (test folder); web research; project builder (Gemma builds, Codex repairs, previews); deploy approvals.
Done 2026-09-26: Share button — Felo asks, Daniel taps Share on the Shares page (deploy 4c8bf39). Handoff: handoffs/2026-09-26-PRJ-05-7.2-share-button.md
Done 2026-09-25: client share-preview links (frozen copy, ends by itself, Level 3; Daniel switches public on with felo-share-public). Handoff: handoffs/2026-09-25-PRJ-05-7.1-share-preview-links.md
Done: coding team = Claude Code for backend + frontend (2.5). To do: QA reviewer; Codex frontend later (IDEAS); designer/images via Codex; docs to real folders; email drafts; Google Calendar; engineer alerts; browser automation rules. Each becomes a Hermes tool after the first decision.

## 8. Channels
Made: Telegram (Hermes); private phone alerts; website form → CRM.
To do: WhatsApp (Hermes supports); Instagram + Facebook (Meta business app); ElevenLabs voice (needs key). Note: Postiz runs on the retired tyx server.

## 9. Interface — movie-style AI
Made: Felo HQ (purple space look, orb, agents, chat, agenda) + pages (Waiting, Servers, Deploys, Calendar, Email, Memory, CRM, Projects); owner-only.
To do: one consistent movie-AI design on every page (Codex); voice in/out; live activity; desktop/phone app.

## The businesses Felo runs (Daniel, 2026-09-24)
Felo manages every business under FGC, each with its own **supervising agent** that reports to Felo (Felo = the boss of the department agents):
- **Felo Studio — agency** (brand & presence, systems & infrastructure; published prices on felostudio.com)
- **Felo Studio Cloud** (live, Stripe live)
- **Zubaloop** (live product, Stripe live, waiting for Meta approval to sell subscriptions)
- **THE REBUILD** — Daniel's real estate business (website now, CRM later)
- **Printing & artwork store** — NEW, to build. Flow: client orders on the site → order on our dashboard → email design + measurements to the printing warehouse (they never see our price) → warehouse emails our cost → we pay → pick up → ship → client gets tracking. Daniel has a basic structure for it.
- Paused: Artiria, Ledger. Retired: tyx (a better replacement later).
Supervisors per business are built after step 2.6 (action tools) and step 7 (department agents); each business also needs its income tracked (finance).
Open task for Felo: research the best offer/prices to win clients now.

## Outside the 9 steps
Client work (pilot oil/energy/mining site, Odalyake) needs the step-7 coding team · where client sites are hosted (open) · safety/approvals stay · retired tyx server (tyx, Postiz, Temporal, backups) · new product to replace tyx (idea) · cloud budget cap.

## Mapping to PROJECTS.md
PRJ-01 = step 1 · PRJ-02/03 = step 7 (coding team + pilot) · PRJ-04 = steps 2+5+7 (one assistant, per-department tools/memory) · PRJ-05 = step 7 (email/calendar/CRM/files) · PRJ-06 = steps 7+8 · PRJ-07 = steps 3+6 · interface = step 9.

## Cost (2026-09-26)
First ~24 h on the API: about $20. Two long chats made up ~$17: Daniel's HQ chat (64 calls) and the pilot relay (80 calls), each re-reading ~100-125k tokens per call. About 70% of the cost was cache writes (Opus 5.5 $5/M), which happen after every 5-min pause and every big tool result. After-chat background reviews added ~$1.60.
Fixed: compression at ~80k tokens (threshold 0.08, was 500k); background review off (CT101 config backup config.yaml.before-cost-*).
Decided 2026-09-26: tiers (see step 3).
