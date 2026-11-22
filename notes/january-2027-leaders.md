# Leaders and governors changing, December 2026 to February 2027

Checked 2026-11-22. Where the site stands: each state's leaders are `LEADERS` in states/<st>/profile.py; the next ones
are `LEADERS_NEXT` (`{house: (name, title, pronoun, "YYYY-MM-DD")}`), which `governors.apply_leaders()` puts in place
from their day at build time. Governors are `GOVERNORS` in profile.py (the governor-elect listed with the day they take
office) and `governor` / `governorNext` in states/legislatures.json (the page's governor-elect line reads
`governorNext` until that day). New on 2026-11-22: a legislatures.json entry's `next`, `[{"from": day, field: value}]`,
swaps a note or coalition on its day (`governors.facts_on()`, read by `balance.table()`). The date is part of each
state's build hash, so every change below shows up in the first build on or after its day; nobody needs to deploy.

Pronouns: from an official biography where it gives them; otherwise "them".

Status:
- **confirmed**: the vote has happened, or the person was elected in November (governors; certification may still be due).
- **nominee**: picked by the majority caucus; the chamber's vote is still to come on the date shown. The site switches
  on that date.
- **pending**: nobody chosen yet. The site keeps the current leader. Add a `LEADERS_NEXT` entry once someone is chosen.

Main sources: NCSL, "Who Leads? State Legislative Leadership Changes in 2027"
(https://www.ncsl.org/elections-and-campaigns/who-leads-state-legislative-leadership-changes-in-2027, updated
2026-11-19); State Capital Lobbyist, "State Legislative Leadership 2027"
(https://statecapitallobbyist.com/elections/state-legislative-leaders-2027/, as of 2026-11-18). Both are secondary
sources; the news items below confirm the newer entries. Most governors' start dates come from each state's
constitution (commit 1e2c3c9; notes/governor-contacts-2026-11-17.md).

## By date

| Date | Change |
|---|---|
| 2026-11-17 | IN: Garten (Senate), Smaltz (House); already showing |
| 2026-12-01 | ND House: Pyle (added 2026-11-22) |
| 2026-12-01 | US Senate Democrats vote on their leader (Schumer or Van Hollen): add the winner by hand, from 2027-01-03 |
| 2026-12-02 | NH: Perkins Kwoka (Senate), Simpson (House) |
| 2026-12-07 | AK governor: Kreiss-Tomkins; HI: Green's second term (no change) |
| 2027-01-01 | MI governor: Benson; NM governor: Haaland (NM's note drops Lujan Grisham) |
| 2027-01-03 | US House: Jeffries; legislatures.json "us" note becomes "Democrats hold both houses" |
| 2027-01-04 | Governors: CA Becerra, MN Klobuchar, NV Ford, WI Crowley, WY Barlow. OH Senate: Reineke. WI: Hesselbein, Neubauer. MT House: Zolnikov |
| 2027-01-05 | Governors: FL Donalds, RI Foulkes. PA Senate: Costa |
| 2027-01-06 | ME governor: Pingree. CT Senate: Duff. MO: Bean, Riley. VT Senate: Perchlik |
| 2027-01-11 | Governors: GA Bottoms, KS Holscher, OH Acton, OK Mazzei. AZ: Sundareshan, De Los Santos. AR Senate: Bryant. GA: McLaurin, Hugley. CO House: Bacon. OR House: Bowman (added 2026-11-22) |
| 2027-01-12 | CO governor: Weiser; IA governor: Sand (as reported). DE Senate: Townsend. MN House: Stephenson (MN's coalition ends). SD: Reed, Stevens. TN Senate: Johnson. WY: Nethercott, Larsen |
| 2027-01-13 | SC governor: Wilson. MI: Camilleri, Puri. NC House: Reives |
| 2027-01-16 | TN governor: Blackburn |
| 2027-01-18 | AL governor: Tuberville |
| 2027-01-19 | TX governor: Hinojosa; TX Lt. Governor: Goodwin. AK: Giessel, Schrage (AK note names them). UT Senate: Vickers |
| 2027-02-01 | NV: Flores (Senate), Marzola (Assembly) |

## Still to enter: decided later

| Where | Role | Now on the site | What's known | Check on |
|---|---|---|---|---|
| US | Senate Majority Leader | John Thune | Democrats hold 55 seats in the 120th. The caucus votes Dec 1, Schumer against Van Hollen ([Wikipedia](https://en.wikipedia.org/wiki/2026_Senate_Democratic_Caucus_leadership_election); [CNN](https://www.cnn.com/2026/11/12/politics/chris-van-hollen-chuck-schumer-senate-democratic-leader)) | Dec 1: add `"S": (winner, "Senate Majority Leader", ..., "2027-01-03")` |
| NC | Senate President Pro Tempore | Phil Berger | Berger lost his March primary, so he leaves the Senate when the new terms begin on January 1. Republicans haven't picked a successor (Hise, Johnson, Lee, Jackson, Burgin running). The Senate elects one on Jan 13 ([Carolina Journal](https://www.carolinajournal.com/burgin-enters-race-for-nc-senate-leader/)). Reported results show the Senate at 25 R, 24 D, 1 uncalled | When the caucus votes. From Jan 1 to Jan 13 the site still names Berger |
| IL | Speaker | Emanuel "Chris" Welch | Welch isn't seeking another term (Nov 5). No successor chosen; the vote is Jan 13 ([WTTW](https://news.wttw.com/2026/11/05/welch-step-aside-illinois-house-speaker-after-26-illinois-democrats-called-new-top)) | Before Jan 13 |
| TX | Speaker | Dustin Burrows | Democrats won the House. Senfronia Thompson is the only declared candidate ([Texas Scorecard](https://texasscorecard.com/state/senfronia-thompson-launches-speaker-bid-as-democrats-seize-texas-house/)). The House votes on Jan 12 | Before Jan 12 |
| KS | Speaker | Daniel Hawkins | Hawkins was elected insurance commissioner. House Republicans elect leaders Dec 7 ([Lawrence Times](https://lawrencekstimes.com/2026/11/17/kns-gop-majority-less-power/)). The session opens Jan 11 | Dec 7 |
| VT | Speaker | Jill Krowinski | Krowinski didn't run again. Lori Houghton has the votes lined up ([Vermont Public](https://www.vermontpublic.org/local-news/2026-08-24/votes-lined-up-next-house-speaker)). The caucus votes Dec 5 ([VTDigger](https://vtdigger.org/2026/11/16/vermont-senate-democrats-nominate-andrew-perchlik-to-be-chambers-next-leader/)) | Dec 5: add Houghton from 2027-01-06 |
| NE | Speaker | John Arch | Arch is term-limited. The senators elect a new Speaker on Jan 6 | Jan 6 |
| ID | Speaker, President Pro Tem | Moyle, Anthon | Caucuses meet in December; no change expected | December |
| AL | President Pro Tem | Garlan Gudger | House Republicans renominated Ledbetter (Nov 5, [Alabama Reflector](https://www.alreporter.com/2026/11/05/alabama-house-gop-reelects-legislative-leadership)). No Senate caucus vote reported. The organizational session is Jan 12 | Jan 12 |

## By state

Roles are the ones the site tracks (`LEADERS`). "Same" means the same person continues, per the sources above.

| State | Role | Outgoing | Incoming | Effective | Source | Status |
|---|---|---|---|---|---|---|
| AK | Governor | Mike Dunleavy | Jonathan Kreiss-Tomkins (D) | 2026-12-07 | [FairVote](https://fairvote.org/results-in-alaskas-2026-ranked-choice-voting-elections/): 51% of first choices, no RCV round | confirmed |
| AK | President of the Senate | Gary Stevens | Cathy Giessel (coalition) | 2027-01-19 | NCSL; [Alaska Beacon via Yahoo](https://www.yahoo.com/news/politics/articles/bipartisan-coalitions-alaska-senate-house-230200622.html) | nominee (three Republicans said they'd leave the coalition) |
| AK | Speaker | Bryce Edgmon | Calvin Schrage (coalition) | 2027-01-19 | NCSL; [ADN](https://www.adn.com/politics/2026/11/18/coalition-aligned-candidates-flip-4-alaska-house-seats-shrinking-gop-minority/) | nominee |
| AL | Governor | Kay Ivey | Tommy Tuberville (R) | 2027-01-18 | election results | confirmed |
| AL | Pro Tem / Speaker | Gudger / Ledbetter | same | 2027-01-12 | Alabama Reflector | nominee (Ledbetter) / pending (Gudger) |
| AR | President Pro Tem | Bart Hester | Joshua Bryant | 2027-01-11 | NCSL; State Capital Lobbyist (elected Nov 5) | confirmed by caucus |
| AR | Speaker | Brian S. Evans | same | | State Capital Lobbyist | confirmed |
| AZ | President of the Senate | Warren Petersen | Priya Sundareshan (D) | 2027-01-11 | NCSL | nominee |
| AZ | Speaker | Steve Montenegro | Oscar De Los Santos (D) | 2027-01-11 | NCSL | nominee |
| CA | Governor | Gavin Newsom | Xavier Becerra (D) | 2027-01-04 | election results | confirmed |
| CA | Pro Tem / Speaker | Limón / Rivas | same | | State Capital Lobbyist | expected |
| CO | Governor | Jared Polis | Phil Weiser (D) | 2027-01-12 | election results | confirmed |
| CO | Speaker | Julie McCluskie | Jennifer Bacon | 2027-01-11 (the session opens Jan 11: [Colorado Politics](https://www.coloradopolitics.com/2026/04/21/colorado-lawmakers-set-jan-11-start-date-for-2027-general-assembly/)) | NCSL | nominee |
| CO | President of the Senate | James Coleman | same | | State Capital Lobbyist | confirmed by caucus |
| CT | President Pro Tem | Martin Looney | Bob Duff | 2027-01-06 | NCSL | nominee |
| CT | Speaker | Matthew Ritter | same | | State Capital Lobbyist | expected |
| DE | President Pro Tem | David P. Sokola | Bryan Townsend | 2027-01-12 | [Newark Post](http://www.newarkpostonline.com/spotlight_delaware/newarks-bryan-townsend-selected-as-leader-of-delaware-senate/article_58d60228-1cab-4850-a3d1-56e52ddd86bf.html); [Delaware Public](https://www.delawarepublic.org/politics-government/2026-11-15/delaware-senate-majority-caucus-election-promotes-two-legislators-to-leadership) | nominee |
| DE | Speaker | Melissa Minor-Brown | same | | State Capital Lobbyist | nominee |
| FL | Governor | Ron DeSantis | Byron Donalds (R) | 2027-01-05 | election results | confirmed |
| FL | President / Speaker | Boyd / Garrison | already in office (organization session Nov 17) | | NCSL | confirmed |
| GA | Governor | Brian Kemp | Keisha Lance Bottoms (D) | 2027-01-11 | election results | confirmed |
| GA | Lt. Governor (presides) | Burt Jones | Josh McLaurin (D) | 2027-01-11 | NCSL | confirmed (elected) |
| GA | Speaker | Jon Burns | Carolyn Hugley (D) | 2027-01-11 | NCSL | nominee |
| HI | Governor | Josh Green | same (re-elected; second term from 2026-12-07) | | election results | confirmed |
| HI | President / Speaker | Kouchi / Nakamura | same | | State Capital Lobbyist | current |
| IA | Governor | Kim Reynolds | Rob Sand (D) | 2027-01-12 | [WGEM](https://www.wgem.com/2026/11/04/democrat-rob-sand-wins-iowa-governor/); one outlet says Jan 19 | confirmed; check the date |
| IA | Majority Leader / Speaker | Klimesh / Grassley | same | | [Bleeding Heartland](https://www.bleedingheartland.com/2026/11/07/iowa-house-senate-republicans-stick-with-current-leaders/) | confirmed by caucus |
| ID | Pro Tem / Speaker | Anthon / Moyle | same expected | | State Capital Lobbyist | pending (December caucus) |
| IL | Senate President | Don Harmon | same | 2027-01-13 | State Capital Lobbyist | expected |
| IL | Speaker | Emanuel "Chris" Welch | ? | 2027-01-13 | WTTW | pending |
| IN | President Pro Tem / Speaker | Bray / Huston | Chris Garten / Ben Smaltz | 2026-11-17 | NCSL | confirmed (showing now) |
| KS | Governor | Laura Kelly | Cindy Holscher (D) | 2027-01-11 | election results | confirmed |
| KS | President of the Senate | Ty Masterson | same (Senate not up in 2026; he lost the governor's race) | | Lawrence Times | current |
| KS | Speaker | Daniel Hawkins | ? | 2027-01-11 | Lawrence Times | pending (caucus Dec 7) |
| KY | President / Speaker | Stivers / Osborne | same | | State Capital Lobbyist | expected |
| LA | President / Speaker | Henry / DeVillier | same (no 2026 election) | | | current |
| MA | President / Speaker | Spilka / Mariano | same | | State Capital Lobbyist | expected |
| MD | President / Speaker | Ferguson / Peña-Melnyk | same | | State Capital Lobbyist | expected |
| ME | Governor | Janet Mills | Hannah Pingree (D) | 2027-01-06 | [MultiState](https://www.multistate.us/elections/governor-race/maine-2026) | confirmed (not yet certified) |
| ME | President / Speaker | Daughtry / Fecteau | same (vote Dec 2) | | State Capital Lobbyist | nominee |
| MI | Governor | Gretchen Whitmer | Jocelyn Benson (D) | 2027-01-01 | election results | confirmed |
| MI | Majority Leader | Winnie Brinks | Darrin Camilleri (D) | 2027-01-13 | NCSL | confirmed by caucus |
| MI | Speaker | Matt Hall | Ranjeev Puri (D) | 2027-01-13 | NCSL | nominee |
| MN | Governor | Tim Walz | Amy Klobuchar (D) | 2027-01-04 | election results | confirmed |
| MN | Majority Leader | Erin Murphy | same | | [MN Medical Association](https://www.mnmed.org/news-and-publications/news/minnesota-legislature-elects-caucus-leaders-2027-2028-session) | confirmed by caucus |
| MN | Speaker | Lisa Demuth | Zack Stephenson (DFL) | 2027-01-12 | NCSL | nominee; the House's coalition flag ends that day (legislatures.json `next`) |
| MO | President Pro Tem | Cindy O'Laughlin | Jason Bean | 2027-01-06 | NCSL | nominee |
| MO | Speaker | Jonathan Patterson | Alex Riley | 2027-01-06 | NCSL | nominee |
| MS | Lt. Gov. / Speaker | Hosemann / White | same (no 2026 election) | | | current |
| MT | President of the Senate | Matt Regier | same | | State Capital Lobbyist | confirmed by caucus |
| MT | Speaker | Brandon Ler | Katie Zolnikov | 2027-01-04 | NCSL | nominee |
| NC | President Pro Tem | Phil Berger | ? | 2027-01-13 | Carolina Journal | pending (Berger leaves office Jan 1) |
| NC | Speaker | Destin Hall | Robert Reives (D) | 2027-01-13 | [NC Newsline](https://ncnewsline.com/2026/11/17/nc-house-dems-elect-reives-butler-to-2027-leadership-roles/) | nominee |
| ND | Majority Leader | David Hogue | same | | [ND Monitor via KFYR](https://www.kfyrtv.com/2026/11/12/state-rep-30-years-will-lead-north-dakota-house-republicans/) | confirmed by caucus |
| ND | Speaker | Robin Weisz | Brandy Pyle | 2026-12-01 (organizational session Dec 1-3) | [Prairie Public](https://news.prairiepublic.org/local-news/2026-11-13/casselton-republican-in-line-to-become-the-fourth-woman-to-be-speaker-of-the-north-dakota-house); dates: [Legislative Council deadlines](https://ndlegis.gov/sites/default/files/resource/70-2027/legislative-deadlines/2027-legislative-deadlines.pdf) | nominee (added 2026-11-22) |
| NE | Speaker | John Arch | ? | 2027-01-06 | State Capital Lobbyist | pending |
| NH | President of the Senate | Sharon Carson | Rebecca Perkins Kwoka (D) | 2026-12-02 | NCSL | nominee |
| NH | Speaker | Sherman Packard | Alexis Simpson (D) | 2026-12-02 | [NH Bulletin via Monadnock Ledger-Transcript](https://ledgertranscript.com/2026/11/16/nh-house-democrats-nominate-simpson-to-be-next-speaker-ahead-of-dec-2-vote/) | nominee (chosen Nov 12) |
| NJ | President / Speaker | Scutari / Coughlin | same (no 2026 election) | | | current |
| NM | Governor | Michelle Lujan Grisham | Deb Haaland (D) | 2027-01-01 | election results | confirmed |
| NM | Pro Tem / Speaker | Stewart / Martínez | same (only the Majority Leader changes, Wirth to Linda Trujillo, a post the site doesn't track) | | NCSL | current |
| NV | Governor | Joe Lombardo | Aaron Ford (D) | 2027-01-04 | election results | confirmed |
| NV | Majority Leader | Nicole Cannizzaro | Edgar Flores | 2027-02-01 | NCSL | confirmed by caucus |
| NV | Speaker | Steve Yeager | Elaine Marzola | 2027-02-01 | NCSL | nominee |
| NY | Majority Leader / Speaker | Stewart-Cousins / Heastie | same | | State Capital Lobbyist | expected |
| OH | Governor | Mike DeWine | Amy Acton (D) | 2027-01-11 | election results | confirmed |
| OH | Senate President | Rob McColley | Bill Reineke | 2027-01-04 | NCSL | nominee |
| OH | Speaker | Matt Huffman | same | | State Capital Lobbyist | current |
| OK | Governor | Kevin Stitt | Mike Mazzei (R) | 2027-01-11 | election results (certified) | confirmed |
| OK | Pro Tem / Speaker | Paxton / Hilbert | same | | State Capital Lobbyist | nominee |
| OR | Senate President | Rob Wagner | same | 2027-01-11 | [Portland Tribune](https://portlandtribune.com/2026/11/14/oregon-senate-democrats-choose-leadership-team-nominate-wagner-to-continue-as-president/) | nominee |
| OR | Speaker | Julie Fahey | Ben Bowman (D) | 2027-01-11 | [Oregon Capital Chronicle](https://oregoncapitalchronicle.com/2026/11/20/oregon-democrats-tap-majority-leader-ben-bowman-as-next-house-speaker/); [OPB](https://www.opb.org/article/2026/11/20/oregon-house-speaker-ben-bowman-to-replace-julie-fahey/) | nominee (added 2026-11-22) |
| PA | President Pro Tem | Kim Ward | Jay Costa (D) | 2027-01-05 | NCSL | nominee |
| PA | Speaker | Joanna McClinton | same | 2027-01-05 | State Capital Lobbyist | nominee |
| RI | Governor | Dan McKee | Helena Foulkes (D) | 2027-01-05 | election results | confirmed |
| RI | President / Speaker | Lawson / Blazejewski | same | | State Capital Lobbyist | current |
| SC | Governor | Henry McMaster | Alan Wilson (R) | 2027-01-13 | election results (certified) | confirmed |
| SC | President / Speaker | Alexander / Smith | same | | State Capital Lobbyist | current |
| SD | President Pro Tem | Chris Karr | Tim Reed | 2027-01-12 | NCSL | nominee |
| SD | Speaker | Jon Hansen | Mike Stevens | 2027-01-12 | NCSL | nominee |
| TN | Governor | Bill Lee | Marsha Blackburn (R) | 2027-01-16 | election results | confirmed |
| TN | Lt. Gov. and Speaker of the Senate | Randy McNally | Jack Johnson | 2027-01-12 | NCSL | nominee |
| TN | Speaker | Cameron Sexton | same | | State Capital Lobbyist | current |
| TX | Governor | Greg Abbott | Gina Hinojosa (D) | 2027-01-19 | election results | confirmed |
| TX | Lieutenant Governor | Dan Patrick | Vikki Goodwin (D) | 2027-01-19 | NCSL | confirmed (elected) |
| TX | Speaker | Dustin Burrows | ? | 2027-01-12 | Texas Scorecard | pending |
| US | President | Donald Trump | same | | | current |
| US | Senate Majority Leader | John Thune | Democratic leader chosen Dec 1 | 2027-01-03 | Wikipedia; CNN | pending |
| US | Speaker | Mike Johnson | Hakeem Jeffries (D) | 2027-01-03 | [Roll Call](https://rollcall.com/2026/11/18/democrats-nominate-jeffries-to-be-house-speaker-a-historic-first); [Axios](https://www.axios.com/2026/11/18/jeffries-speaker-house-democrats-nominate-jan-3) | nominee (251-11 in caucus, Nov 18) |
| UT | President of the Senate | J. Stuart Adams | Evan Vickers | 2027-01-19 | NCSL | nominee |
| UT | Speaker | Mike Schultz | same | | State Capital Lobbyist | confirmed by caucus |
| VA | Majority Leader / Speaker | Surovell / Scott | same (no 2026 election) | | | current |
| VT | Governor | Phil Scott | same (re-elected) | | election results | confirmed |
| VT | President Pro Tem | Philip Baruth | Andrew Perchlik | 2027-01-06 | [VTDigger](https://vtdigger.org/2026/11/16/vermont-senate-democrats-nominate-andrew-perchlik-to-be-chambers-next-leader/) | nominee |
| VT | Speaker | Jill Krowinski | Lori Houghton (expected) | 2027-01-06 | Vermont Public | pending (caucus Dec 5) |
| WA | Majority Leader / Speaker | Pedersen / Jinkins | same | 2027-01-11 | [Washington State Standard](https://washingtonstatestandard.com/2026/11/16/democrats-re-elect-jinkins-as-house-speaker-in-wa-legislature/) | confirmed by caucus |
| WI | Governor | Tony Evers | David Crowley (D) | 2027-01-04 | election results | confirmed |
| WI | Majority Leader | Devin LeMahieu | Dianne Hesselbein (D) | 2027-01-04 | NCSL | nominee |
| WI | Speaker | Robin Vos | Greta Neubauer (D) | 2027-01-04 | NCSL | nominee |
| WV | President / Speaker | Smith / Hanshaw | same | | State Capital Lobbyist | current |
| WY | Governor | Mark Gordon | Eric Barlow (R) | 2027-01-04 | election results | confirmed |
| WY | President of the Senate | Bo Biteman | Tara Nethercott | 2027-01-12 | [Cowboy State Daily](https://cowboystatedaily.com/2026/11/14/tara-nethercott-elected-wyoming-senate-president-lloyd-larsen-house-speaker/) | nominee |
| WY | Speaker | Chip Neiman | Lloyd Larsen | 2027-01-12 | [WyoFile](https://wyofile.com/after-voters-sweep-away-freedom-caucus-traditional-republicans-set-to-lead-wyoming-legislature/) | nominee |

## Party control (balance.py)

- The balance line counts party seats from the member list of the session in office (`contacts_path()`: a 2027 list counts
  from January 1, or earlier in FL, NV, AL and ND). A chamber whose majority flipped therefore shows the new majority
  once the state's 2027 member list is downloaded, not on a fixed day. Until then it shows 2025–26.
- The front page's next-year view reads states/elected_2026.json (reported results, as of 2026-11-14). It agrees with
  the leaders above: Democrats win AZ, MI House, MN House, NC House, NH, PA Senate, TX House and WI; coalitions continue
  in AK; MN loses its tie.
- Changes in legislatures.json, by date (`next`): MN's House coalition flag and note on 2027-01-12; AK's note (naming
  Schrage and Giessel) on 2027-01-19; Congress's note on 2027-01-03; the notes that named an outgoing governor (AL, FL,
  IA, KS, NM, SC) lose that sentence on inauguration day. HI's note now says Green was re-elected.

## Later checks

- Dec 1: the US Senate Democrats' vote. Dec 5: Vermont House Democrats. Dec 7: Kansas House Republicans. December:
  Idaho caucuses. January: NC Senate Republicans, Illinois House Democrats, Texas House, Nebraska (Jan 6).
- Each nominee's date assumes the chamber elects them on its first day. If a floor vote goes another way (Jeffries on
  Jan 3, the AK coalitions on Jan 19, NH on Dec 2), correct `LEADERS_NEXT` that day.
- Governors' contact links that name the outgoing governor still need changing on inauguration day: FL's
  `.../ron-desantis/contact` and ME's `.../governor/mills/contact` (profile.js `govReach` and weighin.html). The new
  administrations' addresses aren't known yet.
- Iowa's inauguration date: Jan 12 as reported by most outlets; one says Jan 19.
- Certification: most governors-elect certify by mid-December. IA, ME, TN and TX certify when their Legislature canvasses
  in January.
