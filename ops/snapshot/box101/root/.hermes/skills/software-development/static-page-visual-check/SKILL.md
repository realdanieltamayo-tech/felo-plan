---
name: static-page-visual-check
description: "Use when a built web page must be checked by eye."
version: 1.0.0
author: Felo
platforms: [linux]
metadata:
  hermes:
    tags: [QA, Website, Playwright, Screenshots]
    related_skills: [felo-website-playbook, felo-dev-team, licensed-stock-images]
---

# Visual + behaviour check of a static page

Automated checkers (felo-team `check-site`) catch titles, labels and broken links, but they can't see layout. Before telling
Daniel a page is done, look at it yourself. The private :8900 preview is a Tailscale address the browser tool refuses,
so check a local copy instead.

## Procedure

1. **Setup (once per container):** in /tmp/shot run `npm i -s playwright@<version matching ~/.cache/ms-playwright>`,
   then `node node_modules/playwright/cli.js install-deps chromium` to install the missing system libraries. If apt reports a
   dpkg lock, wait for the other apt process to finish and retry. Call the CLI through node, because `npx playwright` may lack
   exec permission.
2. **Serve over HTTP, not file://.** Self-hosted fonts are CORS-blocked on file://, so the page renders wrong.
   Run `python3 -m http.server 8811` in the project folder with terminal background=true (a foreground server call is refused),
   and kill it when done.
3. **Script: two contexts**, 1440x900 and 390x844, locale en-US:
   - Record every request not going to localhost (it must be empty), every response with status >= 400, and page errors.
   - Scroll the page in 400 px steps so the scroll-reveal content appears, go back to the top, and take full-page + top screenshots.
   - Assert `document.documentElement.scrollWidth === viewport width` (no horizontal scroll).
   - Desktop: click the ES switch. Check `<html lang>`, the h1 and the title, and that no raw i18n keys show (`^[a-z]+\.[a-zA-Z.]+$`).
     Submit the empty form (errors should be in the current language), fill the required fields, submit, and screenshot the
     contact section to see the thank-you state.
   - Mobile: open the hamburger and take a screenshot.
4. **Review the screenshots** with vision_analyze. Crop tall full-page shots with `region` one section at a time, because a
   7000 px page downscales too far to judge. Things to look for: nav items wrapping onto two lines, a hero headline taller than
   ~4 lines, a scroll indicator overlapping text, an image band rendering as giant stacked images, mobile header collisions
   at 360–390 px, leftover English in ES mode, and photos that don't fit their card's subject.
5. **Copy sweep:** grep the HTML and the i18n dictionary (script.js) for claims that aren't in the brief (years, certifications,
   numbers, "parts", "delivery", "quickly", time promises). Builders embellish copy even when told not to. Send the exact
   replacement lines in EN and ES as a copy-only job.
6. Send exact fixes as ONE follow-up build job, then re-run check-site, the tests and this script on the final version.

## Pitfalls
- check-site's label check needs a `<label for="id">` on every field, including checkboxes wrapped in a label and honeypot
  fields. Put this in the build task up front.
- A relayed message can arrive several times, so parallel build jobs may land on the same project. Run `felo-team.py jobs`
  before starting a job and again before your final check, and verify the final combined state, not your own job's output.
- Long waits: tool calls time out at around 3–7 minutes. Poll builds with short loops (`pgrep -f "claude -p"` or
  `felo-team.py jobs`) rather than one long sleep.
