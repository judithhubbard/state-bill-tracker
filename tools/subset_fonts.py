#!/usr/bin/env python3
"""Makes the site's font files, fonts/*.woff2, from the fonts' own variable TTFs (the google/fonts repository on GitHub:
ofl/archivo/Archivo[wdth,wght].ttf, ofl/publicsans/PublicSans[wght].ttf and PublicSans-Italic[wght].ttf,
ofl/jetbrainsmono/JetBrainsMono[wght].ttf; each folder's OFL.txt is fonts/OFL-<family>.txt).

Each face is cut to what the pages use (site_fonts.FACES: the weights and widths the CSS asks for; the italic only at 400)
and split as Google Fonts splits them: a "latin" file every page loads and a "latin-ext" file a browser fetches only for a
letter in its range (Hawaiian ō, Polish ł ...), with the same unicode-range, so every character is drawn by the same font as
before. Layout features: fontTools' defaults (kerning, ligatures, marks ...) and tabular numbers (font-variant-numeric).
No hinting (as Google serves to current browsers).

Needs fontTools and brotli (pip install fonttools brotli). Run once when a face changes, then commit fonts/:
    python3 tools/subset_fonts.py <folder with the four TTFs>
and, for the fallback faces' sizes (site_fonts.FALLBACKS), on a Mac:
    python3 tools/subset_fonts.py --metrics <folder>
"""
import os, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import site_fonts as SF


def ranges(text):
    out = set()
    for part in text.split(","):
        a, _, b = part.strip()[2:].partition("-")
        out.update(range(int(a, 16), int(b or a, 16) + 1))
    return out


def main(src):
    for face in SF.FACES:
        base = TTFont(os.path.join(src, face["ttf"]))
        limits = {k: tuple(v) if isinstance(v, (list, tuple)) else v for k, v in face["axes"].items()}
        for sub, rng in SF.SUBSETS.items():
            font = TTFont(os.path.join(src, face["ttf"]))
            opts = subset.Options()
            opts.layout_features = subset.Options().layout_features + ["tnum"]
            opts.hinting = False
            opts.desubroutinize = True
            opts.name_IDs = ["*"]  # (the copyright and license notices stay in the file)
            opts.notdef_outline = True
            s = subset.Subsetter(opts)
            s.populate(unicodes=ranges(rng) & set(base.getBestCmap()))
            s.subset(font)
            if limits:
                font = instancer.instantiateVariableFont(font, limits)
            path = os.path.join(HERE, "fonts", f"{face['file']}-{sub}.woff2")
            font.flavor = "woff2"
            font.save(path)
            print(f"{path}: {os.path.getsize(path):,} bytes, {len(font.getBestCmap())} characters")


# A sample of the site's text, for the average letter width.
SAMPLE = ("An act concerning the appropriation of funds for the Department of Education, establishing a program for "
          "affordable housing and making an appropriation; relating to public health, elections and taxes. Passed both houses")


def metrics(src):
    """The fallback faces' size-adjust and line metrics (site_fonts.FALLBACKS), against Arial (macOS's copy)."""
    arial = "/System/Library/Fonts/Supplemental/Arial{}.ttf"

    def width(font):
        cmap, hmtx = font.getBestCmap(), font["hmtx"]
        return sum(hmtx[cmap[ord(c)]][0] for c in SAMPLE) / font["head"].unitsPerEm
    for fam, ttf, loc, ref in (("Archivo", "Archivo[wdth,wght].ttf", {"wght": 700, "wdth": 85}, " Bold"),
                               ("Public Sans", "PublicSans[wght].ttf", {"wght": 400}, "")):
        w = instancer.instantiateVariableFont(TTFont(os.path.join(src, ttf)), loc)
        f = TTFont(arial.format(ref))
        k = width(w) / width(f)
        upm, hh = w["head"].unitsPerEm, w["hhea"]
        print(f'{fam}: "size": "{k * 100:.1f}%", "ascent": "{hh.ascent / upm / k * 100:.1f}%", '
              f'"descent": "{-hh.descent / upm / k * 100:.1f}%", "gap": "{hh.lineGap / upm / k * 100:.1f}%"')


if __name__ == "__main__":
    if sys.argv[1] == "--metrics":
        metrics(sys.argv[2])
    else:
        main(sys.argv[1])
