"""West Virginia's daily floor calendars (2026-11-22), from the Clerks' Bulletin Board on www.wvlegislature.gov
(/Bulletin_Board/ is allowed by robots.txt, which sets no crawl delay).

Each house posts its calendar for the day as a small HTML file, listed newest first on an index page:
- the House's daily calendar, "HOUSE CALENDAR": house_calendar_daily.cfm?ses_year=2025&sesstype=RS&headtype=dc&houseorig=h
  links ?hdc=hdc2025-03-11-28.htm (the day's date and the session's day number), served as
  /Bulletin_Board/2025/RS/h_calendar_daily/hdc2025-03-11-28.htm;
- the House's Special Calendar, the one the House works from (the Rules Committee's choice of the day's bills):
  house_calendar_special.cfm?...&headtype=sc&houseorig=h, ?hsc=hsc2025-03-11-28.htm, /h_calendar_special/;
- the Senate's, "SENATE CALENDAR": senate_calendar.cfm?...&headtype=dc&houseorig=s, ?sdc=sdc 03-11.htm, /s_calendar/.
A calendar is paragraphs: the heading, the day ("Tuesday, March 11, 2025"), the day number, the hour ("11:00 A.M."),
then sections, "THIRD READING", "SECOND READING", "FIRST READING", "UNFINISHED BUSINESS" (resolutions) and "SPECIAL
ORDER OF BUSINESS", each bill a paragraph "Eng. Com. Sub. for S. B. 196 - Lauren's Law (original similar to HB2613)"
(or "(No Bills)").

Third reading is the passage vote. Measured on the Internet Archive's copies of 2024's and 2025's calendars against the
bills' histories: see states/wv/NOTES.md ("Floor calendars"). On the page: a bill on the Senate's or the Special Calendar's
third reading is a floor vote set for that day; one on the House Calendar's third reading (bills the House set aside
from the Special Calendar, which wait there), and second readings (the amendment stage, the day before the vote), are
"listed".
"""
import html
import re
from datetime import date, datetime, timedelta

INDEX = {  # kind -> (index page, the link's parameter, the folder the files are in)
    "hdc": ("house_calendar_daily.cfm", "h", "dc", "h_calendar_daily"),
    "hsc": ("house_calendar_special.cfm", "h", "sc", "h_calendar_special"),
    "sdc": ("senate_calendar.cfm", "s", "dc", "s_calendar"),
}
# ?hdc=hdc2025-04-12-60.htm, ?sdc=sdc 04-12.htm (written with a space; %20 in some links)
LINK = re.compile(r"""[?&](hdc|hsc|sdc)=([^"'&<>]+?\.htm)""", re.I)
PARA = re.compile(r"<p\b[^>]*>(.*?)</p>", re.I | re.S)
DAY = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),"
                 r"\s*(\d{4})\b")
CLOCK = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([AP])\.?\s*M\.?$", re.I)
SECTION = re.compile(r"^(THIRD READING|SECOND READING|FIRST READING|UNFINISHED BUSINESS|SPECIAL ORDER[A-Z ]*)$")
# "Eng. Com. Sub. for S. B. 196 -", "H. B. 2060 -", "Com. Sub. for H. J. R. 8 -": the bill a paragraph starts with
ITEM = re.compile(r"^(?:(?:Eng\.|Enr\.|Com\.\s*Sub\.(?:\s*for)?)\s*)*([HS])\.\s*(B|J\.\s*R)\.\s*(\d{1,4})\b", re.I)


def last_day(year):
    """The regular session's 60th day (profile.js's opens() + 59): from the second Wednesday of January, or of February
    in a year a governor is inaugurated (2025, 2029). Calendars after it are special sessions' (filed in the same
    folder: hsc2024-05-20-02.htm, sdc 10-07.htm, with their own bills, HB 102, SB 2011), or the budget's extension."""
    first = date(year, 2 if year % 4 == 1 else 1, 1)
    return first + timedelta(days=(2 - first.weekday()) % 7 + 7 + 59)


def regular(day):
    """Whether an ISO day is in its year's regular session (January 1 to the 60th day)."""
    d = date.fromisoformat(day[:10])
    return d <= last_day(d.year)


def file_url(site, year, kind, name):
    """The calendar file a link names."""
    return f"{site}/Bulletin_Board/{year}/RS/{INDEX[kind][3]}/{name.strip().replace(' ', '%20')}"


def index_url(site, year, kind):
    page, house, head, _ = INDEX[kind]
    return f"{site}/Bulletin_Board/{page}?ses_year={year}&sesstype=RS&headtype={head}&houseorig={house}"


def links(page):
    """An index page's calendars: [(kind, file name)], newest first, each once."""
    out = []
    for kind, name in LINK.findall(page or ""):
        item = (kind.lower(), html.unescape(name).replace("%20", " ").strip())
        if item not in out:
            out.append(item)
    return out


def name_day(kind, name, year):
    """The day a file's name gives: hdc2025-03-11-28.htm -> 2025-03-11; sdc 03-11.htm -> <year>-03-11."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", name) or re.search(r"(\d{2})-(\d{2})", name)
    try:
        g = m.groups()
        return date(int(g[0]), int(g[1]), int(g[2])) if len(g) == 3 else date(year, int(g[0]), int(g[1]))
    except (AttributeError, ValueError):
        return None


def paragraphs(page):
    out = []
    for p in PARA.findall(page or ""):
        s = html.unescape(re.sub(r"<[^>]+>", " ", p)).replace("\xa0", " ")
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append(s)
    return out


def parse(page):
    """A calendar file -> {"day": "2025-03-11", "time": "11:00", "bills": [(section, "SB196"), ...]} (time "" when
    the calendar has none), or None when it has no day."""
    day, clock, section, bills = None, "", "", []
    for s in paragraphs(page):
        if day is None:
            m = DAY.search(s)
            if m:
                try:
                    day = datetime.strptime(" ".join(m.groups()), "%B %d %Y").date()
                except ValueError:
                    pass
                continue
        t = CLOCK.match(s.replace(". M", ".M"))
        if t and not clock and not bills:
            clock = f"{int(t.group(1)) % 12 + (12 if t.group(3).upper() == 'P' else 0):02d}:{t.group(2) or '00'}"
            continue
        sec = SECTION.match(s.upper()) if s.upper() == s else None
        if sec:
            section = sec.group(1)
            continue
        m = ITEM.match(s)
        if m and section:
            key = f"{m.group(1).upper()}{'B' if m.group(2).upper() == 'B' else 'JR'}{int(m.group(3))}"
            if (section, key) not in bills:
                bills.append((section, key))
    if day is None:
        return None
    return {"day": day.isoformat(), "time": clock, "bills": bills}
