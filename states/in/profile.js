// Indiana: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "in",
  name: "Indiana",
  abbr: "IN",
  // Steps that aren't news on a watchlist card.
  routine: /^(Authored by|Coauthored by|(?:Representatives?|Senators?) .* (?:added|removed) as|(?:House|Senate) sponsors?:|Cosponsors?:|(?:House|Senate) (?:conferees|advisors?) appointed|Motion to (?:concur|dissent) filed|CCR # ?\d+ filed|Signed by the (?:Speaker|President)|Referred to the (?:House|Senate)$|Amendment #\d+ \([^)]*\) (?:failed|ruled out of order)|Joint Rule \d+ Certification|Rule [\d.]+ suspended)/i,
  publicSite: "https://statebilltracker.org/in/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One regular session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are numbered "Public Law 126" (P.L. 126-2025).
  lawWord: "Public Law",
  // A joint resolution proposing a constitutional amendment passes two General Assemblies in a row (a majority of each
  // house's members, with an election between), then goes to the voters at the next general election; never to the
  // governor (Indiana Constitution, Art. XVI, sec. 1). Its digest says which passage it is: "This proposed amendment has
  // been agreed to by one general assembly" (the second) or "has not been previously agreed to" (the first).
  amendments: true,
  amendmentVote: "a majority of each house's members in two General Assemblies in a row",
  ballotEvenYears: true,
  amendmentFinal: (b) => /has been agreed to by one general assembly/i.test(b.summary || ""),
  amendmentAgain(b) {
    const y = +([b.dates.passS, b.dates.passA].sort().pop() || String(DATA.session)).slice(0, 4), vote = y % 2 ? y + 1 : y;
    return `Next: the General Assembly elected in November ${vote} has to pass it again, by a majority of each house's members; then it goes to the voters.`;
  },
  govReach: `<a href="https://www.in.gov/gov/contact-gov-braun/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Indianapolis <a class="phone" href="tel:+13172324567" data-contact="call|governor">(317) 232-4567</a>`,

  // The General Assembly's bill page: /legislative/2025/bills/house/1001/details (joint resolutions under resolutions/).
  billUrl: (p, session = DATA.session) => `https://iga.in.gov/legislative/${session}/${p[1] === "J" ? "resolutions" : "bills"}/${p[0] === "H" ? "house" : "senate"}/${p[1] === "J" ? "joint/" : ""}${+p.slice(2)}/details`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, versions, votes and fiscal notes`)).join("<br>");
  },

  // The session opens in early January (the second Monday, unless the Legislature sets another day) after Organization
  // Day in November, and must adjourn by April 29 in odd years and March 14 in even years (IC 2-2.1-1-2); it usually
  // finishes earlier. `opened` and `dated` hold the actual first and last days.
  opened: { 2025: "2025-01-08", 2026: "2026-01-05" },
  dated: { 2024: "2024-03-08", 2025: "2025-04-24", 2026: "2026-02-27" },
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => STATE.opened[year] || STATE.nth(year, 1, 1, 2),
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || (year % 2 ? `${year}-04-29` : `${year}-03-14`),
  // The governor has 7 days after a bill is presented to sign or veto it; a bill the governor doesn't act on becomes law
  // on the 8th day (Indiana Constitution, Art. 5, sec. 14), in session or after it. The records show the presiding
  // officers' last signature, not the day it was presented (usually a day or a few later), so this is an estimate.
  govDeadline: (iso) => (iso ? STATE.plusDays(iso, 7) : null),
  dueLabel: () => "Governor's decision due (7 days after it's presented; estimated)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the Speaker, the President Pro Tempore and the Lieutenant Governor, then go to the governor."],
  passedBothNext: () => ({
    what: "the Speaker, the Senate President Pro Tempore and the Lieutenant Governor sign it, and it goes to the governor, who has 7 days to sign it or veto it. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  oneNumber: true,
  diesAfterFloor: () => "The session has adjourned, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session adjourned",

  // Indiana's committees don't hold or vote down bills on the record: a bill the chair never schedules dies there.
  heldLabel: "Held without a vote",
  heldTip: "The committee didn't vote on it. In Indiana the chair decides whether a bill gets a hearing and a vote.",
  heldNote: "the committee didn't vote on it; in Indiana the chair decides whether a bill gets a hearing and a vote.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens in early January.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens in early January. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, Y % 2 ? "Long session (budget year)" : "Short session"]],
      gov: [["light", open, adj, "7 days a bill"], ["", adj, STATE.plusDays(due, 7), "Last bills"]],
      events: [
        [open, "up", LEG, MD(open), `The ${Y % 2 ? "long" : "short"} session opens.`],
        [adj, "down", LEG, MD(adj), `The session adjourns (it must by ${Y % 2 ? "April 29" : "March 14"}). Bills that didn't pass both houses die.`],
        [`${Y}-07-01`, "down", LEG, "Jul 1", "Most new laws take effect July 1."],
      ],
      note: "The governor has 7 days after a bill is presented to sign or veto it; a bill the governor doesn't act on becomes law. There's no line-item veto. Overriding a veto takes a majority of each house's members (51 in the House, 26 in the Senate), and the General Assembly can do it until the end of its next regular session.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's list of members",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Committee chairs decide which bills get a hearing.", "A bill that isn't heard dies in committee; Indiana's committees rarely vote a bill down."],
    ["Committees hear bills on their subject.", "A standing committee takes testimony and votes to recommend a bill (\"do pass\", often with amendments); the house then adopts the committee's report."],
    ["Bills that cost money go to a second committee.", "In the House, a bill that spends money or affects revenue goes on to Ways and Means; in the Senate, to Appropriations or Tax and Fiscal Policy."],
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
    "In a standing committee. The chair decides whether it gets a hearing; the committee then votes on whether to recommend it.",
    "A committee recommended it, and it's on the House or Senate floor: second reading (when amendments are offered), then third reading (the vote).",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker, the Senate President Pro Tempore and the Lieutenant Governor sign it, then it goes to the governor.",
    "Sent to the governor, who has 7 days to sign or veto it; if the governor does neither, it becomes law.",
    "Signed into law (or became law without the governor's signature, or over a veto).",
    "Vetoed by the governor. Overriding a veto takes a majority of each house's members, by the end of the next session.",
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
    "Appropriations": ["Ways and Means", "Budget and spending"],
    "Agriculture": ["Agriculture and Rural Development", "Agriculture"],
    "Commerce and Technology": ["Commerce, Small Business and Economic Development", "Commerce"],
    "Corrections and Criminal Law": ["Courts and Criminal Code", "Criminal law"],
    "Education and Career Development": ["Education", "Education"],
    "Elections": ["Elections and Apportionment", "Elections"],
    "Pensions and Labor": ["Employment, Labor and Pensions", "Labor and pensions"],
    "Family and Children Services": ["Family, Children and Human Affairs", "Families and children"],
    "Insurance and Financial Institutions": ["Insurance", "Insurance and banking"],
    "Health and Provider Services": ["Public Health", "Health"],
    "Homeland Security and Transportation": ["Roads and Transportation", "Transportation"],
    "Utilities": ["Utilities, Energy and Telecommunications", "Utilities and energy"],
    "Veterans Affairs and the Military": ["Veterans Affairs and Public Safety", "Veterans"],
    "Rules and Legislative Procedure": ["Rules and Legislative Procedures", "Rules"],
  },
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Ways and Means" },
  secondCommittee: "House bills that cost money go on to Ways and Means; Senate bills, to Appropriations or Tax and Fiscal Policy.",
};
