# Handoff — finish-line #5: last tools (built 2026-09-30, branch last-tools 6928ae1)

**Status: on the Deploy page (deploy #790), waiting for Daniel's tap.** Tests 387 pass (375 + 12 in tests/last-tools.test.cjs).

## What it does
1. **Proposal PDF attached to email drafts.** `felo_email_draft` / `felo_email_draft_update` take
   `attach: [{file:'<project>/proposal/proposal.pdf', name:'FGC-….pdf'}]` (≤3 PDFs, ≤8 MB, must start with %PDF-).
   Drafts become multipart/mixed (email.js mime). Attachment refs are saved (felo_email_drafts.attachments jsonb) and a
   rewrite re-attaches the newest version unless `attach: []`. New read tool `felo_workroom_files`.
   How the PDF reaches box 100: **host** `felo-workroom-sync` (every minute) now also copies project PDFs ≤5 MB
   (depth ≤4, safe names, sha256-checked, ≤5 per run, removed ones deleted) into `felo_workroom_files` (bytea).
   Box 100 still never reaches box 101. Backup: `felo-workroom-sync.before-pdfs-202609301930`. Round trip tested.
2. **Google Calendar.** Connect now asks for calendar.readonly + calendar.events (read-only still works). Stored
   `write` flag → `calendar.insert()` (POST events?sendUpdates=none, no attendees; no change/delete code).
   Felo-added events (`felo_calendar_add_event`) and suggestions Daniel confirms are copied to Google once
   (`felo_calendar_items.google_event_id`); a failure never breaks the Felo calendar. `felo_calendar` now includes
   Google events for the next 14 days (minus ones Felo copied). Calendar page shows "read and add" vs "read only".
   **Google Calendar was never connected** (no row in felo_calendar_connections) → Daniel connects it after deploy.
3. **Nextcloud project folders.** `felo_nextcloud_folder` (create/list `/Felo/Projects/<key>/`, key lowercase) and
   `felo_nextcloud_save` (workroom PDF → that folder, never overwrites, verified read-back). `/Felo/Projects` exists.
Tools: 28 → 31.

## After Daniel taps Deploy (Claude does these)
- Box 101: `python3 /root/felo-plan/ops/skills-after-last-tools.py` is in the plan repo (box 100) → copy to box 101 and
  run: points felo-proposals / felo-client-onboarding / felo-delivery at the new tools (backups *.before-last-tools-*).
- Restart Hermes (`systemctl restart hermes-gateway`, waits for running jobs) so it loads the 3 new tools; this is also
  the first real run of the #3 start hook (check /var/log/felo-hermes-fixes.log).
- Test (after the API limit resets 19:00 CDT): dry-run a proposal draft with attach on a test project.

## Daniel
- Tap Deploy. Then Felo HQ → Calendar → **Connect Google Calendar**, sign in, allow **both** (see + add events).
- Google sign-in is still in **testing mode**: Google ends its connections after 7 days. Taking it out of testing mode
  (his to-do) stops the weekly reconnect for Gmail and Calendar.

## Update 2026-09-30 evening
- Deploy #790 is live. Hermes restarted 21:01 UTC: 31 tools registered; #3 start hook ran (status 0). Playbooks updated
  (ops/skills-after-last-tools.py applied).
- **Google Calendar: dropped by Daniel.** "I asked from the beginning to create our own Felo Calendar, I have never used
  Google Calendar." The roadmap line "Google Calendar" was a misread. Daniel got redirect_uri_mismatch trying to connect
  (Calendar uses /calendar/callback, not registered in Google Cloud) — **not needed; do not ask him to fix it.**
  Branch `felo-calendar-only` (e0a0697, on the Deploy page): felo_calendar reads Google only if a connection exists,
  add-event no longer mentions Google. Onboarding playbook: kickoff times come from the Felo calendar.
  The dormant Google add/mirror code stays (does nothing without a connection).
