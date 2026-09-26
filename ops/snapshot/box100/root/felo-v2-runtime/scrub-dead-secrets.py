#!/usr/bin/env python3
"""Replace dead (rotated) secret values in leftover files with a marker. Never prints values.
PRJ-01 1.1, 2026-09-24. Live settings (app.run.env, intake.env, ntfy.env) are never edited."""
import glob, re, os

LIVE = {"/root/felo-v2-runtime/app.run.env", "/root/felo-v2-runtime/intake.env", "/root/felo-v2-runtime/ntfy.env"}
live_vals = set()
for f in LIVE:
    for line in open(f):
        if "=" in line:
            live_vals.add(line.split("=", 1)[1].strip())

# Collect the old values from the files that held them.
dead = set()
KEYS = r"(NEXTCLOUD_PASS|GMAIL_CLIENT_SECRET|GMAIL_REFRESH_TOKEN|AUTH_TOKEN)"
sources = ["/root/felo-orchestrator/docker-compose.yml", "/root/felo-codex-preview/app.env"] + \
          glob.glob("/root/felo-orchestrator-backups/v1-retire-*/docker-compose.yml") + \
          glob.glob("/root/felo-v2-runtime/app.run.env.before-*")
for f in sources:
    for m in re.finditer(KEYS + r"[:=][ \t]*['\"]?([^'\"\s#]+)", open(f).read()):
        v = m.group(2)
        if len(v) >= 12 and v not in live_vals:
            dead.add(v)
print(f"dead secret values found: {len(dead)} (none of them is in use)")

for f in sources:
    s = open(f).read(); n = 0
    for v in dead:
        if v in s:
            n += s.count(v); s = s.replace(v, "ROTATED-2026-09-24")
    if n:
        open(f, "w").write(s); os.chmod(f, 0o600)
    print(f"  {f}: {n} dead value(s) replaced")
for f in glob.glob("/root/felo-v2-runtime/app.run.env.before-*"):
    os.remove(f); print(f"  removed rollback copy {os.path.basename(f)}")
