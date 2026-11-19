# Tennessee

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

- **Tennessee (built 2026-11-08 from LegiScan):** `states/tn/convert.py`
  (the `Tennessee` rules), `contacts.py` (run after legiscan.py), `towns.py` (run once). Two-year General Assemblies (2025 is
  the 114th, 2025-26), sessions each year from the second Tuesday of January to late April (`STATE.dated`: add each year's
  last day). Only HB/SB under 6000 (extraordinary sessions' bills are 6001+, 7001+ in the same files) and the joint
  resolutions proposing amendments to the Tennessee Constitution (majority in one General Assembly, two-thirds in the next,
  then the voters at the next governor's election: `ballotYear()`); other resolutions left out. Every bill is filed in both
  houses with the same text; LegiScan's sasts "Crossfiled" (and, for joint resolutions, the same title) put the two numbers in
  one record, as NJ's and NY's identical bills are; when one passes, the other house substitutes it for its own ("Comp. SB
  subst." marks the number that gave way: `replaced`). House bills go through subcommittees ("Assigned to s/c ..."): the
  bill stays in the parent committee; subcommittee votes keep their names. Calendar and Rules (House) and Calendar (Senate)
  schedule floor votes (`gates`). Set aside (`heldAction`): "Taken off notice", "Assigned to General Subcommittee", "Deferred
  to Summer Study", "Lay on the Table" ("Placed behind the budget" is a wait, not counted). Laws: "Signed by Governor.",
  "Returned by Governor without signature." (law), "Pub. Ch. 78" and "Pr. Ch." (private acts, narrow "place"); a governor
  recalled by the Senate ("Governor returned.", SB 1758 of 2026) is `unsent`. Public chapters are numbered through the
  General Assembly with no gaps, so laws here match them exactly: 2023-24 1,069 public + 68 private = 1,137; 2025-26 1,142 +
  74 = 1,216; vetoes 0 and 2 (SB 455 of 2025, HB 1882 of 2026). "What it does" is the General Assembly's bill summary
  ("As introduced, ..." / "As enacted, ...", LegiScan's description); the title is its first clause. Governor 10 days,
  Sundays excepted, no pocket veto; override a majority of the members. Leaders: Speaker Cameron Sexton; Lt. Gov. and Senate
  Speaker Randy McNally, who didn't run in 2026 (change `LEADERS` when the 115th General Assembly elects a new one in January
  2027). Governor Bill Lee is term-limited: add the new governor (January 2027) to `GOVERNORS` and states/legislatures.json.
  The governor's contact page and phone haven't been checked by the owner. sos.tn.gov turns automated requests away.
