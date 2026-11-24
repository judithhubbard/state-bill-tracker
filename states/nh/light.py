"""New Hampshire's light history (states/light.py, states/LIGHT.md): the session years before the shared window, from
the Legislature's public read-only SQL Server with fetch.py's own sql_year() (PastLegislation, PastDocket,
PastSponsors, RollCallSummary and RollCallHistory: the same five files in the daily files' shapes, about ten small
queries a year, a second apart). A session year's page needs both years of its General Court (bills kept over to the
second year are in its files), so both are read. Also the General Court's members who appear in them (Legislators,
every member since about 2015: parties), and the code tables (Committees, SubjectCodes, GeneralCodes, BodyStatusCodes)
from the daily files at gc.nh.gov's crawl delay (robots.txt read first, as fetch.py does; today's tables: a committee
renamed since keeps today's name). The server's address and published login come from the Legislature's own document,
read with pypdf (never written into the repository). Needs `pip install pymssql pypdf`. Analyses ("What it does") and
veto messages aren't read: the light records keep the titles."""
import os, sys

SOURCE = "New Hampshire General Court's public SQL Server (PastLegislation and the related views) and gc.nh.gov code tables"
# One session year a page, 2015 up to the window's first (a General Court is two years: 2015-16 ... 2021-22).
from states import window as W
SESSIONS = list(range(2015, W.first_year()))
CODE_TABLES = ("Committees", "SubjectCodes", "GeneralCodes", "BodyStatusCodes")


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        from states.nh import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    first = F.first_year(session)
    folder = os.path.join(data, str(first))
    os.makedirs(folder, exist_ok=True)
    rp = F.robots()
    if rp is None:
        print("nh: robots.txt couldn't be read; nothing downloaded", flush=True)
        return False
    for name in CODE_TABLES:
        F.per_term(rp, name, F.PER_TERM[name], folder)
    try:
        import pymssql, pypdf  # noqa: F401
    except ImportError:
        print("nh: pymssql or pypdf isn't installed (pip install pymssql pypdf)", flush=True)
        return False
    login = F.sql_login(rp)
    if not login:
        print("nh: no SQL Server login from the Legislature's document", flush=True)
        return False
    db = None
    try:
        db = F.Sql(login)
        people = {F.fmt(r["employeeno"]).strip(): r for r in db.rows(
            "SELECT PersonID, Employeeno, LastName, FirstName, MiddleName, LegislativeBody, seatno, countycode, "
            "District, party, Address, address2, city, Expr2, Zipcode, EMailAddress FROM dbo.Legislators")}
        for year in (first, first + 1):
            written = F.sql_year(db, year, people)
            print(f"nh {year}: " + (", ".join(written) or "nothing"), flush=True)
        rows = F.members_of(first, people)
        if rows:
            F.write(os.path.join(folder, "legislators.txt"), rows)
        print(f"nh {first}-{first + 1}: {len(rows)} legislators", flush=True)
    except Exception as e:  # (the login is never printed)
        print(f"nh: SQL Server: {type(e).__name__}: {db.scrub(e) if db else str(e).replace(login['password'], '***')}",
              flush=True)
        return False
    finally:
        if db:
            db.conn.close()
    return all(os.path.exists(os.path.join(folder, f"{n}_{session}.txt")) for n in ("LSRs", "Docket", "LsrSponsors"))
