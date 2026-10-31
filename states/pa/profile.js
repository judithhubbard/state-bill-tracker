// Pennsylvania: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "pa",
  name: "Pennsylvania",
  abbr: "PA",
  // Steps that aren't news on a watchlist card.
  routine: /^(\(Remarks see|In the (?:House|Senate)$|Laid on the table|Removed from table|Signed in (?:House|Senate)|Corrective Reprint|Undefined Action|Transmitted as directed|Act No\.|Second consideration|Third consideration$)/i,
  publicSite: "https://statebilltracker.org/pa/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  govReach: `<a href="https://www.pa.gov/governor/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Harrisburg <a class="phone" href="tel:+17177872500" data-contact="call|governor">(717) 787-2500</a>`,
  // Joint resolutions proposing constitutional amendments pass two successive sessions, then go to the voters; never
  // to the governor (Pennsylvania Constitution, Art. XI).
  amendments: true,
  // A law's number: "Act 28 of 2025".
  lawWord: "Act",

  // The General Assembly's bill page (status, text, votes, fiscal notes).
  billUrl: (p, session = DATA.session) => `https://www.palegis.us/legislation/bills/${session}/${p.toLowerCase()}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, votes and fiscal notes`)).join("<br>");
  },

  // A session convenes the first Tuesday of January of an odd year; members' terms, and the bills, end November 30
  // of the even year.
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7));
    return `${session}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => `${session + 1}-11-30`,
  // A full-time Legislature: it can vote until the session ends.
  floorVotesEnd: false,
  // The governor has 10 days, Sundays excepted, while the Legislature is in session, and 30 days after it adjourns
  // for good (Art. IV, sec. 15).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 10;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const end = STATE.sessionEnds(a % 2 ? a : a - 1);
    return ymd(t) <= end ? ymd(t) : ymd(new Date(a, b - 1, c + 30));
  },
  dueLabel: () => "Governor's decision due (10 days, Sundays excepted; 30 after the session ends)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the session ends", () => "Bills that pass both houses are signed by the Speaker and the Senate's presiding officer, then presented to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate's presiding officer sign it, and it goes to the governor, who can sign it or veto it (or veto items in a spending bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, borough or township",
  addressLookup: true,
  findReps: "https://www.palegis.us/find-my-legislator",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died with it.",
  outOfTimeLine: "Died when the session ended",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t.startsWith(String(y + 1)) && t.slice(5) >= "10-15")
      return `The ${span(y)} session ends November 30, ${y + 1}; bills that haven't passed both houses by then die. The next session convenes in January.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} session convenes ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-06-30`, "Session"], ["light", `${Y}-07-01`, `${Y}-12-31`, "Session continues"],
        ["", `${Y + 1}-01-01`, `${Y + 1}-06-30`, "Session"], ["light", `${Y + 1}-07-01`, close, "Election year: fewer session days"]],
      gov: [["light", open, close, "10 days to act on each bill"]],
      events: [
        [open, "up", LEG, MD(open), "The session convenes."],
        [`${Y}-02-04`, "up", LEG, "February", "The governor proposes the budget."],
        [`${Y}-06-30`, "down", LEG, "June 30", "The budget is due before the fiscal year starts July 1 (it's often late)."],
        [close, "down", LEG, MD(close), "The session ends. Bills that didn't become law die."],
      ],
      note: "The governor has 10 days (Sundays excepted) to sign or veto a bill, or 30 days after the session ends, and can veto items in a spending bill. Overriding a veto takes two-thirds of each house. Most new laws take effect 60 days after they're signed.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's bill records",
  openUntil: (s) => `the session ends November 30, ${s + 1}`,

  commIntro: [
    ["Every bill starts in a committee on its subject.", "The Speaker or the Senate's President Pro Tempore sends it to a standing committee of that house. The majority chair decides whether the committee takes it up."],
    ["Most bills go to Appropriations before the final vote.", "A bill a committee reports usually goes to the floor for first and second consideration, then to the Appropriations Committee, which reports it back for the final vote."],
    ["Committees have two chairs.", "Each committee has a majority chair, who runs it, and a minority chair from the other party."],
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
    "Waiting in a committee. The majority chair decides whether the committee takes it up.",
    "A committee reported it, and it waits for the full House or Senate. Bills are considered three times; most go to Appropriations before the third.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The presiding officers sign it, then it goes to the governor.",
    "Presented to the governor, who has 10 days (Sundays excepted) to sign or veto it.",
    "Signed into law (an Act), or became law without the governor's signature.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee reported it, but it never passed the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in the next one.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Most bills go to the Appropriations Committee before their final vote.",
};
