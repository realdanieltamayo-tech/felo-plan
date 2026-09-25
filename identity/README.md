# Felo identity

`FELO.md` is the one official copy of who Felo is. Hermes loads it as `/root/.hermes/SOUL.md` on box 101.
To change Felo's identity: edit FELO.md here (commit), then copy it to box 101 and restart Hermes
(`pct push 101 FELO.md /root/.hermes/SOUL.md` from the Proxmox host; `systemctl restart hermes-gateway` on box 101).
Facts that change often (prices, clients, statuses) belong in Felo's memory, not only here.
