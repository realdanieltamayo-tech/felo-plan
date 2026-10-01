#!/bin/sh
# Box 100: run the Felo v2 test suite on the work copy exactly like the deployer (sealed, no network).
cd /root/felo-v2-work
T=$(mktemp -d /tmp/felo-v2-test.XXXXXX); cp -a app tests voice intake ops scripts worker $T/ 2>/dev/null
docker run --rm --network none -e NODE_PATH=/app/node_modules -v "$T":/w -w /w felo-v2-runtime:current sh -c 'node --test tests/*.test.cjs 2>&1' > /root/felo-test-out.txt; rc=$?
rm -rf "$T"; grep -E '^# (tests|pass|fail) ' /root/felo-test-out.txt | tr '\n' ' '; echo; grep -E '^not ok' /root/felo-test-out.txt | head -10; exit $rc
