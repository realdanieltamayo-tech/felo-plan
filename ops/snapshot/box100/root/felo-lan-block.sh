#!/bin/sh
# Block the old Felo HQ (v1, port 8080) from the office LAN (eth0).
# Tailscale (tailscale0) and loopback access are untouched, so the
# website lead intake and the ts.net HQ link keep working.
# Added 2026-09-24. Remove with: /root/felo-lan-block.sh remove
for T in iptables ip6tables; do
  for CH in DOCKER-USER INPUT; do
    $T -N DOCKER-USER 2>/dev/null
    RULE="$CH -i eth0 -p tcp --dport 8080 -j DROP"
    if [ "$1" = remove ]; then $T -D $RULE 2>/dev/null
    else $T -C $RULE 2>/dev/null || $T -I $RULE; fi
  done
done
