---
name: felo-website-playbook
description: "How Felo runs a client website project from first brief to Daniel's go-live approval: brief, plan, build in jobs with the dev team, quality check, preview, delivery. Use for ANY website for a client or for one of FGC's own businesses."
version: 1.0.0
author: Felo
platforms: [linux]
metadata:
  hermes:
    tags: [Website, Playbook, Felo, Client-Work]
    related_skills: [felo-dev-team]
---

# Felo website playbook

Clients are professionals. The site must look like a high-performance company built it, and every fact on it must be true.
You manage the project; Claude Code builds it (felo-dev-team skill); you check it; Daniel approves.
Prices and bundles come from your identity (Felo Studio section). Never invent a new price; if nothing fits, ask Daniel.

Tools: `python3 /root/.felo-team/felo-team.py build|review|check-site|jobs <project> ...`
Preview (Daniel's devices only): `https://felo-hermes.tail0ff06a.ts.net:8900/<project>/`

## Phase 1 — Brief (before any code)

Collect, from Daniel, the CRM (felo_crm_search / felo_crm_get), emails (felo_email_search) and memory (felo_memory_search):
- **Business:** legal name, what they sell, to whom, where (cities/countries), what makes them different, years, certifications.
- **Goal of the site:** calls, quote requests, catalog, trust. The ONE action a visitor should take.
- **Content:** products/services list, photos, logo, brand colors, contact info (phone, email, address, hours), languages (English/Spanish?).
- **Pages:** default = Home, About, Products/Services, Contact (+ a page per main product line if they have many).
- **Practical:** domain name, deadline, bundle/price agreed (or not yet), who approves.

Write it to `/workspace/projects/<project>/BRIEF.md` with two lists: **Known facts** (with where each came from) and
**Missing — ask Daniel**. Never fill a gap with invented facts: use clearly marked placeholders like
`[PHONE — confirm with client]`, and list them. Log a CRM note on the client: "Website brief started".

## Phase 2 — Plan (Daniel sees it before building)

Write `/workspace/projects/<project>/PLAN.md`: sitemap, each page's sections in order, the call-to-action, design direction
(3–5 lines: mood, colors, fonts, photo style), and the job list for phase 3. Default tech: plain HTML/CSS/JS (fast, cheap to
host, no build step); a small Node backend only for things that need it (contact form sending, catalog search).
Send Daniel the short version in chat and wait for "go" (spending hours of work = ask first; it is not live, so it is not Level 3,
but Daniel decides direction on client work).

## Phase 3 — Build in jobs (one job at a time, check each one)

Typical jobs (give Claude Code BRIEF.md + PLAN.md by telling it to read them first):
1. Design system + Home page (colors, type, spacing, header, footer, buttons in `styles.css`; responsive).
2. The other pages, reusing the same header/footer/styles.
3. Contact / quote form (front end + a small backend that stores the request; sending email stays off until Daniel approves).
4. Polish pass: SEO titles/descriptions, favicon, social preview tags, accessibility, speed (small images, no unused code).

After EVERY job: `review <project>` and `check-site <project>`, read the main files, then fix with a follow-up job until
check-site says PASS and it looks right. Tell Daniel after each job in 2–3 lines with the preview link.

## Phase 4 — Quality gate (all must be true before you call it done)

- check-site PASS on every page; tests pass if there is a backend.
- Every fact matches BRIEF.md "Known facts"; no placeholder left (or Daniel knowingly accepted each one).
- Looks right on phone and desktop (ask Daniel to open the preview on his phone).
- Consistent header/footer/styles on every page; one clear call-to-action per page.
- Nothing sends email, charges money or talks to an outside service without Daniel's approval.
- README.md explains how to run it and what settings it needs.

## Phase 5 — Delivery (Level 3: ask Daniel first)

Going live, pointing a domain, emailing the client, sending an invoice = **ask Daniel first**, every time.
Prepare for him: preview link, what is in it, open decisions, where it will be hosted (open decision: Daniel's own
servers), and the price/bundle. After it goes live: CRM note "Website delivered", and a task for monthly care if the
bundle includes it.

## Your own businesses

Same playbook for FGC's own sites (THE REBUILD realtamayo.com, the printing & artwork store, Zubaloop pages): Daniel is the client.
