# Handoff — PRJ-12 phase 5a: Products & Money (built 2026-09-26, branch products-money)

- app/lib/money.js: createStripe (GET-only, restricted key STRIPE_READ_KEY, 10-min cache; subscriptions status=all with
  expanded prices, charges last 30 days, active products; MRR normalised per month; trials not counted in MRR; business by
  product name: zubaloop -> Zubaloop; cloud/solo/small team/office/practice/nextcloud/storage -> Felo Studio Cloud;
  print/artwork -> Printing store; rebuild/real estate -> THE REBUILD; else Felo Studio).
  createMoney: felo_products table (seeded 8), products() (+ websites by business, + Stripe per business), update() (Level 1),
  money() (Stripe summary, CRM pipeline by stage excluding test contacts, proposals from felo_project_links + workroom quote).
  Pages /products, /money; menu Products, Money. Felo tools felo_money, felo_product_update.
- Host: `felo-set-secret stripe` (backup /root/.felo-backup/felo-set-secret.before-stripe): only rk_live_ keys; tests
  GET /v1/subscriptions = 200 and POST /v1/products (no body, creates nothing) = 401/403, else refuses; writes CT100
  /root/felo-v2-runtime/stripe.env and runs apply-app-env.sh --from it. Claude never handles the key.
- Daniel: one Stripe account for Zubaloop + Cloud; approved read-only access (2026-09-26).
- Next: phase 5b business supervisors (one agent per business reporting to Felo), phase 6 Team, phase 7 look.

## Stripe connected (2026-09-26)
- Daniel ran `felo-set-secret stripe` from an SSH terminal on his PC: key accepted (reads OK, write refused), applied.
  Pasting in the Proxmox web console scrambled the key (it arrived as 109 characters starting "OIr"); the command now strips
  paste markers/whitespace, finds rk_live_ inside pasted text, names the key type, and shows only the first 8 received
  characters. Tip for secrets: use an SSH terminal, not the web console.
- First numbers: Zubaloop 1 paying subscription, $9.99/month; received last 30 days $9.99; 1 failed payment in 30 days.
