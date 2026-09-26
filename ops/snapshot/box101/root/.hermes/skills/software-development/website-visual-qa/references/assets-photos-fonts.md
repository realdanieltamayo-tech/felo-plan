# Assets: licensed photos and self-hosted fonts

## Photos from Unsplash (a path that works)

The Unsplash/Pexels search APIs and search pages block scripted access, so find the photos through web search:

1. Run web_search, e.g. `unsplash photos open pit mine free photo`. Keep the URLs `unsplash.com/photos/<slug>-<ID>`. The ID is the last
   11 characters. If a result has no `data` key, retry after a few seconds.
2. Check the licence: web_extract the photo page and require "Free to use under the Unsplash License". Reject Unsplash+ photos.
   Note the photographer (`unsplash.com/@user`).
3. Resolve the file: `curl -sI -A "Mozilla/5.0" "https://unsplash.com/photos/<ID>/download?force=true"` returns a 302 whose
   `location:` header points at `https://images.unsplash.com/photo-...`. Strip everything after `?` and fetch
   `"<base>?ixlib=rb-4.1.0&fm=jpg&q=80&w=2400"`.
4. Build a PIL contact sheet (4 per row, labelled with IDs) and inspect it with vision. Choose a hero, one photo per card and one
   wide band photo. Skip photos with brand logos or faces.
5. Compress with PIL into `images/<role>-<subject>.jpg`: hero 1920 px, cards 1200 px, progressive/optimize. Lower the quality
   from 82 until the file is under 290 KB (check-site flags anything over 400 KB).
6. Write CREDITS.md: file, subject, photographer, source URL, licence, and download date. Never hotlink.

## Display font (self-hosted, OFL)

System "condensed" stacks fall back to a wide sans-serif. Headlines then balloon to 6+ lines and look amateur, so ship a real file:

```
curl -sfL -o F-Bold.ttf https://github.com/google/fonts/raw/main/ofl/<family>/<Family>-Bold.ttf   # also SemiBold, ExtraBold
curl -sfL -o OFL.txt   https://github.com/google/fonts/raw/main/ofl/<family>/OFL.txt
pip install -q fonttools brotli
pyftsubset F-Bold.ttf --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+2000-206F,U+20AC,U+2122,U+2190-2193" \
  --flavor=woff2 --layout-features='*' --output-file=<project>/fonts/<family>-bold.woff2
```

The Latin-1 range covers Spanish accents and ñ. Each weight comes out around 23 KB. Copy OFL.txt into fonts/ and add a Fonts table to
CREDITS.md. In the task, ask for `@font-face` (font-display: swap) and a `<link rel=preload>` for the main weight.
Barlow Condensed (`barlowcondensed`) suits industrial and B2B work.
