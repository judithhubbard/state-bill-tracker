// Texas: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "tx",
  name: "Texas",
  abbr: "TX",
  // Steps that aren't news on a watchlist card.
  routine: /^(INTRODUCED|Filed$|Read first time|Received from the (House|Senate)|Scheduled for public hearing|Testimony taken|Committee substitute considered|Comte report filed|Committee report (distributed|printed)|Considered in (Calendars|Local)|Reported engrossed|Reported enrolled|Signed in the (House|Senate)|Co-?author authorized|Co-?sponsor authorized|Statement\(s\) of vote|Vote recorded|Record vote|Nonrecord vote|Rules suspended|Three day rule|Amendment|Point of order|Text of|Senate Amendments (distributed|Analysis)|Corrected|Effective|See remarks|Sent to the Comptroller|Laid out|Not again placed)/i,
  publicSite: "https://statebilltracker.org/tx/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025 (the 89th Legislature's regular session).
  sessionLabel: (s) => String(s),
  govReach: `<a href="https://gov.texas.gov/contact" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · <a class="phone" href="tel:+18008435789" data-contact="call|governor">(800) 843-5789</a>`,

  billUrl(p, session = DATA.session) {
    return `https://capitol.texas.gov/BillLookup/History.aspx?LegSess=${(session - 1847) / 2}R&Bill=${p}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)} on Texas Legislature Online: text, analyses and history`)).join("<br>");
  },

  // The regular session meets for 140 days from the second Tuesday of January in odd years.
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 7);
    return `${session}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  day(session, n) {
    const [y, m, d] = STATE.opens(session).split("-").map(Number), t = new Date(y, m - 1, d + n - 1);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => STATE.day(session, 140),
  floorVotesEnd: false,
  // A House bill has to pass the House on second reading by the 122nd day (May 15, 2025).
  originDeadline: (b) => (b.vers[0].p.startsWith("H") ? STATE.day(DATA.session, 122) : null),
  originWord: "the House's deadline",
  // The governor has 10 days, not counting Sundays, during the session; for bills that arrive in its last 10 days,
  // until 20 days after it adjourns (Texas Constitution, Art. IV, sec. 14). A veto after adjournment can't be overridden.
  govDeadline(iso, session) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d);
    for (let n = 0; n < 10;) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n++; }
    const end = STATE.sessionEnds(session);
    if (ymd(t) <= end) return ymd(t);
    const [ey, em, ed] = end.split("-").map(Number);
    return ymd(new Date(ey, em - 1, ed + 20));
  },
  dueLabel: () => "Governor's decision due (10 days, not counting Sundays, or 20 days after the session ends)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => (live ? "Not yet sent to the governor" : "Never sent to the governor"),
  passedBothGroup: ["On the way to the governor", () => "These passed both houses and go to the governor once they're signed by the presiding officers."],
  passedBothNext: () => ({
    what: "it goes to the governor, who has 10 days (not counting Sundays) to sign or veto it, or 20 days after the session ends for bills passed in its last days. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "County",
  addressLookup: true,
  findReps: "https://wrm.capitol.texas.gov/home",
  oneNumber: true,
  diesAfterFloor: () => "The session is over, so it died with it.",
  outOfTimeLine: "Died when the session ended",

  // A committee that hears a bill and doesn't vote on it "leaves it pending".
  heldLabel: "Left pending in committee",
  heldTip: "Heard but not voted on. The chair can bring it back up, but most bills left pending never come back.",
  heldNote: "heard but not voted on; the chair can bring a bill back up, but most never come back.",

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t <= end) return "";
    const due = STATE.govDeadline(end, y), next = y + 2;
    const filing = (() => { const n = new Date(next - 1, 10, 1); n.setDate(1 + ((2 - n.getDay() + 7) % 7) + 6);
      return `${next - 1}-11-${String(n.getDate()).padStart(2, "0")}`; })();
    if (t <= due) return `The regular session ended ${fmtDate(end)}. The governor has until ${fmtDate(due)} to act on the bills it passed.`;
    return `The ${y} regular session ended ${fmtDate(end)}. The next one opens ${fmtDate(STATE.opens(next))}, and bills for it can be filed from ${fmtDate(filing)}. Now is the time to ask your legislators to file a bill. (Special sessions the governor calls aren't shown here.)`;
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed; committees start hearing them after the session opens. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The calendar: the session's 140 days in the first year; nothing in the second.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), end = STATE.sessionEnds(Y), due = STATE.govDeadline(end, Y);
    return {
      leg: [["", open, end, "Regular session"], ["light", end, `${Y + 1}-11-09`, "Interim"]],
      gov: [["light", open, end, "10 days a bill"], ["", end, due, "20 days"]],
      events: [
        [open, "up", LEG, MD(open), "Session opens (bills filed since November)."],
        [STATE.day(Y, 60), "down", LEG, MD(STATE.day(Y, 60)), "Last day to file most bills."],
        [STATE.day(Y, 122), "up", LEG, MD(STATE.day(Y, 122)), "Last day for the House to pass its own bills."],
        [end, "down", LEG, MD(end), "Session ends. Bills that didn't pass die."],
        [due, "down", GOV, MD(due), "Last day for the governor to act."],
        [`${Y + 1}-11-09`, "up", LEG, "November", "Bills for the next session can be filed."],
      ],
      note: "The governor has 10 days, not counting Sundays, to sign or veto a bill during the session; bills passed in its last days have until 20 days after it ends. A veto after the session ends can't be overridden. Most new laws take effect September 1. The governor can call special sessions of up to 30 days on topics he chooses.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislative Reference Library's list of members",
  openUntil: (s) => `the session ends ${fmtDate(STATE.sessionEnds(s))}`,

  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    prefiled: {
      pipe: ["Filed", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["Filed", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["Filed", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Became law", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. In the House, bills a committee approves go next to the Calendars Committee, which decides which ones reach the floor.",
    "On a calendar for a vote of the full House or Senate.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses and on its way to the governor.",
    "Passed both houses and sent to the governor, who has 10 days to sign or veto it (20 days after the session ends for bills passed in its last days).",
    "Became law: signed by the governor, or filed without the governor's signature.",
    "Vetoed by the governor. A veto after the session ends can't be overridden.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "The regular session is over. Bills that didn't become law have to be filed again for the next session.",

  // Committees in the two houses that cover the same subject (Senate name -> [House name, label]).
  commPairs: {
    "Finance": ["Appropriations", "Budget and spending"],
    "Criminal Justice": ["Criminal Jurisprudence", "Criminal justice"],
    "Jurisprudence": ["Judiciary & Civil Jurisprudence", "Courts and civil law"],
    "Health and Human Services": ["Public Health", "Health and human services"],
    "Business and Commerce": ["Business & Industry", "Business"],
    "Education K-16": ["Public Education", "Education"],
    "Water, Agriculture, and Rural Affairs": ["Agriculture & Livestock", "Agriculture and water"],
    "Natural Resources": ["Natural Resources", "Natural resources"],
    "Local Government": ["Land & Resource Management", "Local government"],
    "Veteran Affairs": ["Defense & Veterans' Affairs", "Veterans"],
    "Border Security": ["Homeland Security, Public Safety & Veterans' Affairs", "Border and public safety"],
  },
  commNotes: {
    "budget and spending": "Bills that cost the state money often go here; the state budget itself is written here and in the Senate Finance Committee.",
  },
  // The House Calendars Committee decides which bills reach the floor.
  chairAsks: {
    "Calendars": ["schedule it for a floor vote", "keep it off the floor calendar"],
    "Local & Consent Calendars": ["schedule it for a floor vote", "keep it off the floor calendar"],
  },
  moneyCommittees: { S: "Finance", H: "Appropriations" },
  secondCommittee: "In the House, bills a committee approves go next to the Calendars Committee, which decides which reach the floor; in the Senate, the Lieutenant Governor decides which bills come up.",
};
