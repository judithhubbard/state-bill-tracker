// Maryland: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "md",
  name: "Maryland",
  abbr: "MD",
  // Steps that aren't news on a watchlist card.
  routine: /^(Hearing|First reading|Second reading)/i,
  publicSite: "https://statebilltracker.org/md/",
  listsApi: "",
  houses: { S: "Senate", H: "House of Delegates" },
  titles: { S: "Sen.", H: "Del." },
  memberWords: { S: "state senator", H: "delegate" },
  greetings: { S: "Senator", H: "Delegate" },
  // One 90-day session a year; bills die when it ends.
  years: 1,
  // Constitutional amendments pass both houses once, by three-fifths, then go to the voters at the next general
  // election (even years); never to the governor (Maryland Constitution, Art. XIV).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "both houses by three-fifths",
  ballotEvenYears: true,
  sessionLabel: (s) => String(s),
  govReach: `<a href="https://md.accessgov.com/governor/Forms/Page/cs/contact-the-governor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Annapolis <a class="phone" href="tel:+14109743901" data-contact="call|governor">(410) 974-3901</a> · toll-free <a class="phone" href="tel:+18008118336" data-contact="call|governor">(800) 811-8336</a>`,

  // The General Assembly's bill page (status, text, fiscal and policy note, votes).
  billUrl: (p, session = DATA.session) => `https://mgaleg.maryland.gov/mgawebsite/Legislation/Details/${p.slice(0, 2).toLowerCase()}${p.slice(2).padStart(4, "0")}?ys=${session}RS`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, fiscal note and votes`)).join("<br>");
  },

  // The session opens the second Wednesday of January and lasts 90 days (Maryland Constitution, Art. III, sec. 14).
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds(year) {
    const [y, m, d] = STATE.opens(year).split("-").map(Number), t = new Date(y, m - 1, d + 89);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // Bills passed at the end of the session are presented to the governor within 20 days of adjournment, and the governor
  // has 30 days after that to sign or veto them (Art. II, sec. 17): late May at the latest.
  govDeadline(iso) {
    if (!iso) return null;
    const y = +iso.slice(0, 4), [a, b, c] = STATE.sessionEnds(y).split("-").map(Number), t = new Date(a, b - 1, c + 50);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's last day to act (about 50 days after the session ends)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "On the way to the governor" : "No action recorded",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses go to the governor, who signs most of them at bill signings in April and May."],
  passedBothNext: () => ({
    what: "it goes to the governor, who can sign it or veto it (and veto items in the budget). A bill the governor doesn't veto becomes law. Vetoes of bills passed at the end of a session are taken up at the next session.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town, community or county",
  addressLookup: true,
  findReps: "https://mgaleg.maryland.gov/mgawebsite/Members/District",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again next year.",
  outOfTimeLine: "Died when the session ended",

  // A committee's unfavorable report ends a bill; the sponsor then usually withdraws it.
  heldLabel: "Withdrawn",
  heldTip: "The sponsor withdrew it, usually after the committee signaled it wouldn't pass it (or it went to summer study).",
  heldNote: "the sponsor withdrew it, usually after the committee signaled it wouldn't pass it.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, "90-day session"]],
      gov: [["light", open, adj, "Signs bills"], ["", adj, due, "Bill signings, vetoes"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens. Most bills get a hearing in the first two months."],
        [adj, "down", LEG, MD(adj), "Sine die: the session ends at midnight. Bills that didn't pass both houses die."],
        [due, "down", LEG, MD(due), "The governor's last vetoes; bills not vetoed become law."],
        [`${Y}-10-01`, "down", LEG, "October 1", "Most new laws take effect."],
      ],
      note: "Bills passed at the end of the session go to the governor within 20 days, and the governor has 30 days to sign or veto them. The governor can veto items in the budget. Overriding a veto takes three-fifths of each house; vetoes of bills from the end of a session are taken up at the next one.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's member pages",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill gets a hearing.", "Each house sends a bill to one of its standing committees (four in the Senate, seven in the House of Delegates), which holds a hearing on nearly every bill."],
    ["Bills from the other house come late.", "A bill that passes one house goes to a committee of the other, often in the session's last weeks."],
    ["Most bills are paired.", "Many House bills have an identical Senate \"cross-file\"; whichever moves first usually becomes the law."],
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
    "Waiting in a committee, which holds a hearing and then votes. Most bills that die, die here.",
    "A committee reported it favorably, and it waits for the full house's second and third readings.",
    "Passed the Senate or the House of Delegates, but not both. Both houses have to pass the same text.",
    "Passed both houses. It goes to the governor within 20 days of the session's end.",
    "With the governor, who has 30 days after it's presented to sign or veto it.",
    "Signed into law (or became law without the governor's signature), with a chapter number.",
    "Vetoed by the governor. Overriding a veto takes three-fifths of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the Senate or the House of Delegates, but not both.",
    "Passed both houses, but the records show no signature or veto.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Budget and Taxation", H: "Appropriations" },
  secondCommittee: "Bills that cost money may also go to Budget and Taxation (Senate) or Appropriations (House of Delegates).",
};
