#!/bin/bash
# Mirror Felo's repositories to GitHub (private repos, one deploy key each).
# Runs from the repos' post-receive hooks (after every push/deploy) and nightly from cron.
#   felo-github-mirror.sh [felo-v2|felo-plan]   (no argument = both)
# On failure: phone alert on Felo's private channel. PRJ-01 1.2, 2026-09-24.
set -u
LOG=/var/log/felo-github-mirror.log
exec 9>/run/felo-github-mirror.lock; flock -w 120 9 || exit 0
alert(){ T=$(sed -n 's/^NTFY_TOPIC=//p' /root/felo-v2-runtime/ntfy.env); [ -n "$T" ] && curl -s -o /dev/null --max-time 15 -H "Title: Felo GitHub copy FAILED" -H "Priority: high" -H "Tags: warning" -d "$1" "https://ntfy.sh/$T"; }
for name in ${1:-felo-v2 felo-plan}; do
  repo=/root/git/$name.git
  if out=$(git --git-dir="$repo" push --mirror --quiet "git@github-$name:realdanieltamayo-tech/$name.git" 2>&1); then
    echo "$(date -u +%FT%TZ) $name ok $(git --git-dir="$repo" rev-parse --short master)" >> $LOG
  else
    echo "$(date -u +%FT%TZ) $name FAILED: $out" >> $LOG
    alert "$name could not be copied to GitHub. Details: $LOG on box 100."
  fi
done
