# Box 101, run AFTER the site-launch-all deploy (+ Hermes restart): point the playbooks at the Launch tools.
import shutil, time
ts = time.strftime("%Y%m%d%H%M"); P = "/root/.hermes/skills/productivity/"
def edit(path, pairs):
    s = open(path, newline="").read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60]); s = s.replace(old, new)
    shutil.copy2(path, path + ".before-launch-" + ts); open(path, "w", newline="").write(s)
edit(P + "felo-delivery/SKILL.md", [
("## 3. Go live (Daniel's tap)\n- Prepare a launch sheet for Daniel in the project folder, `LAUNCH.md`: where it will be hosted (Daniel's decision),\n  the domain, the exact DNS records needed (type, name, value), what to test after, and how to roll back.\n- You never change DNS, hosting or payment settings yourself. Daniel does, or approves the step.",
 "## 3. Go live (Daniel's tap) — client sites run on **Felo core** (built on Proxmox, a copy kept there)\n"
 "- `felo_request_launch` (project, hostname = the real address, e.g. dogogroup.com, why). Level 3: it waits on the\n"
 "  Launches page; Daniel taps Launch; about 2 minutes later it runs as 2 copies with automatic rollback.\n"
 "  Only pages, styles, scripts, images and fonts are published (never notes, briefs or proposal/).\n"
 "- First launch of an address: Daniel adds it in Cloudflare (the Launches page shows exactly what). If the client's\n"
 "  domain is not in Cloudflare yet, write `LAUNCH.md` for Daniel: the domain, that its nameservers must move to\n"
 "  Cloudflare (at the client's registrar), and what to test after.\n"
 "- Follow it with `felo_launches` (status, version, whether the address answers). Updates later = a new request;\n"
 "  a bad update is rolled back by Daniel's Roll back tap (or automatically if it does not start healthy).\n"
 "- You never change DNS, hosting or payment settings yourself."),
("- `felo_website_save` (name, url, contact_id, hosted_on, care_plan, project) → Websites page, checked every 5 minutes.",
 "- `felo_website_save` (name, url, contact_id, hosted_on: \"Felo core\", care_plan, project) → Websites page, checked every 5 minutes."),
])
edit(P + "felo-website-playbook/SKILL.md", [
("Prepare for him: preview link, what is in it, open decisions, where it will be hosted (open decision: Daniel's own\nservers), and the price/bundle.",
 "Prepare for him: preview link, what is in it, open decisions, and the price/bundle. Client sites are hosted on\n**Felo core** (launch with `felo_request_launch`, see felo-delivery)."),
])
print("playbooks updated")
