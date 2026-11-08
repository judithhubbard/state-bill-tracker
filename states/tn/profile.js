// Tennessee: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "tn",
  name: "Tennessee",
  abbr: "TN",
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed for introduction|Intro\.,|Introduced, Passed on First Consideration|P\dC|PNC held|Sponsor\(s\)|Sponsor change|Placed on (?:s\/c )?cal\.? |Placed on Senate .*Committee calendar|Action def|Reset on|Meeting Canceled|No Action Taken|Engrossed|Received from House|Rcvd\. from S|Am\. withdrawn|Amendment withdrawn|H\. adopted am|Senate adopted Amendment|Signed by (?:Senate|H\.) Speaker|Effective date|Subst\. for comp|Senate substituted|Replaced by its companion|Rule #|Approved by Delayed Bills)/i,
  publicSite: "https://statebilltracker.org/tn/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a General Assembly, the 114th).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Laws are numbered "Public Chapter 78" (local private acts: "Private Chapter").
  lawWord: "Public Chapter",
  // A joint resolution proposing an amendment to the Tennessee Constitution passes a majority of each house's members in
  // one General Assembly and two-thirds of each house's members in the next, then goes to the voters at the next
  // election for governor (Tennessee Constitution, Art. XI, sec. 3); never to the governor.
  amendments: true,
  amendmentVote: "a majority of each house's members in one General Assembly, then two-thirds of each house's members in the next",
  ballotYear(d) {
    let y = +(d || String(DATA.session)).slice(0, 4);
    while (y % 4 !== 2) y++;  // governors are elected in 2026, 2030, ...
    return y;
  },
  amendmentAgain(b) {
    const y = +([b.dates.passS, b.dates.passA].sort().pop() || String(DATA.session)).slice(0, 4), vote = y % 2 ? y + 1 : y;
    return `Next: the General Assembly elected in November ${vote} has to pass it again, by two-thirds of each house's members; then it goes to the voters at the next election for governor.`;
  },
  // The governor's office (not checked by the owner yet).
  govReach: `<a href="https://www.tn.gov/governor/contact-us.html" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Nashville <a class="phone" href="tel:+16157412001" data-contact="call|governor">(615) 741-2001</a>`,

  // Each bill's page on the General Assembly's site (v.link, from LegiScan's record) and on LegiScan.
  billUrl: (p, session = DATA.session) => `https://wapp.capitol.tn.gov/apps/BillInfo/Default.aspx?BillNumber=${STATE.padded(p)}&GA=${114 + (session - 2025) / 2}`,
  padded: (p) => p.replace(/^([A-Z]+)(\d+)$/, (m, k, n) => k + n.padStart(4, "0")),
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => `${link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text and amendments`)} · ${link(`https://legiscan.com/TN/bill/${STATE.padded(v.p)}/${DATA.session}`, "on LegiScan")}`).join("<br>");
  },

  // Each year's session starts the second Tuesday of January (Tennessee Constitution, Art. II, sec. 8) and usually
  // ends in late April; `dated` holds the actual last days. A General Assembly lasts until the next one convenes.
  dated: { 2023: "2023-04-21", 2024: "2024-04-25", 2025: "2025-04-22", 2026: "2026-04-23" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || `${year}-04-25`,
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => STATE.plusDays(STATE.opens(session + 2), -1),
  // The governor has 10 days, Sundays excepted, after a bill is presented to sign or veto it; a bill the governor doesn't
  // act on becomes law, in session or after it (Art. III, sec. 18: there's no pocket veto).
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 10;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (10 days, Sundays excepted, after it's sent)",

  passedBothBy: (session) => STATE.govDeadline(STATE.adjourns(session + 1)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the Speakers of both houses, then sent to the governor."],
  passedBothNext: () => ({
    what: "the Speakers of the Senate and the House sign it, and it goes to the governor, who has 10 days (Sundays excepted) to sign it or veto it. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  diesAfterFloor: (y2) => `Unless lawmakers return for a special session, it dies when the General Assembly ends in January ${y2 + 1}.`,
  outOfTimeLine: "Died when the General Assembly ended",

  // Set aside without a vote: the sponsor took it off notice, the House put it behind the budget, the Senate committee sent
  // it to its general subcommittee or to summer study, or tabled it.
  heldAction: /^(Taken off notice|Assigned to General Subcommittee|Deferred to Summer Study|Lay on the Table|Tabled)/i,
  heldLabel: "Set aside",
  heldTip: "Set aside without a vote: the sponsor took it off notice, or a Senate committee sent it to its general subcommittee or to summer study, where bills usually stay.",
  heldNote: "the sponsor took it off notice, or a Senate committee sent it to its general subcommittee or to summer study, where bills usually stay.",
  committeeNext: {
    "Calendar and Rules": "the Calendar and Rules Committee decides whether and when it gets a House floor vote.",
    "Calendar": "the Senate Calendar Committee puts it on a floor calendar.",
  },
  chairAsks: {
    "Calendar and Rules": ["schedule it for a floor vote", "keep it off the floor calendar"],
    "Calendar": ["schedule it for a floor vote", "keep it off the floor calendar"],
  },

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The General Assembly finished its first session ${fmtDate(STATE.adjourns(y))}. Bills that didn't pass stay alive for the second session, which starts ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > STATE.adjourns(y + 1))
      return `The General Assembly finished its second session ${fmtDate(STATE.adjourns(y + 1))}. Bills that didn't pass both houses died; the next General Assembly starts ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} General Assembly starts ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "First session"], ["light", a1, o2, "Interim"], ["", o2, a2, "Second session"], ["light", a2, STATE.sessionEnds(Y), "Interim"]],
      gov: [["light", o1, STATE.govDeadline(STATE.plusDays(a1, 14)), "Acts on bills"], ["light", o2, STATE.govDeadline(STATE.plusDays(a2, 14)), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The General Assembly convenes; bills filed since November."],
        [a1, "down", LEG, MD(a1), "The first session ends. Bills that didn't pass stay alive."],
        [o2, "up", LEG, MD(o2), "The second session starts where the first left off."],
        [a2, "down", LEG, MD(a2), "The second session ends. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "Jul 1", "Most new laws take effect July 1."],
      ],
      note: "The governor has 10 days (Sundays excepted) after a bill arrives to sign or veto it; a bill the governor doesn't act on becomes law. The governor can reduce or strike items in spending bills. Overriding a veto takes a majority of each house's members (17 in the Senate, 50 in the House).",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from LegiScan and Open States",
  openUntil: (s) => `the ${span(s)} General Assembly ends in January ${s + 2}`,

  // The Senate's and the House's Calendar Committees schedule floor votes.
  commIntro: [
    ["Every bill is filed in both houses.", "A bill has a House number and a Senate number with the same text; each goes through its own house's committees, and when one passes its house the other house votes on it in place of its own."],
    ["House committees work through subcommittees.", "A House bill goes first to a subcommittee, then to the full committee, then (if it costs money) to Finance, Ways and Means, then to Calendar and Rules, which schedules floor votes. In the Senate, a committee sends bills to the Calendar Committee."],
    ["Bills can be set aside without a vote.", "The sponsor can take a bill off notice; a Senate committee can send it to its general subcommittee or to summer study; bills that cost money wait \"behind the budget\" until the budget passes."],
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
    "In a committee or subcommittee. The House's Calendar and Rules Committee and the Senate's Calendar Committee then decide when bills reach the floor.",
    "A committee approved it, and it's on (or headed to) the House or Senate floor calendar.",
    "Passed the House or the Senate, but not both. The other house votes on it in place of its own companion bill.",
    "Passed both houses. The Speakers of both houses sign it, then it goes to the governor.",
    "Sent to the governor, who has 10 days (Sundays excepted) to sign or veto it; if the governor does neither, it becomes law.",
    "Became law (signed, without the governor's signature, or over a veto), with a public chapter number.",
    "Vetoed by the governor. Overriding a veto takes a majority of each house's members.",
  ],
  pastStageTips: [
    "Never got out of committee before the General Assembly ended.",
    "A committee approved it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be filed again in the next one.",

  // Each Senate committee's House counterpart and the subject it's shown under (2025-26 names).
  commPairs: {
    "Finance, Ways and Means": ["Finance, Ways and Means", "Budget and taxes"],
    "Calendar": ["Calendar and Rules", "Floor schedule"],
    "Commerce and Labor": ["Commerce", "Business and labor"],
    "Energy, Agriculture and Natural Resources": ["Agriculture and Natural Resources", "Agriculture and natural resources"],
    "Health and Welfare": ["Health", "Health"],
    "Transportation and Safety": ["Transportation", "Transportation"],
  },
  commNotes: {},
  moneyCommittees: { S: "Finance, Ways and Means", H: "Finance, Ways and Means" },
  secondCommittee: "Bills that cost money also go to Finance, Ways and Means in each house (in the House, first its subcommittee, where they often wait \"behind the budget\").",
};
