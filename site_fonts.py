"""The site's fonts, served from the site itself (/assets/fonts/) instead of Google Fonts: Archivo (headings), Public Sans
(text) and, on the state pages, JetBrains Mono (bill numbers, histories) and Public Sans italic. All three are under the
SIL Open Font License (fonts/OFL-<family>.txt, published beside the files).

fonts/<file>-<subset>.woff2 are made by tools/subset_fonts.py from the fonts' own files, cut to the weights and widths the
pages use, in two pieces each as Google splits them: "latin", which every page loads, and "latin-ext", which a browser
fetches only for a letter in its range (unicode-range). The descriptors are Google's, so each piece of text is drawn as
before. On the site each file is named by its contents (install()), so browsers keep it for good (build_site.sh's
_headers rule for /assets/).

css(prefix) is the @font-face rules: with "fonts/" inside the state pages' /assets/app.<hash>.css, with "/assets/fonts/"
in the other pages' own styles. The "... Fallback" faces (Arial, resized to the web font's size: fallback_css()) stand in
until a font arrives, so the text doesn't move when it does; the pages' --display and --body name them second.
"""
import hashlib, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(HERE, "fonts")

# Google Fonts' own ranges for the two pieces (the same for all three families), in Google's order: where the ranges
# overlap (three combining accents) the later rule, latin, is the one used.
SUBSETS = {
    "latin-ext": "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, "
                 "U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF",
    "latin": "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, "
             "U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
}

# Each file: its source (tools/subset_fonts.py), the axis ranges kept, and the @font-face rules that use it. The pages ask
# for Archivo at 700 and 800 in widths 80-100% (the Watchlist heading's lighter "·", .wlsep, is in Public Sans); Public Sans at
# 400, 600 and 700 (500 is drawn at 400, as Google's single-weight faces did); the italic at 400 only; JetBrains Mono at
# 500 and 700 (400 drawn at 500).
FACES = [
    {"file": "archivo", "family": "Archivo", "ttf": "Archivo[wdth,wght].ttf", "axes": {"wght": (700, 800), "wdth": (80, 100)},
     "rules": [("normal", "700 800", "80% 100%")], "pages": "all"},
    {"file": "publicsans", "family": "Public Sans", "ttf": "PublicSans[wght].ttf", "axes": {"wght": (400, 700)},
     "rules": [("normal", "400", None), ("normal", "600", None), ("normal", "700", None)], "pages": "all"},
    {"file": "publicsans-italic", "family": "Public Sans", "ttf": "PublicSans-Italic[wght].ttf", "axes": {"wght": 400},
     "rules": [("italic", "400", None)], "pages": "state"},
    {"file": "jetbrainsmono", "family": "JetBrains Mono", "ttf": "JetBrainsMono[wght].ttf", "axes": {"wght": (500, 700)},
     "rules": [("normal", "500", None), ("normal", "700", None)], "pages": "state"},
]

# The stand-ins while a font loads: Arial (on Windows, Macs and iPhones; elsewhere the next font in the list), resized to
# the web font's average letter width and line metrics (tools/subset_fonts.py --metrics: Archivo's at 700 and its 85%
# width, as most headings use, against Arial Bold). Only for the web font's own letters (unicode-range): other characters
# fall through to the next fonts in the list, as before.
REGULAR, BOLD = ['local("Arial")', 'local("ArialMT")'], ['local("Arial Bold")', 'local("Arial-BoldMT")']
FALLBACKS = [
    ("Archivo", "700 800", BOLD, {"size": "85.8%", "ascent": "102.3%", "descent": "24.5%", "gap": "0%"}),
    ("Public Sans", "400", REGULAR, {"size": "105.4%", "ascent": "90.1%", "descent": "21.3%", "gap": "0%"}),
    ("Public Sans", "600 700", BOLD, {"size": "105.4%", "ascent": "90.1%", "descent": "21.3%", "gap": "0%"}),
]


def _hashed(path):
    with open(path, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:10]
    name = os.path.basename(path)
    return name[:-len(".woff2")] + f".{h}.woff2"


def files():
    """{published name: source path} for every font file (named by its contents) and the license files."""
    out = {}
    for face in FACES:
        for sub in SUBSETS:
            p = os.path.join(FOLDER, f"{face['file']}-{sub}.woff2")
            out[_hashed(p)] = p
    for n in sorted(os.listdir(FOLDER)):
        if n.startswith("OFL"):
            out[n] = os.path.join(FOLDER, n)
    return out


def install(folder):
    """Copies the font files into folder (<site>/assets/fonts)."""
    os.makedirs(folder, exist_ok=True)
    for name, src in files().items():
        dst = os.path.join(folder, name)
        if not os.path.exists(dst):
            shutil.copyfile(src, dst)


def fallback_css():
    out = []
    for fam, weight, src, f in FALLBACKS:
        out.append(f'@font-face{{font-family:"{fam} Fallback";font-weight:{weight};src:{",".join(src)};size-adjust:{f["size"]};ascent-override:{f["ascent"]};'
                   f'descent-override:{f["descent"]};line-gap-override:{f["gap"]};unicode-range:{SUBSETS["latin"].replace(" ", "")}}}')
    return "\n".join(out)


def css(prefix, state=False):
    """The @font-face rules, the files at prefix + name. state: the state pages' faces too (the italic, the mono)."""
    names = {os.path.basename(src): name for name, src in files().items()}
    out = []
    for face in FACES:
        if face["pages"] == "state" and not state:
            continue
        for sub in SUBSETS:
            url = prefix + names[f"{face['file']}-{sub}.woff2"]
            for style, weight, stretch in face["rules"]:
                out.append(f'@font-face{{font-family:"{face["family"]}";font-style:{style};font-weight:{weight};'
                           + (f"font-stretch:{stretch};" if stretch else "")
                           + f'font-display:swap;src:url({url}) format("woff2");unicode-range:{SUBSETS[sub].replace(" ", "")}}}')
    return "\n".join(out) + "\n" + fallback_css() + "\n"


# The source pages load Google Fonts (so they can be looked at as they are, and the Claude copies keep doing so); the
# build puts the site's own fonts in their place (google_link()'s lines, then swap_google()).
GOOGLE = re.compile(r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\n<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\n'
                    r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2\?([^"]*)">\n')


def google_link(page):
    """The Google Fonts lines in page (a match: group(1) is the families asked for). Every page has them once."""
    found = list(GOOGLE.finditer(page))
    assert len(found) == 1, f"expected the Google Fonts lines once in the page, found {len(found)}"
    return found[0]


def swap_google(page, prefix="/assets/fonts/", braces=False):
    """page with its Google Fonts lines replaced by the site's own @font-face rules (in a <style>). The state pages'
    faces too when the page asks for JetBrains Mono. braces: page is a str.format() template (issues_site.HEAD)."""
    m = google_link(page)
    rules = css(prefix, state="JetBrains" in m.group(1))
    if braces:
        rules = rules.replace("{", "{{").replace("}", "}}")
    return page[:m.start()] + "<style>\n" + rules + "</style>\n" + page[m.end():]
