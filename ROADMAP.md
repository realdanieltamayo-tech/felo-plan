# Felo roadmap — Daniel's 9 steps

Published page: https://claude.ai/artifact/A83xso7kLPuiFB4pjMbWXQ (keep in step with this file).
Rule: one step at a time; each step ends with something Daniel can see and use; handoff after each.

## First decision (blocks steps 2–8)
There are two Felos: **Hermes** (box 101: SOUL, memory, 61 skills, tools, Telegram, Claude brain) and **Felo v2** (the Codex-built app: its own chat, Gemma brain, memory, tools, screens). Daniel's list names Hermes as the harness. Proposal: Hermes = the one assistant (steps 2–8); Felo v2 = the screens (step 9) + business apps Hermes uses as tools (CRM, leads, calendar, deploy approvals). **Status: waiting for Daniel's confirmation.**

## 1. Home — the server
Made: Proxmox (Dell) with CT100 (Felo v2, DB, lead intake) and CT101 (Hermes, builder); work PC runs Gemma + Codex bridge; lock-down done (PRJ-01 1.1); nightly encrypted off-site backups, GitHub mirror, tested restore (1.2).
To do: CT101 code into git; down-alerts; Windows Codex bridge off-site backup; cleanup (1.3/1.4). Keep in mind: brain + Codex are down when the work PC is off.

## 2. Harness — Hermes
Made: Hermes running on CT101, Telegram gateway, built-in skills/memory/cron/kanban/browser/web/tts.
To do: confirm Hermes as the one harness; locked connection v2 ⇄ Hermes (old bridge was open and is off); v2 chat goes through Hermes.

## 3. Brain
Decided: assistant = Gemma (local); backend coding = Claude Code; frontend + images = Codex (bridge exists on Daniel's subscription).
To do: switch Hermes from Claude Sonnet (pay-per-use) to Gemma; consider a bigger Gemma that fits 12 GB; monthly cap for any cloud AI.

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
