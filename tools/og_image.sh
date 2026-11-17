#!/bin/bash
# Makes tools/og-image.png (1200 x 630), the link preview image, from tools/og_image.html with headless Chrome.
# Run it again after changing the HTML, look at the result, and commit both.
set -e
cd "$(dirname "$0")"
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
"$CHROME" --headless=new --hide-scrollbars --force-device-scale-factor=1 --window-size=1200,630 \
  --virtual-time-budget=8000 --screenshot="$PWD/og-image.png" "file://$PWD/og_image.html"
python3 -c "from PIL import Image; im = Image.open('og-image.png'); print('og-image.png', im.size)" 2>/dev/null || ls -l og-image.png
