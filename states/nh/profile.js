// New Hampshire: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "nh",
  // What the Legislature is called in sentences ("the General Court isn't meeting until ...").
  bodyName: "the General Court",
  name: "New Hampshire",
  abbr: "NH",
  // Steps that aren't news on a watchlist card.
  routine: /^(==\w+== |(?:Public )?Hearing|Executive Session|(?:Full Committee|Subcommittee|Division \w*) Work Session|Minority Committee Report|Speaker Appoints|President Appoints|Conferee Change|Conference Committee Meeting|Committee of Conference Meeting|Without Objection|Special Order|Pending Motion|Referral Waived|Sen\. \w+ Moved Laid on Table|Enrolled Bill Amendment|ENROLLED)/i,
  publicSite: "https://statebilltracker.org/nh/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year (each General Court spans two); a bill dies with its year unless a committee keeps it over.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are numbered by chapter: "Chapter 74, Laws of 2025".
  lawWord: "Chapter",
  // A CACR (constitutional amendment concurrent resolution) passes once, by three-fifths of each house's members, then
  // goes to the voters at the next general election (November of an even year), where it needs two-thirds of the votes
  // cast; never to the governor (New Hampshire Constitution, Part II, Art. 100).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "three-fifths of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://www.governor.nh.gov/contact" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Concord <a class="phone" href="tel:+16032712121" data-contact="call|governor">(603) 271-2121</a>`,

  // The General Court's bill search for one year and number (a CACR without its house letter: "HCACR1" is CACR 1).
  billUrl: (p, session = DATA.session) => `https://gc.nh.gov/bill_status/legacy/bs2016/results.aspx?txtsessionyear=${session}&txtbillnumber=${p.replace(/^[HS](?=CACR)/, "")}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p.replace(/^[HS](?=CACR)/, ""))}: status, text, docket and roll calls`)).join("<br>");
  },
  // A bill a committee kept over ("Retained in Committee" in the House, "Rereferred to Committee, MA" in the Senate) in
  // the first year of the General Court continues in the second.
  continuedTo(b) {
    if (!(DATA.session % 2)) return null;
    const kept = b.vers.some((v) => v.actions.some(([d, t]) => String(d).startsWith(String(DATA.session)) && /^(Retained in Committee|Rereferred to Committee, MA)/.test(t)));
    return kept ? DATA.session + 1 : null;
  },

  // The session opens the first Wednesday after New Year's Day (the House and Senate meet only a day or two a week) and
  // ends by June 30 (the General Court's joint rules; members are paid for 45 legislative days a year). `opened` and
  // `dated` hold the actual first and last days of floor votes on bills (veto days come later, in the fall).
  opened: { 2023: "2023-01-04", 2024: "2024-01-03", 2025: "2025-01-08", 2026: "2026-01-07" },
  dated: { 2023: "2023-06-29", 2024: "2024-06-13", 2025: "2025-06-26", 2026: "2026-06-04" },
  opens(year) {
    if (STATE.opened[year]) return STATE.opened[year];
    const t = new Date(year, 0, 2); while (t.getDay() !== 3) t.setDate(t.getDate() + 1);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || `${year}-06-30`,
  plusDays(iso, n, sundays = true) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d);
    while (n > 0) { t.setDate(t.getDate() + 1); if (sundays || t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The governor has 5 days (Sundays excepted) after a bill is presented to sign or veto it; otherwise it becomes law
  // without a signature, unless the General Court has adjourned and kept it from being returned (a pocket veto; Part II,
  // Art. 44). The records show when both houses adopted the enrolled bill, not when it was presented, which can be weeks
  // later, so this is the earliest the deadline could be.
  govDeadline: (iso) => (iso ? STATE.plusDays(iso, 5, false) : null),
  dueLabel: () => "Governor's decision due (5 days, Sundays excepted, after it's presented; the earliest it could be)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the Speaker and the Senate President, and presented to the governor."],
  passedBothNext: () => ({
    what: "both houses adopt the enrolled bill, and it goes to the governor, who has 5 days (Sundays excepted) to sign it or veto it. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  // "Where you live" picks a town or a city ward: its senator, and every House district it votes in.
  townWord: "Town or city ward",
  // A place's House districts all represent it: its own and a "floterial" district over it and its neighbors.
  townInAllDistricts: true,
  oneNumber: true,
  diesAfterFloor: (y2, b) => (b && STATE.continuedTo(b) ? `It was kept over to the ${STATE.continuedTo(b)} session, where it can be taken up again.`
    : "The session is over, so it died. It would have to be introduced again in a later session."),
  outOfTimeLine: "Died when the session ended",

  // The House or Senate voting a bill down: adopting a committee's "inexpedient to legislate" (ITL) or "interim study"
  // report, or indefinitely postponing it. Either ends the bill for the year.
  heldAction: /^(?:Inexpedient to Legislate|Indefinitely Postpone|Refer(?:red)? (?:for|to) Interim Study)\b(?:.*[:,;]\s*MA\b|, Senate Rule)/,
  heldLabel: "Killed",
  heldTip: "Voted down by the House or Senate: it adopted a committee's \"inexpedient to legislate\" or \"interim study\" report. Either ends the bill for the year.",
  heldNote: "voted down by the House or Senate (\"inexpedient to legislate\" or interim study); either ends the bill for the year.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return y % 2
        ? `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass died, except those a committee kept over to ${y + 1}; the ${y + 1} session opens in early January.`
        : `The ${y} session ended ${fmtDate(end)}, and with it this General Court. Bills that didn't pass died; the new General Court meets in early January.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens in early January. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, Y % 2 ? "Session (budget year)" : "Session"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, STATE.plusDays(due, 30), "Last bills"]],
      events: [
        [open, "up", LEG, MD(open), `The ${Y} session opens.`],
        [adj, "down", LEG, MD(adj), `The last floor votes on bills (the session must end by June 30).${Y % 2 ? " Bills a committee kept over carry to next year." : " The General Court ends with the year."}`],
        [`${Y}-10-15`, "down", LEG, "Fall", "Veto day: the House and Senate vote on overriding the governor's vetoes."],
      ],
      note: "The governor has 5 days (Sundays excepted) after a bill is presented to sign or veto it; a bill the governor doesn't act on becomes law. There's no line-item veto. Overriding a veto takes two-thirds of the members present in each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Court's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill gets a hearing and a committee vote.", "New Hampshire's committees must report every bill referred to them: \"ought to pass\" (often with an amendment), \"inexpedient to legislate\" (kill it), \"interim study\", or, in the first year of a General Court, \"retained\" or \"re-referred\" to keep working on it into the second."],
    ["The full House or Senate then votes on the report.", "The committee's report goes to the floor, usually on a consent calendar when the committee agreed; the house can adopt it or overturn it."],
    ["Bills that cost money go to a second committee.", "A House bill that spends money goes on to Finance, one that changes taxes or fees to Ways and Means; the Senate sends such bills to Finance or Ways and Means."],
  ],
  stageText: {
    live: {
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
  stageTips: [
    "In a committee, or voted down on its report (\"Killed\"). The committee holds a hearing and recommends what the full house should do.",
    "The committee has reported it, and the full House or Senate hasn't voted on the report yet.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, signed by the Speaker and the Senate President, and presented to the governor.",
    "Sent to the governor, who has 5 days (Sundays excepted) to sign or veto it; if the governor does neither, it becomes law.",
    "Signed into law (or became law without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of the members present in each house.",
  ],
  pastStageTips: [
    "Voted down, kept in committee, or never reported before the session ended.",
    "A committee reported it, but the full house never voted on the report (often left on the table).",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session, unless a committee kept them over to the next year.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Health and Human Services": ["Health, Human Services and Elderly Affairs", "Health and human services"],
    "Energy and Natural Resources": ["Science, Technology and Energy", "Energy"],
    "Commerce": ["Commerce and Consumer Affairs", "Commerce"],
    "Election Law and Municipal Affairs": ["Election Law", "Elections"],
    "Education": ["Education Policy and Administration", "Education"],
    "Education Finance": ["Education Funding", "School funding"],
    "Public and Municipal Affairs": ["Municipal and County Government", "Local government"],
    "Capital Budget": ["Public Works and Highways", "Capital budget"],
    "Rules and Enrolled Bills": ["Rules", "Rules"],
  },
  commNotes: {},
  moneyCommittees: { S: "Finance", H: "Finance" },
  secondCommittee: "House bills that spend money go on to Finance, and bills that change taxes or fees to Ways and Means; the Senate sends such bills to Finance or Ways and Means.",
};
