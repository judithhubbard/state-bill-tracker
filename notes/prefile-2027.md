# Prefiled bills for 2027 (surveyed 2026-11-22)

Each state's next session shows as an "upcoming" page (build_data.py: a session after `P.session_of(this year)`) once
its fetch.py downloads at least one bill for it. The rules every fetcher now follows:

- One cheap request a run to see whether the next session is listed or has bills; no data folder until it has a bill
  (the converter would show an empty session).
- A session that hasn't begun, or has just begun with no bills or files yet, never marks the state incomplete
  (`W.recent(2027)` is True, so `W.settle()` doesn't protect it: each fetcher checks a `begun()` date).
- Converters' bill floors (100 to 1,000 bills before a session shows) apply only to sessions before this calendar
  year; this year's and next year's show from their first bill.
- The session just ended keeps being read into the new year where its last actions (governor, President) come late.

"Now" = bills were up on 2026-11-22. Sessions are keyed by their first year (2027 = 2027 or 2027-28).

| State | Publishes before the session? | Expected | Source | Site status |
|---|---|---|---|---|
| AK | First prefile release, 2nd Friday of January | ~Jan 8 | akleg.gov BASIS session=35 | From January (converter floor removed) |
| AL | Prefiled after the Jan 12 organizational session | mid-Jan | ALISON GraphQL "2027RS" | From January |
| AR | **Yes, now: 15 bills (2027R)** | now | webftp.blr.arkansas.gov LegislativeMeasures.txt | Already downloaded; hidden by the converter's 100-bill floor, fixed: shows at the next publish |
| AZ | Yes (Open States "58th-1st-regular", listed, 0 bills) | any day (2026's first 2025-11-15) | Open States | Fetcher no longer makes an empty folder; shows from the first bill |
| CA | Yes: 2027-28 convenes Dec 7, bills from then | Dec 7 | downloads.leginfo pubinfo daily zip / pubinfo_2027.zip | Shows after Dec 7 (fetcher takes the newest session in the zip) |
| CO | No (introduction day) | Jan 13 | leg.colorado.gov | From January (floor removed) |
| CT | No | ~Jan 6-7 | ftp.cga.ct.gov | From January; empty top folder no longer overwrites 2026 |
| DE | Yes (154th GA listed, empty) | ~mid-Dec | legis.delaware.gov GetAllLegislation | Already handled |
| FL | Yes | | flsenate.gov / myfloridahouse | On the site |
| GA | Prefiling after the election; 2027 not in GetSessions yet | unknown | webservices.legis.ga.gov | Reads it once listed with an HB/SB (new) |
| HI | No | Jan 20 | Open States | From January; current year no longer holds HI back |
| IA | Yes, once ga=92 is listed | Dec-Jan | legis.iowa.gov | Already read; 500-bill floor removed |
| ID | No | ~Jan 12 | legislature.idaho.gov sessioninfo/2027 | From January; missing bill pages of the current year no longer hold ID back |
| IL | Yes: prefiled with the Clerk from early December (1,081 on 2024-12-02) | early Dec | ftp.ilga.gov/Legislation/105 | Already read (CURRENT+2); contacts no longer crash in January |
| IN | 2027 listed (members, committees), no bills | early Jan | Indiana API | Floor removed |
| KS | Unknown: biennium b2027_28 answers 0 bills | Dec or Jan 11 | KLISS /api/v1 | Probes the next biennium from Nov 1 (new); contacts no longer fail |
| KY | Bill requests aren't numbered until the session | ~Jan 5 | apps.legislature.ky.gov record/27rs | From January |
| LA | Prefiling from ~February (session in April) | mid-Feb | legis.la.gov 27RS | Already handled |
| MA | No (numbered mostly in February) | late Jan-Feb | malegislature.gov API court 195 | No longer held off the site in January (new) |
| MD | Yes: 2027RS list exists, empty | December | mgaleg.maryland.gov 2027RS legislation.json | Reads from November (new) |
| ME | LegiScan; bills from January | Jan | LegiScan | legiscan.py reads the next Legislature once listed (new) |
| MI | No prefiling | mid-Jan | legislature.mi.gov 2027-2028 | Floor removed |
| MN | Session 0952027 listed, no bills | ~Jan 12 | revisor.mn.gov | A failed probe no longer marks MN incomplete |
| MO | Yes, from Dec 1 | early Dec | house.mo.gov / senate.mo.gov | Already handled |
| MS | No | Jan 5 | billstatus.ls.state.ms.us | Floor removed |
| MT | Yes | | | On the site |
| NC | No | late Jan | ncleg.gov RSS 2027 (answers, empty) | Empty feed no longer counts as missing; floor removed |
| ND | Yes, with the December organizational session | December | ndlegis.gov api assemblies.json | Already handled |
| NE | No | ~Jan 6-7 | nebraskalegislature.gov | No longer incomplete with an empty list |
| NH | LSRs now; numbered bills late Dec-Jan | late Dec | gc.nh.gov dynamicdatadump | Shows from the first numbered bill; December's new term no longer holds NH back |
| NJ | No new session: 2026-27 runs until January 2028 | | | Nothing to do |
| NM | Yes, once "2027 Regular" is listed | mid-Dec | nmlegis.gov | Already handled (ahead=1) |
| NV | Yes | | | On the site |
| NY | Yes (Nov-Dec of even years) | | Senate API | fetch_bills.py |
| OH | No (API answers 500 for the 137th) | mid-Jan | Ohio API | No longer incomplete in January; the 136th re-read until April for the governor |
| OK | LegiScan; prefiling from December | Dec | LegiScan | legiscan.py reads it once listed (new); even-year folder no longer replaces the odd year's early |
| OR | Pre-session filed measures (2025's on 2024-12-31) | late Dec | api.oregonlegislature.gov 2027R1 | Probes from November (new) |
| PA | No | Jan 5+ | palegis.us BillHistoryData 2027_0 | No longer incomplete; 2025 re-read until Feb 1 |
| RI | LegiScan; January | Jan | LegiScan | Handled by legiscan.py |
| SC | Yes, prefiling in December (session 127 not offered yet) | December | scstatehouse.gov billsearch | No empty session saved (new) |
| SD | Yes: session 174 listed, 0 bills | Dec-early Jan | sdlegislature.gov API | Shows from the first bill (floor removed) |
| TN | LegiScan; filing opens after the election | Nov-Dec | LegiScan | legiscan.py reads it once listed (new) |
| TX | Yes | | | On the site |
| US | No: 120th Congress from Jan 3 | Jan 3-10 | govinfo BILLSTATUS 120 | Read from sitemaps before any zip; 119th re-read until March 1; contacts don't fail before the new members are listed |
| UT | Yes: numbered from early December (2027GS list exists, empty) | early Dec | glen API 2027GS | Reads from November (new); floor removed. The local API token answers "Invalid request" (the workflow's secret assumed fine) |
| VA | Yes | | | On the site |
| VT | LegiScan; January | Jan | LegiScan | Handled by legiscan.py |
| WA | Yes, prefiling from the first Monday of December | Dec 7 | wslwebservices GetPreFiledLegislationInfo | Reads 2027-28's prefiled list (new) |
| WI | No | mid-late Jan | docs.legis.wisconsin.gov 2027 | No longer incomplete before April; floor removed |
| WV | Not surveyed (site timed out); fetcher already reads next year from November | | wvlegislature.gov | Already handled in code |
| WY | Yes, once bills are numbered (BillInformation/2027 empty) | Dec-Jan | lsoservice.wyoleg.gov | Floor removed |

Open questions: GA's and SC's real formats for a session not begun (nothing published yet); WV's site wasn't reachable;
whether LegiScan lists TN and OK 2027 sessions before January (one getMasterList a day each once it does).
