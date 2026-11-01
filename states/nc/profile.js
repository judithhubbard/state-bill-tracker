// North Carolina: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "nc",
  name: "North Carolina",
  abbr: "NC",
  // Steps that aren't news on a watchlist card.
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed|Passed 1st Reading|Withdrawn From Com|Withdrawn From Cal|Regular Message|Special Message|Engrossed|Ordered Engrossed|Cal Pursuant|Serial Referral|Amend Tabled|Amend Failed|Added to Calendar|Placed On Cal|Placed on Today)/i,
  publicSite: "https://statebilltracker.org/nc/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  govReach: `<a href="https://governor.nc.gov/contact/contact-governor-stein" target="_blank" rel="noopener" data-contact="online|governor">Email the governor</a> · Raleigh <a class="phone" href="tel:+19198142000" data-contact="call|governor">(919) 814-2000</a>`,
  // Constitutional amendments are bills that pass both houses by three-fifths and go to the voters at the election the
  // act names; the governor can't veto them (North Carolina Constitution, Art. XIII, sec. 4).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "three-fifths of each house's members",
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || "";
    return d && d.slice(0, 4) < isoToday().slice(0, 4)
      ? "It went to the voters at the election the act named; the records here don't show the result."
      : "Next: the voters, at the election the act names (usually the next general election).";
  },
  // A law's number: "Session Law 2025-13".
  lawWord: "Session Law",

  // The General Assembly's bill page (history, versions, votes, summaries).
  billUrl: (p, session = DATA.session) => `https://www.ncleg.gov/BillLookUp/${session}/${p}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: history, text, votes and summary`)).join("<br>");
  },

  // A two-year session: the long session convenes in January of the odd year, the short session in the spring of the
  // even year; the General Assembly can reconvene through the end of the second year.
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);  // the second Monday
    const w = new Date(t); w.setDate(t.getDate() + 2);  // and the Wednesday after it
    return `${session}-01-${String(w.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => `${session + 1}-12-31`,
  floorVotesEnd: false,
  // The governor has 10 days to sign or veto a bill while the General Assembly is in session, and 30 days after it
  // adjourns (Art. II, sec. 22). Local bills, constitutional amendments and redistricting acts don't go to the governor.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c + 10);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (10 days during the session, 30 after it adjourns)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the session ends", () => "Bills that pass both houses are ratified by the presiding officers; public bills then go to the governor, while local bills become law at once."],
  passedBothNext: () => ({
    what: "the presiding officers ratify it, and a public bill goes to the governor, who can sign it or veto it. A bill the governor doesn't act on becomes law. A local bill becomes law when ratified.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://www.ncleg.gov/FindYourLegislators",
  oneNumber: true,
  diesAfterFloor: () => "The two-year session has ended, so it died with it.",
  outOfTimeLine: "Died when the session ended",

  // Every Senate bill is first sent to the Senate Rules Committee, which decides whether it goes to a committee.
  gates: { S: "Rules" },
  committeeNext: {
    "Rules": "the Rules Committee decides whether it goes on to a committee or the floor.",
  },
  chairAsks: {
    "Rules": ["send it on for a hearing or a vote", "keep it in the Rules Committee"],
  },
  sessionNotice: () => "",
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} session convenes ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-07-31`, "Long session"], ["light", `${Y}-08-01`, `${Y + 1}-04-20`, "Reconvenes as needed"],
        ["", `${Y + 1}-04-21`, `${Y + 1}-07-31`, "Short session"], ["light", `${Y + 1}-08-01`, close, "Reconvenes as needed"]],
      gov: [["light", open, close, "10 days to act on each public bill"]],
      events: [
        [open, "up", LEG, MD(open), "The long session convenes."],
        [`${Y}-05-01`, "down", LEG, "Spring", "Crossover: most bills must have passed one house to stay alive."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The two-year budget is due before the fiscal year starts."],
        [close, "down", LEG, MD(close), "The two-year session ends. Bills that didn't become law die."],
      ],
      note: "The governor has 10 days to act on a public bill while the General Assembly is in session, and 30 days after it adjourns. Local bills and constitutional amendments don't go to the governor. Overriding a veto takes three-fifths of each house's members present and voting.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's member lists",
  openUntil: (s) => `the two-year session ends in ${s + 1}`,

  commIntro: [
    ["Senate bills start in the Rules Committee.", "Every Senate bill is first sent to the Senate Rules Committee, which decides whether it goes on to a committee on its subject."],
    ["Bills often go to several committees.", "A referral like \"Judiciary, if favorable, Rules\" sends a bill to one committee after another; Appropriations and Finance see bills with a cost."],
    ["Local bills are different.", "Bills for one city or county pass with the support of that area's legislators and become law when ratified, without the governor."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Law", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. Senate bills start in the Rules Committee, which decides whether they go on.",
    "A committee reported it favorably, and it waits for the calendar and the second and third readings.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses and ratified. A public bill goes to the governor; a local bill is already law.",
    "Presented to the governor, who has 10 days (30 after the session adjourns) to sign or veto it.",
    "Became law (a Session Law): signed, ratified as a local bill, passed over a veto, or not acted on.",
    "Vetoed by the governor. Overriding a veto takes three-fifths of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee reported it, but it never passed the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in the next one.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations/Base Budget", H: "Appropriations" },
  secondCommittee: "Bills with a cost go on to Appropriations or Finance.",
};
