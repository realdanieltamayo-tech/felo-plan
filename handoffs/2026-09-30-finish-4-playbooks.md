# Handoff — finish-line #4: last playbooks (built 2026-09-30)

Three Hermes skills on box 101 (`/root/.hermes/skills/productivity/`), same format as felo-proposals / felo-website-playbook:
- **felo-studio-voice** — the Felo Studio voice (from memory #93 + design brief voice): positioning, 8 rules, how to write,
  naming (Felo Studio for clients; FGC Corp only legal), imagery, a check before handing to Daniel. Load before anything a client reads.
- **felo-client-onboarding** — client says yes: confirm with Daniel → CRM (stage won, category client, note, deposit-invoice
  task for Daniel) → project link + Nextcloud folder (task for Daniel until #5 gives a folder tool) + BRIEF.md → welcome
  email draft (next steps, what we need, two kickoff times; logins never by email) → kickoff call + agenda → follow-up
  tasks (one nudge per week max) → build work only after Daniel confirms the deposit.
- **felo-delivery** — final review (change rounds counted) → final 50% task, launch only after paid → LAUNCH.md for Daniel
  (hosting = Daniel's decision, DNS records, rollback) → after launch: check-site on files + browser check of live pages,
  felo_website_save, ask about open share links → HANDOVER.md + email draft (no passwords) → CRM close + 2-week check-in
  → LESSONS.md + felo_propose_memory.
Links added: felo-proposals ends with "yes → felo-client-onboarding"; website playbook phase 5 points to felo-delivery;
SOUL.md "How Felo Studio talks to clients" names the voice skill and the chain proposals → onboarding → website → delivery.
Backups: `*.before-playbooks-202609301*` next to each edited file. `felo-fresh-chats` run (2 threads).
`hermes skills list`: all three enabled. The nightly ops snapshot saves them (glob skills/*/felo-*).

Only real tools are named (checked in app/lib/felo-tools.js). CRM stage is free text; "won" is the value the dashboard
treats as closed.

**Not tested with Felo yet:** the Anthropic account hit its API usage limit 2026-09-30 12:11 CDT (back 19:00 CDT).
Test after that (box 101, dry run, only skill tools):
`hermes chat --query-file q.txt --oneshot -Q -t skills` with "TEST ONLY — DRY RUN ... Daniel says Dogo Group accepted
the proposal. Which playbooks, which steps?" Expect: felo-client-onboarding + felo-studio-voice, steps in order.

**Open questions for Daniel (defaults used until he answers):**
- Spanish with clients: tú or usted? (Playbooks say only "neutral Latin American".)
- Client email sign-off: identity says "Daniel Tamayo · Felo Global Concepts", but the Felo Studio voice rule says FGC is
  legal-only, never marketing. Should Felo Studio client emails be signed "Daniel Tamayo · Felo Studio"? (Unchanged for now.)
