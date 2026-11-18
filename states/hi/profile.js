// Hawaii: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "hi",
  name: "Hawaii",
  abbr: "HI",
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed in the|Introduced in the|Then to:|Heard jointly with|Bill (?:re-)?scheduled to be heard|Bill scheduled for decision making|The committee\(?s?\)? on .* (?:has scheduled|will hold|has rescheduled)|The (?:House|Senate) vote:|Received in the (?:House|Senate)$|Back in the (?:House|Senate)|Second reading; on the calendar|The .* Committee (?:approved it|put off)|The conference committee's .* members approved|Floor [Aa]mendment|A message from the governor|Notice of the proposed amendment)/i,
  publicSite: "https://statebilltracker.org/hi/",
  listsApi: "https://state-lists.lists-worker.workers.dev",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A two-year Legislature (2025–26 is the 33rd), with a session each year; bills carry over from the first to the second.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Laws are Acts, numbered each year ("Act 250 of 2025").
  lawWord: "Act",
  // Constitutional amendments are bills ("PROPOSING AN AMENDMENT TO ARTICLE ..."): two-thirds of each house's members on
  // final reading in one session, or a majority of each house's members in two successive sessions, sends one to the
  // voters at the next general election (November of an even year). The governor gets notice of it but has no veto
  // (Constitution, Art. XVII, sec. 3).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members (17 senators, 34 representatives), or a majority of each in two successive sessions",
  ballotEvenYears: true,
  // The governor's contact form and main line, from governor.hawaii.gov's contact pages (read by program 2026-11-15, not
  // checked by the owner).
  govReach: `<a href="https://governor.hawaii.gov/contact-us/contact-the-governor/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Honolulu <a class="phone" href="tel:+18085860034" data-contact="call|governor">(808) 586-0034</a>`,

  // The Legislature's bill status page (history, each version's text, committee reports, testimony). Visitors follow these
  // links; the tracker never reads the site (it turns automated readers away).
  billUrl(p, year) {
    const [, type, n] = String(p).match(/^([A-Z]+)(\d+)$/) || [];
    return `https://www.capitol.hawaii.gov/session/measure_indiv.aspx?billtype=${type}&billnumber=${n}&year=${year}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const year = String(b.last || DATA.session).slice(0, 4);
    const out = b.vers.map((v) => link(STATE.billUrl(v.p, year), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: the Legislature's page (history, each version's text, committee reports, testimony)`));
    return out.join("<br>");
  },

  // Each year's session opens the third Wednesday of January (Constitution, Art. III, sec. 10) and lasts 60 session days,
  // to early May. `dated` holds each year's last day (sine die) and the governor's 35th and 45th days after it (Saturdays,
  // Sundays and holidays aren't counted: Art. III, sec. 16), from the floor votes and the governor's announcements; a year
  // not listed is estimated. Add each year's.
  dated: {
    2023: { end: "2023-05-04", intent: "2023-06-26", veto: "2023-07-11" },
    2024: { end: "2024-05-03", intent: "2024-06-25", veto: "2024-07-10" },
    2025: { end: "2025-05-02", intent: "2025-06-24", veto: "2025-07-09" },
    2026: { end: "2026-05-08", intent: "2026-06-30", veto: "2026-07-15" },
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7) + 14);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  // Weekdays after a day, leaving out Hawaii's state holidays in May to July (Memorial Day, Kamehameha Day, July 4).
  workdays(iso, n) {
    const [y] = iso.split("-").map(Number);
    const obs = (t) => { if (t.getDay() === 6) t.setDate(t.getDate() - 1); if (t.getDay() === 0) t.setDate(t.getDate() + 1); return t; };
    const lastMon = new Date(y, 5, 0); lastMon.setDate(lastMon.getDate() - ((lastMon.getDay() + 6) % 7));
    const fmt = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const hol = new Set([fmt(lastMon), fmt(obs(new Date(y, 5, 11))), fmt(obs(new Date(y, 6, 4)))]);
    let d = iso, k = 0;
    while (k < n) {
      d = STATE.plusDays(d, 1);
      const w = new Date(`${d}T12:00`).getDay();
      if (w !== 0 && w !== 6 && !hol.has(d)) k++;
    }
    return d;
  },
  days(year) {
    if (STATE.dated[year]) return STATE.dated[year];
    const end = STATE.workdays(STATE.plusDays(STATE.opens(year), 100), 1);
    return { end, intent: STATE.workdays(end, 35), veto: STATE.workdays(end, 45) };
  },
  sessionEnds: (session) => STATE.days(session + 1).end,
  // The governor has 10 days (Saturdays, Sundays and holidays left out) to act on a bill presented while the session has
  // more than 10 days to run. For a bill presented later, or after the session (most of them), the governor has until the
  // 45th such day after adjournment, and must give the Legislature notice by the 35th day of any bill to be vetoed (the
  // intent-to-veto list); the Legislature can meet on the 45th day to override. A bill not acted on becomes law without the
  // signature (Art. III, sec. 16).
  govDeadline(iso) {
    if (!iso) return null;
    const y = Number(iso.slice(0, 4)), d = STATE.days(y), ten = STATE.workdays(iso, 10);
    return ten <= d.end ? ten : d.veto;
  },
  dueLabel: () => "Governor's decision due (the 45th working day after the session ends, or it becomes law without a signature)",

  passedBothBy: (session) => STATE.days(session + 1).end,
  passedBothNote: (live) => live ? "Waiting to be enrolled" : "Never presented to the governor",
  passedBothGroup: ["Waiting to be enrolled", () => "A bill that passed both houses is enrolled and sent to the governor within a day or two."],
  passedBothNext: () => ({
    what: "it's enrolled and sent to the governor. For a bill sent in the session's last days or after it (most are), the governor has until the 45th working day after the session ends, and must name by the 35th day any bill to be vetoed (the intent-to-veto list); a bill not acted on becomes law without a signature. Overriding a veto takes two-thirds of each house's members (17 senators, 34 representatives), which the Legislature can do in a special session on the 45th day.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "Community or county",
  addressLookup: true,
  findReps: "https://www.capitol.hawaii.gov/legislature/district_maps.aspx",
  oneNumber: true,
  floorVotesEnd: true,
  diesAfterFloor: () => "The Legislature's two years are over, so it died. It would have to be introduced again.",
  outOfTimeLine: "Died when the Legislature's two years ended",

  heldLabel: "Deferred",
  heldTip: "The committee deferred it: set it aside. Hawaii's committees rarely vote a bill down; a deferred bill usually goes no further.",
  heldNote: "the committee deferred it (set it aside), which usually ends it.",
  heldAction: /^Deferred by the /,

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end1 = STATE.days(y).end, end2 = STATE.days(y + 1).end, v1 = STATE.days(y).veto, v2 = STATE.days(y + 1).veto;
    if (t > end1 && t < `${y + 1}-01-01`) return `The ${y} session ended ${fmtDate(end1)}${t <= v1 ? `; the governor has until ${fmtDate(v1)} to act on the bills it passed` : ""}. Bills that haven't passed carry over to ${y + 1}, when the Legislature meets again from ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > end2) return `The ${y}–${String(y + 1).slice(2)} Legislature's last session ended ${fmtDate(end2)}${t <= v2 ? `; the governor has until ${fmtDate(v2)} to act on the bills it passed` : ""}. Bills that didn't pass both houses died. The next Legislature opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session}–${String(raw.session + 1).slice(2)} Legislature opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Bills you star now stay on your watchlist when the session opens.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, each followed by the governor's 45 days.
  calendarDays: 14,
  calendar(Y) {
    const LEG = 112, d1 = STATE.days(Y), d2 = STATE.days(Y + 1), o1 = STATE.opens(Y), o2 = STATE.opens(Y + 1);
    const MDt = (iso) => new Date(`${iso}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" });
    const el = (() => { const t = new Date(Y + 1, 10, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1); return `${Y + 1}-11-${String(t.getDate()).padStart(2, "0")}`; })();
    return {
      leg: [["", o1, d1.end, "Session"], ["light", STATE.plusDays(d1.end, 1), o2, "Interim"], ["", o2, d2.end, "Session"], ["light", STATE.plusDays(d2.end, 1), el, "Interim"]],
      gov: [["light", o1, d1.end, "10 days a bill"], ["", d1.end, d1.veto, "45 days"], ["light", o2, d2.end, "10 days a bill"], ["", d2.end, d2.veto, "45 days"]],
      events: [
        [o1, "up", LEG, MDt(o1), "The Legislature opens. Bills are introduced in the first week or two."],
        [d1.end, "down", LEG, MDt(d1.end), "The session ends (sine die). Bills that haven't passed carry over to next year."],
        [d1.veto, "up", LEG, MDt(d1.veto), "The governor's last day: bills not signed or vetoed become law."],
        [o2, "up", LEG, MDt(o2), "The second year's session opens; carried-over bills pick up where they were."],
        [d2.end, "down", LEG, MDt(d2.end), "The last session ends. Bills that didn't pass both houses die."],
        [el, "up", LEG, MDt(el), "Election day: every House seat and about half the Senate's."],
      ],
      note: "The governor names the bills to be vetoed by the 35th working day after the session (the intent-to-veto list, in late June) and decides by the 45th (mid-July). Each session has deadlines set by the leaders: bills must clear their committees (\"decking\") and pass their own house (\"first crossover\") by early March, and pass the other house's committees and floor (\"second crossover\") by early April; then conference committees work out the differences. The budget year starts July 1. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members.",
    };
  },
  waitingHead: "Waiting for the governor",
  govYearsNote: "",
  partySource: "Party from Open States' list of legislators",
  openUntil: (s) => `the governor acts on the last bills in July ${s + 1}`,

  commIntro: [
    ["Most bills go to two or three committees, one after another.", "Each bill is referred to its committees when it's introduced (\"HLT, CPC, FIN\"); a slash means two committees hear it together (\"AEN/TCA\"). In each house the money committee (Finance in the House, Ways and Means in the Senate) is usually the last stop. Each committee holds a hearing with public testimony, then a decision-making vote."],
    ["Committees pass bills or defer them.", "A committee recommends a bill be passed, often with amendments (a new draft: HD 1, SD 1), or defers it, which usually ends it. Every committee vote is recorded member by member, including those voting \"aye with reservations\"."],
    ["Conference committees settle the differences.", "When the second house changes a bill, the first can agree, or disagree and go to conference. Conferees from both houses agree on a final draft (CD 1) that both houses pass on final reading; the money chairs decide which bills that spend money get funded."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died on the floor (never brought up for a vote)", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Law", "Vetoed"],
    },
  },
  stageTips: [
    "In one of the committees it was referred to; it has to get through each of them.",
    "Through its committees and waiting for the house's third-reading vote.",
    "Passed the House or the Senate, but not both. If the second house changes it, the first has to agree, or a conference committee writes a final version both pass.",
    "Passed both houses in the same form. It's enrolled and sent to the governor.",
    "Sent to the governor, who has until the 45th working day after the session ends (10 days for a bill sent early in the session); a bill not acted on becomes law.",
    "Became law as an Act: signed, law without the governor's signature, or passed over a veto.",
    "Vetoed by the governor. Overriding takes two-thirds of each house's members.",
  ],
  pastStageTips: [
    "Never got through its committees before the Legislature's two years ended.",
    "Through its committees, but never passed by the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses but was never sent to the governor.",
    "Sent to the governor; no signature or veto is recorded.",
  ],
  outOfTime: "This Legislature is over. Bills that didn't become law have to be introduced again in a later one.",

  // Each Senate committee's House counterpart (2025–26's names) and the subject it's shown under.
  commPairs: {
    "Agriculture and Environment": ["Agriculture and Food Systems", "Agriculture and environment"],
    "Commerce and Consumer Protection": ["Consumer Protection and Commerce", "Consumer protection"],
    "Economic Development and Tourism": ["Economic Development and Technology", "Economic development"],
    "Energy and Intergovernmental Affairs": ["Energy and Environmental Protection", "Energy"],
    "Health and Human Services": ["Health", "Health"],
    "Judiciary": ["Judiciary and Hawaiian Affairs", "Courts and law"],
    "Labor and Technology": ["Labor", "Labor"],
    "Public Safety and Military Affairs": ["Public Safety", "Public safety"],
    "Water, Land, Culture and the Arts": ["Water and Land", "Land and water"],
    "Ways and Means": ["Finance", "The budget"],
  },
  commNotes: {
    "Ways and Means": "The Senate Ways and Means Committee writes the Senate's version of the budget and is the last committee for most bills that spend money.",
    "Finance": "The House Finance Committee writes the House's version of the budget and is the last committee for most bills that spend money.",
    "Legislative Management": "The House Legislative Management Committee handles the Legislature's own operations.",
  },
  moneyCommittees: { S: "Ways and Means", H: "Finance" },
  secondCommittee: "Bills that spend money go to Ways and Means (Senate) or Finance (House) last.",
};
