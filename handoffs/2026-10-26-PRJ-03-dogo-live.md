# Handoff — PRJ-03 Dogo Group / Texas Supply LIVE on Felo core (2026-10-26)

Daniel approved step C ("run /root/dogo-launch-stepC.sh on core now").

## Live
- https://dogo-group.com (+ www): websites, release oil-equipment-site:2026.10.26-1, service dogo-site.
- https://app.dogo-group.com: back office, release dogo-backoffice:2026.10.26-1, service dogo-app.
- dogo-db: Postgres 16.15 (core store), felo-node-2, /srv/dogo/pgdata. Documents /srv/dogo/documents (felo-node-2).
- Network dogo-net (overlay, encrypted, internal). Secrets dogo_db_owner_pw, dogo_app_pw, dogo_ip_hash_secret (never shown).
- Cloudflare: domain registered at Hostinger, DNS on Cloudflare (rudy/zita). felo-core tunnel routes:
  dogo-group.com + www.dogo-group.com → http://dogo-site:80 ; app.dogo-group.com → http://dogo-app:3000.
  Parking A record 2.57.91.91 + www CNAME deleted by Daniel.
- Owner account `daniel`, temporary password in /root/dogo-owner-temp-password.txt (Proxmox host, 600). Delete the
  file after Daniel's first sign-in.

## Verified live (through Cloudflare)
All 6 pages 200; notes/content/other API paths 404; back office /healthz ok, login page, 401 when logged out, CSP +
X-Frame-Options; US form → Dogo lead, AR form → Texas Supply lead, IP from CF-Connecting-IP, email queued as skipped.
Test rows deleted (0 leads/contacts/submissions/outbox). App role: not superuser, no BYPASSRLS; 20/20 tables FORCE RLS.

## Backups
felo-core-app-backup has a dogo section (pg_dump -Fc checked + documents tar from felo-node-2) → /var/lib/felo-core-backups/dogo,
14 days → felo-offsite-backup (restic, encrypted). Restore tested into a scratch DB (0 errors, 26 tables), dropped.
Previous script: /usr/local/sbin/felo-core-app-backup.before-dogo-20261026.

## Mistake today (fixed)
The image store moved to core on 2026-10-22 (box 100 store intentionally stopped). My step C script still used the old
store for dogo-db → pull 502. I restarted the old box 100 store, then found the move, re-stopped it and re-pointed dogo-db to
core.tail0ff06a.ts.net:5443. Script fixed. felo-app-launch already used the core store.
Launcher false positive: route_ok counted Hostinger's parking page (served via Cloudflare) as "answering" → follow-up.

## Releases / rollback
felo-app-launch dogo-backoffice app.dogo-group.com · felo-app-launch oil-equipment-site dogo-group.com · --rollback.
Recipes: box 100 /root/felo-core/apps/{dogo-backoffice,oil-equipment-site}. Dry run: /root/dogo-dryrun.sh.

## Open
- Real content from Lucas (names, bios, photos, email, WhatsApp, AR headline/wordmark) → website update + relaunch.
- Domain mailboxes (provider TBD) → MX/SPF/DKIM/DMARC + SMTP secrets + SEND_EMAIL=true.
- Invoice settings: EIN, CUIT, tax rates. AR staff accounts. ARCA later.
- v1 limit: database on one machine (felo-node-2).

## 2026-10-26 fix: website showed without styles (release 2026.10.26-2)
The site's Content-Security-Policy lost its quotes ('self' → self) when I wrote the recipe through a single-quoted shell,
so browsers blocked the site's own CSS/JS. curl-based checks (dry run + live) cannot see this. Fixed in
box 100 apps/oil-equipment-site/Dockerfile (backup Dockerfile.before-csp-fix), added connect-src 'self', relaunched.
Verified in a real browser (Playwright, live through Cloudflare): styles + script load; only the Cloudflare Web Analytics
beacon is blocked (auto-injected by Cloudflare; harmless; can be switched off in the dogo-group.com Web Analytics settings).
LESSON: launch checks must include a real-browser load that fails on CSP/console errors.

## 2026-10-26 redesign live (oil-equipment-site 2026.10.26-5)
Daniel: the first design was "so simple, nothing modern or sophisticated"; quality bar = felostudio.com. Claude redesigned
directly (commits d7e3ff0, 6e0c223, b598a0a): dark industrial design system (frosted header + tabs, cinematic hero with
grain/glow + frosted industries panel, mosaic industries grid, frosted-glass contact form, entrance motion with
reduced-motion support), home page restyled. Tests 29/29.
- Cache-busting added: styles.css?v=<hash> / script.js?v=<hash> (Cloudflare kept serving the old CSS after release -3).
- Verified live in a real browser: dark styles on every page, 16-17/17 sections reveal, no errors (except Cloudflare's
  injected analytics beacon, blocked by CSP), no "Dogo" on Texas Supply pages outside the company tabs.
- Releases -3 and -4 were intermediate (stale cache, panel readability on the bright truck photo).

## 2026-10-26 real Dogo content live (oil-equipment-site 2026.10.26-7)
Client material: Nextcloud Felo/Projects/dogo/Photos - originals/USA - Dogo Group (6 logo versions, 74 photos, 8 phone videos).
- Logo traced to SVG with potrace (no AI): icon from the client's dark version logic (white face + black ink, CSS backlight
  glow) and wordmark from the horizontal logo. Work files: box 101 workspace/demo-dogo/logo (trace.js, CLOSE_R=45).
- Web copies made with ffmpeg (resize + JPEG, all metadata/GPS stripped); originals untouched. Hero = heavy-haul truck
  (#23), oil card = rig at dusk (#11), 12-photo gallery with full-screen viewer, President portrait (#80, name still [Name]),
  vertical rig video card (V1, 12 s, mp4 + webm).
- Email sales@dogo-group.com on the US contact section (mailto). At launch dogo-group.com had NO MX/SPF/DMARC in Cloudflare.
- Fixed: inline style attribute blocked by CSP (hero focus moved to CSS); test now rejects inline styles.
- Verified live in a real browser: video plays, 12/12 gallery images, viewer opens, 28/28 reveals, no errors.

## 2026-10-26 later
- President: Cristian Osorio (20+ years, bio EN/ES approved by Daniel), release -8.
- Preview notes removed from all pages (release -9).
- Live end-to-end form test in a real browser: US form -> Dogo Group LLC lead, AR form -> Texas Supply SRL lead (both named TEST/PRUEBA, left in the CRM for Daniel to see and delete).
- Daniel (owner) has not signed in yet (must_change_password = true).
