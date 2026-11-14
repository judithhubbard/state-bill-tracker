// Massachusetts: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ma",
  // What the Legislature is called in sentences ("the General Court isn't meeting until ...").
  bodyName: "the General Court",
  name: "Massachusetts",
  abbr: "MA",
  // Steps that aren't news on a watchlist card.
  routine: /^(Senate concurred|House concurred$|Hearing (?:scheduled|rescheduled|canceled|updated)|Location Changed|Reporting date extended|No further action take|Amendment \(changing reporting date|Rules suspended|Emergency preamble|Read second$|Read third$|Taken out of the Orders|Read; and placed|New draft of|Pending new draft|New draft substituted|Committee of conference (?:appointed|membership)|For message, see|Returned from the Secretary|Read for its information)/i,
  publicSite: "https://statebilltracker.org/ma/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a two-year General Court).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Constitutional amendments the Legislature proposes never go to the governor. The House and Senate meet together in a
  // joint session (a constitutional convention); approved there by a majority of all 200 members in two General Courts
  // in a row, one goes to the voters at the next state election, in an even year (Amendments, Art. 48). The second
  // approval is recorded as "Amendment again agreed to", on the document the next General Court takes "from the files".
  amendments: true,
  amendmentVote: "a joint session of both houses, by a majority of all members, in two General Courts in a row",
  ballotEvenYears: true,
  amendmentFinal: (b) => b.vers.some((v) => v.actions.some(([, t]) => /^Amendment again agreed to\b/i.test(t))),
  amendmentAgain: (b) => `Next: the next General Court, elected in November ${DATA.session + 1}, has to approve it again in a joint session; then it goes to the voters.`,
  govReach: `<a href="https://www.mass.gov/orgs/office-of-the-governor" target="_blank" rel="noopener" data-contact="online|governor">The governor's office</a> · Boston <a class="phone" href="tel:+16177254005" data-contact="call|governor">(617) 725-4005</a> · toll-free in Massachusetts <a class="phone" href="tel:+18888707770" data-contact="call|governor">(888) 870-7770</a>`,

  // The General Court's bill page (status, text and history). 2025 is the 194th General Court.
  court: (session) => (session - 1637) / 2,
  billUrl: (p, session = DATA.session) => `https://malegislature.gov/Bills/${STATE.court(session)}/${p}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text and history`)).join("<br>");
  },

  // A General Court opens the first Wednesday of January in odd years and lasts two years. Formal sessions, with
  // roll calls and debate, end July 31 of the second year (Joint Rule 12A); after that, informal sessions pass only
  // bills no one objects to, until the next General Court opens.
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7));
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  formalEnds: (session) => `${session + 1}-07-31`,
  sessionEnds(session) {
    const [y, m, d] = STATE.opens(session + 2).split("-").map(Number), t = new Date(y, m - 1, d - 1);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The governor has 10 days to sign, veto or return a bill with amendments (Amendments, Art. 90 and 56).
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c + 10);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (10 days)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the General Court ends", () => "Bills that pass both houses are enacted by each, then laid before the governor."],
  passedBothNext: () => ({
    what: "the House and then the Senate vote to enact it, and it goes to the governor, who can sign it, veto it, send it back with amendments, or veto items in a spending bill. A bill the governor doesn't act on within 10 days becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or town",
  addressLookup: true,
  findReps: "https://malegislature.gov/Search/FindMyLegislator",
  oneNumber: true,
  diesAfterFloor: (y2) => `It dies when the General Court ends in January ${y2 + 1}, unless it passes in an informal session, which takes every member's consent.`,
  outOfTimeLine: "Died when the General Court ended",

  // A joint committee that won't move a bill usually sends it to a "study order", which ends it for the session.
  heldAction: "SENT TO STUDY",
  heldLabel: "Sent to study",
  heldTip: "The committee sent it to a study order, which ends it for this session; the study itself rarely happens.",
  heldNote: "the committee sent it to a study order, the usual way Massachusetts committees end a bill for the session.",
  committeeNext: {
    "House Steering, Policy and Scheduling": "the House Steering, Policy and Scheduling Committee, run by the Speaker's team, decides whether it gets a floor vote.",
    "House Ways and Means": "House Ways and Means decides whether it goes on to the floor.",
    "Senate Ways and Means": "Senate Ways and Means decides whether it goes on to the floor.",
  },
  chairAsks: {
    "House Steering, Policy and Scheduling": ["schedule it for a floor vote", "keep it off the calendar"],
  },

  // The note above the bill list (empty while formal sessions run).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y), formal = STATE.formalEnds(y);
    if (t > end) return "";
    if (t > formal)
      return `Formal sessions ended ${fmtDate(formal)}. Until the General Court ends ${fmtDate(end)}, the House and Senate meet in informal sessions, where a bill passes only if no member objects. Bills still waiting then die.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} General Court opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o = STATE.opens(Y), f = STATE.formalEnds(Y), e = STATE.sessionEnds(Y);
    return {
      leg: [["", o, f, "Formal sessions"], ["light", f, e, "Informal sessions"]],
      gov: [["light", o, STATE.govDeadline(e), "Acts on bills (10 days each)"]],
      events: [
        [o, "up", LEG, MD(o), "The General Court opens. Bills filed by mid-January get a public hearing in a joint committee."],
        [`${Y + 1}-07-01`, "up", LEG, "July 1", "The state budget is due (it's often late)."],
        [f, "down", LEG, MD(f), "Formal sessions end. After this, bills pass only if no member objects."],
        [e, "down", LEG, MD(e), "The General Court ends. Bills that didn't become law die."],
      ],
      note: "The governor has 10 days to sign or veto a bill, or to send it back with amendments; items in spending bills can be vetoed one by one. Overriding a veto takes two-thirds of each house. Most new laws take effect 90 days after they're signed; an emergency preamble makes one take effect at once.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Court's list of members",
  openUntil: (s) => `the ${span(s)} General Court ends in January ${s + 2}`,

  // Almost all committees are joint: members of both houses hear every bill on their subject.
  commIntro: [
    ["Committees are joint.", "Almost every committee has members of both the House and the Senate, with a House chair and a Senate chair. Every bill gets a public hearing."],
    ["Committees report by a deadline.", "The joint rules set a date for each committee to report; it's often extended. Most bills a committee won't move are sent to a \"study order\", which ends them for the session."],
    ["Then each house's own committees.", "A bill a joint committee approves usually goes to House or Senate Ways and Means, and in the House to Steering, Policy and Scheduling, which decides when it reaches the floor."],
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
    "Waiting in a committee. Most are joint committees of House and Senate members; a bill they approve usually goes on to Ways and Means.",
    "Reported to the full House or Senate and waiting for its readings and a vote.",
    "Passed (\"engrossed\") by the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. Each votes to enact it, then it goes to the governor.",
    "Laid before the governor, who has 10 days to sign it, veto it or send it back with amendments.",
    "Signed into law (or became law without the governor's signature), with a chapter number in the Acts of the year.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the General Court ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it was never enacted and sent to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Court is over. Bills that didn't become law have to be filed again in the next one.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Senate Ways and Means", H: "House Ways and Means" },
  secondCommittee: "Bills that cost money go on to House or Senate Ways and Means.",
};
