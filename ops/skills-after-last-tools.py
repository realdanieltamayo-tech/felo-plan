# Box 101, run AFTER the last-tools deploy: point the playbooks at the new tools.
import shutil, time
ts = time.strftime("%Y%m%d%H%M"); P = "/root/.hermes/skills/productivity/"
def edit(path, pairs):
    s = open(path, newline="").read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60]); s = s.replace(old, new)
    shutil.copy2(path, path + ".before-last-tools-" + ts); open(path, "w", newline="").write(s)
edit(P + "felo-proposals/SKILL.md", [
("- **Email draft** to the client with the link (`felo_email_draft`; he presses Send).",
 "- **Email draft** to the client with the link **and the PDF attached**: `felo_email_draft` with\n"
 "  `attach: [{file: \"<project>/proposal/proposal.pdf\", name: \"<proposal number>.pdf\"}]` (he presses Send).\n"
 "  The PDF appears in `felo_workroom_files` about a minute after `proposal-pdf`.\n"
 "- Save a copy for the client file: `felo_nextcloud_folder` (create) then `felo_nextcloud_save` (same file and name)."),
])
edit(P + "felo-client-onboarding/SKILL.md", [
("- Client files folder in Nextcloud: `/Felo/Projects/<project key>/`. If you have no tool to create it, add a task for\n  Daniel: \"Create Nextcloud folder /Felo/Projects/<key>/\". Never tell anyone a path you did not see created.",
 "- Client files folder in Nextcloud: `felo_nextcloud_folder` (project key, create) → `/Felo/Projects/<key>/`; tell Daniel the\n"
 "  path only when it returned ok. Save the accepted proposal there (`felo_nextcloud_save`, name = proposal number)."),
("- Kickoff call: offer two concrete times (check `felo_calendar`; weekdays, business hours Houston time).",
 "- Kickoff call: offer two concrete times that are free in `felo_calendar` (it includes Daniel's Google Calendar;\n  weekdays, business hours Houston time)."),
("When the client picks a time: `felo_calendar_add_event` (certain) or `felo_propose_calendar_event` (not certain).",
 "When the client picks a time: `felo_calendar_add_event` (certain; it also lands on Daniel's Google Calendar) or\n`felo_propose_calendar_event` (not certain)."),
])
edit(P + "felo-delivery/SKILL.md", [
("## 5. Handover pack (`HANDOVER.md` in the project, sent through an email draft)",
 "## 5. Handover pack (`HANDOVER.md` in the project, sent through an email draft)\n"
 "If you make it a PDF, attach it to the draft (`attach`) and save it to `/Felo/Projects/<key>/` (`felo_nextcloud_save`)."),
])
print("skills updated")
