// Michigan: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "mi",
  name: "Michigan",
  abbr: "MI",
  // Steps that aren't news on a watchlist card.
  routine: /^(read a first time|bill electronically reproduced|introduced by|INTRODUCED BY|read a second time|read a third time|transmitted|received on|RULES SUSPENDED|rule suspended|PASSED BY (HOUSE|SENATE)|inserted full title|INSERTED FULL TITLE|full title agreed|FULL TITLE AGREED|title amended|GIVEN IMMEDIATE EFFECT|COMMITTEE RECOMMENDED IMMEDIATE EFFECT|laid over one day|filed with Secretary|FILED WITH SECRETARY|assigned PA|ASSIGNED PA|returned to (House|Senate)|RETURNED TO (HOUSE|SENATE)|roll call Roll Call)/i,
  publicSite: "https://statebilltracker.org/mi/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 103rd Legislature).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // A law's number: "Public Act 2 of 2025".
  lawWord: "Public Act",
  govReach: `<a href="https://somgovweb.state.mi.us/ContactGovernor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Lansing <a class="phone" href="tel:+15173357858" data-contact="call|governor">(517) 335-7858</a>`,

  // The Legislature's bill page is addressed by the year the bill was introduced ("2026-SB-0968"): a version's "link".
  billUrl(p) {
    const v = (BILLS || []).flatMap((b) => b.vers).find((x) => x.p === p);
    return v?.link || "https://www.legislature.mi.gov/Bills";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text, analyses and votes`)).join("<br>");
  },

  // A Legislature convenes the second Wednesday of January of an odd year and sits until the end of the next year.
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7) + 7);
    return `${session}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => `${session + 1}-12-31`,
  // A full-time Legislature: it can vote until the session ends.
  floorVotesEnd: false,
  // The governor has 14 days, Sundays excepted, after a bill is presented; a bill not returned becomes law, unless the
  // Legislature has adjourned for good (Michigan Constitution, Art. IV, sec. 33).
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 14;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (14 days after it reached the governor, Sundays excepted)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the session ends", () => "Bills that pass both houses are enrolled, then presented to the governor."],
  passedBothNext: () => ({
    what: "it's enrolled and presented to the governor, who has 14 days to sign or veto it (or veto items in a spending bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or township",
  addressLookup: true,
  findReps: "https://www.michigan.gov/sos/elections/voters/district-lookup",
  oneNumber: true,
  diesAfterFloor: () => "The Legislature's two-year session has ended, so it died with it.",
  outOfTimeLine: "Died when the session ended",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t.startsWith(String(y + 1)) && t.slice(5) >= "11-15")
      return `The ${span(y)} session ends December 31, ${y + 1}; bills that haven't passed both houses by then die. The next Legislature convenes in January.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} Legislature convenes ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-06-30`, "Session"], ["light", `${Y}-07-01`, `${Y}-12-31`, "Session continues"],
        ["", `${Y + 1}-01-01`, `${Y + 1}-06-30`, "Session"], ["light", `${Y + 1}-07-01`, close, "Election year: fewer sessions"]],
      gov: [["light", open, close, "10 days to act on each bill"]],
      events: [
        [open, "up", LEG, MD(open), "The Legislature convenes."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The budget is due by law, ahead of the fiscal year that starts October 1."],
        [`${Y + 1}-11-03`, "up", LEG, "November", "Election; the lame-duck session follows."],
        [close, "down", LEG, MD(close), "The session ends. Bills that didn't pass both houses die."],
      ],
      note: "The governor has 14 days (Sundays excepted) to sign or veto a bill, and can veto items in a spending bill. Overriding a veto takes two-thirds of each house. A law takes effect 91 days after the session's year ends, unless two-thirds of each house give it immediate effect.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the caucus websites the Legislature lists for each member",
  openUntil: (s) => `the session ends December 31, ${s + 1}`,

  commIntro: [
    ["Every bill starts in a committee on its subject.", "The Speaker or the Senate Majority Leader sends it to a standing committee; the chair decides whether it gets a hearing and a vote."],
    ["Then the floor.", "A House bill a committee reports goes to second and third reading; in the Senate, to the Committee of the Whole and then third reading."],
    ["Bills that spend money go to Appropriations.", "Each house's Appropriations Committee writes the budget bills and decides many bills with a cost."],
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
    "Waiting in a committee. The chair decides whether it gets a hearing and a vote.",
    "A committee reported it, and it waits for the full House (second and third reading) or Senate (the Committee of the Whole, then third reading).",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The presiding officers sign it, then it goes to the governor.",
    "Presented to the governor, who has 14 days (Sundays excepted) to sign or veto it.",
    "Signed into law (a public act), or became law without the governor's signature.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in the next Legislature.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that spend money often go on to the Appropriations Committee.",
};
