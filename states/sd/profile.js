// South Dakota: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "sd",
  name: "South Dakota",
  abbr: "SD",
  // Steps that aren't news on a watchlist card.
  routine: /^(Scheduled for hearing|Motion to amend|Amend the amendment|Certified uncontested|Deferred to another day|Intent to reconsider|First Reading (?:House|Senate)|Remove from Consent|Removed from Consent|Conference Committee appointments|Prime Sponsor Changed|PLACED ON FLOOR|ENROLLED)/i,
  publicSite: "https://statebilltracker.org/sd/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  // Joint resolutions proposing constitutional amendments pass once, by a majority of each house's members, then go to
  // the voters at the next general election (November of an even year); never to the governor (South Dakota
  // Constitution, Art. XXIII, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://governor.sd.gov/office/contact.aspx" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Pierre <a class="phone" href="tel:+16057733212" data-contact="call|governor">(605) 773-3212</a>`,

  // The Legislature's bill page, addressed by its own bill id (a version's `link`).
  billUrl(p) {
    const v = (BILLS || []).flatMap((b) => b.vers).find((x) => x.p === p);
    return v?.link || `https://sdlegislature.gov/Session/Bills/${DATA.session}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text and votes`)).join("<br>");
  },

  // The session opens the second Tuesday of January and lasts 40 legislative days in odd years, 35 in even years; the
  // last regular day is in mid-March, and the Legislature returns for one day near the end of March to consider vetoes
  // (South Dakota Constitution, Art. III, sec. 7). `dated` holds a year whose last regular day differs.
  dated: { 2026: "2026-03-12" },
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => STATE.nth(year, 1, 2, 2),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 58),
  vetoDay: (year) => STATE.plusDays(STATE.sessionEnds(year), 18),
  // The governor has 5 days (Sundays excepted) during the session; a bill presented in the session's last days gets 15
  // days after adjournment (Art. IV, sec. 4).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const plus = (from, n, sundays) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (sundays || t.getDay() !== 0) n--; } return ymd(t); };
    const end = STATE.sessionEnds(+iso.slice(0, 4)), five = plus(iso, 5, false);
    return five <= end ? five : plus(end > iso ? end : iso, 15, true);
  },
  dueLabel: () => "Governor's decision due (5 days during the session, 15 days after it)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the Speaker and the Senate President, then go to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate President sign it, and it goes to the governor, who can sign it or veto it (or veto items in an appropriation bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://sdlegislature.gov/Legislators/Find",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // There are only 40 legislative days, so deferring a bill to the 41st kills it.
  heldLabel: "Deferred to the 41st day",
  heldTip: "Killed in committee: the session has only 40 legislative days, so a bill deferred to the 41st never comes back. Committees kill most bills this way, or by tabling them.",
  heldNote: "killed in committee by deferring it to the 41st legislative day (the session has only 40) or tabling it.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session's regular days ended ${fmtDate(end)}; the Legislature returned ${fmtDate(STATE.vetoDay(y))} to consider vetoes. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), veto = STATE.vetoDay(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, "Session"], ["light", veto, veto, "Veto day"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "15 days"]],
      events: [
        [open, "up", LEG, MD(open), Y % 2 ? "The session opens (40 legislative days)." : "The session opens (35 legislative days)."],
        [adj, "down", LEG, MD(adj), "The last regular day. Bills that didn't pass both houses die."],
        [veto, "up", LEG, MD(veto), "Veto day: the Legislature returns to consider the governor's vetoes."],
        [`${Y}-07-01`, "down", LEG, "July 1", "Most new laws take effect."],
      ],
      note: "During the session the governor has 5 days (Sundays excepted) to act on a bill; bills that arrive at the end get 15 days after adjournment, and become law unless vetoed. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill starts in a committee on its subject.", "Each house has its own committees with the same subjects (Agriculture and Natural Resources, Judiciary, State Affairs and so on). Every bill gets a hearing."],
    ["Committees kill bills by deferring them.", "The session has 40 legislative days, so a committee that defers a bill \"to the 41st day\" ends it; tabling does the same."],
    ["Uncontested bills go on the consent calendar.", "A committee can put a bill no one opposed on the consent calendar, where the house passes them together."],
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
    "In a committee, which holds a hearing and votes on whether to recommend it (\"do pass\").",
    "A committee recommended it, and it's on the House or Senate calendar for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate President sign it, then it goes to the governor.",
    "Sent to the governor, who has 5 days (Sundays excepted) during the session or 15 days after it.",
    "Signed into law (or became law without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Killed in committee, or never got out of committee before the session ended.",
    "A committee recommended it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that spend money often go on to the Appropriations Committee.",
};
