// Mississippi: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ms",
  name: "Mississippi",
  abbr: "MS",
  // Steps that aren't news on a watchlist card.
  routine: /^(Sent to the (?:House|Senate)$|Also referred to|(?:House|Senate): (?:Amended|Immediate Release|Unanimous Consent Granted|Committee Substitute Adopted|Point of Order|Amendment Failed|Title Suff Do Be Adopted|Tabled Failed)|(?:House|Senate): motion to reconsider tabled|Signed by the (?:Speaker|Lieutenant Governor)|Conference committee report filed|(?:House|Senate) conference committee members)/i,
  publicSite: "https://statebilltracker.org/ms/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year; bills die when it adjourns, and most die earlier, at a deadline.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are chapters of each year's session laws ("Chapter 364" of 2026).
  lawWord: "Chapter",
  // A concurrent resolution proposing an amendment to the Mississippi Constitution passes each house once, by two-thirds,
  // and goes to the voters, never to the governor (Constitution, sec. 273).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house",
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || "";
    const y = +d.slice(0, 4);
    return isoToday() > `${y + 1}-11-10` ? "It went to the voters at the election the resolution named; the records here don't show the result." : "Next: the voters, at the election the resolution names (usually the next November general election).";
  },
  govReach: `<a href="https://governorreeves.ms.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Jackson <a class="phone" href="tel:+16013593150" data-contact="call|governor">(601) 359-3150</a>`,

  // The bill's status page in the Legislature's bill status system (each version's `link`, from convert.py):
  // /2026/pdf/history/HB/HB0001.xml.
  billUrl(p, session = DATA.session) {
    const m = /^([HS][BC])(\d+)$/.exec(p);
    return m ? `https://billstatus.ls.state.ms.us/${session}/pdf/history/${m[1]}/${m[1]}${m[2].padStart(4, "0")}.xml` : "https://billstatus.ls.state.ms.us/";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: history, text, amendments and roll calls`)).join("<br>");
  },

  // The session opens the Tuesday after the first Monday of January and lasts 90 days, or 125 in the first year of a
  // four-year term (2024, 2028); it often ends a little early or runs a few days over. `dated` holds each year's last
  // floor day (add each year's).
  dated: { 2024: "2024-05-14", 2025: "2025-04-03", 2026: "2026-04-15" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionDays: (year) => (year % 4 === 0 ? 125 : 90),
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), STATE.sessionDays(year) - 1),
  // The governor has 5 days (Sundays excepted) after a bill is presented while the Legislature is in session; a bill it
  // can't be returned to because the Legislature adjourned becomes law unless vetoed within 15 days after adjournment
  // (Constitution, sec. 72). A bill the governor doesn't act on becomes law.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    for (let n = 5; n > 0;) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const five = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const end = STATE.sessionEnds(a);
    return five <= end ? five : STATE.plusDays(end > iso ? end : iso, 15);
  },
  dueLabel: () => "Governor's decision due (5 days during the session, Sundays excepted; 15 days after it adjourns)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the Speaker and the Lieutenant Governor, and sent to the governor."],
  passedBothNext: () => ({
    what: "it's enrolled, signed by the Speaker and the Lieutenant Governor, and sent to the governor, who has 5 days (Sundays excepted) to sign it or veto it, or 15 days after the session adjourns; the governor can veto parts of an appropriation bill. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town, village or county",
  addressLookup: true,
  findReps: "https://openstates.org/find_your_legislator/",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // Mississippi's committees seldom vote a bill down: a bill they don't report by the deadline dies there ("Died In
  // Committee"), as most do.
  heldLabel: "Died in committee",
  heldTip: "The committee didn't report it by the deadline, which ends the bill for this session.",
  heldNote: "the committee didn't report it by the deadline, which ends the bill for this session.",
  // Deadlines end bills before the session does: a committee's, the floor's, and the conference committees'. What the page
  // says about a bill that died at one, instead of what comes next.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const i = texts.findLastIndex((t) => /^Died (?:in|on the) (?:House|Senate) (?:committee|calendar) \(deadline\)$|^Died in conference$/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |^REPORTED|^REFERRED TO /.test(t))) return null;
    const t = texts[i], h = (t.match(/House|Senate/) || [""])[0];
    const where = /conference/.test(t) ? "in conference" : /calendar/.test(t) ? `on the ${h} calendar` : `in ${h} committee`;
    return {
      status: b.stage === 2 && b.passedIn && h && b.passedIn !== h ? `Passed the ${b.passedIn}; died ${where}` : `Died ${where}`,
      when: /conference/.test(t) ? `Died in conference ${fmtDate(acts[i][0])}: the houses didn't agree on a version by the deadline.`
        : `Died ${where} at the deadline, ${fmtDate(acts[i][0])}.`,
      tail: "Mississippi's deadlines end bills that miss them, unless the Legislature suspends the deadlines for a bill by a two-thirds vote, which is rare. It would have to be introduced again in a later session.",
    };
  },

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.plusDays(adj, 15);
    return {
      leg: [["", open, adj, `${STATE.sessionDays(Y)}-day session`]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "15 days"]],
      events: [
        [open, "up", LEG, MD(open), `The session opens (${STATE.sessionDays(Y)} days${Y % 4 === 0 ? ", the first year of a four-year term" : ""}). Most bills are filed in its first weeks.`],
        [STATE.plusDays(open, 28), "down", LEG, "Early February", "The first deadlines: committees have to report general bills from their own house, then each house has to pass them. Bills that miss a deadline die."],
        [adj, "down", LEG, MD(adj), "The session adjourns sine die. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "July 1", "Most new laws take effect, and the state's budget year starts."],
      ],
      note: "During the session the governor has 5 days (Sundays excepted) to act on a bill; after the session adjourns, 15 days. A bill the governor doesn't act on becomes law. The governor can veto parts of an appropriation bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member pages",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Bills go to a standing committee on their subject.", "The Speaker refers House bills, and the Lieutenant Governor Senate bills. Many go to two committees: a policy committee, then Appropriations or Ways and Means (Finance in the Senate)."],
    ["Deadlines decide most bills.", "A committee that doesn't report a bill by the deadline kills it (\"Died In Committee\"), and a bill the full house doesn't take up by its deadline dies on the calendar. Committee chairs and the presiding officers decide which bills move."],
    ["Reported bills go on the calendar.", "A bill reported \"do pass\" goes on its house's calendar for a vote. A member can hold a bill that passed with a motion to reconsider, which keeps it in that house until the motion is decided."],
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
    "In a standing committee, which has until its deadline to report it (\"title sufficient, do pass\"); a bill it doesn't report dies there.",
    "A committee reported it, and it's on the House or Senate calendar for a vote before the floor deadline.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, signed by the Speaker and the Lieutenant Governor, and sent to the governor.",
    "Sent to the governor, who has 5 days (Sundays excepted) to sign or veto it, or 15 days after the session adjourns; if the governor does neither, it becomes law.",
    "Became law: signed, or became law without the governor's signature or over a veto. Laws are chapters of the year's session laws.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Its committee didn't report it by the deadline.",
    "A committee reported it, but the full house didn't pass it by the deadline.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Business and Financial Institutions": ["Banking and Financial Services", "Banking and finance"],
    "Finance": ["Ways and Means", "Taxes and bonds"],
    "Elections": ["Apportionment and Elections", "Elections"],
    "Highways and Transportation": ["Transportation", "Transportation"],
    "Public Health and Welfare": ["Public Health and Human Services", "Health and welfare"],
    "Environment Protection, Conservation and Water Resources": ["Conservation and Water Resources", "Environment and water"],
    "Ports and Marine Resources": ["Marine Resources", "Marine resources and ports"],
    "Veterans and Military Affairs": ["Military Affairs", "Veterans and the military"],
    "Economic and Workforce Development": ["Workforce Development", "Workforce"],
    "Interstate and Federal Cooperation": ["Interstate Cooperation", "Interstate cooperation"],
  },
  commNotes: {
    "Judiciary, Division A": "Both houses split judiciary bills between two committees: the Senate's Divisions A and B, the House's Judiciary A and B.",
    "Appropriations": "The House divides spending bills among Appropriations A through E; the Senate has one Appropriations Committee.",
  },
  moneyCommittees: { S: "Appropriations", H: "Appropriations A" },
  secondCommittee: "Bills that spend money often go on to Appropriations after their policy committee, and bills about taxes or bonds to Ways and Means (Finance in the Senate).",
};
