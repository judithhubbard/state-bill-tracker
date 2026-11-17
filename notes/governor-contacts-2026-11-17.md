# Governors' contact information, checked 2026-11-17

What was checked, for the 50 states and Congress (the White House):
- the governor named in `GOVERNORS` (states/<st>/profile.py);
- the phone numbers and contact link in `govReach` (states/<st>/profile.js), which states/<st>/weighin.html repeats under
  "Governor's office" (the two agree in every state; weighin.html sometimes lists extra numbers);
- the mailing address in weighin.html ("Mail: ...").

How: one request for each site's robots.txt and one for the contact page (curl, user agent
"StateBillTracker-linkcheck/1.0"; no path checked was disallowed), plus the governor's own home or contact page where the
first page didn't show the phone. Where a site answered automated requests with 403 or not at all, it wasn't retried
another way: web search results were used instead, and the table says so. "Page" means the governor's official page
as fetched today; "search" means web search results quoting official pages (state, county or Blue Book directories).

Summary: 51 checked. 5 contact links fixed (below). Every governor's name is right for today. Every phone number is the
office's published main or constituent line (none changed). 6 flagged as uncertain (no change made): the White House
comments line, and the contact links of Colorado, Kansas, Massachusetts, Michigan and New Hampshire, which can't be
loaded by a program (403 or no answer) but which search results show are still the official pages.

## Fixes made (profile.js and weighin.html, the same change in both)

| State | Before | After | Why |
|---|---|---|---|
| FL | https://www.flgov.com/eog/contact | https://www.flgov.com/eog/leadership/people/ron-desantis/contact | The old page is the site's "Website feedback" form; the new one is "Contact Governor Ron DeSantis" (name, email, phone, subject, message). The address has the governor's name in it: change it when the new governor takes office (January 5, 2027). |
| MD | https://md.accessgov.com/governor/Forms/Page/cs/contact-the-governor | https://govassist.maryland.gov/gov-assist/constituent-management/p/intake/dept-the-office-of-the-governor-987ee424 | The old address now redirects there (and answers 404 to a HEAD request); governor.maryland.gov links the new one. |
| MS | https://governorreeves.ms.gov/contact/ ("Contact the governor") | profile.js: mailto:governor@govreeves.ms.gov ("Email the governor"); weighin.html: https://governorreeves.ms.gov/ ("governorreeves.ms.gov"), the email line below it unchanged | The contact page is gone (404); the site no longer has a contact form. Its footer gives governor@govreeves.ms.gov and (601) 359-3150, as does the Secretary of State's 2025 directory. CLAUDE.md still names governorreeves.ms.gov/contact/ as the source (not edited here). |
| RI | https://governor.ri.gov/contact-us | https://governor.ri.gov/contact | The old page is 404; the home page links /contact ("Contact the Governor", with (401) 222-2080). |
| VT | https://governor.vermont.gov/contact-us | https://governor.vermont.gov/contact-us-requests | The old page is 404; the home page links "Contact Us & Requests" (with 802-828-3333). |

## Every state

Phone: "page" = the number is on the governor's page fetched today; "search" = confirmed by search results.

| State | Governor in GOVERNORS | Name OK? | Phone (site has) | Phone confirmed | Contact link | Mailing address (weighin.html) | Source | Fix |
|---|---|---|---|---|---|---|---|---|
| AK | Dunleavy | Yes (until Dec 7, 2026) | (907) 465-3500 | page (gov.alaska.gov/contact/) | 200, "Email the Dunleavy Administration" | P.O. Box 110001, Juneau 99811: on page | page | none |
| AL | Ivey | Yes | (334) 242-7100 | page | 200 | 600 Dexter Ave., 36130: on page | page | none |
| AR | Sanders | Yes | (501) 682-2345 | page | 200 (redirects to /interact/contact-the-governor/, the same form) | 500 Woodlane St., 72201: on page | page | none (could use the new address) |
| AZ | Hobbs | Yes | (602) 542-4331 | page | 200, "Voice an Opinion" | 1700 W. Washington St., 85007: on page | page | none |
| CA | Newsom | Yes | (916) 445-2841 | page | 200 | 1021 O St., Suite 9000, 95814: on page | page | none |
| CO | Polis | Yes | (303) 866-2885 | search: colorado.gov/governor/contact-us lists it as the Constituent Services Help Line (front desk (303) 866-2471, which weighin.html also lists) | **No answer** (governor.colorado.gov timed out twice, robots.txt too); not checked | Room 136, 200 E. Colfax: search agrees | search | **flag**: owner to open the link once |
| CT | Lamont | Yes | (860) 566-4840 | search: portal.ct.gov "Mailing Address and Phone Numbers" (toll-free 800-406-1527, in weighin.html) | 200, "Email Governor Lamont" | 210 Capitol Ave., 06106: on page | page + search | none |
| DE | Meyer | Yes | (302) 744-4101, (302) 577-3210 | page | 200 | Tatnall Building, Dover 19901: on page | page | none |
| FL | DeSantis | Yes | (850) 717-9337 | search: flgov.com lists it for the Office of Citizen Services | was the website feedback form | 400 S. Monroe St., 32399: on page | page + search | **fixed** (above) |
| GA | Kemp | Yes | (404) 656-1776 | page | 200 | 206 Washington St., Suite 203, 30334: on page | page | none |
| HI | Green | Yes | (808) 586-0034 | search: governor.hawaii.gov "General Contact Information" | 200 | 415 S. Beretania St., 96813: search agrees | search | none |
| IA | Reynolds | Yes | (515) 281-5211 | page (governor.iowa.gov, which answered 200 today) | 200 | 1007 E. Grand Ave., 50319: on page | page | none. CLAUDE.md says governor.iowa.gov answers 403; it didn't today. |
| ID | Little | Yes | (208) 334-2100 | page | 200 | PO Box 83720, 83720: on page | page | none |
| IL | Pritzker | Yes | (217) 782-0244, (312) 814-2121 | search: gov.illinois.gov lists 782-0244 as the Constituent Affairs Help Line and 814-2121 as the Chicago office (Springfield office 782-6830) | 200 (contact-us.html; the form itself is contact-us/contact-the-governor.html) | 207 State House, 62706: not on the fetched page (built by script) | search | none |
| IN | Braun | Yes | (317) 232-4567 | page | 200 | Statehouse, 46204-2797: on page | page | none |
| KS | Kelly | Yes | (785) 296-3232 | search: governor.ks.gov lists it as "Local" (toll-free 877-579-6757; constituent services 785-368-8500) | **403** to automated requests; link is the home page | 300 SW 10th Ave., Suite 241S, 66612: search agrees | search | **flag**: link not checkable by program; search shows www.governor.ks.gov/contact/contact as the contact page |
| KY | Beshear | Yes | (502) 564-2611 | search: governor.ky.gov "Constituent Services" | 200 (ppc.ky.gov constituent services form) | 501 High St., 2nd Floor, 40602: search agrees (temporary while the Capitol is renovated) | search | none |
| LA | Landry | Yes | (225) 342-0991 | page | 200 | P.O. Box 94004, 70804: zip on page | page | none |
| MA | Healey | Yes | (617) 725-4005, (888) 870-7770 | search: mass.gov Constituent Services, both numbers | **403** to automated requests | Room 280, 24 Beacon St., 02133: search agrees | search | **flag**: link not checkable by program (search shows the page exists) |
| MD | Moore | Yes | (410) 974-3901, (800) 811-8336 | page (governor.maryland.gov/contact-us) | redirected to a new address | 100 State Circle, 21401: on page | page | **fixed** (above) |
| ME | Mills | Yes | (207) 287-3531 | page | 200 | 1 State House Station, 04333: on page | page | none; the link has "mills" in it (changes January 6, 2027) |
| MI | Whitmer | Yes | (517) 335-7858 | search: the governor's constituent services line (general office 517-373-3400) | **403** to automated requests | P.O. Box 30013, 48909: search agrees; the line names "Governor Gretchen Whitmer" | search | **flag**: link not checkable by program (search shows it's the governor's form) |
| MN | Walz | Yes | (651) 201-3400 | search (several directories; toll-free 800-657-3717) | 200 | 130 State Capitol, 55155: on page | page + search | none |
| MO | Kehoe | Yes | (573) 751-3222 | page | 200 | P.O. Box 720, 65102: on page | page | none |
| MS | Reeves | Yes | (601) 359-3150 | page (site footer) | **404** | none in weighin.html; P.O. Box 139, Jackson 39205 per the 2025 directory | page + search | **fixed** (above) |
| MT | Gianforte | Yes | (406) 444-3111 | page | 200 | PO Box 200801, 59620: on page | page | none |
| NC | Stein | Yes | (919) 814-2000 | page | 200 | 20301 Mail Service Center, 27699: on page | page | none |
| ND | Armstrong | Yes | (701) 328-2200 | page | 200 | 600 E. Boulevard Ave., 58505: on page | page | none |
| NE | Pillen | Yes | (402) 471-2244 | page | 200 | P.O. Box 94848, 68509: zip on page | page | none |
| NH | Ayotte | Yes | (603) 271-2121 | search (several directories; the Census partner page says 271-8637, likely old) | **403** to automated requests | 107 N. Main St., 03301: search agrees | search | **flag**: link not checkable by program |
| NJ | Sherrill | Yes | (609) 292-6000 | search (county and state directories) | 200 (home page; no contact form found) | P.O. Box 001, 08625: on page | search | none |
| NM | Lujan Grisham | Yes | (505) 476-2200 | page | 200 | 490 Old Santa Fe Trail, Room 400: on page | page | none |
| NV | Lombardo | Yes | (775) 684-5670, (702) 486-2500 | page | 200 (redirects to www.gov.nv.gov, the same page) | 101 N. Carson St., 89701: on page | page | none |
| NY | Hochul | Yes | (518) 474-8390 | page | 200 | (no weighin.html) | page | none |
| OH | DeWine | Yes | (614) 644-4357 | page (governor.ohio.gov/contact) | 200 (home page) | 77 S. High St., 30th Floor, 43215: on page | page | none (could link governor.ohio.gov/contact) |
| OK | Stitt | Yes | (405) 521-2342 | page | 200 | 2300 N. Lincoln Blvd., Suite 212: on page | page | none |
| OR | Kotek | Yes | (503) 378-4582 | page | 200 | 900 Court St., Suite 254: on page | page | none |
| PA | Shapiro | Yes | (717) 787-2500 | page | 200 | 508 Main Capitol, 17120: on page | page | none |
| RI | McKee | Yes | (401) 222-2080 | page | **404** | 82 Smith St., 02903: on page | page | **fixed** (above) |
| SC | McMaster | Yes | (803) 734-2100 | search: the governor's contact page, the SC FAQ and the 2025/2026 Legislative Manual | 200 (Salesforce contact form) | 1100 Gervais St., 29201: search agrees; the line names "The Honorable Henry McMaster" | search | none (the phone, unchecked before, is right) |
| SD | Rhoden | Yes | (605) 773-3212 | page | 200 | 500 E. Capitol Ave., 57501: on page | page | none |
| TN | Lee | Yes | (615) 741-2001 | page | 200 | State Capitol, 37243: on page | page | none |
| TX | Abbott | Yes | (800) 843-5789 | page (the Citizen's Opinion Hotline; main 512-463-2000) | 200 | P.O. Box 12428, 78711: on page | page | none |
| UT | Cox | Yes | (801) 538-1000 | page | 200 | 350 N. State St., Suite 200: on page | page | none |
| VA | Spanberger | Yes | (804) 786-2211 | page | 200 (governor.virginia.gov answered today) | P.O. Box 1475, 23218: on page | page | none |
| VT | Scott | Yes | (802) 828-3333 | page | **404** | 109 State St., 05609: on page | page | **fixed** (above) |
| WA | Ferguson | Yes | (360) 902-4111 | search: governor.wa.gov | 200 | PO Box 40002, 98504: search agrees | search | none |
| WI | Evers | Yes | (608) 266-1212 | search: 2025-26 Blue Book | 200 (wi.accessgov.com "Voice an opinion") | P.O. Box 7863, 53707: search agrees (Blue Book) | search | none |
| WV | Morrisey | Yes | (304) 558-2000 | page (governor.wv.gov, with 888-438-2731) | 200 (wv.accessgov.com) | 1900 Kanawha Blvd. E, 25305: on page | page | none |
| WY | Gordon | Yes | (307) 777-7434 | search (a radio station's guide, the Oil and Gas Commission's page; the Census partner page says 777-2463) | 200 (page is a script app; content not readable) | 200 W. 24th St., 82002: search agrees | search | none |
| US | Trump | Yes | (202) 456-1111 (comments line) | **uncertain**: the current whitehouse.gov/contact page shows only a web form, no phone numbers; 211 Arizona listed the comments line in October 2025 | 200 (whitehouse.gov/contact, the contact form) | 1600 Pennsylvania Ave. NW, 20500: zip on page | page + search | **flag**: owner could call once, or drop the number |

## Governors changing (data fine until then)

From states/elected_2026.json (unofficial results gathered 2026-11-14; Alaska and Maine marked "close"). Dates are the
day the state's law sets for the new term; confirm each. When each takes office: add them to `GOVERNORS` in
profile.py and to states/legislatures.json, and check the contact link, phone and mail line, especially those with the
old governor's name in them.

| State | Leaving | Taking over | Takes office | Contact details with the old name in them |
|---|---|---|---|---|
| AK | Mike Dunleavy | Jonathan Kreiss-Tomkins (D; ranked-choice count still close) | December 7, 2026 | link "email-the-governor" is generic, but its page is titled "Email the Dunleavy Administration" |
| AL | Kay Ivey | Tommy Tuberville (R) | January 18, 2027 | |
| CA | Gavin Newsom | Xavier Becerra (D) | January 4, 2027 | |
| CO | Jared Polis | Phil Weiser (D) | January 12, 2027 | |
| FL | Ron DeSantis | Byron Donalds (R) | January 5, 2027 | the new link (…/people/ron-desantis/contact) |
| GA | Brian Kemp | Keisha Lance Bottoms (D) | January 11, 2027 | |
| IA | Kim Reynolds | Rob Sand (D) | January 2027 (date not announced) | |
| KS | Laura Kelly | Cindy Holscher (D) | January 11, 2027 | |
| ME | Janet Mills | Hannah Pingree (D; close) | January 6, 2027 | link …/governor/mills/contact |
| MI | Gretchen Whitmer | Jocelyn Benson (D) | January 1, 2027 | weighin.html mail line "Governor Gretchen Whitmer" |
| MN | Tim Walz | Amy Klobuchar (D) | January 4, 2027 | |
| NM | Michelle Lujan Grisham | Deb Haaland (D) | January 1, 2027 | |
| NV | Joe Lombardo | Aaron Ford (D) | January 4, 2027 | |
| OH | Mike DeWine | Amy Acton (D) | January 11, 2027 | |
| OK | Kevin Stitt | Mike Mazzei (R) | January 11, 2027 | |
| RI | Dan McKee | Helena Foulkes (D) | January 5, 2027 | |
| SC | Henry McMaster | Alan Wilson (R) | January 13, 2027 | weighin.html mail line "The Honorable Henry McMaster" |
| TN | Bill Lee | Marsha Blackburn (R) | January 16, 2027 | |
| TX | Greg Abbott | Gina Hinojosa (D) | January 19, 2027 | |
| WI | Tony Evers | David Crowley (D) | January 4, 2027 | |
| WY | Mark Gordon | Eric Barlow (R) | January 4, 2027 | |

Re-elected or not up, with the name in a link or mail line that can stay: CT (email-governor-lamont), IN
(contact-gov-braun), MS (governorreeves.ms.gov), NC (contact-governor-stein), WA (send-gov-ferguson-e-message), PA (mail
line "Governor Josh Shapiro"). Hawaii's new term also starts December 7, 2026 (Green re-elected). Governors' websites
often move to new addresses with a new governor, so every changing state's link is worth a check in its first week.
