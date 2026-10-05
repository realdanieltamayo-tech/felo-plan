# Handoff — Felo's own inbox info@felostudio.com (built 2026-10-05, branch felo-inbox 433b59d)

Daniel: Felo used his personal Gmail; business mail should use Felo Studio's own address. Do this before the email campaign.
Found: felostudio.com mail = Hostinger Email (MX mx1/mx2.hostinger.com, SPF Hostinger, DKIM hostingermail-a/b/c CNAMEs present, DMARC p=none).

- **felo-mail service** (box 100, `mail/`): python:3.12-slim, standard library only. Docker network felo-codex-preview, alias
  felo-mail:8080, no published port, read-only, cap-drop ALL, 128 MB. Answers ONLY the app container (client IP must resolve
  from `felo-codex-preview-app`; intake gets 403). IMAP imap.hostinger.com:993: inbox list/search (readonly select, BODY.PEEK,
  so nothing is marked read), read one message (plain text, html stripped, attachment names), save DRAFT (APPEND to the
  \Drafts folder, From "Felo Studio <info@felostudio.com>", replies keep In-Reply-To/References). No SMTP, no send code.
  Settings `/root/felo-v2-runtime/mail.env` (600; MAIL_USER, MAIL_PASSWORD, MAIL_FROM_NAME) — never print.
  (Re)start: `sh /root/felo-codex-preview/mail/run.sh`. Started now from the work copy (not configured until the password).
- **Password:** Daniel runs `felo-set-secret info-mail` on the Proxmox host over SSH → pending/info-mail on box 100 →
  `mail/apply-info-mail.sh` writes mail.env, restarts felo-mail, checks the login, deletes the pending copy (prints only OK/FAIL).
  Host helper backup: /usr/local/bin/felo-set-secret.before-info-mail-*.
- **App** (`app/lib/mailbox.js`): page /email/info ("Felo inbox": Inbox / Unread / Felo's drafts / search, open message),
  link on /email; API GET /api/email/info/status|messages|messages/:id (owner gate). Tools (felo-tools.js, now 36):
  felo_info_inbox, felo_info_read, felo_info_draft (LEVEL 2, logged).
- **felo-outreach skill** (CT101) now uses the info@ tools; it stops and tells Daniel if the inbox is not connected.
- Tests: 398 node pass; tests/mail_server_test.py 4 pass (python:3.12-slim).

Not yet (next small steps): felo-events watching info@ for new mail (lead replies) like Gmail; Clients page showing info@ threads;
optional sending after a one-tap batch approval (would need SMTP + an L3 approval page). Note: Felo's existing chats keep
their old tool list until a fresh start (Hermes reloads MCP tools on restart; run felo-fresh-chats only if Felo says it lacks them).

## 2026-10-05 tools reload
/reload-mcp works only as a Telegram command while that chat is idle; the API (Felo HQ) does not run slash commands. Daniel's reload did not reach Hermes (no new "registered" line). Installed CT101 /root/reload-when-idle.sh, started as transient unit felo-reload-when-idle: waits until no conversation turn is open in agent.log (the Tyx job was polling a build every 3 min), then restarts hermes-gateway (max 6 h). Check: grep registered /root/.hermes/logs/agent.log | tail -1 -> 36 tools.
