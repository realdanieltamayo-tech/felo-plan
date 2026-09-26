---
name: felo-proposals
description: "How Felo writes a client quote / proposal for Felo Studio work: gather facts, pick published prices, fill the Felo Studio proposal design, senior-advisor review, PDF, CRM, then Daniel decides and sends. Use for ANY quote, estimate, proposal or price offer to a client."
version: 1.0.0
author: Felo
platforms: [linux]
metadata:
  hermes:
    tags: [Proposal, Quote, Sales, Felo, Client-Work]
    related_skills: [felo-website-playbook, felo-dev-team]
---

# Felo proposals and quotes

A proposal wins or loses the client. It must be clear, true, and priced from Felo Studio's published prices.
You prepare it; the senior advisor (Opus) checks it; **Daniel approves every price and sends it himself.**

Commands (terminal):
- `python3 /root/.felo-team/felo-team.py proposal-start <project> <CODE>` → `/workspace/projects/<project>/proposal/index.html`
  from the Felo Studio design, with its number FGC-YYYY-MMDD-CODE (CODE = 3 capital letters for the client, e.g. DGO).
- `python3 /root/.felo-team/felo-team.py proposal-pdf <project>` → refuses while any `{{...}}` blank is left; makes `proposal.pdf`.
- Daniel's preview (his devices): `https://felo-hermes.tail0ff06a.ts.net:8900/<project>/proposal/`

**Link the project to its client** as soon as you start: Felo tool `felo_project_link` (project, contact_id). It then shows on the client's page in the Clients hub and on Projects & jobs.

## 1. Facts first
Read the project's BRIEF.md (if any), the CRM (contact, lead), emails with the client, and memory. Write down:
the client's goal in their words, what they asked for, pages/features, language(s), deadline, who approves.
**Never invent** client facts, years, certifications, results or promises. Unknown → ask Daniel, or leave it out.

## 2. Price (from your identity: "Felo Studio published prices")
- Pick the published package(s) that fit: projects (one-time) + monthly service, or a bundle (Launch / Modernize / Operate).
  Say which package and why (e.g. "4 pages bilingual = starter site range").
- Inside a range, choose by scope and write one line of reasoning for Daniel (not in the proposal).
- Discounts, friend/pilot rates, anything below a range or not on the price list: **Daniel decides.** Ask him before
  finishing; until he answers, show the published price and tell him it is waiting for his decision.
- Double-check the math: totals, one-time vs monthly, 50/50 amounts.

## 3. Standard terms (Daniel, 2026-09-26) — use these unless Daniel says otherwise
- Projects: **50% to start, 50% before launch.**
- Proposal **valid 30 days.**
- **2 rounds of changes** per design included; more at $110–140/hour, agreed in advance.
- Monthly services start at launch, month to month, 30 days' notice. Client owns the work on final payment.
  Client data leaves with them, no exit fee. Anything outside scope is quoted in writing first.

## 4. Write it (Felo Studio design)
Run `proposal-start`, then replace every `{{...}}` in `proposal/index.html` (use a small Python edit, not sed, for long text):
title (the outcome, not "Website proposal") · goals in the client's words · what we will build (checkable deliverables) +
"not included" · phases with honest timing · investment table · terms · next steps + what we need from them.
Write in the **client's language** (Spanish sections: use the Spanish headings; set `<html lang="es">`). Short sentences,
no jargon, no hype. Delete sections that do not apply rather than leaving filler.

## 5. Senior advisor review (required)
Delegate to the Opus advisor with a short brief + the proposal text + the facts + which prices you used. Ask it to check:
facts vs sources, price vs published list, math, missing scope/terms, tone for this client, anything risky. Apply fixes.

## 6. PDF and record
- `proposal-pdf <project>` → fix anything it reports. Look at the result (Chrome screenshot if needed).
- CRM (Level 1): lead `stage: proposal`, `value_cents` = one-time total in cents, `next_step`: "Daniel reviews proposal
  FGC-…"; add a note with the proposal number, total and monthly.

## 7. Hand to Daniel (he decides and sends)
Tell Daniel in a few lines: number, what is offered, one-time + monthly total, the prices that need HIS decision,
the preview link. Then, only when he says so:
- **Share link** for the client: `felo_request_share` (Level 3). The client link is the share link + `proposal/` (e.g. https://…/s/<id>/proposal/).
- **Email draft** to the client with the link (`felo_email_draft`; he presses Send).
Never send, share or promise a price yourself.
