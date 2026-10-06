# Handoff — Felo offline 6 h: box 101 lost DNS (2026-10-06)

Daniel thought the API credit ran out again. It had not (test answered fine after the fix). From 12:00 UTC box 101 could not
look up any address: Tailscale MagicDNS (100.100.100.100) logged "no upstream resolvers set, returning SERVFAIL", so every
Claude call failed with "Connection error" and Felo stopped. Fix: `systemctl restart tailscaled` on CT101 (upstream Comcast
DNS from /etc/resolv.pre-tailscale-backup.conf picked up again).
Prevention: `/usr/local/sbin/felo-dns-heal` on CT100 + CT101, every 2 min (/etc/cron.d/felo-dns-heal): if api.anthropic.com
cannot be looked up twice, restart tailscaled; logs to syslog tag felo-dns-heal.
Cost note: 2026-10-05 was about $23 of API (Tyx chat $10.9, 4 Opus advisor runs for the Excel $6.4, Excel chat $4.5, scheduled $1).
Hermes' session estimate shows Opus subagents as $0; use session_model_usage for real numbers (the Team page does).
