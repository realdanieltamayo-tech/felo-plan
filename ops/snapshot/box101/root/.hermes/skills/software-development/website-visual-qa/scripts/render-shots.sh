#!/usr/bin/env bash
# Render desktop (1440) + mobile (375) screenshots of /workspace/projects/<project>/<page>, sliced for vision.
# Usage: bash render-shots.sh <project> [page.html]
# Output: /tmp/shots/first.png (real 1440x900 first view), d*.jpg desktop slices, m*.jpg mobile slices
set -e
P="$1"; PAGE="${2:-index.html}"; SRC=/workspace/projects/$P
[ -f "$SRC/$PAGE" ] || { echo "no $SRC/$PAGE"; exit 1; }
CH=$(ls -d /root/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | sort | tail -1)
[ -x "$CH" ] || { echo "no chromium: pip install playwright && playwright install chromium"; exit 1; }
if ldd "$CH" | grep -q 'not found'; then
  apt-get install -y -q libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libxfixes3 libgbm1 libpango-1.0-0 libcairo2 libasound2t64 >/dev/null 2>&1 || true
  ldd "$CH" | grep 'not found' && { echo "still missing libs above"; exit 1; }
fi
rm -rf /tmp/render /tmp/shots; mkdir -p /tmp/shots; cp -r "$SRC" /tmp/render
shot() { "$CH" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size="$1" --virtual-time-budget=5000 \
  --screenshot="$2" "file:///tmp/render/$PAGE" >/dev/null 2>&1; }
shot 1440,900 /tmp/shots/first.png
sed -i 's|</head>|<style>.hero{height:900px!important;min-height:900px!important;max-height:900px!important}.reveal,[data-reveal]{opacity:1!important;transform:none!important}</style></head>|' "/tmp/render/$PAGE"
shot 1440,7000 /tmp/shots/desktop.png
sed -i 's|height:900px!important;min-height:900px!important;max-height:900px!important|height:780px!important;min-height:780px!important;max-height:780px!important|' "/tmp/render/$PAGE"
shot 375,10000 /tmp/shots/mobile.png
python3 - <<'EOF'
from PIL import Image
def slices(path, prefix, step):
    im = Image.open(path).convert('RGB')
    for i in range(0, im.height, step):
        im.crop((0, i, im.width, min(im.height, i + step))).save(f'/tmp/shots/{prefix}{i // step}.jpg', quality=80)
    print(prefix, im.size)
slices('/tmp/shots/desktop.png', 'd', 1750)
slices('/tmp/shots/mobile.png', 'm', 1700)
EOF
ls /tmp/shots
