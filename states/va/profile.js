// Virginia: the page's settings and rules that are particular to this state. build_data.py puts this file
// into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
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

  // The day each regular session adjourned (or is scheduled to).
  adjourned: { 2024: "2024-03-09", 2025: "2025-02-22", 2026: "2026-03-14", 2027: "2027-02-27" },
  sessionEnds: (session) => STATE.adjourned[session] || `${session}-03-01`,
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
  diesAfterFloor: () => "The session is over, so it died with it.",
  outOfTimeLine: "Died when the session ended",

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
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
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
