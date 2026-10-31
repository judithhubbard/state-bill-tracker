// Wisconsin: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "wi",
  name: "Wisconsin",
  abbr: "WI",
  // Steps that aren't news on a watchlist card.
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced by|Representatives? |Senators? |Fiscal estimate received|Received from (?:Assembly|Senate)$|Ordered immediately messaged|Rules suspended|LRB correction|Published|Made a special order|Laid on the table|Ordered to a third reading|Report correctly enrolled|(?:Assembly|Senate) (?:Substitute )?Amendment \d+ offered)/i,
  publicSite: "https://statebilltracker.org/wi/",
  listsApi: "",
  houses: { S: "Senate", A: "Assembly" },
  titles: { S: "Sen.", A: "Rep." },
  memberWords: { S: "state senator", A: "state representative" },
  greetings: { S: "Senator", A: "Representative" },
  // How a session is written: 2025–26.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // A law's number: "2025 Wisconsin Act 12".
  lawWord: "Act",
  govReach: `<a href="https://wi.accessgov.com/public/Forms/Page/governor/voice-an-opinion" target="_blank" rel="noopener" data-contact="online|governor">Share your opinion with the governor</a> · Madison <a class="phone" href="tel:+16082661212" data-contact="call|governor">(608) 266-1212</a>`,

  // The Legislature's bill page (history, text, analysis, votes).
  billUrl: (p, session = DATA.session) => `https://docs.legis.wisconsin.gov/${session}/proposals/${p.toLowerCase()}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: history, text, analysis and votes`)).join("<br>");
  },

  // A session convenes in January of an odd year; the Legislature meets in floor periods, the last for general business
  // in the spring of the second year, when bills still pending fail (the date is set each session by joint resolution;
  // the ones past are from the bills' histories).
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7));
    return `${session}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  dated: { 2023: "2024-04-15" },
  sessionEnds: (session) => STATE.dated[session] || `${session + 1}-04-15`,
  // The governor has 6 days, Sundays excepted, after a bill is presented (Wisconsin Constitution, Art. V, sec. 10); the
  // governor can veto parts of spending bills.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 6;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (6 days after it reached the governor, Sundays excepted)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the session ends", () => "Bills that pass both houses are enrolled, then presented to the governor."],
  passedBothNext: () => ({
    what: "it's enrolled and presented to the governor, who has 6 days to sign it, veto it, or veto parts of a spending bill. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, village or town",
  addressLookup: true,
  findReps: "https://maps.legis.wisconsin.gov/",
  oneNumber: true,
  diesAfterFloor: () => "The session's last floor period has passed, so it died.",
  outOfTimeLine: "Died when the session ended",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t > STATE.sessionEnds(y)) return `The ${span(y)} session's last floor period has ended; bills that hadn't passed both houses failed. The next Legislature convenes in January ${y + 2}.`;
    if (t.startsWith(String(y + 1)) && t.slice(5) >= "02-15")
      return `The ${span(y)} session's last floor period ends in the spring of ${y + 1}; bills that haven't passed both houses by then fail. The next Legislature convenes in January ${y + 2}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} Legislature convenes ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-06-30`, "Floor periods; the budget"], ["light", `${Y}-07-01`, `${Y + 1}-01-01`, "Fall floor periods"], ["", `${Y + 1}-01-01`, close, "Last floor periods"]],
      gov: [["light", open, close, "6 days to act on each bill"]],
      events: [
        [open, "up", LEG, MD(open), "The Legislature convenes."],
        [`${Y}-06-30`, "down", LEG, "June 30", "The two-year budget is due before the fiscal year starts July 1."],
        [close, "down", LEG, MD(close), "The last general-business floor period ends; bills still pending fail."],
      ],
      note: "The governor has 6 days (Sundays excepted) to sign or veto a bill, and can veto parts of a spending bill. Overriding a veto takes two-thirds of each house. A new law takes effect the day after it's published, unless it says otherwise.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member pages",
  openUntil: (s) => `the session's last floor period, spring ${s + 1}`,

  // Each house's scheduling committee (Assembly Rules; Senate Organization) decides which bills reach the floor.
  committeeNext: {
    "Rules": "the Assembly Committee on Rules decides whether it gets a floor vote.",
    "Senate Organization": "the Committee on Senate Organization decides whether it gets a floor vote.",
  },
  chairAsks: {
    "Rules": ["schedule it for a floor vote", "keep it off the calendar"],
    "Senate Organization": ["schedule it for a floor vote", "keep it off the calendar"],
  },
  commIntro: [
    ["Every bill starts in a committee on its subject.", "The Speaker or the Senate President sends it to a standing committee; the chair decides whether it gets a public hearing and an executive session (the vote)."],
    ["Then the scheduling committees.", "A bill a committee recommends goes to the Assembly Committee on Rules or the Committee on Senate Organization, which decide which bills reach the floor."],
    ["Bills that cost money go to Joint Finance.", "The Joint Committee on Finance, with members of both houses, writes the budget and reviews bills with a cost."],
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
    "Waiting in a committee. The chair decides whether it gets a public hearing and a vote.",
    "A committee recommended it, and it waits for the Rules Committee (Assembly) or Senate Organization to put it on the calendar.",
    "Passed the Assembly or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The presiding officers sign it, then it goes to the governor.",
    "Presented to the governor, who has 6 days (Sundays excepted) to sign or veto it.",
    "Signed into law (a Wisconsin Act), sometimes with parts vetoed, or became law without the governor's signature.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the Assembly or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in the next Legislature.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Finance", A: "Finance" },
  secondCommittee: "Bills that spend money often go on to the Joint Committee on Finance.",
};
