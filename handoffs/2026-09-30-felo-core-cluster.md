# Handoff — Felo core cluster: failover proven (2026-09-30 evening)

Continued here from the other chat's handoff (Daniel: "you continue the cluster work here").
Access: dedicated key `/root/.ssh/felo-core_ed25519` on the Proxmox host, added by Daniel to root on all three machines,
`from="10.1.10.190,100.85.82.45"` (this host only). SSH config: `ssh core|felo-node-1|felo-node-2`.
Scope agreed: cluster work on core only; felostudio.com, Cloud/Nextcloud, Office and core's system settings are not touched without asking.

## Machines (checked live)
| Machine | OS | CPU / RAM / free disk | Network |
|---|---|---|---|
| core | Ubuntu 26.04 | 20 / 30 GB / 380 GB | **Wi-Fi wlo1** 10.1.10.212 (ethernet port dead) |
| felo-node-1 | Ubuntu 24.04.5 | 4 / 15 GB / 85 GB | wired enp2s0 10.1.10.27 |
| felo-node-2 | Ubuntu 24.04.5 | 4 / 15 GB / 85 GB | wired enp2s0 10.1.10.143 |
Docker 29.7/29.8. Swarm: **3 managers** (the other chat's handoff showed only the leader; all three are managers).
Secrets (names only): felo_token, meta_app_secret, meta_page_token, meta_verify_token (8 days old).
`felo-leads:latest` (87f631891cd0) on all three. No registry yet. Nodes run nothing else.

## Test (felo-leads-test, dummy values — no real secret used; decision A/B not needed for the proof)
2 replicas, max 1 per node, constraint node.hostname!=core (core runs production containers), published 18094,
healthcheck on /health. Probed /health every 0.5 s for 60 s through two surviving machines:
1. Stopped Docker on felo-node-2 (worker replica + manager): **208/208 OK**; node-2 Down, rejoined in ~5 s, back to 2/2.
2. Stopped Docker on felo-node-1 (**the leader**): **208/208 OK**; core was elected leader; node-1 rejoined, 2/2.
Routing mesh works: core answered for the service without running a replica.
Test service removed; no containers or port 18094 left anywhere. Current leader: core.

## Next (in order)
1. felo-leads secrets fix (A): read `/run/secrets/<name>` with env fallback; then a real service with the swarm secrets.
   Pointing the real Meta webhook / website form at it = going live → Daniel.
2. Private registry in the swarm (images today are copied by hand with docker save/scp).
3. Public way in: cloudflared as a swarm service (2 replicas) — Daniel creates the tunnel/token.
4. Then finish-line #6: each client site = small web-server image → registry → 2-replica service on the nodes,
   one-tap Launch with health check + rollback.

## Found, not changed (for Daniel)
- core has **no firewall** (ufw inactive) and publishes on all addresses: Postgres 5432, Redis 6380 (artiria-redis),
  Portainer 9000, Metabase 3000, n8n 5678, Nextcloud 8080, finance-app 8000, provisioner 8093, OnlyOffice 8082,
  felostudio-web 8091. Anyone on the office network/Wi-Fi can reach them. Worth closing to localhost/Tailscale.
- core is still on Wi-Fi and is currently the swarm leader (fine: any manager can lead; failover proven).
