# PRJ-03 Dogo / Texas Supply — launch plan for Felo core (draft 2026-10-17, NOT approved)

Same proven pattern as tyxcrm (handoffs/2026-10-05-tyxcrm-on-felo-core.md): build on Proxmox box 100, image store,
swarm services on core, felo-core Cloudflare tunnel, nightly backup from Proxmox + encrypted off-site.

## Addresses
- https://DOMAIN → websites (home, /us, /ar, /es…). The site's nginx forwards /api/public/contact to the back office,
  so forms post to the same address (no cross-site setup).
- https://app.DOMAIN → back office login.

## Steps
A. Daniel: buy DOMAIN at Cloudflare; choose a mail provider (e.g. Hostinger Email) and create the mailboxes.
B. Claude, on Proxmox only (no live change):
   1. Release recipes on box 100 /root/felo-core/apps/: dogo-backoffice (Dockerfile, felo-entry.sh builds DB URLs from
      /run/secrets, app.json) and dogo-site (nginx: static pages + /api/public/contact proxy + security headers).
   2. Felo job: production checks: real visitor IP behind Cloudflare (CF-Connecting-IP) for rate limits, cookie
      Secure, healthz, migrations as one-time run, create-owner as a one-time run.
   3. Site: set form.endpoint = /api/public/contact, rebuild, tests.
   4. Dry run on box 100 with docker compose (build images, migrate, log in, submit a test form).
C. Claude on core, after Daniel's GO:
   1. Secrets made on core, never shown: dogo_db_owner_pw, dogo_app_pw, dogo_ip_hash_secret.
   2. Services: dogo-db (Postgres 16, pinned felo-node-2, /srv/dogo/pgdata), dogo-app (felo-node-2,
      /srv/dogo/documents, networks felo-edge + dogo-net), dogo-site (nginx, 2 replicas, stateless).
      dogo-net = overlay, encrypted, internal. App role: not superuser, no BYPASSRLS.
   3. felo-app-launch dogo-backoffice app.DOMAIN (migrations job → start-first update → health checks).
   4. Owner account: create-owner one-time run; temporary password given to Daniel only; he sets his own.
   5. Daniel adds 2 routes in Cloudflare (felo-core tunnel → Published application routes):
      DOMAIN → http://dogo-site:80   ·   app.DOMAIN → http://dogo-app:3000
   6. Live checks through Cloudflare: pages, /healthz, test form US + AR land in the right company (then deleted),
      AR staff test account sees no Dogo data (then removed).
D. Backups (before any real data):
   felo-core-app-backup gets a dogo section: pg_dump -Fc checked with pg_restore --list + documents tar from
   felo-node-2 → /var/lib/felo-core-backups/dogo/ (14 days) → felo-offsite-backup sends it encrypted off-site.
   Restore test into a scratch database. Releases stay on Proxmox (newest 5) for rollback.
E. Email (when mailboxes exist): MX/SPF/DKIM/DMARC in Cloudflare DNS; SMTP as secrets; SEND_EMAIL=true; test one
   notification per company.

## Decisions for Daniel
- Domain name. Texas Supply staff will see it in the back-office address: neutral name or one with "dogo"?
- Back-office address app.DOMAIN OK?
- Mail provider.
- Lucas sees it before or after launch?

## Known limits (v1)
- Database on one machine (felo-node-2), like tyxcrm. If that node fails: restore on another node from last night.
- Rollback never undoes database changes.
- Argentina invoices are internal documents until ARCA.

## Step B DONE (2026-10-17)
- Felo job 20261017-225333: production readiness (CF-Connecting-IP only, start-up safety checks, __Host- Secure cookie,
  /healthz checks the DB, request log without bodies, TEMPORARY_PASSWORD= line). dogo-backoffice: 133 tests pass.
- Recipes on box 100: /root/felo-core/apps/dogo-backoffice (Dockerfile, felo-entry.sh, app.json: dogo-app, felo-node-2,
  secrets dogo_app_pw / dogo_ip_hash_secret, the migration run gets dogo_db_owner_pw) and /root/felo-core/apps/oil-equipment-site
  (2 stages: builds the pages with the forms ON; nginx serves the pages and passes only POST /api/public/contact to dogo-app;
  nginx.conf is inlined in the Dockerfile because felo-app-launch copies only Dockerfile + felo-entry.sh).
  Both launch with the existing felo-app-launch.
- Dry run: Proxmox host /root/dogo-dryrun.sh (builds both images on box 100, throwaway network). 26/26 PASS:
  images build; migrations run and rerun; no password in the output; app role not superuser / no BYPASSRLS / owns no
  tables; owner created; all 6 pages + assets; forms ON; no notes/content/other API paths served; US form → Dogo lead,
  AR form → Texas Supply lead; IP taken from CF-Connecting-IP; login works; cookie __Host- + Secure; restart OK; logs clean.
- Left for step C (needs the GO + domain): dogo-db service (Postgres 16 from the store, felo-node-2, /srv/dogo/pgdata),
  network dogo-net (overlay, encrypted, internal), secrets, /srv/dogo folders, launches, Cloudflare routes, and the
  dogo section in felo-core-app-backup (added only at launch, so the nightly run does not fail before then).
