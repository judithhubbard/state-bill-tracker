// Oregon: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "or",
  name: "Oregon",
  abbr: "OR",
  // Steps that aren't news on a watchlist card.
  routine: /^(First reading|Introduction and first reading|Referred to (?:Speaker|President).s desk|Public Hearing (?:held|cancelled|Cancelled)|Work Session (?:held|cancelled)|Informational Meeting|Second reading|Carried over|Rules suspended\. Carried over|Vote explanation|Assigned to|Returned to|Effective date|Public Hearing and Work Session|Speaker signed|President signed|ENROLLED)/i,
  publicSite: "https://statebilltracker.org/or/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  govReach: `<a href="https://www.oregon.gov/gov/Pages/share-your-opinion.aspx" target="_blank" rel="noopener" data-contact="online|governor">Share your opinion with the governor</a> · Salem <a class="phone" href="tel:+15033784582" data-contact="call|governor">(503) 378-4582</a>`,

  // The Legislature's bill page (OLIS).
  billUrl: (p, session = DATA.session) => `https://olis.oregonlegislature.gov/liz/${session}R1/Measures/Overview/${p}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, votes and analyses`)).join("<br>");
  },

  // A long session in odd years opens the second Monday of January and must end within 160 days (late June); a short
  // one in even years opens the first Monday of February and lasts 35 days (Oregon Constitution, Art. IV, sec. 10).
  monday(year, month, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => year % 2 ? STATE.monday(year, 1, 2) : STATE.monday(year, 2, 1),
  sessionEnds(year) {
    const [y, m, d] = STATE.opens(year).split("-").map(Number), t = new Date(y, m - 1, d + (year % 2 ? 165 : 34));
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The governor has 5 days (Saturdays and Sundays excepted) during the session; a bill that arrives after it adjourns,
  // or too late, gets 30 business days after adjournment (Art. V, sec. 15b).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const plus = (from, n) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0 && t.getDay() !== 6) n--; } return ymd(t); };
    const end = STATE.sessionEnds(+iso.slice(0, 4)), five = plus(iso, 5);
    return five <= end ? five : plus(end > iso ? end : iso, 30);
  },
  dueLabel: () => "Governor's decision due (5 weekdays during the session, 30 business days after it)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the Speaker and the Senate President, then go to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate President sign it, and it goes to the governor, who can sign it or veto it (or veto items in a budget bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: true,
  findReps: "https://www.oregonlegislature.gov/FindYourLegislator/leg-districts.html",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again next year.",
  outOfTimeLine: "Died when the session adjourned",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, Y % 2 ? "Long session" : "Short session"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "30 business days"]],
      events: [
        [open, "up", LEG, MD(open), Y % 2 ? "The long session opens (160 days at most)." : "The short session opens (35 days)."],
        [adj, "down", LEG, MD(adj), "The session adjourns. Bills that didn't pass both houses die."],
        [`${Y + 1}-01-01`, "down", LEG, "January 1", "Many new laws take effect; others on the 91st day after adjournment."],
      ],
      note: "During the session the governor has 5 days (Saturdays and Sundays excepted) to act on a bill; bills that arrive at the end get 30 business days after adjournment. The governor can veto items in a budget bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  // Most committees belong to one house; joint committees (Ways and Means, the budget committee) have members of both.
  commIntro: [
    ["Every bill starts in a committee on its subject.", "Each house has its own committees; the Speaker or the Senate President decides where a bill goes. The committee holds a public hearing, then a work session where it votes."],
    ["Committees have deadlines.", "Each session sets dates by which committees must act on bills; a bill that misses them usually dies \"in committee upon adjournment\"."],
    ["Bills that cost money go to Ways and Means.", "The Joint Committee on Ways and Means, with members of both houses, writes the budget and decides most bills with a cost; tax bills go to the revenue committees."],
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
    "Waiting in a committee, which holds a public hearing and then votes in a work session. Bills with a cost also go to the Joint Committee on Ways and Means.",
    "A committee reported it favorably, and it's on the House or Senate calendar for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate President sign it, then it goes to the governor.",
    "Sent to the governor, who has 5 days during the session or 30 business days after it.",
    "Signed into law (or became law without the governor's signature).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session adjourned.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Ways and Means", H: "Ways and Means" },
  secondCommittee: "Bills that cost money go on to the Joint Committee on Ways and Means.",
};
