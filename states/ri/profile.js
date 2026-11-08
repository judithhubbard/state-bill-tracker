// Rhode Island: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ri",
  name: "Rhode Island",
  abbr: "RI",
  // Steps that aren't news on a watchlist card.
  routine: /^(Scheduled for|Meeting postponed|Committee postponed|Proposed Substitute|Substitute [A-Z]$|Committee heard|Committee continued|Committee voted to reconsider|Removed from|Senate held on desk|Scheduled to be heard)/i,
  publicSite: "https://statebilltracker.org/ri/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills that don't become law die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are numbered "Public Law 2025-123", but the data doesn't carry the numbers.
  lawWord: "Public Law",
  // A joint resolution proposing an amendment to the Rhode Island Constitution passes by a majority of each house's
  // members and goes to the voters at the next general election (even Novembers); never to the governor (Rhode Island
  // Constitution, Art. XIV).
  amendments: true,
  amendmentOnce: true,
  ballotEvenYears: true,
  amendmentVote: "a majority of each house's members",
  // The governor's office (not checked by the owner yet).
  govReach: `<a href="https://governor.ri.gov/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Providence <a class="phone" href="tel:+14012222080" data-contact="call|governor">(401) 222-2080</a>`,

  // Each bill's page on LegiScan (v.link). The General Assembly's bill status site has no page per bill to link to.
  billUrl: (p, session = DATA.session) => `https://legiscan.com/RI/bill/${p}/${session}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || `https://legiscan.com/RI/bill/${v.p}/${DATA.session}`, `${esc(v.p)}: status, text and votes on LegiScan`)).join("<br>") +
      `<br>${link("https://status.rilegislature.gov/", "The General Assembly's bill status search")}`;
  },

  // Each year's session opens the first Tuesday of January (Rhode Island Constitution, Art. VI, sec. 3) and usually
  // ends in June; `dated` holds the actual last days of floor votes (add each year's).
  dated: { 2024: "2024-06-14", 2025: "2025-06-21", 2026: "2026-06-11" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7));
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || `${year}-06-20`,
  sessionEnds: (year) => STATE.adjourns(year),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The governor has 6 days, Sundays excepted, after a bill is transmitted to sign or veto it; a bill the governor doesn't
  // act on becomes law without a signature (Art. IX, sec. 14). (If the General Assembly adjourns in the meantime, the
  // governor has 10 days after the adjournment; it recesses in June instead, so the 6 days apply.)
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 6;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (6 days, Sundays excepted, after it's sent)",

  passedBothBy: (session) => STATE.govDeadline(STATE.plusDays(STATE.adjourns(session), 14)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are transmitted to the governor, usually within a week or two."],
  passedBothNext: () => ({
    what: "it's transmitted to the governor, who has 6 days (Sundays excepted) to sign it or veto it. A bill the governor doesn't act on becomes law without a signature.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or town",
  addressLookup: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again next year.",
  outOfTimeLine: "Died when the session ended",

  // Most bills end here: the committee hears the bill and recommends it "be held for further study" (Senate committees
  // vote on it; House committees don't). A held bill can be brought back for a vote later in the session.
  heldAction: /^Committee recommended (?:measure|Substitute \w+|as amended)[^.]*be held for further study/i,
  heldLabel: "Held for further study",
  heldTip: "The committee heard it and recommended it be “held for further study”, the usual way Rhode Island committees set a bill aside. It can be brought back for a vote later in the session, but most aren't.",
  heldNote: "the committee heard it and recommended it be held for further study, the usual way Rhode Island committees set a bill aside. It can come back for a vote later in the session, but most don't.",

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.adjourns(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.adjourns(Y), due = STATE.passedBothBy(Y);
    return {
      leg: [["", open, adj, "Session"]],
      gov: [["light", open, due, "6 days a bill"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens. Most bills are introduced by early March, then heard in committee."],
        [adj, "down", LEG, MD(adj), "The last floor votes, usually in June, after the budget. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "Jul 1", "The state's budget year starts; many new laws take effect."],
      ],
      note: "The governor has 6 days (Sundays excepted) after a bill is sent to sign or veto it; a bill the governor doesn't act on becomes law. Overriding a veto takes three-fifths of the members present in each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from LegiScan and Open States",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Most bills have a companion.", "A bill is usually introduced in both houses with the same text, a House bill and a Senate bill. Each goes through its own house's committee, then the other house's; often both pass and both become law. They're shown here as one bill."],
    ["Committees hear bills, then usually hold them.", "At a bill's hearing the committee usually recommends it be “held for further study”. Only the bills the chair (and the leaders) bring back are voted out, often late in the session."],
    ["There's no Rules Committee.", "The Speaker and the Senate President, with the committee chairs, decide which bills go to the floor."],
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
    "In a committee. Most bills are heard and then “held for further study”; few come back for a vote.",
    "A committee recommended passage, and it's on (or headed to) the House or Senate calendar.",
    "Passed the House or the Senate, but not both. The other house has to pass the same version (“in concurrence”).",
    "Passed both houses in the same version; it's transmitted to the governor.",
    "Sent to the governor, who has 6 days (Sundays excepted) to sign or veto it; if the governor does neither, it becomes law.",
    "Became law (signed, without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes three-fifths of the members present in each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee recommended it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Each Senate committee's House counterpart and the subject it's shown under (2026 names).
  commPairs: {
    "Housing and Municipal Government": ["Municipal Government and Housing", "Housing and local government"],
    "Commerce": ["Corporations", "Business and utilities"],
    "Environment and Agriculture": ["Environment and Natural Resources", "Environment"],
    "Labor and Gaming": ["Labor", "Labor"],
    "Special Legislation and Veterans Affairs": ["Special Legislation", "Special legislation"],
    "Rules, Government Ethics and Oversight": ["State Government and Elections", "Government and elections"],
    "Artificial Intelligence and Emerging Technology": ["Innovation, Internet, and Technology", "Technology"],
  },
  commNotes: {},
  moneyCommittees: { S: "Finance", H: "Finance" },
  secondCommittee: "Bills that cost money usually go to Finance, where they wait for the budget.",
};
