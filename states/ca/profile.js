// California: the page's settings and rules that are particular to this state. build_data.py puts this file
// into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ca",
  // Steps that aren't news on a watchlist card.
  routine: /^(INTRODUCED|Read first time|Introduced\.|From printer|May be (heard|acted upon)|Coauthors revised|Authors? revised|Ordered to (third|second) reading|Read second time\.|In (Senate|Assembly)\. Read first time|Joint Rule|Set for hearing|Hearing postponed|In committee: (Set|Hearing postponed|Hearing canceled)|Ordered to (special )?consent calendar|From (special )?consent calendar|Notice of intention|Art\. IV|Enrolled$|Assembly Rule|Senate Rule|Placed on|Withdrawn from committee\.$)/i,
  publicSite: "https://statebilltracker.org/ca/",
  listsApi: "",
  houses: { S: "Senate", A: "Assembly" },
  titles: { S: "Sen.", A: "Asm." },
  memberWords: { S: "state senator", A: "Assembly member" },
  greetings: { S: "Senator", A: "Assemblymember" },
  // How a session is written: 2025–26.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  govReach: `<a href="https://www.gov.ca.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · <a class="phone" href="tel:+19164452841" data-contact="call|governor">(916) 445-2841</a>`,

  // Constitutional amendments (ACA, SCA) pass each house by two-thirds of its members, then go to the voters at the next
  // statewide election, never to the governor (California Constitution, Art. XVIII, sec. 1 and 4).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  // The measure names its election: usually the next November general election, sometimes a special election (Prop 50,
  // November 2025), and the Legislature can move it; so the page doesn't guess the date.
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || "";
    return d && d.slice(0, 4) < isoToday().slice(0, 4)
      ? "It went to the voters at the election the measure named; the records here don't show the result."
      : "Next: the voters, at the election the measure names (usually the next November general election).";
  },
  ballotEvenYears: true,

  billUrl(p, session = DATA.session) {
    return `https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=${session}${session + 1}0${p}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)} on the Legislature's site: text, analyses and votes`)).join("<br>");
  },

  // The deadlines (Joint Rule 61) fall on Fridays. Checked against the floor votes of 2021-26: each house has to
  // pass its own bills by the first Friday in June in the first year and the first Friday on or after May 24 in the
  // second, and bills left from the first year by January 31; the last day for floor votes is the Friday on or
  // after September 9 in the first year and August 31 in the second. A year that differs goes in `dated`.
  dated: { 2023: { lastDay: "2023-09-14" } },
  friday: (y, m, d) => { const t = new Date(y, m - 1, d); t.setDate(d + ((5 - t.getDay() + 7) % 7));
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`; },
  originBy: (year) => STATE.dated[year]?.origin || (year % 2 ? STATE.friday(year, 6, 1) : STATE.friday(year, 5, 24)),
  lastDay: (year) => STATE.dated[year]?.lastDay || (year % 2 ? STATE.friday(year, 9, 9) : `${year}-08-31`),
  plus: (iso, n) => { const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`; },
  // Floor votes end on August 31 of the second year; the session formally adjourns November 30.
  sessionEnds: (session) => STATE.lastDay(session + 1),
  floorVotesEnd: false,
  // The next session starts the first Monday in December of the second year, when new members are sworn in.
  opens(session) {
    const t = new Date(session - 1, 11, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7));
    return `${session - 1}-12-${String(t.getDate()).padStart(2, "0")}`;
  },
  // A bill has to pass its own house: one introduced in the first year by January 31 of the second, one introduced
  // in the second year by its late-May deadline.
  // Constitutional amendments have no such deadline (ACA 5 of 2023 passed the Assembly in late June, ACA 13 in September).
  originDeadline: (b) => b.topics.includes("const") ? null : (b.first < `${DATA.session + 1}` ? `${DATA.session + 1}-01-31` : STATE.originBy(DATA.session + 1)),
  originWord: "the deadline",
  // The governor has 12 days. Bills presented in the first year's last 12 days have until 30 days after it; in the
  // second year, bills that reach the governor near the end have until September 30 (Constitution, Art. IV, sec. 10).
  govDeadline(iso, session) {
    if (!iso) return null;
    const y = +iso.slice(0, 4), twelve = STATE.plus(iso, 12);
    if (y === session) { const last = STATE.lastDay(y); return twelve <= last ? twelve : STATE.plus(last, 30); }
    return twelve < `${y}-09-01` ? twelve : `${y}-09-30`;
  },
  dueLabel: () => "Governor's decision due (12 days after it reached the governor, or later for bills passed at the end of a year)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => (live ? "Not yet sent to the governor" : "Never sent to the governor"),
  passedBothGroup: ["On the way to the governor", () => "These passed both houses and go to the governor once they're printed, usually within days."],
  passedBothNext: () => ({
    what: "it goes to the governor, who has 12 days to sign or veto it (until September 30 for bills passed at the end of the session).",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  name: "California",
  abbr: "CA",
  // Most counties are split among districts, so the public site also looks up an address (the Census geocoder).
  townWord: "County",
  addressLookup: true,
  findReps: "https://www.assembly.ca.gov/assemblymembers/find-my-rep",
  // A bill keeps its number through both houses (AB 1 goes to the Senate as AB 1).
  oneNumber: true,
  diesAfterFloor: () => "The session is over, so it died with it.",
  outOfTimeLine: "Died when the session ended",

  // Most bills that cost money are decided on the Appropriations committees' suspense file; the ones a committee
  // doesn't move are "held in committee" without a vote.
  heldLabel: "Held in committee",
  heldTip: "Kept in committee without a vote. Most are bills that cost money, held on the Appropriations Committee's “suspense file,” where hundreds are decided in one hearing. In practice the bill is dead.",
  heldNote: "kept in committee without a vote, most of them on the Appropriations Committee's “suspense file”; in practice these bills are dead.",

  // The note above the bill list between the Legislature's working months (empty while it meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y), last1 = STATE.lastDay(y);
    if (t > last1 && t < `${y + 1}-01-01`) {
      const due = STATE.plus(last1, 30);
      return `The Legislature is on its fall recess until January.${t <= due ? ` The governor has until ${fmtDate(due)} to act on the bills it passed in September.` : ""} Bills still in their own house can move again in January, until ${fmtDate(`${y + 1}-01-31`)}.`;
    }
    if (t <= end) return "";
    const next = y + 2, opens = STATE.opens(next);
    const gov = t <= `${y + 1}-09-30` ? ` The governor has until ${fmtDate(`${y + 1}-09-30`)} to act on the last bills.` : "";
    return `Floor votes for the ${STATE.sessionLabel(y)} session ended ${fmtDate(end)}.${gov} The ${STATE.sessionLabel(next)} session begins ${fmtDate(opens)}, when new legislators take office and bills can be introduced. Now is the time to ask your legislators to introduce a bill: most are introduced by late February.`;
  },
  upcomingNotice: (raw, cur) => `The ${STATE.sessionLabel(raw.session)} session began ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced; committees start hearing them in the spring. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: the Legislature's and the governor's bars ([class, from, to, text]), the events marked on
  // it ([date, "up"/"down", row, when, text]; rows are LEG = 112, GOV = 150) and a note.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, last1 = STATE.lastDay(Y), last2 = STATE.lastDay(Y + 1), due1 = STATE.plus(last1, 30);
    return {
      leg: [["", `${Y}-01-01`, last1, "In session"], ["light", last1, `${Y + 1}-01-05`, "Recess"],
        ["", `${Y + 1}-01-05`, last2, "In session"]],
      gov: [["light", `${Y}-01-01`, last1, "12 days a bill"], ["", last1, due1, "30 days"],
        ["light", `${Y + 1}-01-05`, last2, "12 days a bill"], ["", last2, `${Y + 1}-09-30`, "Sept. 30"]],
      events: [
        [`${Y}-01-05`, "up", LEG, `January ${Y}`, "Session begins (new bills since December). Bills are introduced until late February."],
        [STATE.originBy(Y), "down", LEG, MD(STATE.originBy(Y)), "Last day for each house to pass its own bills this year."],
        [last1, "up", LEG, MD(last1), "Last floor votes of the year, then the fall recess."],
        [`${Y + 1}-01-31`, "down", LEG, "January 31", "Last day for last year's bills to pass their own house."],
        [STATE.originBy(Y + 1), "up", LEG, MD(STATE.originBy(Y + 1)), "Last day for each house to pass its own bills."],
        [last2, "down", LEG, "August 31", "Last floor votes of the session. Bills that didn't pass die."],
        [`${Y + 1}-09-30`, "down", GOV, "September 30", "Last day for the governor to act."],
      ],
      note: "Once a bill reaches the governor, there are 12 days to sign or veto it; for bills passed at the end of each year, until mid-October (first year) or September 30 (second year). Overriding a veto takes two-thirds of each house, which almost never happens. New laws usually take effect January 1.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `floor votes end on August 31, ${s + 1}`,

  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    prefiled: {
      pipe: ["Introduced", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["Introduced", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["Introduced", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. Bills that cost money also go to the Appropriations Committee. Most bills that die, die in committee.",
    "A committee approved it, and it's waiting for a vote of the full Assembly or Senate.",
    "Passed the Assembly or the Senate, but not both. Both houses have to pass the same text; if the second house amends it, the first has to agree.",
    "Passed both houses and on its way to the governor.",
    "Passed both houses and sent to the governor, who has 12 days to sign or veto it (longer at the end of each year).",
    "Signed into law and given a chapter number.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house, which almost never happens.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the Assembly or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This two-year session is over. Bills that didn't become law have to be introduced again in the next session.",

  // Committees in the two houses that cover the same subject (Senate name -> [Assembly name, label]).
  commPairs: {
    "Budget and Fiscal Review": ["Budget", "Budget"],
    "Environmental Quality": ["Environmental Safety and Toxic Materials", "Environment"],
    "Natural Resources and Water": ["Natural Resources", "Natural resources and water"],
    "Energy, Utilities and Communications": ["Utilities and Energy", "Energy and utilities"],
    "Labor, Public Employment and Retirement": ["Labor and Employment", "Labor and public employees"],
    "Business, Professions and Economic Development": ["Business and Professions", "Business and professions"],
    "Insurance, Banking and Financial Institutions": ["Insurance", "Insurance and banking"],
    "Governance and Finance": ["Revenue and Taxation", "Taxes and local finance"],
    "Housing": ["Housing and Community Development", "Housing"],
    "Elections and Constitutional Amendments": ["Elections", "Elections"],
    "Privacy, Digital Technologies, and Consumer Protection": ["Privacy and Consumer Protection", "Privacy and consumer protection"],
  },
  commNotes: {
    "appropriations": "Bills that cost money come here after their subject committee. Most are put on the “suspense file” and decided together in one hearing in May (bills in their own house) or August (bills from the other house).",
  },
  moneyCommittees: { S: "Appropriations", A: "Appropriations" },
  secondCommittee: "Bills that cost money also go to the Appropriations Committee, which decides most of them on its suspense file.",
};
