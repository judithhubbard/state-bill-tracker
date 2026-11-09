// Delaware: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "de",
  name: "Delaware",
  abbr: "DE",
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced$|Amendment [HS]A .* (filed|withdrawn)|An amendment (filed|withdrawn)|The (House|Senate) vote:|Released by the|On the committee's agenda|Taken (from|off) the table|Laid on the table|Restored to the|CHAPTER \d+|The governor vetoed items)/,
  publicSite: "https://statebilltracker.org/de/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 153rd General Assembly).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  assembly: (s) => 153 + (s - 2025) / 2,
  // "153rd General Assembly"
  ga(s) { const n = STATE.assembly(s), t = n % 100; return `${n}${t > 10 && t < 14 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" })[n % 10] || "th"}`; },
  govReach: `<a href="https://governor.delaware.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Dover <a class="phone" href="tel:+13027444101" data-contact="call|governor">(302) 744-4101</a> · Wilmington <a class="phone" href="tel:+13025773210" data-contact="call|governor">(302) 577-3210</a>`,
  // Laws are chapters of the Laws of Delaware, a volume per General Assembly ("Volume 85, Chapter 341").
  lawWord: "Chapter",

  // Constitutional amendments are bills: "An act proposing an amendment ..." passes each house by two-thirds of its
  // members, and after an election the next General Assembly passes "An act concurring in ..." the same way, without
  // changes. Then it's part of the constitution: Delaware alone among the states doesn't send amendments to the voters
  // (Constitution, Art. XVI, sec. 1), and they never go to the governor.
  amendments: true,
  amendmentVote: "two-thirds of each house's members in two General Assemblies in a row, with an election between",
  amendmentFinal: (b) => /^Constitutional amendment \(second passage\)/.test(b.title),
  amendmentDone: "Second passage: now part of the constitution",
  amendmentAgain: (b) => `Next: the General Assembly elected in November ${DATA.session + 1} has to pass it again, unchanged, by two-thirds of each house's members. Then it's part of the constitution; it doesn't go to the voters.`,
  ballotLine: () => "It's now part of the constitution: in Delaware, amendments don't go to the voters.",

  // The bill's page on legis.delaware.gov is addressed by its LegislationId (a version's `link`, from convert.py).
  billUrl(p) {
    const b = typeof BILLS !== "undefined" && BILLS.find((x) => x.nums.includes(p));
    return b?.vers?.[0]?.link || "https://legis.delaware.gov/AllLegislation";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.sub ? `${v.sub}` : v.p.replace(/^([A-Z]+)/, "$1 "))}: text, amendments, fiscal note and roll calls`)).join("<br>");
  },

  // Each year's session opens the second Tuesday of January and runs to June 30 (often past midnight into July 1). The
  // General Assembly then recesses; it can be called back, and its term ends at the November election of its second year.
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // Election day: the Tuesday after the first Monday of November.
  election(year) {
    const t = new Date(year, 10, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
    return `${year}-11-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => `${session + 1}-06-30`,
  floorVotesEnd: false,
  // The governor has 10 days (Sundays excepted) after a bill is presented; after the General Assembly's final
  // adjournment, 30 days, and a bill not signed by then doesn't become law (a pocket veto). Constitution, Art. III, sec. 18.
  // Bills are presented when the General Assembly sends them, often weeks or months after they pass.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 10;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (10 days after it's presented, Sundays excepted)",

  passedBothBy: (session) => STATE.plusDays(STATE.election(session + 1), 30),
  passedBothNote: (live) => live ? "Not yet acted on by the governor" : "No action by the governor recorded",
  passedBothGroup: ["Waiting for the governor", () => "The General Assembly sends bills to the governor when it chooses, often weeks or months after they pass; the governor then has 10 days (Sundays excepted). After the General Assembly's term ends, a bill not signed within 30 days doesn't become law."],
  passedBothNext: () => ({
    what: "it goes to the governor, who has 10 days (Sundays excepted) once it's presented to sign it or veto it; the records don't show when a bill is presented, often weeks or months after it passes. A bill the governor doesn't act on becomes law, except after the General Assembly's term ends, when it has to be signed within 30 days. The governor can veto items in an appropriation bill.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town, community or county",
  addressLookup: true,
  findReps: "https://legis.delaware.gov/",
  oneNumber: true,
  diesAfterFloor: () => "The General Assembly has ended, so it died with it.",
  outOfTimeLine: "Died when the General Assembly ended",

  // Committees hold a bill by tabling it (it can be lifted from the table later).
  heldAction: "Tabled in committee",
  heldLabel: "Tabled",
  heldTip: "Tabled in committee: how a Delaware committee holds a bill. It stays there unless the committee takes it off the table.",
  heldNote: "tabled in committee, which is how Delaware's committees hold bills.",
  // A stricken bill (withdrawn, usually at the sponsor's request, or replaced) ends there; a bill voted down on the floor
  // ends too, unless the house restores it.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const w = texts.findLastIndex((t) => /^Stricken/.test(t));
    if (w >= 0 && b.stage <= 1) return { status: "Stricken", when: `Stricken (withdrawn) ${fmtDate(acts[w][0])}.`, tail: "That ends it, unless it's restored to the agenda." };
    const i = texts.findLastIndex((t) => /^Failed in the (House|Senate)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |^Restored to the/.test(t))) return null;
    const h = texts[i].match(/the (House|Senate)/)[1];
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `${texts[i].replace(/,.*$/, "")} on ${fmtDate(acts[i][0])}.`,
      tail: "That ends it, unless the house votes to restore it.",
    };
  },

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, md = t.slice(5);
    if (t.startsWith(String(y)) && md > "07-01") return `The ${y} session ended June 30. Bills that haven't passed stay alive for the second year, which opens ${fmtDate(STATE.opens(y + 1))}. The governor acts on bills that passed both houses.`;
    if (t.startsWith(String(y + 1)) && md > "07-01" || t > `${y + 1}-12-31`) return `The ${STATE.ga(y)} General Assembly's last session ended June 30, ${y + 1}. Bills that didn't pass both houses died; the governor acts on the rest. The next General Assembly opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${STATE.ga(raw.session)} General Assembly opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, each from January to June 30.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), o2 = STATE.opens(Y + 1), el = STATE.election(Y + 1);
    return {
      leg: [["", o1, `${Y}-06-30`, "Session"], ["light", `${Y}-07-01`, o2, "Recess"], ["", o2, `${Y + 1}-06-30`, "Session"], ["light", `${Y + 1}-07-01`, el, "Recess"]],
      gov: [["light", o1, STATE.plusDays(el, 30), "Acts on bills as they're presented"]],
      events: [
        [o1, "up", LEG, MD(o1), "The General Assembly opens."],
        [`${Y}-02-15`, "up", LEG, "February", "Budget hearings: the Joint Finance Committee meets while the houses take a break."],
        [`${Y}-06-30`, "down", LEG, "June 30", "The session ends with the budget, the bond bill and grants-in-aid. Bills stay alive for the second year."],
        [o2, "up", LEG, MD(o2), "The second year's session opens."],
        [`${Y + 1}-06-30`, "down", LEG, "June 30", "The last session day. Bills that didn't pass both houses die."],
        [el, "down", LEG, MD(el), "Election day: the next General Assembly's members take office."],
      ],
      note: "The fiscal year starts July 1, so the budget, the capital (bond) bill and grants-in-aid pass by June 30. The governor has 10 days (Sundays excepted) once a bill is presented, and can veto items in an appropriation bill. Overriding a veto takes three-fifths of each house's members.",
    };
  },
  waitingHead: "Waiting for the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's member list",
  openUntil: (s) => `the General Assembly's last session ends June 30, ${s + 1}`,

  commIntro: [
    ["A committee releases a bill when most of its members sign.", "Each member signs the committee's report favorable, unfavorable or \"on its merits\" (neither for nor against). A bill most members don't sign stays in committee, and a committee can also table a bill."],
    ["Then the majority leader decides when it comes up.", "A released bill goes on the ready list, and the house's majority leader puts it on the agenda for a vote. Bills that cost money go on to the House Appropriations or Senate Finance Committee first."],
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
    "Waiting in a committee. A committee releases a bill when most of its members sign the report (favorable, unfavorable or \"on its merits\"), or tables it.",
    "Released by its committee and on the ready list. The majority leader decides when it comes up for a vote of the full house.",
    "Passed the House or the Senate, but not both. If the second house amends it, the first has to pass it again.",
    "Passed both houses. It goes to the governor when the General Assembly sends it.",
    "Sent to the governor, who has 10 days (Sundays excepted).",
    "Signed into law, or became law without the governor's signature or over a veto: a chapter of the Laws of Delaware.",
    "Vetoed by the governor. Overriding takes three-fifths of each house's members.",
  ],
  pastStageTips: [
    "Never released by its committee before the General Assembly ended.",
    "Released by its committee, but never passed by the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show no action by the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be filed again in the next one.",

  // Each Senate committee's House counterpart (the 153rd General Assembly's names) and the subject it's shown under.
  commPairs: {
    "Banking, Business, Insurance & Technology": ["Economic Development/Banking/Insurance & Commerce", "Business and banking"],
    "Corrections & Public Safety": ["Public Safety & Homeland Security", "Public safety"],
    "Environment, Energy & Transportation": ["Natural Resources & Energy", "Environment and energy"],
    "Health & Social Services": ["Health & Human Development", "Health"],
    "Housing & Land Use": ["Housing", "Housing"],
    "Finance": ["Appropriations", "Budget and spending"],
    "Capital Improvement": ["Capital Infrastructure", "Capital (bond bill) spending"],
    "Legislative Oversight & Sunset": ["Sunset (Policy Analysis & Government Accountability)", "Sunset reviews of state agencies"],
    "Executive": ["Administration", "Leaders' committees"],
  },
  commNotes: {
    "Environment, Energy & Transportation": "The Senate's Environment, Energy & Transportation Committee also takes transportation bills; in the House, the Transportation Committee does.",
    "Finance": "Bills that cost money go to the Senate Finance or House Appropriations Committee after their policy committee. Tax bills go to the House Revenue & Finance Committee and the Senate Finance Committee.",
    "Executive": "The Senate's Executive Committee (chaired by the President Pro Tempore) and the House Administration Committee (the majority leader's) take nominations, constitutional amendments and bills on the General Assembly and state government.",
  },
  moneyCommittees: { S: "Finance", H: "Appropriations" },
  secondCommittee: "Bills that cost money go on to the House Appropriations or Senate Finance Committee after their policy committee.",
};
