# New Hampshire

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **New Hampshire (built 2026-11-08):** `python3 states/nh/fetch.py`
  downloads the General Court's daily data files (the current year), and past years (2023-25) from its public SQL Server in
  the same shapes (see its docstring), into data/nh/<first year of the General Court>/; `states/nh/contacts.py` runs after
  it. A page is one session year (`YEARS = 1`; decided 2026-11-08): each year has its own deadlines, laws ("Chapter 74,
  Laws of 2025") and governor's actions, and the files are split by session year. A bill dies with its year unless a
  committee keeps it over to the second year of the General Court ("Retained in Committee" in the House, "Rereferred to
  Committee, MA" in the Senate): such bills are only in the second year's files, so `bill_rows()` gives the first year's
  page those with its LSR prefix ("25-"), their history cut at the line that kept them, and both pages show them under the
  same number (`STATE.continuedTo`, "Carried over to 2026 in the Finance Committee"). CACRs (constitutional amendments)
  are numbered "CACR 1" in both houses; the site reads a bill's house from its number, so they're "HCACR1"/"SCACR1"
  (`official()` drops the letter for links). `states/nh/convert.py` reads the Docket's lines as written ("Ought to Pass
  with Amendment 2025-0695h: MA RC 212-161 03/20/2025 HJ 9 P. 28"; MA/MF motion adopted/failed): a house passes a bill
  with the last "Ought to Pass" it adopts that isn't followed by a second referral ("Referred to Finance", the Senate's
  "...; Refer to Finance Rule 4-5"), unless that committee waives it ("Referral Waived by Committee Chair per House Rule
  47(f)"); the Senate's passage needs "OT3rdg" ("Ought to Pass: MA" alone leaves the motion pending, and the bill can be
  tabled on it: HB 246 of 2026). Adopting "Inexpedient to Legislate", interim study or indefinite postponement kills it:
  stage 0, shown as "Killed" (`STATE.heldAction` is a pattern here); its first committee's report decides `commFate`
  (no "held"). Passed both houses: both passed, and enrolled, or the first concurred, or both adopted a conference
  report, or the second passed it with no amendment. Line dates are the event's; entry times are the clerks' and out of
  order across houses, so lines sort by day, then house of origin / other house / between the houses / enrollment /
  governor, then step. Members' votes are the roll calls on the bill's own question (OTP, OTPA, Concur, conference
  report, veto override; not ITL, whose "yea" is against the bill); most votes are voice votes. Seats: "S:12", and a
  House district's members "H:612a", "H:612b" ... (Hillsborough 12 = county code times 100 plus the number; up to 10 a
  district), named by data/nh/district_names.json. "Where you live" (`states/nh/towns.py`, run once) reads the districts
  from the law, RSA 662:3 and 662:5, by town and city ward; a place votes in all its House districts (its own and a
  "floterial" one over it and its neighbors: `STATE.townInAllDistricts`, read by `myReps()`/`setTown()`). The public site
  also looks up an address: the Census geocoder gives the Senate district and the base House district ("Merrimack 18";
  its 164 House districts leave out the 39 floterials), and `floterials()` in tracker.html adds the floterials of the towns
  in that base district (each base district's towns all share them, checked 2026-11-22). "What it
  does" is the analysis at the top of each bill's latest text (by the Office of Legislative Services; `analyses()` in
  fetch.py: billText.aspx?id=...&sy=...; the id from LsrsOnly, from the LSR number and year for 2023-24, else from the
  bill's status page), labelled by version ("... of the final version", "... as amended by the House", "... as introduced"
  when the analysis wasn't rewritten). A bill is read again only when the Docket shows a new adopted amendment or a
  chapter (data/nh/<first year>/analyses_<year>.json); summaries never mark the state incomplete, and the first copy (about
  5,100 requests at the 11-second delay, about 12 minutes a run) fills in over about a week. The budget bills say "No
  analysis needed." and have none. 142 representatives list no phone; none is invented. The governor's phone and contact page haven't been
  checked by the owner. Laws and vetoes match the LSRs file's chapters and status codes exactly (2023: 243 and 9; 2024:
  381 and 13; 2025: 305 and 12; 2026: 344 and 25). Add each year's first and last floor days to `opened`/`dated`.
- (2026-11-19) A veto one house overrode and the other sustained stands (SB 434, SB 552, SB 661, HB 1766 of 2026; HB 337 of
  2023; HB 274, HB 1415, HB 1581 of 2024). "Veto Sustained" lines (the House's "Veto Sustained 08/19/2026: RC 165-140 ...",
  the Senate's "... Veto Sustained, lacking the necessary two-thirds vote") are read as "VETO SUSTAINED", the day's last
  step (`GROUP["sustain"]`, after "override"), so the last action no longer reads "VETO OVERRIDDEN".
- **Next year's bills (2026-11-22):** the daily files hold only the current session year (2026 only on 2026-11-22);
  when they switch to 2027 (around the new General Court's organization day in December), `by_year()` puts its rows in
  data/nh/2027/, and convert.py's `sessions()` shows this or next year from its first numbered bill (not 100 LSRs). In
  December, before the session, `missing()` counts the last biennium's per-term files, so the new term's never hold New
  Hampshire off the site.
