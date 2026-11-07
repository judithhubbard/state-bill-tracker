// Utah: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ut",
  name: "Utah",
  abbr: "UT",
  // Steps that aren't news on a watchlist card.
  routine: /^(Bill Numbered|Numbered Bill|LFA\/|(?:House|Senate)\/ (?:received|to (?:Senate|House|Printing)|enrolled bill|circled|uncircled|placed on|signed by)|Bill Received|Draft of Enrolled|Enrolled Bill|(?:House|Senate)\/ (?:committee report|comm rpt)|PLACED ON FLOOR|ENROLLED)/i,
  publicSite: "https://statebilltracker.org/ut/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  // Joint resolutions proposing constitutional amendments pass once, by two-thirds of each house's members, then go to
  // the voters at the next general election (November of an even year); never to the governor (Utah Constitution,
  // Art. XXIII, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://governor.utah.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Salt Lake City <a class="phone" href="tel:+18015381000" data-contact="call|governor">(801) 538-1000</a>`,

  // The Legislature's bill page (numbers padded to four digits: HB0010).
  billUrl: (p, session = DATA.session) => `https://le.utah.gov/~${session}/bills/static/${p.replace(/\d+$/, (n) => n.padStart(4, "0"))}.html`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, votes and fiscal note`)).join("<br>");
  },

  // The general session opens the third Tuesday of January and lasts 45 days (Utah Constitution, Art. VI, sec. 16).
  // `dated` holds a year whose last day differs.
  dated: {},
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => STATE.nth(year, 1, 2, 3),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 45),
  // The governor has 10 days (Sundays excepted) during the session, and 20 days after it adjourns (Art. VII, sec. 8).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const plus = (from, n, sundays) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (sundays || t.getDay() !== 0) n--; } return ymd(t); };
    const end = STATE.sessionEnds(+iso.slice(0, 4)), ten = plus(iso, 10, false);
    return ten <= end ? ten : plus(end > iso ? end : iso, 20, true);
  },
  dueLabel: () => "Governor's decision due (10 days during the session, 20 days after it)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the Speaker and the Senate President, then go to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate President sign it, and it goes to the governor, who can sign it or veto it (or veto items in a budget bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://le.utah.gov/GIS/findDistrict.jsp",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // Each house's Rules Committee decides which bills go to a committee for a hearing, and later which reach the floor.
  gates: { H: "Rules", S: "Rules" },
  committeeNext: { "Rules": "the Rules Committee decides whether to send it to a committee for a hearing, or on to the floor." },
  chairAsks: { "Rules": ["send it to a committee for a hearing", "keep it in the Rules Committee"] },
  heldLabel: "Held in committee",
  heldTip: "The committee held it, tabled it or didn't take it up, so it never got a recommendation.",
  heldNote: "held, tabled or not considered by the committee; the bill stays there unless the committee takes it up again.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, "General session"]],
      gov: [["light", open, adj, "10 days a bill"], ["", adj, due, "20 days"]],
      events: [
        [open, "up", LEG, MD(open), "The 45-day general session opens."],
        [adj, "down", LEG, MD(adj), "The session adjourns. Bills that didn't pass both houses die."],
        [`${Y}-05-01`, "down", LEG, "May", "Most new laws take effect in early May, 60 days after the session ends."],
      ],
      note: "During the session the governor has 10 days (Sundays excepted) to act on a bill; bills that arrive at the end get 20 days after adjournment, and become law unless vetoed. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house, and the Legislature can call itself back to do it.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill starts in the Rules Committee.", "Each house's Rules Committee, which the leaders control, decides which bills go to a standing committee for a hearing, and later which reach the floor. Many bills wait there."],
    ["Committees hear bills on their subject.", "A standing committee takes public comment and votes to recommend a bill (favorably, with amendments, or as a substitute), or holds it."],
    ["Many bills come from interim committees.", "Between sessions, interim committees of both houses study issues and recommend bills for the next session."],
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
    "In the Rules Committee or a standing committee. Rules decides whether a bill gets a hearing; the standing committee takes public comment and votes on whether to recommend it.",
    "A committee recommended it, and it's on the House or Senate calendar (or back in Rules, which decides which bills reach the floor).",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate President sign it, then it goes to the governor.",
    "Sent to the governor, who has 10 days (Sundays excepted) during the session or 20 days after it.",
    "Signed into law (or became law without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of the Rules Committee or a standing committee before the session adjourned.",
    "A committee recommended it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: {},
  secondCommittee: "",
};
