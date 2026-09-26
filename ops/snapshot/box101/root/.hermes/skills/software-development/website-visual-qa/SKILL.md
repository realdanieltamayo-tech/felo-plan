---
name: website-visual-qa
description: "Use when building a client site: assets and visual QA."
version: 1.0.0
author: Felo
platforms: [linux]
metadata:
  hermes:
    tags: [Website, Design, QA, Assets]
    related_skills: [felo-website-playbook, felo-dev-team]
---

# Website assets and visual QA

This skill adds to felo-website-playbook (the phases) and felo-dev-team (the build jobs). It covers the two steps those skills
leave thin: getting real assets into the project, and actually looking at the result.

## Design bar (Daniel's standard, always)

A plain or simple page gets rejected, pitch previews included. Every build task must spell out, in concrete terms:
- a full-bleed photo hero with a dark gradient and a real self-hosted display font (condensed, for industrial/B2B work);
- photo cards for each service or industry, plus at least one full-bleed image band or mosaic;
- hover lift/zoom, scroll-reveal (respecting prefers-reduced-motion), brand-colour focus rings;
- no invented facts, numbers or brands, with placeholders like [Phone] styled on purpose.

Name the sections and which photo goes where. Vague asks ("make it modern") come back basic.

## Procedure

1. **Assets first.** The builder (Claude Code) has no internet, so download everything before the job. Put licensed photos in
   `images/` and the font in `fonts/`, both credited in CREDITS.md. Recipe: `references/assets-photos-fonts.md`.
2. **Build task.** Give file names, pixel sizes and roles for each asset, plus the design bar above.
3. **Checks.** Run `felo-team.py review` and `check-site`. Also grep for external URLs.
4. **Look at it.** Run `bash scripts/render-shots.sh <project>` and view every desktop and mobile slice, plus `first.png` (the real
   1440x900 first view). check-site can't judge beauty. The browser tool refuses the private tailnet preview URL, so render
   locally from `file://`. Bug checklist: `references/visual-qa.md`.
5. **Fix.** Send a follow-up job listing each visual bug precisely. Tiny CSS or attribute fixes you can make yourself, then
   re-run check-site and the tests and commit.
6. **Report** in Daniel's language, short: preview link, what changed, what you checked, what's still open.

## Finding earlier work

When asked to redo "the preview you already made", session_search the client name and `ls /workspace/projects/`. Workbench
project names (e.g. "Dogo Group LLC") differ from folder slugs (e.g. `oil-equipment-site`).
