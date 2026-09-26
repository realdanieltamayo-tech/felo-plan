#!/bin/bash
# Felo v2 deployer. Runs on container 100 (felo-orchestrator) only, as root,
# from cron via felo-v2-deploy-watch.py after Daniel approves on /deploy.
# The in-repo copy is ops/felo-v2-deploy.sh; the one that runs is
# /root/felo-v2-deploy.sh. Change both together.
#
#   felo-v2-deploy.sh <sha>
#
# 1. Refuses if the live copy was edited by hand.
# 2. Refuses unless <sha> builds on what is live now (fast-forward only).
# 3. Runs the full test suite on <sha> in a sealed container. Nothing live
#    changes if a test fails.
# 4. Moves the live copy to <sha>, restarts the app, health-checks it.
# 5. On a failed health check: puts the previous version back and restarts.
set -u
LIVE=/root/felo-codex-preview
APP=felo-codex-preview-app
DB=felo-codex-preview-db
INTAKE=felo-v2-intake
SHA="${1:-}"

[ "$(hostname)" = "felo-orchestrator" ] || { echo "WRONG MACHINE: run this on container 100"; exit 2; }
[ -n "$SHA" ] || { echo "usage: $0 <sha>"; exit 2; }
exec 9>/run/felo-v2-deploy.lock
flock -n 9 || { echo "BUSY: another deploy is running"; exit 1; }
cd "$LIVE" || { echo "no live copy at $LIVE"; exit 1; }

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "REFUSED: the live copy has hand edits that are not in git. Nothing was changed."
  git status --short --untracked-files=no | head -10
  exit 1
fi

PREV=$(git rev-parse HEAD)
git fetch -q origin || { echo "could not read the repository"; exit 1; }
SHA=$(git rev-parse --verify -q "$SHA^{commit}") || { echo "unknown commit $1"; exit 1; }
if [ "$SHA" = "$PREV" ]; then echo "ALREADY LIVE $(git rev-parse --short HEAD)"; exit 0; fi
if ! git merge-base --is-ancestor "$PREV" "$SHA"; then
  echo "CONFLICT: $(git rev-parse --short "$SHA") is not built on the live version $(git rev-parse --short "$PREV"). Rebuild it from master. Nothing was changed."
  exit 1
fi

# ---- tests, sealed: no network, throwaway copy of the new version ----
# Tests run on the same named runtime image the app runs on (built from the
# exact libraries v2 used; see /root/felo-v2-runtime/Dockerfile).
IMG=felo-v2-runtime:current
NP=/app/node_modules
T=$(mktemp -d /tmp/felo-v2-test.XXXXXX)
git archive "$SHA" | tar -x -C "$T"
TESTOUT=$(timeout 600 docker run --rm --network none -e NODE_PATH="$NP" -v "$T":/w -w /w "$IMG" \
  sh -c 'node --test tests/*.test.cjs 2>&1' ); TRC=$?
rm -rf "$T"
SUMMARY=$(printf '%s\n' "$TESTOUT" | grep -E '^# (tests|pass|fail) ' | tr '\n' ' ')
if [ $TRC -ne 0 ]; then
  echo "TESTS FAILED on $(git rev-parse --short "$SHA"): $SUMMARY Nothing was changed."
  printf '%s\n' "$TESTOUT" | grep -E '^not ok' | head -5
  exit 1
fi

health() {
  # The app only starts listening after every module and database step has
  # finished, so any answer from its owner check means it fully started.
  local since="$1" i body
  for i in $(seq 1 45); do
    sleep 2
    [ "$(docker inspect "$APP" --format '{{.State.Running}}')" = "true" ] || continue
    body=$(curl -s --max-time 5 http://127.0.0.1:8081/hq) || continue
    if printf '%s' "$body" | grep -q 'Felo owner access' \
       && docker logs --since "$since" "$APP" 2>&1 | grep -q 'preview is ready' \
       && docker exec "$DB" pg_isready -q; then
      return 0
    fi
  done
  return 1
}

intake_health() {
  local i
  for i in $(seq 1 20); do
    sleep 2
    curl -s --max-time 5 http://127.0.0.1:8080/health | grep -q '"ok":true' && return 0
  done
  return 1
}
# The website intake container runs intake/ from this same live copy.
INTAKE_CHANGED=0
if docker inspect "$INTAKE" >/dev/null 2>&1 && [ -n "$(git diff --name-only "$PREV" "$SHA" -- intake/)" ]; then INTAKE_CHANGED=1; fi

git merge -q --ff-only "$SHA" || { echo "could not move the live copy. Nothing was changed."; exit 1; }
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker restart "$APP" >/dev/null
[ $INTAKE_CHANGED = 1 ] && docker restart "$INTAKE" >/dev/null
if health "$START" && { [ $INTAKE_CHANGED = 0 ] || intake_health; }; then
  FELO_DEPLOYER=1 git push -q origin HEAD:refs/heads/master 2>/dev/null
  FELO_DEPLOYER=1 git push -q -f origin HEAD:refs/heads/deployed 2>/dev/null
  echo "DEPLOYED $(git rev-parse --short HEAD)  tests: $SUMMARY"
  exit 0
fi

git reset -q --hard "$PREV"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker restart "$APP" >/dev/null
[ $INTAKE_CHANGED = 1 ] && docker restart "$INTAKE" >/dev/null
if health "$START"; then
  echo "ROLLED BACK to $(git rev-parse --short "$PREV"): the new version did not start healthy."
else
  echo "ROLLED BACK to $(git rev-parse --short "$PREV") BUT THE APP IS STILL NOT HEALTHY. Check docker logs $APP."
fi
docker logs --since 3m "$APP" 2>&1 | tail -5
exit 1
