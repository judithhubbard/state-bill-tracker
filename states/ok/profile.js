// Oklahoma: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ok",
  name: "Oklahoma",
  abbr: "OK",
  // Steps that aren't news on a watchlist card.
  routine: /^(First Reading|Introduced$|Authored by|Coauthored by|Remove (?:as )?(?:co|principal )?author|remove as|Referred for engrossment|Engrossed|Signed, returned|Enrolled measure signed|Enrolled, signed|Enrolled, to|To (?:Senate|House)$|Measure (?:returned|sent) to|Title (?:stricken|restored)|Enacting clause|Emergency (?:added|removed)|HAs read|SA's received|Received from|Notice served|Motion expired|House Rule suspended|Withdrawn from .*[Cc]ommittee$|HC's named|SCs (?:named|changed)|Conference granted|Naming of)/i,
  publicSite: "https://statebilltracker.org/ok/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a Legislature, the 60th).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Laws are chapters of the year's session laws ("Chapter 1, O.S.L. 2025"); LegiScan's data has no chapter numbers.
  lawWord: "Chapter",
  // Placeholder bills ("Schools; Education Reform Act of 2026; effective date."): convert.py marks them `shell`.
  shellTip: "A placeholder that only names a new act. Leaders file hundreds of these so they can later rewrite one into a real bill, often late in the session. Most are never used.",
  shellNote: "Shell bills (placeholders that only name a new act) are left out unless they moved past a committee.",
  // A joint resolution proposing an amendment to the Oklahoma Constitution passes a majority of each house's members
  // and goes to the voters at the next general election, or at a special election the Legislature sets (Oklahoma
  // Constitution, Art. XXIV, sec. 1); never to the governor.
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members",
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || String(DATA.session);
    let y = +d.slice(0, 4); if (y % 2) y++;
    const t = new Date(y, 10, 1); t.setDate(2 + ((1 - t.getDay() + 7) % 7));  // election day: the Tuesday after the first Monday
    const vote = `${y}-11-${String(t.getDate()).padStart(2, "0")}`;
    return isoToday() > vote ? `It went to the voters (in November ${y}, unless the Legislature set a special election); the records here don't show the result.`
      : `Next: the voters, in November ${y}, unless the Legislature sets a special election.`;
  },
  // The governor's office (not checked by the owner yet).
  govReach: `<a href="https://oklahoma.gov/governor/contact.html" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Oklahoma City <a class="phone" href="tel:+14055212342" data-contact="call|governor">(405) 521-2342</a>`,

  // Each bill's page on the Legislature's site (v.link, from LegiScan's record) and on LegiScan. A Legislature's bills
  // are filed under its second year there.
  billUrl: (p, session = DATA.session) => `https://www.oklegislature.gov/BillInfo.aspx?Bill=${p.toLowerCase()}&Session=${String(session + 1).slice(2)}00`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => `${link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text and amendments`)} · ${link(`https://legiscan.com/OK/bill/${esc(v.p)}/${DATA.session + 1}`, "on LegiScan")}`).join("<br>");
  },

  // Each year's session starts the first Monday in February and must end by 5 p.m. on the last Friday in May (Oklahoma
  // Constitution, Art. V, sec. 26); in odd years the new Legislature first meets in January to organize. `dated` holds
  // the actual last days (2026's ended early, May 14).
  dated: { 2023: "2023-05-26", 2024: "2024-05-30", 2025: "2025-05-30", 2026: "2026-05-14" },
  opens(year) {
    const t = new Date(year, 1, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7));
    return `${year}-02-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns(year) {
    if (STATE.dated[year]) return STATE.dated[year];
    const t = new Date(year, 4, 31); t.setDate(31 - ((t.getDay() - 5 + 7) % 7));
    return `${year}-05-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // A Legislature's bills die when its second session ends; the next one organizes in January.
  sessionEnds: (session) => STATE.adjourns(session + 1),
  // The governor has 5 days, Sundays excepted, while the Legislature is in session; for a bill that arrives in the last
  // five days, 15 days after the session ends, and a bill not signed by then doesn't become law (a pocket veto). Art. VI,
  // sec. 11.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 5;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const due = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const end = STATE.adjourns(a);
    return iso <= end && due > end ? STATE.plusDays(end, 15) : due;
  },
  dueLabel: () => "Governor's decision due (5 days, Sundays excepted; 15 days after the session ends)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session + 1), 15),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the presiding officers of both houses, then sent to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the President Pro Tempore sign it, and it goes to the governor, who has 5 days (Sundays excepted) to sign or veto it while the Legislature meets; if it doesn't, the bill becomes law. After the session ends, the governor has 15 days, and a bill not signed by then dies (a pocket veto).",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  diesAfterFloor: (y2) => `Unless lawmakers return for a special session, it dies when the session ends in May ${y2}.`,
  outOfTimeLine: "Died when the Legislature's second session ended",

  // Oklahoma's committees don't set bills aside by a vote: a bill not heard just stays.
  heldAction: /(?!)/,
  heldLabel: "Set aside",
  heldTip: "Set aside without a vote.",
  heldNote: "set aside without a vote.",
  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The Legislature finished its first session ${fmtDate(STATE.adjourns(y))}. Bills that didn't pass stay alive for the second session, which starts ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > STATE.adjourns(y + 1))
      return `The Legislature finished its second session ${fmtDate(STATE.adjourns(y + 1))}. Bills that didn't pass both houses died; the next Legislature's first session starts ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} Legislature's first session starts ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "First session"], ["light", a1, o2, "Interim"], ["", o2, a2, "Second session"], ["light", a2, `${Y + 1}-12-31`, "Interim"]],
      gov: [["light", o1, STATE.plusDays(a1, 15), "Acts on bills"], ["light", o2, STATE.plusDays(a2, 15), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The first session convenes; bills were filed in December and January."],
        [a1, "down", LEG, MD(a1), "The first session ends (by the last Friday in May). Bills that didn't pass stay alive."],
        [o2, "up", LEG, MD(o2), "The second session starts where the first left off."],
        [a2, "down", LEG, MD(a2), "The second session ends. Bills that didn't pass both houses die."],
        [`${Y}-11-01`, "down", LEG, "Nov 1", "Most new laws take effect November 1."],
      ],
      note: "The governor has 5 days (Sundays excepted) to sign or veto a bill while the Legislature meets; a bill not acted on becomes law. After the session ends, the governor has 15 days, and a bill not signed dies (a pocket veto). Overriding a veto takes two-thirds of each house's members (32 senators and 68 representatives), or three-fourths (36 and 76) for a bill with an emergency clause.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from LegiScan and Open States",
  openUntil: (s) => `the ${span(s)} Legislature's second session ends in May ${s + 1}`,

  commIntro: [
    ["House bills go to a policy committee first.", "Since 2025 the House sends a bill to an oversight committee and, within it, to a policy committee (Civil Judiciary under Judiciary and Public Safety Oversight, for example). The policy committee recommends it to the oversight committee, which reports it to the floor. Bills that cost money go through Appropriations and Budget and its subcommittees the same way. Many House bills are first sent to the Rules Committee and later moved to the committee that hears them."],
    ["Senate committees then Appropriations.", "A Senate bill goes to a standing committee, and bills that cost money then to Appropriations (or Revenue and Taxation)."],
    ["The floor leaders decide what gets a vote.", "A bill a committee approves goes on the General Order calendar; each house's majority floor leader decides which bills are taken up."],
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
    "In a committee. In the House that's usually a policy committee, which recommends it to its oversight committee.",
    "A committee approved it, and it's on the General Order calendar; the majority floor leader decides when it gets a vote.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses. The presiding officers of both houses sign it, then it goes to the governor.",
    "Sent to the governor, who has 5 days (Sundays excepted) while the Legislature meets, or 15 days after the session ends.",
    "Became law: signed, without the governor's signature, or over a veto.",
    "Vetoed by the governor (or not signed within 15 days after the session: a pocket veto). Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the Legislature ended.",
    "A committee approved it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This Legislature is over. Bills that didn't become law have to be filed again in the next one.",

  // Each Senate committee's House counterpart and the subject it's shown under (2025-26 names).
  commPairs: {
    "Appropriations": ["Appropriations and Budget", "Budget"],
    "Judiciary": ["Judiciary and Public Safety Oversight", "Courts and public safety"],
    "Education": ["Education Oversight", "Education"],
    "Health and Human Services": ["Health and Human Services Oversight", "Health and human services"],
    "Energy": ["Energy and Natural Resources Oversight", "Energy and natural resources"],
    "Business and Insurance": ["Commerce and Economic Development Oversight", "Business"],
    "Retirement and Government Resources": ["Government Oversight", "State government"],
  },
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations and Budget" },
  secondCommittee: "Bills that cost money also go to Appropriations in the Senate, and to Appropriations and Budget (through one of its subcommittees) in the House.",
};
