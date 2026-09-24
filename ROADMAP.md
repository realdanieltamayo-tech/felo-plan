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
- 2.2 Felo's chat screen talks to Hermes → the same Felo on the screen and on Telegram.
- 2.3 Hermes gets Felo's tools (CRM, leads, calendar, email, memory, files, projects).
- 2.4 One identity + one memory (steps 4–5).
- 2.5 Hermes delegates: backend to Claude Code, frontend/images to Codex (step 7).

## 1. Home — the server
Made: Proxmox (Dell) with CT100 (Felo v2, DB, lead intake) and CT101 (Hermes, builder); work PC runs Gemma + Codex bridge; lock-down done (PRJ-01 1.1); nightly encrypted off-site backups, GitHub mirror, tested restore (1.2).
To do: CT101 code into git; down-alerts; Windows Codex bridge off-site backup; cleanup (1.3/1.4). Keep in mind: brain + Codex are down when the work PC is off.

## 2. Harness — Hermes
Made: Hermes running on CT101, Telegram gateway, built-in skills/memory/cron/kanban/browser/web/tts.
To do: confirm Hermes as the one harness; locked connection v2 ⇄ Hermes (old bridge was open and is off); v2 chat goes through Hermes.

## 3. Brain
Decided: brain = Claude (Hermes, Daniel's subscription); backend coding = Claude Code; frontend + images = Codex (bridge exists on Daniel's subscription). Gemma stays only for small local jobs if useful.
To do: model choice inside Claude (everyday vs hard tasks); watch subscription limits.

## 4. Who it is
Made: Hermes SOUL.md (2 KB, mostly safety); 74 facts in v2 memory; Felo Studio voice/design rules as memories.
To do: one "Felo identity" document (Daniel, company, brands, services/prices, projects, clients, how to work and speak) loaded by Hermes; Daniel reviews once.

## 5. Long-term memory
Made: v2 memory (103, used in every answer, Keep/Drop suggestions); Hermes has separate MEMORY.md/USER.md.
To do: one memory — Hermes reads/writes the Felo memory; later per client/project.

## 6. Skills
Made: 61 generic Hermes skills; v2 project templates.
To do: Felo's own skills (website build playbook, proposals/quotes, Felo Studio voice, client onboarding, deploy process); prune unused.

## 7. Tools
Made (in v2): Gmail read-only; Felo calendar + meetings from email; CRM + direct website leads; Nextcloud (test folder); web research; project builder (Gemma builds, Codex repairs, previews); deploy approvals.
To do: coding team (Claude Code backend, Codex frontend, QA reviewer) — was PRJ-02; designer/images via Codex; docs to real folders; email drafts; Google Calendar; engineer alerts; browser automation rules. Each becomes a Hermes tool after the first decision.

## 8. Channels
Made: Telegram (Hermes); private phone alerts; website form → CRM.
To do: WhatsApp (Hermes supports); Instagram + Facebook (Meta business app); ElevenLabs voice (needs key). Note: Postiz runs on the retired tyx server.

## 9. Interface — movie-style AI
Made: Felo HQ (purple space look, orb, agents, chat, agenda) + pages (Waiting, Servers, Deploys, Calendar, Email, Memory, CRM, Projects); owner-only.
To do: one consistent movie-AI design on every page (Codex); voice in/out; live activity; desktop/phone app.

## Outside the 9 steps
Client work (pilot oil/energy/mining site, Odalyake) needs the step-7 coding team · where client sites are hosted (open) · safety/approvals stay · retired tyx server (tyx, Postiz, Temporal, backups) · new product to replace tyx (idea) · cloud budget cap.

## Mapping to PROJECTS.md
PRJ-01 = step 1 · PRJ-02/03 = step 7 (coding team + pilot) · PRJ-04 = steps 2+5+7 (one assistant, per-department tools/memory) · PRJ-05 = step 7 (email/calendar/CRM/files) · PRJ-06 = steps 7+8 · PRJ-07 = steps 3+6 · interface = step 9.
