// Alaska: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ak",
  name: "Alaska",
  abbr: "AK",
  // Steps that aren't news on a watchlist card.
  routine: /^(Heard and held|Read the first time|Read the second time|Advanced to third reading|The (?:House|Senate) vote:|\S+ gave notice of reconsideration|.* Committee report: |The Rules Committee put it on the calendar)/,
  publicSite: "https://statebilltracker.org/ak/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 34th Legislature).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  legislature: (s) => 34 + (s - 2025) / 2,
  govReach: `<a href="https://gov.alaska.gov/contact/email-the-governor/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Juneau <a class="phone" href="tel:+19074653500" data-contact="call|governor">(907) 465-3500</a>`,
  // Laws are chapters of the session laws of Alaska ("Chapter 5, SLA 2025"), numbered from 1 each year.
  lawWord: "Chapter",
  // Joint resolutions proposing amendments to the Alaska Constitution pass each house once, by two-thirds of its members,
  // then go to the voters at the next general election (Alaska Constitution, Art. XIII, sec. 1); never to the governor.
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  ballotEvenYears: true,

  // The Legislature's bill page: /basis/Bill/Detail/34?Root=HB%2057 (joint resolutions "HJR 12").
  billUrl: (p, session = DATA.session) => `https://www.akleg.gov/basis/Bill/Detail/${STATE.legislature(session)}?Root=${encodeURIComponent(`${p[0]}${p[1] === "J" ? "JR" : "B"} ${+p.slice(2)}`)}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text, fiscal notes, sponsor statement and votes`)).join("<br>");
  },

  // Each year's regular session opens the third Tuesday of January and may last 121 days (Alaska Constitution, Art. II,
  // sec. 8; a statute says 90, but the sessions run the full 121). `dated` holds the actual last days. Special sessions,
  // called by the governor or two-thirds of the members, belong to the same Legislature.
  dated: { 2023: "2023-05-17", 2024: "2024-05-16", 2025: "2025-05-20", 2026: "2026-05-20" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 14);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 120),
  sessionEnds: (session) => STATE.adjourns(session + 1),
  // The governor has 15 days (Sundays excepted) after delivery while the Legislature is in session, and 20 days (Sundays
  // excepted) when it has adjourned (Art. II, sec. 17). Bills are often delivered weeks or months after they pass.
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = iso <= STATE.adjourns(a) ? 15 : 20;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return ymd(t);
  },
  dueLabel: () => "Governor's decision due (15 days during a session, 20 after it, Sundays excepted)",

  // No set day for sending a passed bill to the governor: the Legislature transmits them through the summer and fall
  // (as New York's do), so the year's end stands in.
  passedBothBy: (session) => `${session + 1}-12-31`,
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Waiting to go to the governor", () => "Bills that pass both houses are sent to the governor when the Legislature transmits them, often weeks or months later. The governor's time starts then."],
  passedBothNext: () => ({
    what: "it goes to the governor when the Legislature transmits it (often weeks later). The governor then has 15 days, or 20 if the Legislature has adjourned (Sundays excepted), to sign it or veto it, and can veto or reduce items in an appropriation bill. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, community or borough",
  findReps: "https://openstates.org/find_your_legislator/",
  oneNumber: true,
  // Shown after the second year's floor votes are over.
  diesAfterFloor: (y2) => `Unless a special session takes it up, it dies when the Legislature ends in January ${y2 + 1}.`,
  outOfTimeLine: "Died when the Legislature ended",

  committeeNext: {
    "Rules": "the Rules Committee decides whether and when it goes on the floor calendar.",
  },
  chairAsks: {
    "Rules": ["put it on the floor calendar", "keep it off the floor calendar"],
  },

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The ${y} session ended ${fmtDate(STATE.adjourns(y))}. Bills that didn't pass carry over to the ${y + 1} session, which opens ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > end && t < STATE.opens(y + 2))
      return `The ${y + 1} session ended ${fmtDate(end)}. Bills that didn't pass both houses died, except those taken up in a special session; the next Legislature opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} Legislature opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 20,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "121-day session"], ["light", a1, o2, "Interim"], ["", o2, a2, "121-day session"]],
      gov: [["light", o1, STATE.plusDays(a1, 90), "Acts on bills"], ["light", o2, STATE.plusDays(a2, 90), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The first session opens."],
        [a1, "down", LEG, MD(a1), "The session adjourns. Bills that didn't pass carry over."],
        [o2, "up", LEG, MD(o2), "The second session opens where the first left off."],
        [a2, "down", LEG, MD(a2), "The session adjourns. Bills that didn't pass both houses die, unless a special session takes them up."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The state's budget year starts."],
      ],
      note: "Bills reach the governor when the Legislature transmits them, often through the summer. The governor then has 15 days, or 20 after the Legislature adjourns (Sundays excepted), and can veto or reduce items in an appropriation bill. Overriding a veto takes the House and Senate meeting together: two-thirds of the 60 members (40), or three-fourths (45) for an appropriation bill. Laws take effect 90 days after the governor acts, unless the bill says otherwise.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members (independents are nonpartisan or undeclared)",
  openUntil: (s) => `the ${span(s)} Legislature ends in January ${s + 2}`,

  commIntro: [
    ["Bills go through each committee they're referred to, in order.", "The presiding officer refers a bill to one or more committees (most bills that cost money end with Finance). Each committee's chair decides whether it gets a hearing; many bills are heard and held more than once before a vote."],
    ["A committee's report lists each member's recommendation.", "\"Do pass\", \"do not pass\", \"amend\" or \"no recommendation\": a report sends the bill on even when some members oppose it, and a committee can rewrite it as a committee substitute (CS)."],
    ["Then the Rules Committee.", "After its last committee, a bill goes to the house's Rules Committee, which decides whether and when it goes on the floor calendar."],
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
    "Waiting in a committee, or in the Rules Committee after its last committee approved it. The Rules Committee decides which bills reach the floor.",
    "The Rules Committee put it on the calendar: second reading (amendments), then third reading (the vote).",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It goes to the governor when the Legislature transmits it, often weeks later.",
    "Delivered to the governor, who has 15 days during a session, or 20 after it (Sundays excepted).",
    "Signed into law, or became law without the governor's signature or over a veto: a chapter of the session laws.",
    "Vetoed by the governor. Overriding takes two-thirds of the 60 legislators meeting together (three-fourths for an appropriation bill).",
  ],
  pastStageTips: [
    "Never got out of committee before the Legislature ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This Legislature is over. Bills that didn't become law have to be introduced again in the next one.",

  // Both houses' committees mostly share names; the House also has special committees that take bills (Fisheries,
  // Energy, Military and Veterans' Affairs, Tribal Affairs, Ways and Means).
  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Finance", H: "Finance" },
  secondCommittee: "Bills that cost money end with the Finance Committee; then every bill goes to the Rules Committee, which decides which reach the floor.",
};
