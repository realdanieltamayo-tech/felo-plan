---
name: felo-outreach
description: "How Felo runs email outreach to potential clients from a lead list (Excel/CSV): keep the list in the workroom, pick the best leads, write short personal first emails and follow-ups as Gmail DRAFTS in small daily batches, track who got what, stop on reply. Use for ANY email campaign, cold email, prospecting or lead-list request."
version: 1.0.0
author: Felo
platforms: [linux]
metadata:
  hermes:
    tags: [Email, Outreach, Sales, Leads, Felo]
    related_skills: [felo-studio-voice, felo-proposals, felo-client-onboarding]
---

# Felo outreach playbook

Goal: win Felo Studio clients with emails that read like Daniel wrote them to one person. Few, personal, well aimed beats many.
Outreach goes from Felo Studio's own mailbox info@felostudio.com: drafts with felo_info_draft, replies checked with felo_info_inbox / felo_info_read. (Daniel's personal Gmail tools are only for his own mail.) If the info@ tools say the inbox is not connected, stop and tell Daniel. Sending is Level 3: Felo only writes DRAFTS; Daniel reads and sends. Never send.

## 1. The lead list (cheap, once)
- Daniel sends the Excel/CSV on Telegram (lands in /root/.hermes/cache/documents/) or names a file. Copy it to
  /workspace/outreach/<list-name>/source.<ext> and never edit the original.
- Read it with ONE python script (openpyxl / csv), not by hand: write /workspace/outreach/<list-name>/leads.csv with columns
  id, company, contact name, role, email, phone, website, city/country, industry, notes, status, last_step, last_date.
  status starts as "new". Report to Daniel: how many rows, how many with email, duplicates, obvious junk, top industries.
- Do NOT create every lead in the CRM up front (it costs a tool call each). A lead goes into the CRM (felo_crm_create,
  lead + contact) only when its first draft is written.

## 2. Ask Daniel before the first batch (once per list)
Which offer (published felostudio.com prices only, from memory/identity; never invent prices), which industry or city to start
with, English or Spanish, and the daily batch size (default 15, max 30). Show 2 sample drafts first; start the batch after he says go.

## 3. Each batch
- Pick the next leads with status "new" that best fit the offer. Skip: no email, generic info@ for huge companies, competitors,
  anyone who unsubscribed (status "stop").
- Look at each lead's website briefly ONLY if it is in the list; one quick check, no deep research (cost).
- Write the first email (felo-studio-voice):
  - Subject: short, specific, lower-key (e.g. "Quick idea for <Company>'s website"). No clickbait, no ALL CAPS.
  - 60-120 words. One real observation about THEIR business, one clear benefit, one small ask ("Worth a 15-minute call this week?").
  - From Daniel, first person. Plain text feel, no images, at most one link (felostudio.com).
  - Language of the lead (Spanish = neutral Latin American, tú/usted as fits a business contact).
  - Footer, always: "Felo Global Concepts · <business address from memory; if unknown, ask Daniel once and remember it>"
    and "If this isn't relevant, just reply 'no thanks' and I won't write again."
- Save each with felo_info_draft; update leads.csv (status "sent?" -> Daniel sends; last_step 1, last_date) and create the CRM
  lead + a follow-up task in 4 days.
- Tell Daniel in one short message: "<N> drafts ready in Gmail for <segment>. Send them when you like."

## 4. Follow-ups
- Before each batch, check replies in info@ (felo_info_inbox with from=<lead address> and days since last_date; read with felo_info_read).
  Replied -> status "replied", stop the sequence, tell Daniel who and what they said, draft a reply if easy.
  "no thanks"/unsubscribe -> status "stop", never write again. Bounce -> status "bad email".
- No reply after 4 days -> follow-up 1 (2-3 lines, new small value point). After 7 more days -> follow-up 2 (short, polite close).
  Then status "done". Max 3 emails per person, ever.

## 5. Limits that protect felostudio.com
Max 30 new drafts per day across all lists (Gmail limits and spam reputation). No attachments in first emails. No buying or
scraping lists. Keep a short results note in /workspace/outreach/<list-name>/RESULTS.md (sent, replies, calls, wins) and
summarise it to Daniel weekly.

## 6. CRM stages (Daniel tracks outreach on the Clients page — keep them exact)
Every lead that gets a draft is in the CRM (contact + lead, source "outreach: <list-name>", category "outreach"). Set the lead
stage with felo_crm_update, always one of:
- `draft ready` — first email is in info@ Drafts, Daniel has not sent it yet.
- `contacted` — Daniel sent it (he tells you "sent", or the draft is gone from info@ Drafts). Add a note: date + subject.
- `follow-up 1` / `follow-up 2` — that follow-up was sent.
- `replied` — they answered (put a 1-line summary of the reply in next_step and tell Daniel).
- `call booked` — a meeting is set (also add it with felo_calendar_add_event).
- `proposal` — a proposal was sent (felo-proposals skill).
- `won` — became a client. `not interested` — said no, or asked not to be contacted (never write again). `bad email` — bounced.
- `no reply` — 3 emails, no answer: sequence finished.
When Daniel asks "who did I email / who answered", answer from the CRM stages, with counts per stage.
