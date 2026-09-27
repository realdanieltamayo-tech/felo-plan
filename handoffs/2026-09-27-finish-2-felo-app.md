# Handoff — Finish-line #2: Felo as an installable app (built 2026-09-27, branch felo-app)

- app/lib/pwa.js: /manifest.webmanifest (Felo, start /hq, scope /, standalone, #05020d/#0b0520, maskable icon, shortcuts
  Chat/Waiting/Money), /sw.js (navigation-only; network first; only an offline "check Tailscale" page is cached; nothing
  private), /pwa/<icon>.png (allowlist), /favicon.ico. Icons in app/pwa/ generated from the neural-core design
  (scratchpad make-icons.py, PIL in Felo's workroom).
- hq.html: app links in <head>, service worker registered. Other pages get the same links through theme.js HEAD.
- Gate: GET manifest, sw.js, favicon, /pwa/*.png only. HTTPS comes from Tailscale Serve (ts.net certificate).
- Install: iPhone Safari → Share → Add to Home Screen; Android Chrome → ⋮ → Install app; Windows/Mac Chrome or Edge →
  install icon in the address bar. Tailscale must be on (the offline page says so).
- Tests: 374 pass.
