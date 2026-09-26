---
name: licensed-stock-images
description: "Use when a project needs legally usable stock photos."
version: 1.0.0
author: Felo
platforms: [linux]
metadata:
  hermes:
    tags: [Images, Licensing, Website, Assets]
    related_skills: [felo-website-playbook, felo-dev-team, static-page-visual-check]
---

# Licensed stock images into a project

Use this for client sites, pitch pages, print and social posts.
Daniel's rule: only images we may legally use. That means Unsplash licence or Pexels licence (commercial use OK), or original SVG.
Images are downloaded into the project (never hotlinked), compressed, and credited in CREDITS.md.
Felo does this step herself BEFORE the build job, because Claude Code (felo-dev-team) has no internet.

## Procedure

1. **Find photo pages with web_search.** For example, `unsplash photos <subject> free photo`. One query per slot
   (hero, each card, a band). Keep only URLs shaped `unsplash.com/photos/<slug>-<ID>`. The ID is the part after the last dash.
   Unsplash's own search pages and JSON endpoints block scripted access, so web_search is the reliable way to discover photos.
   web_search sometimes returns no `data` key: retry the same query after a short pause.
2. **Verify the licence per photo.** web_extract the photo page. It must say "Free to use under the Unsplash License" and
   show "Download free". Skip Unsplash+ / premium-only photos. Get the photographer from the "by <Name>" line or the @username.
3. **Download through the official link**, sized at the source:
   ```bash
   loc=$(curl -sI -A "Mozilla/5.0" "https://unsplash.com/photos/$ID/download?force=true" | grep -i '^location' | tr -d '\r' | cut -d' ' -f2)
   base=${loc%%\?*}
   curl -s -o "$ID.jpg" "$base?ixlib=rb-4.1.0&fm=jpg&q=80&w=2400"
   ```
   The redirect's `dl=<photographer>-<ID>-unsplash.jpg` also gives you the photographer's name.
4. **Look before choosing.** Build a PIL contact sheet (thumbnails with the ID under each) and view it. Reject miniatures or
   dioramas, visible brand logos, recognisable faces, and shots that don't read at card size. Download 2 candidates per slot.
5. **Compress into `<project>/images/`** (`pip install pillow` if needed). Widths: hero 1920, full-bleed band 1600,
   card 1200. Save as JPEG, progressive, quality 82 stepping down by 4 until the file is under ~290 KB. Name files by slot and
   subject, e.g. `hero-oil-pumpjack-sunset.jpg`, `mining-open-pit.jpg`.
6. **Write `CREDITS.md`**: a table of file | subject | photographer | source URL (`https://unsplash.com/photos/<ID>`), plus the
   licence line, the download date, "resized/recompressed, not hotlinked", and the rule for adding new images. If you self-host
   fonts, credit them too (OFL + OFL.txt in fonts/).
7. **Hand off:** in the build task, list each image as path + dimensions + subject + intended slot, and tell the builder not to
   modify images/, fonts/ or CREDITS.md.

## Rules
- If you can't confirm a photo's licence, don't use it. If every download fails, tell the builder to use polished original
  SVG illustrations in the brand palette, and say so to Daniel.
- Keep every file under 300 KB (check-site flags anything over 400 KB as heavy).
- Photos of real work scenes (rigs, mines, fields, power lines) read as "serious supplier". Avoid staged office people.
