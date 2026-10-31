// Connecticut: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ct",
  name: "Connecticut",
  abbr: "CT",
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed with lco|Rptd\. out of lco|File no\.|Referred to olr|House calendar number|Senate calendar number|Vote to draft|Drafted by committee|Transmitted to secretary of the state|Transmitted pursuant|Reserved for subject matter|Immediate transmittal|Rules suspended|Public hearing|House adopted|Sen\. adopted|House rejected|Sen\. rej\.|Amendment withdrawn|Public act|Special act|In concurrence|On consent calendar)/i,
  publicSite: "https://statebilltracker.org/ct/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  govReach: `<a href="https://portal.ct.gov/governor/contact/email-governor-lamont" target="_blank" rel="noopener" data-contact="online|governor">Email the governor</a> · Hartford <a class="phone" href="tel:+18605664840" data-contact="call|governor">(860) 566-4840</a>`,

  // The General Assembly's bill status page, and the bill as introduced.
  billUrl: (p, session = DATA.session) => `https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&which_year=${session}&bill_num=${p.slice(2)}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)}: status, text and votes`)).join("<br>");
  },

  // Sessions open the Wednesday after the first Monday of January (odd years) or February (even years) and adjourn
  // the Wednesday after the first Monday of June (odd) or May (even) (Connecticut Constitution, Art. III, sec. 2).
  wedAfterFirstMonday(year, month) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 2);
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => STATE.wedAfterFirstMonday(year, year % 2 ? 1 : 2),
  sessionEnds: (year) => STATE.wedAfterFirstMonday(year, year % 2 ? 6 : 5),
  // The governor has 5 days (Sundays and holidays excepted) during the session; a bill presented after it adjourns,
  // or too late to return, gets 15 days (Art. IV, sec. 15).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 5;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return ymd(t) <= STATE.sessionEnds(a) ? ymd(t) : ymd(new Date(a, b - 1, c + 15));
  },
  dueLabel: () => "Governor's decision due (5 days during the session, 15 after it)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses get a Public Act number and go to the governor through the Secretary of the State."],
  passedBothNext: () => ({
    what: "it gets a Public Act number and goes to the governor, who can sign it or veto it (or veto items in a budget bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "Town",
  addressLookup: true,
  findReps: "https://www.cga.ct.gov/asp/menu/cgafindleg.asp",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again next year.",
  outOfTimeLine: "Died when the session adjourned",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, Y % 2 ? "Long session" : "Short session"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "15 days"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens. Committees hold public hearings and must report bills by their deadlines."],
        [adj, "down", LEG, MD(adj), "The session adjourns at midnight. Bills that didn't pass both houses die."],
        [`${Y}-10-01`, "down", LEG, "October 1", "Most new laws take effect."],
      ],
      note: "The governor has 5 days (Sundays and holidays excepted) to act on a bill during the session, or 15 days for bills that arrive after it adjourns, and can veto items in a budget bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's legislator database",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  // Committees are joint: the same committee hears a bill for both houses.
  commIntro: [
    ["Committees are joint.", "Each committee has members from both the House and the Senate, and hears bills from both. A bill's committee holds a public hearing, then votes on a \"Joint Favorable\" report."],
    ["Committees have deadlines.", "Each committee must report its bills by a deadline set each session; bills that miss it usually die there."],
    ["Some bills need a second committee.", "Bills that cost money go on to Appropriations or Finance, Revenue and Bonding; others are sent on with a change of reference."],
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
    "Waiting in a committee. Connecticut's committees are joint (House and Senate members together) and must report bills by a deadline.",
    "A committee reported it favorably, and it's on the House or Senate calendar for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses and got a Public Act number; it goes to the governor through the Secretary of the State.",
    "Sent to the governor, who has 5 days during the session or 15 after it.",
    "Signed into law (or became law without the governor's signature).",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session adjourned.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that cost money go on to Appropriations or Finance, Revenue and Bonding.",
};
