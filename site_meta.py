"""Link previews (Open Graph and Twitter card tags) and canonical links, for every page of statebilltracker.org: the
front page (build_site.sh), each state's pages (build_data.py's github_page()), the issue pages (issues_site.py) and
the page-not-found page. Addresses are the public ones once launched (LAUNCHED=1), else the preview's (SITE_BASE, or
statebilltracker.pages.dev). The preview image, /og-image.png, is tools/og-image.png (made by tools/og_image.sh)."""
import html
import os


def attr(s):
    """Text for a double-quoted attribute (apostrophes left as they are)."""
    return html.escape(s, quote=False).replace('"', "&quot;")

PUBLIC = "https://statebilltracker.org/"
PREVIEW = "https://statebilltracker.pages.dev/"
SITE_NAME = "State Bill Tracker"
# GoatCounter's site code for the whole site (<code>.goatcounter.com); counted only once launched. A state's own
# profile.py GOATCOUNTER_CODE, if set, takes its place on that state's pages.
GOATCOUNTER = "statebilltracker"
# Contributions: the State Bill Tracker Stripe account's Payment Link (visitors choose the amount). Linked from the About
# page and the footers, and from the state pages' "Glad this helped" note (support_meta()).
SUPPORT = "https://buy.stripe.com/00w6oGfNWcyx4DI9R49EI00"


def launched():
    return os.environ.get("LAUNCHED", "0") == "1"


def root():
    """The site's top address, ending in "/"."""
    if launched():
        return PUBLIC
    base = os.environ.get("SITE_BASE") or PREVIEW
    return base if base.endswith("/") else base + "/"


def support_meta():
    """The contribution link for a state's pages (tracker.html's supportNote() reads it)."""
    return f'<meta name="support" content="{attr(SUPPORT)}">\n' if SUPPORT else ""


def analytics(code=None):
    """The visit counter's tag, once launched; "" before (the preview isn't counted)."""
    code = GOATCOUNTER if code is None else code
    if not (launched() and code):
        return ""
    return (f'<script data-goatcounter="https://{code}.goatcounter.com/count" '
            'async src="https://gc.zgo.at/count.js"></script>\n')


def state_root(public_url, site_url):
    """A state's folder address: its public one once launched, else the one it's built for."""
    return public_url if launched() else site_url


def tags(title, desc, url, canonical=True):
    """The head tags for one page. title and desc are plain text (escaped here)."""
    t, d, u = attr(title), attr(desc), attr(url)
    img = attr(root() + "og-image.png")
    out = (f'<meta property="og:type" content="website">\n'
           f'<meta property="og:site_name" content="{SITE_NAME}">\n'
           f'<meta property="og:title" content="{t}">\n'
           f'<meta property="og:description" content="{d}">\n'
           f'<meta property="og:url" content="{u}">\n'
           f'<meta property="og:image" content="{img}">\n'
           f'<meta property="og:image:width" content="1200">\n'
           f'<meta property="og:image:height" content="630">\n'
           f'<meta property="og:image:alt" content="{SITE_NAME}">\n'
           f'<meta name="twitter:card" content="summary_large_image">\n'
           f'<meta name="twitter:title" content="{t}">\n'
           f'<meta name="twitter:description" content="{d}">\n'
           f'<meta name="twitter:image" content="{img}">\n')
    if canonical:
        out += f'<link rel="canonical" href="{u}">\n'
    return out
