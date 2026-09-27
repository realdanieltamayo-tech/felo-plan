# Handoff — Finish-line #1: chat threads + late answers (built 2026-09-27, branch chat-threads 8406d49)

## Threads
- app/lib/threads.js: felo_threads(key, name, sort, unread, last_at); felo_turns.thread (default 'general').
  Seeded: general, felo-studio, felo-studio-cloud, zubaloop, the-rebuild. New threads from the UI ("+ New thread").
  Hermes conversation per thread: general -> felo-hq (the original, continuity), others -> felo-hq-<key>.
  Every message in a non-general thread is sent with a short topic note ("[Felo HQ thread: X. This conversation is only
  about X ...]"); the saved chat text is Daniel's own words.
- hq-routes.js: /api/hq/history?thread=&before=|after=, /api/hq/ask {text, requestId, thread}; thread routes mounted there.
- hq.html: thread tabs above the conversation (chat view), unread badges on tabs and on the Chat menu item, current thread
  remembered in localStorage, placeholder shows the thread; polls /api/hq/threads every 30 s; new Felo messages in the
  current thread are appended (and spoken if voice is on); Home shows "Felo has an update in ...".

## Late answers
- Hermes API chats cannot receive pushed results: an async delegation result is appended to the session as a user
  message with display_kind 'async_delegation_complete' and Felo does not reply until the next message.
- Proxmox /usr/local/sbin/felo-late-answers (cron every minute via felo-ran; AUTOMATIONS row "late-answers"): scans CT101
  response_store.db (conversation name -> latest response -> session_id) + state.db (last message of the session) for
  felo-hq* conversations whose last message is such a result; runs `docker exec felo-codex-preview-app node
  /repair/scripts/late-answer.js <thread>` which asks Felo to report the outcome (1-4 lines) and saves it as an unread Felo
  turn; each result handled once (/var/lib/felo-late-answers.json). Test conversations (no matching thread) are skipped.
- Tests: tests/threads.test.cjs; helpers/hermes-chat/preview-dashboard tests updated; 372 pass.

## Next (finish line)
#2 Felo as an installable app · #3 Hermes update safety · #4 last playbooks · #5 last tools · #6 client hosting (decision) · #7 WhatsApp (number).
