// New Jersey: the page's settings and rules that are particular to this state. build_data.py puts
// this file into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  // The public site, and the Worker that keeps published watchlists (none yet for New Jersey).
  publicSite: "https://statebilltracker.org/nj/",
  listsApi: "",
  houses: { S: "Senate", A: "Assembly" },
  // How a session is written: 2026–27.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // The governor's office, wherever it's the one to contact.
  govReach: `<a href="https://www.nj.gov/governor/" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · <a class="phone" href="tel:+16092926000" data-contact="call|governor">(609) 292-6000</a>`,

  billUrl(p, session = DATA.session) {
    return `https://www.njleg.gov/bill-search/${session}/${p}`;
  },
  textLinks(b) {
    // The Legislature's bill page has each version's text and statements.
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)} on the Legislature's site: text and statements`)).join("<br>");
  },

  // A two-year session ends the second Tuesday of January after its second year (YYYY-MM-DD).
  sessionEnds(session) {
    const jan1 = new Date(session + 2, 0, 1).getDay();
    return `${session + 2}-01-${String(1 + ((9 - jan1) % 7) + 7).padStart(2, "0")}`;
  },
  // The governor has 45 days after a bill is presented (NJ Constitution, Art. V, sec. I, para. 14).
  // The data has no presentation date, so this counts from the day it passed both houses. When the
  // session ends first, the governor has until the seventh day after, or the bill dies (a pocket veto).
  govDeadline(iso, session) {
    if (!iso) return null;
    const ymd = (dt) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
    const [y, m, d] = iso.split("-").map(Number);
    const [ey, em, ed] = STATE.sessionEnds(session).split("-").map(Number);
    const due = ymd(new Date(y, m - 1, d + 45)), last = ymd(new Date(ey, em - 1, ed + 7));
    return due < last ? due : last;
  },

  // Bills that passed both houses go straight to the governor; any others die when the session ends.
  passedBothBy: (session) => STATE.sessionEnds(session),
  // The line under "Passed both houses", in the stage list and (with the bill) in its row. Most bills
  // here were sent back with the governor's changes (a conditional veto).
  passedBothNote: (live, b) => !live ? "Never sent to the governor"
    : !b ? "Includes bills sent back with the governor's changes"
    : b.vers.some((v) => v.actions.some(([, t]) => t === "CONDITIONALLY VETOED")) ? "Sent back with the governor's changes" : "Not yet sent to the governor",
  passedBothGroup: ["Before the session ends", () => "These go to the governor once they pass both houses. Any still waiting die when the two-year session ends in January."],

  // The governor's deadline in a bill's key dates (from govDeadline()).
  dueLabel: () => "Governor's decision due (estimated: 45 days after it passed both houses, or a week after the session ends)",
  // What happens to a bill that passed both houses: the line under "Next:", and the asks (support, oppose).
  // A bill sent back with the governor's changes needs both houses to accept them, one after the other:
  // the house it's been delivered to since votes now.
  passedBothNext(b) {
    const acts = b.vers.flatMap((v) => v.actions).sort((x, y) => (x[0] < y[0] ? -1 : 1));
    const cv = acts.map(([, t]) => t).lastIndexOf("CONDITIONALLY VETOED");
    if (cv < 0) return {
      what: "it goes to the governor, who then has 45 days to sign it, veto it, or send it back with changes.",
      gov: ["sign it", "veto it"],
      reps: ["urge the governor to sign it", "urge the governor to veto it"],
    };
    const after = acts.slice(cv).map(([, t]) => t);
    const now = [...after].reverse().find((t) => t.startsWith("DELIVERED TO "))?.endsWith("ASSEMBLY") ? "A" : "S";
    const other = now === "S" ? "A" : "S", done = after.some((t) => t === `REPASSED ${STATE.houses[other].toUpperCase()}`);
    return {
      what: done ? `the ${STATE.houses[now]} votes on the governor's changes; the ${STATE.houses[other]} already accepted them. Then it goes back to the governor to sign.`
        : `the ${STATE.houses[now]} votes on the governor's changes, then the ${STATE.houses[other]}. If both accept them, it goes back to the governor to sign.`,
      leaders: [now],
      leaderAsk: ["bring it to a vote to accept the governor's changes", "keep it from coming to a vote"],
      reps: ["vote to accept the governor's changes", "vote no"],
    };
  },

  // The Legislature meets, with long breaks, until the session's last day in January.
  floorVotesEnd: false,

  // Stage names (the stage numbers are build_data.py's), and their tips.
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
    "Waiting in a committee. Most bills never get out of committee.",
    "A committee approved it, and it's waiting for a vote of the full Senate or Assembly. Leaders decide which bills get a vote.",
    "Passed the Senate or the Assembly, but not both. Both houses have to pass the same text.",
    "Passed both houses. A bill the governor sent back with changes (a conditional veto) waits here until both houses vote to accept them.",
    "Passed both houses and sent to the governor, who has 45 days to sign it, veto it, or send it back with changes.",
    "Signed into law and given a chapter number.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house, which is rare.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the Senate or the Assembly, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This two-year session is over. Bills that didn't become law have to be reintroduced in the next session.",

  // How a bill becomes law: committees in the two houses that cover the same subject (Senate name ->
  // [Assembly name, label]), notes on some, and which bills need a second committee.
  commPairs: {
    "Budget and Appropriations": ["Appropriations", "Budget and spending"],
    "Environment and Energy": ["Environment and Solid Waste", "Environment and energy"],
    "Health, Human Services and Senior Citizens": ["Health", "Health and human services"],
    "Law and Public Safety": ["Public Safety and Preparedness", "Public safety"],
    "Transportation": ["Transportation and Independent Authorities", "Transportation"],
    "Community and Urban Affairs": ["Housing", "Housing and urban affairs"],
    "State Government, Wagering, Tourism & Historic Preservation": ["State and Local Government", "State and local government"],
    "Commerce": ["Commerce and Economic Development", "Business"],
    "Economic Growth": ["Commerce and Economic Development", "Business"],
  },
  commNotes: {
    "budget and spending": "Bills that cost the state money often come here after their subject committee.",
  },
  // The committees bills that cost money go to after their subject committee.
  moneyCommittees: { S: "Budget and Appropriations", A: "Appropriations" },
  secondCommittee: "Bills that cost money often go to Assembly Appropriations or Senate Budget and Appropriations after their subject committee.",
  // The two-year calendar: the Legislature's and the governor's bars ([class, from, to, text]), the
  // events marked on it ([date, "up"/"down", row, when, text]; rows are LEG = 112, GOV = 150) and a
  // note. It runs into January of the third year, when the session ends.
  calendarDays: 20,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.sessionEnds(Y - 2), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-06-30`, "In session"], ["light", `${Y}-07-01`, `${Y}-08-31`, "Summer"],
        ["", `${Y}-09-01`, `${Y + 1}-06-30`, "In session"], ["light", `${Y + 1}-07-01`, `${Y + 1}-11-10`, "Campaigns"],
        ["", `${Y + 1}-11-10`, close, "Rush"]],
      gov: [["", open, `${Y + 2}-01-20`, "Signs or vetoes each bill within 45 days, all year"]],
      events: [
        [open, "up", LEG, `January ${Y}`, "Session opens. Committees meet and bills pass all year, except in summer."],
        [`${Y}-04-15`, "down", LEG, "April", "Committees mostly pause for budget hearings."],
        [`${Y}-06-30`, "up", LEG, "June 30", "Each year's budget is due, and many bills pass in the last weeks of June."],
        [`${Y}-11-01`, "down", LEG, "September to December", "Committees and floor votes start again after the summer break."],
        [`${Y + 1}-10-01`, "down", LEG, "July to November", "Hardly any meetings while legislators campaign for the November election."],
        [close, "up", LEG, `January ${Y + 2}`, "The busiest weeks of the session, then it ends. Bills that aren't law die."],
      ],
      note: "Once a bill reaches the governor, there are 45 days to sign it, veto it, or send it back with changes. Bills passed at the very end have until a week after the session ends; any left unsigned die (a pocket veto).",
    };
  },
};
