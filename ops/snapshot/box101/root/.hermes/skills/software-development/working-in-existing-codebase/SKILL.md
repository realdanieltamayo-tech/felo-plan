---
name: working-in-existing-codebase
description: "Add features to existing codebases safely with hard limits."
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos, windows]
---

# Working in an Existing Codebase

Use this skill when adding features or fixes to a codebase with existing conventions, especially when hard limits (no live systems, no credentials, work only in one dir) are in play and/or the task must land as several separately-reviewable commits.

## Producing separate commits for logically distinct fixes
When asked to address multiple review findings and "commit each separately":
1. Read the full findings doc AND the original brief/hard-limits doc together before writing code. A follow-up fix brief usually says hard limits from round 1 still apply without restating them in full.
2. Implement and test every fix together first — fastest way to see how they interact and to get one full green test run.
3. Then `git checkout -- <file>` back to baseline and reapply each fix's diff one at a time: syntax-check (`node -c` or equivalent) after each reapply, then commit that one fix alone before moving to the next. This produces clean single-purpose commits without losing the integration testing already done. Run the full test suite once more at the very end against the fully-reassembled file to confirm nothing was dropped in the split.
4. Write commit messages that state the bug/symptom and the fix's mechanism, not just "fix N" — a future reviewer approves or rejects from the message alone.

## Testing DB-backed transactional code
Don't trust a `BEGIN`/`COMMIT`/`ROLLBACK` block is correct by code inspection alone — if invalid records are filtered out before the insert loop even runs, the ROLLBACK branch may never actually execute in your test suite. Write a small throwaway script that forces a genuine DB-level error mid-transaction (e.g. a NOT NULL violation the app-level validation doesn't catch) and confirm the row count is 0 afterward. Report that you verified it in the commit/notes; delete the throwaway script rather than committing it.

## Parsing LLM/model JSON output robustly
Never call `JSON.parse` directly on raw model output and let a throw fall into a generic catch that discards the output. Guard with `Array.isArray` (or whatever shape is expected) and, on failure, fall back to scanning for the first balanced bracket/brace block in the raw text before giving up — models wrap JSON in markdown fences or prose more often than not. On total failure, store the raw output on the task/error result for diagnosis instead of swallowing it.

## Extracting dates/times from free text with an LLM
An LLM asked to extract a date from prose ("Tuesday", "tomorrow", "next Friday") has no notion of "today" unless the prompt states it, and will silently guess — wrong guesses land days in the past or future with no error. Always inject the current date, day-of-week, and the user's UTC offset into the prompt itself, computed at request time, and add a server-side validation pass that rejects (not just flags) any resulting timestamp that lands unreasonably in the past — the prompt fix and the validation gate are both required, since the gate catches what the prompt fix doesn't. See references/llm-date-extraction.md for the timezone-derivation snippet and the tolerance-window pattern.

## Test fixtures under dedup/idempotency logic
If the code under test suppresses reprocessing of anything it's already seen (an email id, an idempotency key, a `source_*_id` column), every test scenario needs its OWN unique id — reusing an id (or a shared fixture) across test cases makes a later scenario silently return "already processed" instead of exercising the path you meant to test, and the assertion failure will look like the fix is broken when the real bug is fixture reuse.

## Adding a browser page to an existing backend with hard limits
When asked to add a UI page (e.g. an admin/review page) to an existing Express-style app under "no deployment config changes":
- Check what the Dockerfile/build actually ships (`COPY index.js .` vs a whole directory) before adding a static file or a new `public/` dir — if only specific files are copied into the image, a new static asset silently won't ship and touching the Dockerfile to fix that is itself a forbidden deployment-config change. Inlining the page as a template string returned from the existing route handler needs no build change and no new dependency.
- If the app has a bearer-token `auth` middleware and no login system, do NOT put that middleware on the HTML page route itself — a plain browser navigation cannot attach a custom `Authorization` header, so the page becomes unreachable. Serve the HTML unauthenticated; keep every *data* endpoint the page calls behind the existing auth exactly as before. Client-side: prompt once for the token (`window.prompt`), cache it in `sessionStorage` (never `localStorage` unless the user asks for persistence, never hardcode it in the page source), and on any 401 clear the cached token, reprompt, and retry the request once.

## Testing a page's client-side JS when the browser tool can't reach the target
If the app only runs on localhost/private IPs (common for internal tools) and the browser automation tool refuses private addresses, don't skip client-side verification — extract the actual `<script>` block from the rendered HTML at runtime (regex out of the served page or the source string) and `eval` it in a plain Node script with a minimal hand-rolled DOM/fetch shim (stub `document.getElementById`, `sessionStorage`, `window.prompt`, `fetch`). This exercises the real shipped code, not a reimplementation, and catches bugs in escaping, date/timezone formatting, and auth-retry logic that a syntax check alone won't. Pair it with real `curl` calls against the running server (with and without the token) to prove the server side independently. Report both to the user; flag the real-browser rendering/layout check as still needed if the tool genuinely can't reach the target.

## Widening a recurring endpoint's scan/query window
When asked to broaden what a recurring job looks at (e.g. "unread only" -> "everything from the last N days", or any narrow filter -> a wider recency/volume window), two things that were previously non-issues become load-bearing and need explicit attention, not just a query-string swap:
- **Dedup/idempotency logic goes from decorative to critical.** Under a narrow filter (unread, new-since-last-run) the same item usually can't reappear on its own. Under a wider window, every run re-fetches everything in range regardless of prior state, so dedup is now the only thing preventing the job from reprocessing its entire history every time. Call this out explicitly in the docs/notes rather than assuming the existing check still "just works" — verify it against the new fetch path with a test, don't just leave it in place unexamined.
- **A bigger window can exceed the API's page/result cap that the narrow filter never hit.** Check whether the list API reports truncation (e.g. a `nextPageToken`) and surface that fact in the response/UI (a `truncated` flag plus a human-readable warning) rather than silently dropping the tail of the window. Don't auto-paginate to "fix" it without being asked — each extra page is usually N more per-item API calls, an unbounded cost the endpoint shouldn't take on silently; recommend raising the batch/result limit instead and let the user decide once real volume is known. Make any new scope-controlling parameter (e.g. a day-window) configurable but clamp it to a sane max so a bad or malicious value can't turn a bounded job into a full-history scan.

## Keeping an append-only NOTES/decisions doc consistent
When a repo's NOTES.md (or similar) accumulates a new dated section every time you touch the repo, a numbered "decisions" or "open questions" list inside it will drift: pasting a new decisions block can duplicate a section header already used lower in the file, or restart numbering at 1 instead of continuing the running count. After inserting a new block into a long-lived doc, grep the file for the section header and for the list's leading numerals before committing, and renumber/dedupe headers so the count stays sequential end to end — a reviewer skimming the doc treats broken numbering as a sign the content itself wasn't checked.

See references/mocking-externals.md for mocking external HTTP services and local Postgres setup/auth.
