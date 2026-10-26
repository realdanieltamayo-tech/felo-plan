# Handoff — PRJ-03 Dogo Group / Texas Supply: back office built (2026-10-17)

Daniel (2026-10-16): "proceed into working on the rest of the roadmap for this project until I come back." Claude ran each phase as a Felo dev-team job (felo-team.py build) on box 101 and checked every phase by rerunning the tests.

## Projects (box 101, workspace/projects/)
- oil-equipment-site — public websites (tab model from Daniel's sketch: Home / Dogo Group LLC — USA / Texas Supply SRL — Argentina, EN+ES). 29 tests. Forms carry form.endpoint (empty = preview, nothing sent). To go live: set "/api/public/contact" in content/*.json and rebuild.
  Preview for Daniel: https://felo-hermes.tail0ff06a.ts.net/s/pAFwALr4Kww1JICPE2HqeEXn8H8ns7Sy/ (expires 2026-10-30; it's a snapshot from before the form wiring, which doesn't change how the pages look).
- dogo-backoffice — Node 20/Express/Postgres, plain JS UI, EN/ES. 109 tests (embedded Postgres; the app runs as a non-superuser role).
  1. Login/users/roles: the owner sees both companies (switcher); staff see one company only (AR). Postgres row-level security, forced, fails closed. CLI: npm run create-owner.
  2. CRM: companies, contacts, leads (board + list), activities/tasks, dashboard; public POST /api/public/contact (site us → Dogo, ar → Texas Supply), honeypot, rate limit, email OFF (outbox 'skipped').
  4. Inventory: locations, categories, items, serials, append-only movement ledger, no overselling, CSV import/export.
  5. Invoices: drafts, gapless numbers per company, immutable once issued, payments, aging, PDF (pdfkit). AR invoices are internal documents ("no válido como factura") until ARCA; the ARCA columns already exist.
  6. Documents: disk storage per company, file-type check by magic bytes, quotas, versions, trash, links to CRM/items/invoices.
  Task briefs: workspace/jobs/dogo-backoffice-phase*-task.txt.

## Needs Daniel / Lucas
- Content: names, bios and photos (Nextcloud Felo/Projects/dogo/Photos - originals), email and WhatsApp per company, OK on the AR headline and wordmark.
- Domain to buy; domain email (SMTP) for notifications.
- Invoices: EIN, CUIT, tax rates (e.g. AR IVA), prefixes (defaults INV- / TS-).
- Who the AR staff users are; the owner's username.
- Extra document types (e.g. .dwg CAD drawings)?
- Lead delete = owner role (not the lead's assignee): confirm.

## Not done (needs Daniel's go — L3)
- Deploy to core (swarm service + Postgres + documents volume + nightly backup to Proxmox + off-site), Cloudflare routes, domain, email.
- Sharing the preview with Lucas.
- ARCA e-invoicing (later phase).
- No visual review of the back office UI yet (tests only); do a screenshot pass before showing it.
