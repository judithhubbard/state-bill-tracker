# California

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **California (built 2026-10-29):** `python3 states/ca/fetch.py` reads the Legislature's database tables out of its pubinfo
  zips (see the ca-data-sources memory) into data/ca/<session>/ (session = its odd first year); `states/ca/pubinfo.py`
  reads only the wanted files from a remote zip by HTTP range (with curl: the server turns away Python's client), so
  a day's run reads about 11 MB, not 1.2 GB. The daily zip's text files are numbered differently each day, so the
  bill texts (the Legislative Counsel's Digest, `states/ca/texts.py`, cached by version in digests.json) and veto
  messages (vetoes.json) are read from the same zip as the tables. `states/ca/convert.py` decodes the plain-English
  history (each line also says where the bill went: house, Committee/Floor/Desk, committee code) and spells out the
  committee abbreviations; "From committee chair, with author's amendments" is not a committee vote. Only regular-session
  AB and SB bills are shown. Joint authors are all primes. Deadlines (`originBy()`, `lastDay()` in states/ca/profile.js)
  were fitted to the 2021-26 floor votes; the governor has 12 days (a 12th day on a weekend or
  holiday moves to the next working day, Art. IV, sec. 10(b)(5)), or 30 days after the first year's last day, or
  until September 30. `states/ca/contacts.py` reads the Senate's senator, committee and leadership pages and the
  Assembly's member-data API; each member carries `dataName`, the name the database uses ("Limón"), to tie votes and
  authors to seats ("S:21", "A:30"). "Where you live" picks a county (`states/ca/towns.py`, run once: the Senate's
  counties PDF and the Assembly's list) and, on the public site, looks up an address with the Census geocoder
  (`STATE.addressLookup`). Earlier sessions are linked by subject and digest (`earlier()`, like Virginia's), never
  spot bills. A new governor takes office January 4, 2027: add them to `GOVERNORS`.
- **The next session's bills (2026-11-22):** the daily zip moves to the new session when it convenes (the first Monday of December of an even year: 2027-28 on 2026-12-07, when bills are first introduced), and `fetch.py` already reads CURRENT + 2's own zip (pubinfo_2027.zip, a 404 until it's published) and saves a daily zip into the folder of the newest session its BILL table names; `load_session()` keeps only rows of its own session (BILL's session column), in case a zip around the switch holds both. 2025-26's copy then comes from pubinfo_2025.zip. No 2027 data on 2026-11-22.
