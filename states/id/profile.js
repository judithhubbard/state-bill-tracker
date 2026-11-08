// Idaho: the page's settings and rules that are particular to this state. build_data.py puts this file into every page,
// just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "id",
  name: "Idaho",
  abbr: "ID",
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced \(a committee asked|Read the (?:first|second) time|Held on the calendar|Floor sponsor:|The (?:House|Senate) vote:|Received from the|Signed by the (?:President|Speaker)|Back from the (?:House|Senate) with|Filed in the office|Enrolled; signed|Returned from the (?:House|Senate), passed; sent to be enrolled|Amendments|Bills? as Amended|Reported [Ee]ngrossed|Read first time as amended|Filed for First Reading|Takes effect:|Printed and placed|Sent to the whole|Placed on the order|Came out of the amending|The .* Committee recommended it pass|Notice to reconsider|U\.C\.|Read Third Time in Full –|Read third time in full –|Ret’d|File for)/i,
  publicSite: "https://statebilltracker.org/id/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year (the two-year Legislature's bills die when each year's session adjourns).
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are chapters of each year's Session Laws ("Chapter 296" of 2025).
  lawWord: "Chapter",
  // A joint resolution proposing an amendment to the Idaho Constitution passes each house once, by two-thirds of its
  // members, and goes to the voters at the next general election, never to the governor (Art. XX, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://gov.idaho.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Boise <a class="phone" href="tel:+12083342100" data-contact="call|governor">(208) 334-2100</a>`,

  // The Legislature's bill page: /sessioninfo/2025/legislation/H0003/ (each version's `link`, from convert.py).
  billUrl(p, session = DATA.session) {
    const m = /^([A-Z]+)(\d+)$/.exec(p), n = m ? m[2].padStart(m[1].length > 1 ? 3 : 4, "0") : "";
    return `https://legislature.idaho.gov/sessioninfo/${session}/legislation/${m ? m[1] + n : p}/`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: text, Statement of Purpose, amendments and votes`)).join("<br>");
  },

  // The session opens the second Monday of January and has no fixed length; it adjourns sine die in late March or April.
  // `dated` holds each year's last floor day, when bills that haven't passed die (add each year's).
  dated: { 2024: "2024-04-10", 2025: "2025-04-04", 2026: "2026-04-02" },
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => STATE.nth(year, 1, 1, 2),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // Days counted with Sundays excepted.
  plusWeekdays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d);
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 85),
  // The governor has 5 days (Sundays excepted) after a bill is presented while the Legislature is in session; a bill it
  // can't be returned to because the Legislature adjourned becomes law unless vetoed within 10 days (Sundays excepted)
  // after adjournment (Constitution, Art. IV, sec. 10). There's no pocket veto: a bill the governor doesn't act on
  // becomes law.
  govDeadline(iso) {
    if (!iso) return null;
    const end = STATE.sessionEnds(+iso.slice(0, 4)), five = STATE.plusWeekdays(iso, 5);
    return five <= end ? five : STATE.plusWeekdays(end > iso ? end : iso, 10);
  },
  dueLabel: () => "Governor's decision due (5 days during the session, Sundays excepted; 10 days after it adjourns)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the Speaker and the President of the Senate, and delivered to the governor, usually within a day or two."],
  passedBothNext: () => ({
    what: "it's enrolled, signed by the Speaker and the President of the Senate, and delivered to the governor, who has 5 days (Sundays excepted) to sign it or veto it, or 10 days after the session adjourns. A bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: true,
  findReps: "https://legislature.idaho.gov/legislators/whosmylegislator/",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // Idaho's histories don't record a committee holding a bill: a bill its committee never reports out just stays there
  // and dies when the session adjourns.
  heldLabel: "Held in committee",
  heldTip: "The committee voted to keep it, which ends it for the session.",
  heldNote: "the committee voted to hold it, which ends it for the session.",
  // Bills that die after leaving committee were mostly voted down on the floor, not left waiting: the Statistics charts
  // say "died on the floor".
  oddsExits: ["Died in committee", "Died on the floor"],
  fateLabels: { floor: "Died on the floor" },
  // A bill voted down on the floor is dead at once, unless the house reconsiders the vote (usually the next day).
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const i = texts.findLastIndex((t) => /^Failed to pass the (House|Senate)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |^The (House|Senate) voted to reconsider/.test(t))) return null;
    const h = texts[i].match(/the (House|Senate)/)[1];
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `${texts[i].replace(/ \(.*$/, "")} on ${fmtDate(acts[i][0])}.`,
      tail: "That ends it, unless the house reconsiders the vote.",
    };
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t < `${y + 1}-01-01`)
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, "Session"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "10 days"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens (the governor's State of the State address). Committees hold print hearings to introduce bills."],
        [adj, "down", LEG, MD(adj), "The session adjourns sine die. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "July 1", "Most new laws take effect, and the state's budget year starts."],
      ],
      note: "During the session the governor has 5 days (Sundays excepted) to act on a bill; after the session adjourns, 10 days. A bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of the members present in each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's committee and member lists",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["A committee introduces the bill.", "Most bills are introduced by a committee, at a \"print hearing\" where a member presents the idea and the committee votes to print it; the bill then carries the committee's name, not the member's. A member can also introduce a bill personally, but those are filed with the clerk and rarely go further."],
    ["A standing committee holds the hearing.", "The printed bill goes to a standing committee (often the one that introduced it), which takes public testimony and votes. A bill the committee never reports out dies there when the session adjourns."],
    ["Reported bills go to the floor.", "A \"do pass\" bill goes on the calendar for second and third reading; one the committee wants amended goes to the amending stage first (General Orders in the House, the 14th Order in the Senate)."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died on the floor (voted down, or never voted on)", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Printed and sent to a standing committee (or still at the desk). The committee decides whether to report it out.",
    "Reported out by its committee and on the floor: the amending stage (General Orders in the House, the 14th Order in the Senate) or the calendar for third reading.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, signed by the Speaker and the President of the Senate, and delivered to the governor.",
    "Delivered to the governor, who has 5 days (Sundays excepted) to sign or veto it, or 10 days after the session adjourns; if the governor does neither, it becomes law.",
    "Became law: signed, or became law without the governor's signature or over a veto. Laws are chapters of each year's Session Laws.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of the members present in each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session adjourned (or was never sent to one).",
    "Reported out of committee, but voted down on the floor or never brought to a vote.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Judiciary and Rules": ["Judiciary, Rules and Administration", "Courts and crime"],
    "Resources and Environment": ["Resources and Conservation", "Natural resources"],
    "Transportation": ["Transportation and Defense", "Transportation"],
    "Finance": ["Appropriations", "The budget"],
    "Local Government and Taxation": ["Revenue and Taxation", "Taxes and local government"],
  },
  commNotes: {
    "Finance": "The Senate Finance and House Appropriations Committees meet together as the Joint Finance-Appropriations Committee (JFAC), which writes the budget bills; each house's committee introduces its share, and they go straight to the floor.",
    "Local Government and Taxation": "The Senate's Local Government and Taxation Committee takes both; the House has a Revenue and Taxation Committee and a Local Government Committee.",
  },
  moneyCommittees: { S: "Finance", H: "Appropriations" },
  secondCommittee: "The budget bills are written by the Joint Finance-Appropriations Committee (the Senate Finance and House Appropriations Committees together) and go straight to the floor.",
};
