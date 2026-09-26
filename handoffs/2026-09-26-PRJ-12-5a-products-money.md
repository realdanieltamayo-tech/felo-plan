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
