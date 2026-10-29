// Virginia: the page's settings and rules that are particular to this state. build_data.py puts this file
// into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "va",
  // Steps that aren't news on a watchlist card.
  routine: /^(INTRODUCED|Prefiled|Placed on .*Agenda|Assigned .*sub|(Fiscal )?Impact [Ss]tatement|Bill text|Printed as|Committee substitute printed|Title replaced|Engrossed|Read (first|second) time|Constitutional reading|Enrolled$|Signed by (Speaker|President)|Governor's Action Deadline|Acts of Assembly Chapter text|Conference report released|Conference substitute printed|Taken up|Passed by for the day|Rules suspended|VOTE:)/,
  publicSite: "https://statebilltracker.org/va/",
  listsApi: "",
  // The House of Delegates ("H") is the lower house; its members are delegates.
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Del." },
  memberWords: { S: "state senator", H: "delegate" },
  greetings: { S: "Senator", H: "Delegate" },
  // Sessions run one year, and bill numbers start over each year.
  years: 1,
  sessionLabel: (s) => String(s),
  govReach: `<a href="https://www.governor.virginia.gov/constituent-services/" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · <a class="phone" href="tel:+18047862211" data-contact="call|governor">(804) 786-2211</a>`,

  billUrl(p, session = DATA.session) {
    return `https://lis.virginia.gov/bill-details/${session}1/${p}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)} on the Legislature's site: text, summary and history`)).join("<br>");
  },

  // The session's dates follow from its opening day (the second Wednesday of January): it runs 60 days in even
  // years and 46 in odd ones, and crossover, the last day for each house to pass its own bills, has been the 35th
  // day of a 60-day session and the 28th of a 46-day one (2024-26). A year that differs goes in `dated`.
  dated: {},
  day: (year, n) => { const [y, m, d] = STATE.opens(year).split("-").map(Number), t = new Date(y, m - 1, d + n - 1);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`; },
  sessionEnds: (session) => STATE.dated[session]?.adjourns || STATE.day(session, session % 2 ? 46 : 60),
  crossover: (session) => STATE.dated[session]?.crossover || STATE.day(session, session % 2 ? 28 : 35),
  // A bill that hasn't passed its own house has to by crossover (a continued bill's starts over in the new session).
  originDeadline: (b) => STATE.crossover(DATA.session),
  originWord: "crossover",
  // The reconvened session, for the governor's amendments and vetoes: the sixth Wednesday after adjournment.
  reconvenes(session) {
    const [y, m, d] = STATE.sessionEnds(session).split("-").map(Number);
    const end = new Date(y, m - 1, d), wed = new Date(end);
    wed.setDate(end.getDate() + ((3 - end.getDay() + 7) % 7 || 7) + 35);
    return `${wed.getFullYear()}-${String(wed.getMonth() + 1).padStart(2, "0")}-${String(wed.getDate()).padStart(2, "0")}`;
  },
  // The governor has 7 days for a bill presented while the session has more than 7 days to run; otherwise
  // 30 days after adjournment (Constitution of Virginia, Art. V, sec. 6).
  govDeadline(iso, session) {
    if (!iso) return null;
    const ymd = (dt) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
    const [y, m, d] = iso.split("-").map(Number), [ey, em, ed] = STATE.sessionEnds(session).split("-").map(Number);
    const seven = ymd(new Date(y, m - 1, d + 7)), end = STATE.sessionEnds(session);
    return seven < end ? seven : ymd(new Date(ey, em - 1, ed + 30));
  },
  dueLabel: () => "Governor's decision due (7 days after it reached the governor, or 30 days after the session adjourned)",

  // A bill the governor sent back with amendments waits for the reconvened session.
  amended: (b) => b.vers.some((v) => v.actions.some(([, t]) => /Governor's (recommendation|amendment)/i.test(t))),
  passedBothBy: (session) => STATE.reconvenes(session),
  passedBothNote: (live, b) => !live ? "Never sent to the governor"
    : !b ? "Includes bills sent back with the governor's amendments"
    : STATE.amended(b) ? "Sent back with the governor's amendments" : "Not yet sent to the governor",
  passedBothGroup: ["Before the reconvened session", () => `The Legislature meets on ${monthDay(STATE.reconvenes(DATA.session))} to vote on the governor's amendments and vetoes.`],
  passedBothNext(b) {
    if (!STATE.amended(b)) return {
      what: "it goes to the governor, who has 7 days to act during the session, or 30 days after it adjourns, to sign it, veto it or send it back with amendments.",
      gov: ["sign it", "veto it"],
      reps: ["urge the governor to sign it", "urge the governor to veto it"],
    };
    return {
      what: `both houses vote on the governor's amendments at the reconvened session on ${fmtDate(STATE.reconvenes(DATA.session))}. If they accept them, the bill becomes law with the changes; if not, it goes back to the governor.`,
      leaders: ["S", "H"],
      leaderAsk: ["bring up the governor's amendments", "keep the governor's amendments from passing"],
      reps: ["vote to accept the governor's amendments", "vote against the governor's amendments"],
    };
  },
  // "Where you live" picks a county or city; a split one can look up the address on the Legislature's site.
  townWord: "County or city",
  findReps: "https://whosmy.virginiageneralassembly.gov/",
  // A bill keeps its number through both houses (HB1 goes to the Senate as HB1).
  oneNumber: true,
  // Once the session is over: dead, unless a committee continued it to next year's session.
  continuedTo(b) {
    const cont = b.vers.flatMap((v) => v.actions).map(([, t]) => t.match(/Continued to (?:next session|(\d{4}))/i)).find(Boolean);
    return cont ? +(cont[1] || DATA.session + 1) : null;
  },
  diesAfterFloor: (y2, b) => (b && STATE.continuedTo(b) ? `It was continued to the ${STATE.continuedTo(b)} session, where it can be taken up again.`
    : "The session is over, so it died with it."),
  outOfTimeLine: "Died when the session ended",

  // A committee that "passes a bill by indefinitely" sets it aside; it's dead for the year.
  heldLabel: "Passed by indefinitely",
  heldTip: "Set aside by a committee vote instead of being voted down. In practice the bill is dead for the year.",
  heldNote: "set aside by a committee vote instead of being voted down; in practice the bill is dead for the year.",

  // The session opens on the second Wednesday of January.
  opens(year) {
    const first = new Date(year, 0, 1), wed = 1 + ((3 - first.getDay() + 7) % 7) + 7;
    return `${year}-01-${String(wed).padStart(2, "0")}`;
  },
  // The note above the bill list once the session has adjourned (empty while it runs).
  sessionNotice(raw) {
    const today = isoToday(), y = raw.session, end = STATE.sessionEnds(y), back = STATE.reconvenes(y);
    const due = STATE.govDeadline(end, y);
    if (today <= end) return "";
    if (today <= back) return `The ${y} session adjourned ${fmtDate(end)}. The governor has until ${fmtDate(due)} to act on its bills, and the Legislature returns ${fmtDate(back)} to vote on the governor's amendments and vetoes.`;
    const next = y + 1, carried = raw.sessions.find((x) => x.session === next);
    // Between sessions is when bills for the next one are planned: the session itself is a sprint.
    return `The ${y} session is over, and the ${next} session opens ${fmtDate(STATE.opens(next))}. Now is the time to ask your legislators to sponsor bills for it: they're drafted over the fall and can be filed from mid-November${carried ? `. Bills continued from ${y} are already on the ${next} <a href="${esc(carried.url)}">page</a>` : ""}.`;
  },
  // The year's calendar: the Legislature's and the governor's bars ([class, from, to, text]), the events marked on
  // it ([date, "up"/"down", row, when, text]; rows are LEG = 112, GOV = 150) and a note.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), back = STATE.reconvenes(Y);
    const due = STATE.govDeadline(adj, Y);
    return {
      leg: [["", open, adj, "In session"], ["", back, `${back.slice(0, 8)}${String(+back.slice(8) + 3).padStart(2, "0")}`, ""]],
      gov: [["light", open, adj, "7 days a bill"], ["", adj, due, "30 days"]],
      events: [
        [open, "up", LEG, `January ${Y}`, `Session opens. By crossover, ${MD(STATE.crossover(Y))}, each house must have passed its own bills.`],
        [adj, "down", LEG, MD(adj), "Session adjourns. Bills that didn't pass die."],
        [back, "up", LEG, MD(back), "Reconvened session: votes on the governor's amendments and vetoes."],
        [`${Y}-07-01`, "down", LEG, "July 1", "Most new laws take effect."],
        [`${Y}-11-17`, "up", LEG, "November", "Bills for next year's session can be filed."],
      ],
      note: "The governor can sign a bill, veto it, or send it back with amendments: within 7 days during the session, or 30 days after it adjourns for bills that arrive in its last week. Overriding a veto takes two-thirds of the members present in each house.",
    };
  },
  waitingHead: "Sent back with the governor's amendments",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: () => "the governor acts on the last bills in the spring",

  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    // Before the session opens (its page shows continued and early-filed bills, already in committees).
    prefiled: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  // The next session's page before it opens: bills continued from this year pick up where they stopped (one that
  // passed its own house doesn't pass it again), and bills filed early for it go to committees as they're filed.
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. This page has bills continued from ${raw.session - 1}, which pick up where they stopped (a bill that passed one house doesn't have to pass it again), and bills filed early for ${raw.session}. Stars you add here carry over when the session starts.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,
  stageTips: [
    "Waiting in a committee or subcommittee. Most bills never get out of committee.",
    "A committee approved it, and it's waiting for a vote of the full House or Senate.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. A bill the governor sent back with amendments waits here for the reconvened session.",
    "Passed both houses and sent to the governor, who can sign it, veto it, or send it back with amendments.",
    "Signed into law and given a chapter number.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "The session is over. Bills that didn't become law have to be introduced again next year.",

  // Committees in the two houses that cover the same subject (Senate name -> [House name, label]).
  commPairs: {
    "Agriculture, Conservation and Natural Resources": ["Agriculture, Chesapeake and Natural Resources", "Agriculture and natural resources"],
    "Commerce and Labor": ["Labor and Commerce", "Commerce and labor"],
    "Finance and Appropriations": ["Appropriations", "Budget and spending"],
    "Local Government": ["Counties, Cities and Towns", "Local government"],
    "General Laws and Technology": ["General Laws", "General laws"],
    "Education and Health": ["Education", "Education"],
    "Rehabilitation and Social Services": ["Health and Human Services", "Health and human services"],
  },
  commNotes: {
    "budget and spending": "Bills that cost the state money often come here after their subject committee.",
  },
  moneyCommittees: { S: "Finance and Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that cost money also go to House Appropriations or Senate Finance and Appropriations.",
};
