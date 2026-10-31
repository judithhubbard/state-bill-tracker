// Ohio: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "oh",
  name: "Ohio",
  abbr: "OH",
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced|INTRODUCED|Informally passed|Conference managers|Removed from|Added as|Motion to|Reported - Re-referred|Line item veto receipt|line item veto receipt)/i,
  publicSite: "https://statebilltracker.org/oh/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 136th General Assembly).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  govReach: `<a href="https://governor.ohio.gov/" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · Columbus <a class="phone" href="tel:+16144663555" data-contact="call|governor">(614) 466-3555</a>`,

  // The Legislative Service Commission's API serves each bill's texts.
  billUrl: (p, session = DATA.session) => `https://www.legislature.ohio.gov/legislation/${(session - 1753) / 2}/${p.toLowerCase()}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const ga = (DATA.session - 1753) / 2;
    return b.vers.map((v) => `${link(STATE.billUrl(v.p), `${esc(v.p)}: status and history`)} · ${link(`https://search-prod.lis.state.oh.us/api/v2/general_assembly_${ga}/legislation/${v.p.toLowerCase()}/00_IN/html/`, "text as introduced")}`).join("<br>");
  },

  // A General Assembly convenes the first Monday of January of an odd year and sits until December 31 of the next.
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7));
    return `${session}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => `${session + 1}-12-31`,
  // A full-time Legislature: it can vote until the General Assembly ends.
  floorVotesEnd: false,
  // The governor has 10 days, Sundays excepted, after a bill is presented; a bill not returned becomes law (Ohio
  // Constitution, Art. II, sec. 16).
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 10;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (10 days after it reached the governor, Sundays excepted)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the General Assembly ends", () => "Bills that pass both houses are signed by the presiding officers, then sent to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate President sign it, and it goes to the governor, who has 10 days to sign or veto it (or veto items in a spending bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, village or county",
  addressLookup: true,
  findReps: "https://www.legislature.ohio.gov/legislators/find-my-legislators",
  oneNumber: true,
  diesAfterFloor: () => "The General Assembly has ended, so it died with it.",
  outOfTimeLine: "Died when the General Assembly ended",

  // Each house's Rules and Reference Committee, chaired by the presiding officer, schedules floor votes.
  committeeNext: {
    "Rules and Reference": "the Rules and Reference Committee, which the leaders chair, decides whether it gets a floor vote.",
  },
  chairAsks: {
    "Rules and Reference": ["schedule it for a floor vote", "keep it off the floor calendar"],
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t.startsWith(String(y + 1)) && t.slice(5) >= "11-15")
      return `The ${(y - 1753) / 2}th General Assembly ends December 31, ${y + 1}; bills that haven't passed both houses by then die. The next one convenes in January.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${(raw.session - 1753) / 2}th General Assembly convenes ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-06-30`, "Budget year"], ["light", `${Y}-07-01`, `${Y}-12-31`, "Session continues"],
        ["", `${Y + 1}-01-01`, `${Y + 1}-06-30`, "Session"], ["light", `${Y + 1}-07-01`, close, "Election year: fewer sessions"]],
      gov: [["light", open, close, "10 days to act on each bill"]],
      events: [
        [open, "up", LEG, MD(open), "The General Assembly convenes."],
        [`${Y}-06-30`, "down", LEG, "June 30", "The two-year operating budget is due before the fiscal year starts July 1."],
        [`${Y + 1}-11-03`, "up", LEG, "November", "Election; the lame-duck session follows."],
        [close, "down", LEG, MD(close), "The General Assembly ends. Bills that didn't pass both houses die."],
      ],
      note: "The governor has 10 days (Sundays excepted) to sign or veto a bill, and can veto items in a spending bill. Overriding a veto takes three-fifths of each house. Most new laws take effect 90 days after the governor signs them.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's list of members",
  openUntil: (s) => `the General Assembly ends December 31, ${s + 1}`,

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
    "Waiting in a committee, which holds hearings and votes on whether to report it to the floor.",
    "A committee reported it, and it waits for the Rules and Reference Committee to schedule a vote of the full House or Senate.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The presiding officers sign it, then it goes to the governor.",
    "Sent to the governor, who has 10 days (Sundays excepted) to sign or veto it.",
    "Signed into law, or became law without the governor's signature.",
    "Vetoed by the governor. Overriding a veto takes three-fifths of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the General Assembly ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be introduced again in the next one.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Finance", H: "Finance" },
  secondCommittee: "Bills that spend money often go on to the Finance Committee; a committee can also send a bill to the Rules and Reference Committee, which schedules floor votes.",
};
