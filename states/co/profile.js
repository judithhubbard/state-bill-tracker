// Colorado: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "co",
  name: "Colorado",
  abbr: "CO",
  // Steps that aren't news on a watchlist card.
  routine: /^((?:House|Senate) (?:Second|Third) Reading (?:Special Order - )?Laid Over|(?:House|Senate) Committee of the Whole Amendment|PLACED ON FLOOR|ENROLLED)/i,
  publicSite: "https://statebilltracker.org/co/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  // Concurrent resolutions proposing constitutional amendments aren't in the download (it reads bills only).
  govReach: `<a href="https://governor.colorado.gov/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Constituent services <a class="phone" href="tel:+13038662885" data-contact="call|governor">(303) 866-2885</a>`,

  // The General Assembly's bill page: "HB25-1001".
  billUrl: (p, session = DATA.session) => `https://leg.colorado.gov/bills/${p.slice(0, 2)}${String(session).slice(2)}-${p.slice(2)}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, votes, fiscal notes and summary`)).join("<br>");
  },

  // The regular session opens the second Wednesday of January and lasts at most 120 days (Colorado Constitution, Art. V,
  // sec. 7). `dated` holds a year whose last day differs.
  dated: {},
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => STATE.nth(year, 1, 3, 2),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 119),
  // The governor has 10 days (Sundays excepted) during the session, and 30 days after it adjourns (Art. IV, sec. 11).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const plus = (from, n, sundays) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (sundays || t.getDay() !== 0) n--; } return ymd(t); };
    const end = STATE.sessionEnds(+iso.slice(0, 4)), ten = plus(iso, 10, false);
    return ten <= end ? ten : plus(end > iso ? end : iso, 30, true);
  },
  dueLabel: () => "Governor's decision due (10 days during the session, 30 days after it)",

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
  findReps: "https://leg.colorado.gov/find-my-legislator",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  heldLabel: "Laid over",
  heldTip: "The committee laid it over without a vote; near the end of the session that ends it.",
  heldNote: "laid over by the committee without a vote; near the end of the session that ends the bill.",

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
      leg: [["", open, adj, "Regular session"]],
      gov: [["light", open, adj, "10 days a bill"], ["", adj, due, "30 days"]],
      events: [
        [open, "up", LEG, MD(open), "The 120-day regular session opens."],
        [adj, "down", LEG, MD(adj), "The session adjourns. Bills that didn't pass both houses die."],
        [STATE.plusDays(adj, 91), "down", LEG, MD(STATE.plusDays(adj, 91)), "Most new laws take effect, 90 days after the session ends."],
      ],
      note: "During the session the governor has 10 days (Sundays excepted) to act on a bill; bills that arrive at the end get 30 days after adjournment, and become law unless vetoed. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill gets a hearing.", "Colorado's committees of reference must hear every bill referred to them. The Speaker or the Senate President picks the committee."],
    ["Committees vote bills up or down.", "A committee refers a bill on (to another committee or the floor), lays it over, or kills it by \"postponing it indefinitely\"."],
    ["Bills that cost money go to Appropriations.", "Bills with a cost go on to the Appropriations Committee, which many hold until the budget is set late in the session."],
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
    "In a committee, which hears it and votes to refer it on, or kills it by postponing it indefinitely.",
    "A committee sent it to the floor. The full house debates and amends it on second reading, then votes on third reading.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate President sign it, then it goes to the governor.",
    "Sent to the governor, who has 10 days (Sundays excepted) during the session or 30 days after it.",
    "Signed into law (or became law without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Killed or laid over in committee, or never acted on before the session adjourned.",
    "A committee recommended it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that cost money go on to the Appropriations Committee.",
};
