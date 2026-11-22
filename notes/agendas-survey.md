# Committee agendas: survey and readers (2026-11-22)

Upcoming committee meetings with the bills on their agendas ("On an upcoming committee agenda"), from each state's
`agendas(session)` in states/<st>/convert.py: {bill: [["House Judiciary", "2027-02-03T10:00:00"], ...]}, meetings from today
on. Before this, 32 states had none: an empty `agendas()` or none at all. All of them were surveyed. 31 now have a reader; Georgia is blocked.
Each state's NOTES.md has a paragraph on its reader.

**Nothing has been tested against a live session's agendas.** It's between sessions: no state had bills on upcoming
agendas on 2026-11-22, except Massachusetts (4 bills on hearings Nov 30-Dec 15). Each reader was tested on past meetings in the same
format: live past pages, saved pages, or Internet Archive copies, which were used for development only. In those tests the
date was set back and the output's keys were matched against the records' numbers. `test/data_check.py` now checks
agendas: it fails when a bill named isn't a record's number or when an entry is malformed, and LOOKs at the count.

The states that already had readers (AK AR CA FL HI IA MT ND NE NH NJ NV OH OR TX VA WA, and New York's own) are unchanged.
Congress is handled separately.

## Table

| State | Agenda source | Format | Bills listed? | Posted how far ahead | Automated access | Result |
|---|---|---|---|---|---|---|
| AL | ALISON GraphQL, alison.legislature.state.al.us/graphql, `meetings{agendaItems{instrumentNbr}}` (the query its "Today's Schedule" page sends) | JSON (UTC times) | yes | days to weeks | no robots.txt | done (as of 2026-03-03 on the live server's past data: 344 bills, all matched) |
| AZ | www.azleg.gov/standing-committee (the session's standing committee meetings) + each agenda PDF /agendas/MMDDnnCCCCSSS.pdf | HTML + PDF (pdftotext) | yes (PDFs) | about a week (estimate) | robots.txt allows both paths; 120 s crawl delay kept (about 7 PDFs a run); apps.azleg.gov never read | done (tested on the 2026-02-17 House Education agenda: 21 bills) |
| CO | leg.colorado.gov /committees?sess=YYYYa, each committee's "Upcoming Schedule", /agenda/committee/<id> | HTML | yes | next 1-2 meetings per committee | robots bars only floor calendars, journals, downloads; 3 s apart | done (tested on archived 2026 pages; runs January to June 20 only) |
| CT | www.cga.ct.gov/basin/api/v1/calendar-events/ + each event's agenda PDF | JSON + PDF (pdftotext) | yes | feed ~1 year; PDFs when posted | robots bars /asp/cgabillstatus/, /html/ etc., not /basin/ or /<year>/ | done (tested on March 2026 agendas) |
| DE | POST legis.delaware.gov/json/CommitteeMeetings/GetUpcomingCommitteeMeetings, then /json/MeetingNotice/GetCommitteeMeetingItems?committeeMeetingId=N | JSON | yes | about a week | no robots.txt | done (tested on the past-meetings grid, May-June 2026: 16 bills, all matched; the upcoming grid's date format is assumed to match the past grid's) |
| GA | www.legis.ga.gov/api/meetings | JSON | unknown | unknown | gated: 401 without a token built from a key hidden in the site's script; the SOAP services have no meetings service; house.ga.gov and senate.ga.gov time out | **blocked** (a deliberate gate, not worked around; would need the General Assembly's permission or a feed) |
| ID | legislature.idaho.gov/sessioninfo/agenda/hagenda/ and sagenda/ (fallback: each standing committee's page) | PDF (pdftotext) | yes | days | robots bars only /committee-calendar/action~* | done (tested on 4 live March 2026 PDFs: 16 bills, all matched) |
| IL | `<committeehearing>` lines in each bill's status XML, ftp.ilga.gov (already downloaded) | XML | per bill | as posted; nightly sync | the file repository is allowed; www.ilga.gov blocks bots (not touched) | done (Senate wording untested) |
| IN | api.iga.in.gov /<year>/meetings?minDate=&maxDate=, /<year>/meetings/<id> | JSON API (key in hand) | yes | from early December for the next session | API, 0.6 s apart | done (date set to 2026-02-02: 189 bills, all matched) |
| KS | kslegislature.gov/api/v1/hearings/?biennium=b2025_26&from=..&to=.. (built from the journals' "Hearing:" lines) | JSON | yes | 1-9 days (mostly 5-7) | no robots.txt; 30 requests/min without a key | done (date set to 2026-02-10: 233 of 234 bills matched; hearings only, meetings that only vote aren't listed) |
| KY | apps.legislature.ky.gov/LegislativeCalendar/ (agendas inline) + apps.legislature.ky.gov/CommitteeDocuments/<id>/ agenda PDFs | HTML + PDF (pdftotext) | yes ("26RS HB 414") | rest of the week; PDFs when uploaded | no robots.txt; 1 request/s | done (archived 2026-02-17 calendar plus live past PDFs: 43 bills) |
| LA | legis.la.gov/legis/ByCmte.aspx + Agenda.aspx?m=<id> | HTML | yes | ~1-3 weeks | no robots.txt; 1 request/s | done (saved April-May 2026 agendas: 23 bills, all matched) |
| MA | malegislature.gov/api/Hearings + /api/Hearings/<id> | JSON (HearingAgendas with BillNumber) | yes | weeks | robots allows all | done (2025 hearings: 111 bills, all matched; a live run found 4 upcoming bills) |
| MD | mgaleg.maryland.gov/mgawebsite/Meetings/Day/<from><to>?...&ys=<year>rs (one page for three weeks) | HTML | yes (hearings and voting sessions) | weeks | no robots.txt | done (2026-02-16 to 02-20: 423 bills, all matched; struck-through bills dropped) |
| ME | each bill's LegiScan `calendar` (already downloaded); committee from the bill's referral | JSON | per bill | as LegiScan has them | legislature.maine.gov: only bill pages are read (robots bars search pages) | done (2026's saved calendars: 128 bills, all matched) |
| MI | www.legislature.mi.gov/Committees/Meetings + /Committees/Meeting?meetingID=N | HTML (canceled meetings struck through) | yes | ~1-3 weeks | no robots.txt; the Legislature's 1 request/s kept | done (archived Feb 2025 list, past meeting pages; joint resolutions left out) |
| MN | House www.house.mn.gov/Schedules/All; Senate www.mnsenate.gov/api/schedule/range/<from>/<to> | HTML / JSON | yes | a few days | house.mn.gov bars only /Fiscal2/; mnsenate.gov has no robots.txt | done (March 2026 pages: 233 bills, all matched) |
| MO | Senate www.senate.mo.gov/hearingsschedule/hrings.htm; House: the `<Hearings>` blocks in the House XML exports already downloaded | HTML; XML | yes | about a week | Senate robots bars only /Trade/, /DistrictWebApps/; house.mo.gov itself not read | done (archived Feb and Apr 2026 Senate pages: 450 and 204 bills, all matched) |
| MS | Senate: legislature.ms.gov/calendars-and-schedules/senate-committee-agenda/, which links one PDF the Senate rewrites; House: billstatus.ls.state.ms.us/htms/h_sched.htm (times and rooms only) | PDF (pdftotext) | Senate yes; House no | 1-2 days | no robots.txt | Senate done (two archived 2025 copies: 73 bills); **House: no agendas with bills published**, so its meetings are shown as "the committee meets" on every bill in that committee (h_sched.htm, HTML, every run; tested on 2025 archived copies) |
| NC | www.ncleg.gov/LegislativeCalendar/<m>/<yyyy> | HTML (chamber, committee, CANCELLED/UPDATED, bill links) | yes | weeks | robots bars only /WHPTest/, /Ethics/; Crawl-delay 2 kept | done (June 2025: 135 of 141 matched; the rest are confirmation resolutions the converter doesn't keep) |
| NM | www.nmlegis.gov/Calendar/Session (fallback: /Calendar/Session_Archive?Year=YYYY): committee agenda PDFs and daily schedules | PDF (pdftotext) | yes | 1-3 days | robots bars only /*.axd | done (as of 2026-02-04: 88 bills, all matched; tested by the archive path) |
| OK | each bill's LegiScan `calendar` (already downloaded) | JSON | per bill | as LegiScan has them | (the LegiScan route, states/LEGISCAN.md) | done (2026's saved calendars: 886 bills, all matched; only the latest "REVISED" agenda is kept) |
| PA | www.palegis.us/house/rss/committee/schedule and /senate/rss/committee/schedule | RSS (parss: MeetingDate, Time, Committee, Bills) | yes | ~1-3 weeks | robots limits only an accessibility scanner | done (archived March 2026 House feed: 27 bills, all matched; Senate feed untested) |
| RI | each bill's LegiScan `calendar` (already downloaded) | JSON | per bill | as LegiScan has them | (LegiScan; rilegislature.gov's robots.txt bars its committee PDFs) | done (2026's saved calendars: 2,144 bills, all matched) |
| SC | www.scstatehouse.gov/meetings?chamber=H\|S&selecteddate=<Monday> + each meeting's agenda PDF | HTML + PDF | yes | about a week | robots bars only images, /dashboard/, /sys/ | done (live Feb 2026 weeks: 59 bills, all matched) |
| SD | sdlegislature.gov/api/SessionCommittees/Documents/<id>?Type=3&Type=5, then /api/Documents/<docId>.html | JSON + HTML | yes | a few days | robots bars only /pdfviewer, logos | done (2026 House Judiciary agendas) |
| TN | each bill's LegiScan `calendar` (already downloaded) | JSON | per bill | as LegiScan has them | capitol.tn.gov: robots.txt "Disallow: /" for all but named search engines | done (2026's saved calendars: 976 bills, all matched); **LegiScan has no House hearings after January 2026** |
| UT | each bill's `agendaList` in the glen.le.utah.gov API record (already downloaded) + `agencal/<mtgID>` for meetings in `legcal` | JSON | yes | ~1 week | API with key; le.utah.gov Crawl-delay 10 | done (date set to 2026-01-26: 820 bills; the agencal half is untested because the local token answered "Invalid request") |
| VT | each bill's LegiScan `calendar` (already downloaded) | JSON | per bill | as LegiScan has them | (LegiScan; legislature.vermont.gov Crawl-delay 30) | done (2026's saved calendars: 203 bills, all matched) |
| WI | committeeschedule.legis.wisconsin.gov/?StartDate=<today>&... | events in the page's script (~2 MB, the whole session) | yes | the whole session's posted meetings | no robots.txt on that host | done (Feb 2026: 283 bills, all matched) |
| WV | www.wvlegislature.gov/committees/House/house_com_agendas.cfm?Chart=<code>&input=<day>, Senate the same | HTML | yes | days | /committees/ allowed (fetch.py's robots check of 2026-11-09) | written, **not run live**: the site timed out from this computer all day on 2026-11-22; tested only on archived pages (runs January-April) |
| WY | api.wyoleg.gov/v2/Calendar/Events/<YYYYMMDD> | JSON (`sessionMeetingBills`) | yes | ~5 weeks around the day | no robots.txt | done (saved 2026-02-12 calendar: 184 of 190 matched; the rest are joint resolutions the converter doesn't keep) |

## Download changes

- pdftotext is now installed in the download jobs for AZ, CT, KY, MS and SC; the others that read PDFs already had it.
  The install comes before the fetch with `;`, so a failed install doesn't stop the download.
- Arizona's time limit went from 100 to 110 minutes, for up to 14 minutes of agenda PDFs at its 120-second crawl delay.
- No new cache paths: every file sits in the state's existing data folder.

## January test plan

For every state, after the first in-session runs:
- Check the fetch log's "agendas: N bills on M meetings" line.
- Open data/<st>/<session>/agendas.json (MD: data/md/agendas_<year>.json). It should be non-empty once committees meet, with keys like "HB12" (not "HB0012") and names starting House/Senate/Joint.
- Run `python3 test/data_check.py <st>`. Its agendas line should show a count, and no FAIL for stray numbers.
- Compare two or three bills with the committee's own page, and check that the "On an upcoming committee agenda" filter shows them.
- Check that times aren't all T00:00:00, except RI's and Maine's "after session" meetings.

By state:
- **AL**: compare with alison.legislature.state.al.us/todays-schedule. Watch for new wording of cancellations.
- **AZ**: www.azleg.gov/standing-committee should list 2027 meetings by default. The log's "R PDFs read now, L left" count: if L keeps growing, raise `AGENDA_LIMIT` or the job's minutes. Check the Senate's agenda layout.
- **CO**: from about January 14, compare leg.colorado.gov/committees/2027A/house/Judiciary's "Upcoming Schedule" with the file. Watch for "no committee list" (2027A not set up yet) and for 429s. Check how a canceled agenda is worded.
- **CT**: check pdftotext ran ("0 agendas unreadable"), and compare one committee's agenda PDF. Watch for revised PDFs.
- **DE**: compare with legis.delaware.gov/CommitteeMeetings. A "meeting times not understood" warning means the upcoming grid writes dates differently from the past grid.
- **GA**: nothing to test. Getting agendas needs the General Assembly's web staff to grant API access or offer a feed: the owner's decision.
- **ID**: check whether /sessioninfo/agenda/hagenda/ links "...-Agenda.pdf" files. If it doesn't, the log shows about 25 committee-page requests (the fallback).
- **IL**: once a Senate committee posts hearings, check for "Senate ..." entries with the right times.
- **IN**: data/in/2027/agendas.json should appear in December, and shows on the site from January. Check a canceled meeting in the window.
- **KS**: kslegislature.gov/api/v1/hearings/?biennium=b2027_28&upcoming=true. Check that /api/v1/biennia/ names b2027_28 active.
- **KY**: apps.legislature.ky.gov/LegislativeCalendar/. Bills should be "27RS". During session the calendar may show only today, so later days depend on materials PDFs.
- **LA** (session opens April 2027): legis.la.gov/legis/ByCmte.aspx. Check that Senate Agenda.aspx pages are laid out like the House's. "bills of another session left out" should be about 0.
- **LegiScan states (ME OK RI TN VT)**: check that hearings appear in data/<st>/legiscan/<id>/bill/*.json `calendar` before their day: freshness depends on the getBill allowance, and on whether a new hearing changes the bill's change_hash (not yet seen). **TN**: are there any House entries? **OK**: are House and Senate both there? **ME**: work sessions as well as public hearings?
- **MA** (195th General Court): data/ma/hearings.json fills with GeneralCourtNumber 195; data/ma/2027/agendas.json appears once the 2027 folder exists.
- **MD**: compare mgaleg.maryland.gov/mgawebsite/Meetings/Week. Check that ys=2027rs works.
- **MI**: compare www.legislature.mi.gov/Committees/Meetings and a few meeting pages. Bill ranges ("HBs 4001-4003") read only the first number.
- **MN**: compare www.house.mn.gov/Schedules/All and www.mnsenate.gov/schedule/senate/upcoming-all. Check the House page's size in session, and that canceled meetings drop out.
- **MS**: the riskiest reader. The Archive's 2026 copies of the Senate PDF held only a heading. Check that the PDF lists "S. B. No." bills under committee headings, and that the file isn't always empty while meetings are posted. House: the log's "house schedule: N House committee meetings" should be over 0 once committees meet; open a House bill in committee and check it says "The House ... Committee meets ...; this bill could come up" and is under "Committee meets soon", not "On an upcoming committee agenda".
- **NC**: compare www.ncleg.gov/LegislativeCalendar/1/2027 with the file. Check how the "UPDATED" and "Joint ..." names read.
- **NM**: check whether /Calendar/Session links /Agendas/Standing/*.pdf during session. The tested path is the archive fallback.
- **PA**: check that `<parss:Bills>` is filled on both feeds, and how a canceled meeting appears.
- **SC**: compare /meetings?chamber=S, and check for "House House ..." names and the number of PDFs the first run reads.
- **SD**: compare a committee's Agendas tab on sdlegislature.gov.
- **UT**: check that the GitHub secret token answers `agencal` (the local token got "Invalid request" for every route on 2026-11-22, billlist included: check Utah's normal download too).
- **WI**: the log's "(N meetings listed)" count should be over 0, with 2027 meetings.
- **WV** (most important): confirm the site answers from GitHub's runners. Open house_com_agendas.cfm?Chart=jud&input=<today> and check that bills come through. If 0 bills come back while meetings exist, look at the `AGENDA_*` regexes.
- **WY**: compare with wyoleg.gov/Calendar. Watch how canceled meetings appear.

## Known gaps

- Georgia: blocked (above). Rechecked 2026-11-22 from a GitHub runner: house.ga.gov, senate.ga.gov and www.legis.ga.gov all time out there; the chamber sites have been retired since 2025 (states/ga/NOTES.md).
- Mississippi House: it publishes no bills with its meeting times; the page says only that a bill's committee meets (kind "meets", states/ms/NOTES.md).
- Tennessee House: missing from LegiScan since February 2026, and the official site bars robots.
- Open States (2026-11-22, research only, the owner's decision): its /events had 6 Georgia and 11 Tennessee meetings, all November-December 2026 interim ones with no bills, read from the same gated (GA) or robots-barred (TN, wapp.capitol.tn.gov) pages. The API returns only recent and upcoming events and no creation time, so lead time and bill match rates can only be measured by polling it during the 2027 sessions.
- Kansas: hearings only.
- Michigan and Kentucky: joint resolutions are left out. Michigan's are lettered ("HJRA"), and build_data.py drops a final capital when looking up agendas, so all of them would hit the same key; that needs a build_data.py change.
- Massachusetts: a past hearing later moved to a future date would be missed.
- Missouri: the Senate page gives dates with no year, and the reader takes the year nearest today.
