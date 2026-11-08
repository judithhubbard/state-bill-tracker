// Maine: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "me",
  name: "Maine",
  abbr: "ME",
  // The records never show the governor's signature (a law is a bill both houses enacted that has chaptered text): "Became law".
  noSignatures: true,
  // Steps that aren't news on a watchlist card.
  routine: /^(Work Session Held|Voted: |Carry Over (?:Requested|Approved)|Sent (?:for|down for) concurrence|Ordered sent (?:down )?forthwith|ORDERED SENT FORTHWITH|In concurrence\. ORDERED SENT|Reports? (?:was )?READ|Unfinished Business|Speaker laid before|Later today assigned|Taken from the table|READ ONCE|(?:The |Bill )?(?:Bill|Resolve|RESOLUTION) was READ ONCE|Bill READ ONCE|Under suspension of the rules,? (?:CONSENT CALENDAR|the (?:Bill|Resolve) was given)|ASSIGNED FOR SECOND READING|COMMITTEE ON BILLS IN THE SECOND READING|Committee Amendment|House Amendment|Senate Amendment|Received by the (?:Clerk|Secretary)|Committee on .* suggested and ordered printed|This being an emergency measure|Placed in (?:the )?Legislative Files|Pursuant to Joint Rule|Died (?:in|on)|CARRIED OVER|Carried over|Roll Call Ordered|ROLL CALL NO)/i,
  publicSite: "https://statebilltracker.org/me/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a Legislature, the 132nd).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Laws are numbered by year and kind: "Public Law 2025, chapter 12" (also private and special laws, and resolves).
  lawWord: "Chapter",
  // A resolution proposing an amendment to the Constitution of Maine passes each house once, by two-thirds, then goes to
  // the voters at the next statewide election in November (Constitution of Maine, Art. X, sec. 4); never to the governor.
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house",
  // The governor's office (not checked by the owner yet).
  govReach: `<a href="https://www.maine.gov/governor/mills/contact" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Augusta <a class="phone" href="tel:+12072873531" data-contact="call|governor">(207) 287-3531</a>`,

  // Each bill's page on the Legislature's site (v.link, from LegiScan's record) and on LegiScan. Record numbers carry the
  // house in front ("HLD1328" is LD 1328, a House paper).
  ld: (p) => p.replace(/^[HS]LD/, ""),
  billUrl: (p, session = DATA.session) => `https://legislature.maine.gov/legis/bills/display_ps.asp?LD=${STATE.ld(p)}&snum=${132 + (session - 2025) / 2}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => `${link(v.link || STATE.billUrl(v.p), `LD ${esc(STATE.ld(v.p))}: status, text and amendments`)} · ${link(`https://legiscan.com/ME/bill/LD${STATE.ld(v.p)}/${DATA.session}`, "on LegiScan")}`).join("<br>");
  },
  oneNumber: true,

  // A Legislature convenes the first Wednesday of December after the election (the 132nd on December 4, 2024). Its first
  // session runs into June of the odd year (the law sets the third Wednesday; it's often extended), its second from the
  // Wednesday after the first Tuesday of January to April of the even year. `dated` holds each session's actual last day,
  // `vetoDay` the day the Legislature came back for vetoes and held bills (add each year's).
  dated: { 2023: "2023-07-26", 2024: "2024-04-18", 2025: "2025-06-25", 2026: "2026-04-14" },
  vetoDays: { 2024: "2024-05-10", 2026: "2026-04-29" },
  convenes(year) {  // the first Wednesday of December of an even year
    const t = new Date(year, 11, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7));
    return `${year}-12-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens(year) {
    if (year % 2) return `${year}-01-0${[1, 2, 3, 4, 5, 6, 7].find((d) => new Date(year, 0, d).getDay() === 3)}`;
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 1);  // the Wednesday after the first Tuesday
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || (year % 2 ? `${year}-06-18` : `${year}-04-15`),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => STATE.plusDays(STATE.convenes(session + 1), -1),
  // The governor has 10 days, Sundays excepted, to sign or veto a bill; one she doesn't act on becomes law. When the
  // Legislature adjourns first, she can hold it until three days after it meets again; if the Legislature doesn't meet
  // again, a held bill doesn't become law (Constitution of Maine, Art. IV, Part 3, sec. 2).
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 10;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (10 days, Sundays excepted, after it's enacted)",

  passedBothBy: (session) => STATE.govDeadline(STATE.vetoDays[session + 1] || STATE.adjourns(session + 1)),
  passedBothNote: (live) => live ? "Waiting for the governor" : "No governor's action recorded",
  passedBothGroup: ["Before the governor's deadline", () => "Bills enacted by both houses go to the governor, who has 10 days (Sundays excepted) to act."],
  passedBothNext: () => ({
    what: "it goes to the governor, who has 10 days (Sundays excepted) to sign it or veto it. A bill the governor doesn't act on becomes law; one enacted as the Legislature adjourns can be held until it meets again.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or plantation",
  addressLookup: true,
  diesAfterFloor: (y2) => `Unless lawmakers return for a special session, it dies when the Legislature ends in December ${y2}.`,
  outOfTimeLine: "Died when the Legislature ended",

  // Set aside without a floor vote: the committee reported "Leave to Withdraw" (the sponsor asked to withdraw it).
  heldAction: /^Committee report: Leave to Withdraw/i,
  heldLabel: "Withdrawn",
  heldTip: "The committee reported \"Leave to Withdraw\": the sponsor asked to withdraw the bill, and it ends there.",
  heldNote: "the committee reported \"Leave to Withdraw\": the sponsor asked to withdraw it.",

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The Legislature finished its first session ${fmtDate(STATE.adjourns(y))}. Bills carried over stay alive for the second session, which starts ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > (STATE.vetoDays[y + 1] || STATE.adjourns(y + 1)))
      return `The Legislature finished its second session ${fmtDate(STATE.adjourns(y + 1))}. Bills that weren't enacted died; the next Legislature convenes ${fmtDate(STATE.convenes(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} Legislature convenes ${fmtDate(STATE.convenes(raw.session - 1))}. Bills appear here as they're printed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1), v2 = STATE.vetoDays[Y + 1];
    return {
      leg: [["", o1, a1, "First session"], ["light", a1, o2, "Interim"], ["", o2, a2, "Second session"], ["light", a2, STATE.sessionEnds(Y), "Interim"]],
      gov: [["light", o1, STATE.govDeadline(a1), "Acts on bills"], ["light", o2, STATE.govDeadline(v2 || a2), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The first session gets under way (the Legislature convened in December)."],
        [a1, "down", LEG, MD(a1), "The first session ends. Bills carried over stay alive."],
        [o2, "up", LEG, MD(o2), "The second session: budget changes, carried-over bills and emergency bills."],
        [a2, "down", LEG, MD(a2), "The second session ends; lawmakers return later for vetoes. Bills not enacted die."],
      ],
      note: "The governor has 10 days (Sundays excepted) to sign or veto a bill; one she doesn't act on becomes law. Overriding a veto takes two-thirds of the members present in each house. Laws without an emergency clause take effect 90 days after the session adjourns.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from LegiScan and Open States",
  openUntil: (s) => `the ${span(s)} Legislature ends in December ${s + 1}`,

  commIntro: [
    ["Committees are joint.", "Each bill goes to one Joint Standing Committee of senators and representatives, which holds a public hearing and a work session, then reports: Ought to Pass (often as amended), Ought Not to Pass, or Leave to Withdraw. A committee can split into a majority and a minority report, and each house then votes on which report to accept."],
    ["A unanimous \"Ought Not to Pass\" ends a bill.", "Unless a member asks to take it up, it goes to the Legislative Files (Joint Rule 310.3)."],
    ["Bills that cost money wait on the Appropriations Table.", "After the House enacts them, the Senate usually places them on the Special Appropriations Table; the Appropriations Committee decides which to fund at the end of the session, and the rest die there."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Enacted by both houses", "On the governor's desk", "Became law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Enacted by both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Enacted", "Governor's desk", "Law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Enacted by both houses", "Held by the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Enacted by both houses, no governor's action recorded", "Held by the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Enacted", "Held", "Law", "Vetoed"],
    },
  },
  stageTips: [
    "With a joint committee of senators and representatives, which holds a hearing and a work session, then reports.",
    "The committee reported it, and it's on (or headed to) the House or Senate floor.",
    "One house passed it (to be engrossed, or also enacted), but not both. Bills that cost money often wait on the Senate's Special Appropriations Table after the House enacts them.",
    "Enacted by both houses: it goes to the governor.",
    "Held by the governor until the Legislature meets again (the governor then has three days to act).",
    "Became law (signed, without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of the members present in each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the Legislature ended.",
    "The committee reported it, but it never got through the full house.",
    "Passed one house, but not both; many died on the Special Appropriations Table.",
    "Enacted by both houses, but the records show no governor's action.",
    "Held by the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This Legislature is over. Bills that didn't become law have to be filed again in the next one.",

  // The committees are joint: each is listed under both houses with the same name.
  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations and Financial Affairs", H: "Appropriations and Financial Affairs" },
  secondCommittee: "Bills that cost money can also go to Appropriations and Financial Affairs; most wait on the Senate's Special Appropriations Table after the House enacts them, and that committee decides which are funded.",
};
