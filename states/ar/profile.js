// Arkansas: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ar",
  name: "Arkansas",
  abbr: "AR",
  // The records give a law its Act number without saying whether the governor signed it or let it become law
  // without a signature (a few say "Approved by the Governor"): laws say "Became law".
  noSignatures: true,
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed$|REPORTED CORRECTLY ENGROSSED|RULES SUSPENDED|Rules suspended|Received from the (?:House|Senate)|RECEIVED FROM THE SENATE|EMERGENCY CLAUSE ADOPTED|Ordered immediately|Placed on second reading for (?:the )?purpose of amendment|Returned (?:from|to|From|To)\s+(?:the )?(?:House|Senate) as (?:passed|adopted|concurred)|Sine Die adjournment$|Roll call (?:was )?requested|Sounding of the Ballot requested)/i,
  publicSite: "https://statebilltracker.org/ar/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year: the regular session in odd years, the fiscal session in even years; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => `${s} ${s % 2 ? "regular" : "fiscal"}`,
  // Laws are numbered "Act 123" (of the session: Act 123 of 2025).
  lawWord: "Act",
  // A joint resolution proposing a constitutional amendment passes both houses once, by a majority of each house's
  // members, and goes to the voters at the next general election, never to the governor (Arkansas Constitution, Art. 19,
  // sec. 22). The General Assembly can refer up to three at a time. The records still show the presiding officers
  // enrolling it and the governor "approving" it, a formality.
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members (the General Assembly can refer up to three per election)",
  ballotEvenYears: true,
  govReach: `<a href="https://governor.arkansas.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Little Rock <a class="phone" href="tel:+15016822345" data-contact="call|governor">(501) 682-2345</a>`,

  // The Legislature's bill page: /Bills/Detail?id=HB1001&ddBienniumSession=2025%2F2025R (joint resolutions "HJR1001").
  billUrl(p, session = DATA.session) {
    const b = session - ((session + 1) % 2), kind = p[1] === "J" ? "JR" : "B";
    return `https://arkleg.state.ar.us/Bills/Detail?id=${p[0]}${kind}${p.slice(2)}&ddBienniumSession=${b}%2F${session}${session % 2 ? "R" : "F"}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text, amendments and votes`)).join("<br>");
  },

  // The regular session opens the second Monday of January in odd years and lasts 60 days unless two-thirds of each
  // house extend it; in practice it recesses in April and adjourns sine die a few weeks later. The fiscal session opens
  // the second Wednesday of April in even years and lasts 30 days (45 with three-fourths' consent) (Art. 5, sec. 5;
  // Amendment 86). `dated` holds each year's sine die adjournment, when bills die (add each year's).
  dated: { 2023: "2023-05-01", 2024: "2024-05-09", 2025: "2025-05-05", 2026: "2026-04-29" },
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => year % 2 ? STATE.nth(year, 1, 1, 2) : STATE.nth(year, 4, 3, 2),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), year % 2 ? 112 : 29),
  // The governor has 5 days (Sundays excepted) to sign or veto a bill while the General Assembly is in session; a bill it
  // can't be returned to because the session adjourned becomes law unless vetoed within 20 days after adjournment
  // (Art. 6, sec. 15). A bill the governor doesn't act on becomes law.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    for (let n = 5; n > 0;) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const five = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const end = STATE.sessionEnds(+iso.slice(0, 4));
    return five <= end ? five : STATE.plusDays(end > iso ? end : iso, 20);
  },
  dueLabel: () => "Governor's decision due (5 days during the session, Sundays excepted; 20 days after it adjourns)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the Speaker and the Senate President, and sent to the governor."],
  passedBothNext: () => ({
    what: "it's enrolled and sent to the governor, who has 5 days (Sundays excepted) to sign it or veto it, or 20 days after the session adjourns; the governor can veto items in an appropriation bill. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://arkleg.state.ar.us/Legislators/List",
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // Arkansas's committees can recommend that a bill "do not pass", or send it to an interim committee for study, where it
  // dies; most bills that fail are simply never taken up.
  heldAction: "INTERIM STUDY",
  heldLabel: "Sent to interim study",
  heldTip: "The committee recommended it for study between sessions by an interim committee. That ends the bill for this session.",
  heldNote: "the committee sent it to an interim committee for study, which ends the bill for this session.",

  // Even years' fiscal sessions are almost all appropriations: say so, so the counts don't look wrong.
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    const fiscal = y % 2 ? "" : " It was a fiscal session: 30 days for the budget's appropriation bills; any other bill needed two-thirds of each house to be introduced, so there are far fewer bills than in a regular session.";
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} ${y % 2 ? "fiscal" : "regular"} session opens ${fmtDate(STATE.opens(y + 1))}.${fiscal}`;
    if (!(y % 2) && t <= end)
      return `${y} is a fiscal session: 30 days for the budget's appropriation bills; any other bill needs two-thirds of each house to be introduced.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj), effective = STATE.plusDays(adj, 92);
    return {
      leg: [["", open, adj, Y % 2 ? "Regular session" : "Fiscal session"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "20 days"]],
      events: [
        [open, "up", LEG, MD(open), Y % 2 ? "The regular session opens (60 days, often extended; it recesses in April)." : "The fiscal session opens (30 days, for appropriations)."],
        [adj, "down", LEG, MD(adj), "The session adjourns sine die. Bills that didn't pass both houses die."],
        [effective, "down", LEG, MD(effective), "Laws without an emergency clause or another date take effect on the 91st day after adjournment."],
      ],
      note: "During the session the governor has 5 days (Sundays excepted) to act on a bill; after the session adjourns, 20 days. A bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. Overriding a veto takes a majority of each house's members (51 in the House, 18 in the Senate).",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Bills go to a standing committee on their subject.", "Each house has ten standing committees, and appropriation bills go to the Joint Budget Committee, made up of members of both houses."],
    ["The committee recommends it, or not.", "A committee votes to report a bill \"do pass\" (often after amending it), \"do not pass\", or recommends it for interim study; a bill the committee never takes up dies there when the session adjourns."],
    ["Reported bills go on the calendar.", "A bill reported \"do pass\" goes on its house's calendar for a third reading and vote."],
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
    "In a standing committee (appropriations: the Joint Budget Committee). The committee decides whether to recommend it.",
    "A committee recommended it (\"do pass\"), and it's on the House or Senate calendar for a third reading and vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled and sent to the governor.",
    "Sent to the governor, who has 5 days (Sundays excepted) to sign or veto it, or 20 days after the session adjourns; if the governor does neither, it becomes law.",
    "Became law: signed, or became law without the governor's signature or over a veto. Laws are numbered as Acts.",
    "Vetoed by the governor. Overriding a veto takes a majority of each house's members.",
  ],
  pastStageTips: [
    "Never got out of committee before the session adjourned.",
    "A committee recommended it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Revenue and Tax": ["Revenue and Taxation", "Taxes"],
    "Transportation, Technology and Legislative Affairs": ["Public Transportation", "Transportation"],
    "Children and Youth": ["Aging, Children and Youth, and Legislative Affairs", "Children and youth"],
    "Rules, Resolutions and Memorials": ["Rules", "Rules"],
  },
  commNotes: {},
  moneyCommittees: { S: "Joint Budget", H: "Joint Budget" },
  secondCommittee: "Appropriation bills go to the Joint Budget Committee, which members of both houses sit on.",
};
