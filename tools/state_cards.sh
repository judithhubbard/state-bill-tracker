#!/bin/bash
# Makes tools/cards/<st>.png (1200 x 630), each state's link preview card for its bill links (/<st>/bill/<number>), from
# tools/state_card.html with headless Chrome. Run it again only when the design changes (or a state is added), look at a
# few, and commit them; build_site.sh copies them to /cards/. Usage: tools/state_cards.sh [st ...]   (default: all)
set -e
cd "$(dirname "$0")"
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
mkdir -p cards
NAMES="al:Alabama ak:Alaska az:Arizona ar:Arkansas ca:California co:Colorado ct:Connecticut dc:District_of_Columbia
de:Delaware fl:Florida ga:Georgia hi:Hawaii id:Idaho il:Illinois in:Indiana ia:Iowa ks:Kansas ky:Kentucky la:Louisiana
me:Maine md:Maryland ma:Massachusetts mi:Michigan mn:Minnesota ms:Mississippi mo:Missouri mt:Montana ne:Nebraska nv:Nevada
nh:New_Hampshire nj:New_Jersey nm:New_Mexico ny:New_York nc:North_Carolina nd:North_Dakota oh:Ohio ok:Oklahoma or:Oregon
pa:Pennsylvania ri:Rhode_Island sc:South_Carolina sd:South_Dakota tn:Tennessee tx:Texas ut:Utah vt:Vermont va:Virginia
wa:Washington wv:West_Virginia wi:Wisconsin wy:Wyoming us:Congress"
for pair in $NAMES; do
  st=${pair%%:*}; name=${pair#*:}
  if [ $# -gt 0 ] && ! printf ' %s ' "$@" | grep -q " $st "; then continue; fi
  ST=$(echo "$st" | tr a-z A-Z)
  "$CHROME" --headless=new --hide-scrollbars --force-device-scale-factor=1 --window-size=1200,630 \
    --virtual-time-budget=8000 --screenshot="$PWD/cards/$st.png" \
    "file://$PWD/state_card.html?st=$ST&name=${name//_/%20}" 2>/dev/null
  echo "cards/$st.png"
done
