// Connecticut: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ct",
  name: "Connecticut",
  abbr: "CT",
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed with lco|Rptd\. out of lco|File no\.|Referred to olr|House calendar number|Senate calendar number|Vote to draft|Drafted by committee|Transmitted to secretary of the state|Transmitted pursuant|Reserved for subject matter|Immediate transmittal|Rules suspended|Public hearing|House adopted|Sen\. adopted|House rejected|Sen\. rej\.|Amendment withdrawn|Public act|Special act|In concurrence|On consent calendar)/i,
  publicSite: "https://statebilltracker.org/ct/",
  listsApi: "https://state-lists.lists-worker.workers.dev",
  houses: { S: "Senate", H: "House" },
  // The picture at the top of How (tracker.html's renderHowPic()): how bills move ("twins": the same bill filed in
  // both houses moves in each until both pass the same text; "relay": one bill goes house to house), what a bill the
  // governor doesn't sign does ("law" or "dies" lines, each with an optional ⓘ tip), and who can override a veto.
  tracks: "relay",
  unsigned: [{ law: "Not signed in 5 days: becomes law", tip: "Sundays and holidays excepted; 15 days if the session adjourns first." }],
  override: "Two-thirds can override",
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  // Constitutional amendments (joint resolutions, HJ and SJ) never go to the governor. Adopted by three-fourths of each
  // house's members, one goes to the voters at the next general election (even Novembers); adopted by a majority but
  // less, it has to be adopted again, by a majority, by the Legislature elected next, then goes to the voters
  // (Connecticut Constitution, Art. XII). The files have no votes, but the history says when a house adopted it "but
  // not by the necessary 3/4ths" or "failed to adopt by 3/4".
  amendments: true,
  amendmentOnce: true,
  ballotEvenYears: true,
  amendmentVote: "both houses by three-fourths, or by a majority in two Legislatures with an election between",
  amendmentFinal(b) {
    const short = b.vers.some((v) => v.actions.some(([, t]) => /3\/4/.test(t)));
    if (!short) return true;
    // A second adoption: the same amendment passed both houses in a session before the last election (even years).
    return b.earlier.some((e) => e[2] >= 3 && (e[0] % 2 ? e[0] + 1 : e[0]) < DATA.session);
  },
  amendmentAgain(b) {
    const y = +([b.dates.passS, b.dates.passA].sort().pop() || String(DATA.session)).slice(0, 4), vote = y % 2 ? y + 1 : y;
    return `Next: it passed with less than three-fourths, so the Legislature elected in November ${vote} has to pass it again, by a majority of each house; then it goes to the voters.`;
  },
  govReach: `<a href="https://portal.ct.gov/governor/contact/email-governor-lamont" target="_blank" rel="noopener" data-contact="online|governor">Email the governor</a> · Hartford <a class="phone" href="tel:+18605664840" data-contact="call|governor">(860) 566-4840</a>`,

  // The General Assembly's bill status page, and the bill as introduced.
  // A resolution's number is written in full ("HJ00032"), since resolutions and bills are numbered separately.
  billUrl: (p, session = DATA.session) => `https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&which_year=${session}&bill_num=${p[1] === "J" ? p.slice(0, 2) + p.slice(2).padStart(5, "0") : p.slice(2)}`,
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
  // The state's legal holidays in the months of a regular session (C.G.S. sec. 1-4: New Year's Day, Martin Luther King
  // Day, Lincoln's Birthday, Washington's Birthday, Memorial Day; a fixed date on a Sunday is kept the Monday after, on a
  // Saturday the Friday before), and Good Friday, which the governor proclaims each year.
  holidays(y) {
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const fixed = (m, d) => { const t = new Date(y, m - 1, d); t.setDate(d + (t.getDay() === 0 ? 1 : t.getDay() === 6 ? -1 : 0)); return ymd(t); };
    const monday = (m, from) => { const t = new Date(y, m - 1, from); t.setDate(from + ((1 - t.getDay() + 7) % 7)); return ymd(t); };
    // Easter (the anonymous Gregorian computus), then the Friday before it.
    const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
    const em = Math.floor((h + l - 7 * m + 114) / 31), ed = ((h + l - 7 * m + 114) % 31) + 1;
    const lastMonMay = new Date(y, 4, 31); lastMonMay.setDate(31 - ((lastMonMay.getDay() + 6) % 7));
    return new Set([fixed(1, 1), monday(1, 15), fixed(2, 12), monday(2, 15), ymd(new Date(y, em - 1, ed - 2)), ymd(lastMonMay)]);
  },
  // "In case the governor shall not transmit the bill to the secretary, either with his approval or with his objections,
  // within five calendar days, Sundays and legal holidays excepted, after the same shall have been presented to him, it
  // shall be a law at the expiration of that period; except that, if the general assembly shall then have adjourned any
  // regular or special session, the bill shall be a law unless the governor shall, within fifteen calendar days after
  // the same has been presented to him, transmit it to the secretary with his objections" (Art. IV, sec. 15). "Then" is
  // the end of the five days: a bill presented in the session's last days, whose five days run past adjournment, gets
  // the fifteen days too, counted from presentment, as does one presented after.
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c), off = STATE.holidays(a);
    let n = 5;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0 && !off.has(ymd(t))) n--; }
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
  outOfTimeLine: "Died when the session ended",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session ended ${fmtDate(end).replace(/, \d{4}$/, "")}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.${y % 2 ? "" : " It was a short session (three months), with far fewer bills than a long one."}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Bills you star now stay on your watchlist when the session opens.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

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
      note: "The governor has 5 days (Sundays and holidays excepted) to act during the session, and 15 days if it adjourns before then.",
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
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Became law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Became law", "Vetoed"],
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
    "Passed both houses but was never sent to the governor.",
    "Sent to the governor; no signature or veto is recorded.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that cost money go on to Appropriations or Finance, Revenue and Bonding.",
};
