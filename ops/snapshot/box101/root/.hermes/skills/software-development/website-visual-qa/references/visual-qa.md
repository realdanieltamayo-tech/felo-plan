# Visual QA of a built page

## Why render-shots.sh tweaks a copy
- A `height: 100vh` hero stretches to the full screenshot window height and swallows the page. The script copies the project to
  /tmp/render and pins the hero height. The real files are never touched.
- Scroll-reveal content stays at opacity 0 in a static screenshot and looks like empty sections, so the script forces `.reveal` visible.
  `first.png` is rendered without the overrides and shows the real first impression.

## Bugs builders typically leave (check each one)
- Nav links or header buttons wrap to two lines at desktop widths. Fix with `white-space: nowrap` and a hamburger breakpoint around 1100 px.
- The hero headline runs 6+ lines. Fix with a real condensed font, clamp() sizing, line-height ~0.95 and max-width ~18–19ch.
- The scroll indicator overlaps the text row under the hero buttons.
- `<ol>` step or value lists show browser numbers next to the custom badges. Fix with `list-style: none; padding-left: 0`.
- A tall dark side panel next to a form is mostly empty. Give it a photo backdrop under a gradient.
- On mobile (360–414 px), inline rows (dots, chips) wrap and overlap the next strip, and the header items collide.
- A checkbox wrapped in `<label>` without `for=` fails check-site's label test. Add `for="<id>"`.
- Hero content is indented differently from the logo. Everything should share the container's left edge.

## Before reporting
- check-site PASS, and the tests pass.
- External URLs: only the SVG xmlns (`grep -o 'https\?://[^\"]*' *.html *.css *.js | sort -u`).
- The preview note is visible and the placeholders are styled on purpose.
