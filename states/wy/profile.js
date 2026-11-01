// Wyoming: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "wy",
  name: "Wyoming",
  abbr: "WY",
  // Steps that aren't news on a watchlist card.
  routine: /^(Bill Number Assigned|[HS] Received for (?:Introduction|Concurrence)|[HS] Placed on General File|[HS] COW:Passed|[HS] 2nd Reading:Passed|[HS] (?:Speaker|President) Signed|Assigned Number|Assigned Chapter Number|[HS] Appointed JCC|[HS] (?:2nd|3rd) Reading:Laid Back|PLACED ON FLOOR|ENROLLED)/i,
  publicSite: "https://statebilltracker.org/wy/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  // Joint resolutions proposing constitutional amendments pass once, by two-thirds of each house's members, then go to
  // the voters at the next general election (November of an even year); never to the governor (Wyoming Constitution,
  // Art. 20, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://governor.wyo.gov/contact/governor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Cheyenne <a class="phone" href="tel:+13077777434" data-contact="call|governor">(307) 777-7434</a>`,

  // The Legislature's bill page (numbers padded to four digits: HB0010).
  billUrl: (p, session = DATA.session) => `https://wyoleg.gov/Legislation/${session}/${p.replace(/\d+$/, (n) => n.padStart(4, "0"))}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, votes and fiscal note`)).join("<br>");
  },

  // A general session in odd years opens the second Tuesday of January and lasts at most 40 legislative days (early
  // March); a budget session in even years opens the second Monday of February and lasts at most 20 (early March)
  // (Wyoming Constitution, Art. 3, sec. 6, and W.S. 28-1-101). `dated` holds a year whose last day differs.
  dated: { 2024: "2024-03-08", 2025: "2025-03-06", 2026: "2026-03-06" },
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => year % 2 ? STATE.nth(year, 1, 2, 2) : STATE.nth(year, 2, 1, 2),
  sessionEnds(year) {
    if (STATE.dated[year]) return STATE.dated[year];
    const [y, m, d] = STATE.opens(year).split("-").map(Number), t = new Date(y, m - 1, d + (year % 2 ? 51 : 25));
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The governor has 3 days (Sundays excepted) during the session; a bill the session's end keeps from being returned
  // becomes law unless vetoed within 15 days after adjournment (Art. 4, sec. 8).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const plus = (from, n, sundays) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (sundays || t.getDay() !== 0) n--; } return ymd(t); };
    const end = STATE.sessionEnds(+iso.slice(0, 4)), three = plus(iso, 3, false);
    return three <= end ? three : plus(end > iso ? end : iso, 15, true);
  },
  dueLabel: () => "Governor's decision due (3 days during the session, 15 days after it)",

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
  findReps: "https://wyoleg.gov/Legislators",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // In budget sessions (even years) a bill other than the budget needs two-thirds of its house to be introduced.
  heldAction: "FAILED INTRODUCTION",
  heldLabel: "Not introduced",
  heldTip: "Never introduced: it missed the vote or the deadline for introduction. In a budget session (even years) a bill other than the budget needs two-thirds of its house to be introduced.",
  heldNote: "never introduced: in a budget session a bill other than the budget needs a two-thirds vote to be introduced, and in a general session bills not introduced by the deadline die.",

  // Even years' budget sessions have far fewer bills: say so, so the counts don't look wrong.
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    const short = y % 2 ? "" : ` It was a budget session: 20 days, and bills other than the budget needed two-thirds of a house to be introduced, so there are far fewer bills than in a general session.`;
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.${short}`;
    if (!(y % 2) && t <= end)
      return `${y} is a budget session: 20 days, and bills other than the budget need two-thirds of a house to be introduced.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, Y % 2 ? "General session" : "Budget session"]],
      gov: [["light", open, adj, "3 days a bill"], ["", adj, due, "15 days"]],
      events: [
        [open, "up", LEG, MD(open), Y % 2 ? "The general session opens (40 legislative days at most)." : "The budget session opens (20 legislative days at most)."],
        [adj, "down", LEG, MD(adj), "The session adjourns. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "July 1", "Many new laws take effect."],
      ],
      note: "During the session the governor has 3 days (Sundays excepted) to act on a bill; bills that arrive at the end get 15 days after adjournment, and become law unless vetoed. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  // Each house has twelve standing committees with the same numbers and subjects (H09 and S09 are both Minerals).
  commIntro: [
    ["Every bill starts in a committee on its subject.", "Each house has twelve standing committees, numbered the same in both (01 Judiciary, 02 Appropriations, 03 Revenue and so on). The Speaker or the Senate President picks the committee."],
    ["Many bills come from the interim committees.", "Between sessions, joint interim committees of both houses study issues and sponsor bills, which often pass more easily."],
    ["Sessions move fast.", "Committees have to report bills by a cutoff before the Committee of the Whole; a bill with no report by then dies."],
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
    "Waiting to be introduced, or in a committee, which takes public comment and votes on whether to recommend it.",
    "A committee recommended it. The full house debates it in the Committee of the Whole, then votes on second and third reading.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate President sign it, then it goes to the governor.",
    "Sent to the governor, who has 3 days during the session or 15 days after it.",
    "Signed into law (or became law without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never introduced, or never got out of committee before the session adjourned.",
    "A committee recommended it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that spend money often go on to the Appropriations Committee.",
};
