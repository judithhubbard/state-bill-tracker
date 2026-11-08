// North Dakota: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "nd",
  name: "North Dakota",
  abbr: "ND",
  // Steps that aren't news on a watchlist card.
  routine: /^(Hearing in the|Introduced|Received from the|Amendments adopted|An amendment|The (?:House|Senate) vote:|The .* Committee (?:recommended|reported|was divided)|Laid over|Conference committee appointed|Signed by the (?:President|Speaker)|The emergency clause|Part [A-Z] |The question was divided|The amendment was divided|The (?:House|Senate) took (?:it back|up the governor's veto)|A motion to reconsider failed|Placed on the calendar|Read the first time|Filed with the Secretary of State)/,
  publicSite: "https://statebilltracker.org/nd/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 69th Legislative Assembly; its regular session met in 2025).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  assembly: (s) => 69 + (s - 2025) / 2,
  govReach: `<a href="https://www.governor.nd.gov/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Bismarck <a class="phone" href="tel:+17013282200" data-contact="call|governor">(701) 328-2200</a>`,
  // Laws are chapters of the Session Laws, numbered from 1 each assembly ("Chapter 47").
  lawWord: "Chapter",
  // Concurrent resolutions proposing amendments to the Constitution of North Dakota pass each house once, by a majority of
  // its members, then go to the voters (Art. IV, sec. 16); never to the governor.
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members",
  ballotEvenYears: true,
  // The resolution names the statewide election (a June primary or the November general election); this says which year.
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || "";
    const y = +d.slice(0, 4) + (+d.slice(0, 4) % 2 ? 1 : 0);
    return isoToday() > `${y}-11-10` ? `It went to the voters by November ${y}; the records here don't show the result.` : `Next: the voters, at the statewide election the resolution names (by November ${y}).`;
  },

  // The Legislature's bill page: /assembly/69-2025/regular/bill-overview/bo1012.html (special sessions' bills carry their
  // own address, "link", from convert.py).
  billUrl: (p, session = DATA.session) => `https://ndlegis.gov/assembly/${STATE.assembly(session)}-${session}/regular/bill-overview/bo${p.replace(/^\D+/, "")}.html`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: versions, hearings, testimony and votes`)).join("<br>");
  },

  // The regular session meets only in the assembly's first year, from the first Tuesday after the first Monday of January,
  // for at most 80 legislative days (to late April or early May). `dated` holds each session's last floor day (add each
  // new one). The Legislative Management or the governor can call special sessions in between.
  opened: { 2019: "2019-01-03" },
  dated: { 2023: "2023-04-29", 2025: "2025-05-02" },
  opens(year) {
    if (STATE.opened[year]) return STATE.opened[year];
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 116),
  sessionEnds: (session) => STATE.adjourns(session),
  // Bills that didn't pass die when the regular session adjourns; nothing waits for a second year.
  floorVotesEnd: false,
  // The governor has 3 days (Sundays excepted) after a bill is presented while the Legislative Assembly is in session, and
  // 15 days after it adjourns (Constitution, Art. V, sec. 9). Bills reach the governor a day or two after they pass.
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    const end = STATE.adjourns(a % 2 ? a : a - 1);
    if (iso > end && iso <= STATE.plusDays(end, 15)) return STATE.plusDays(end, 15);
    let n = 3;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const due = ymd(t);
    return due > end && iso <= end ? STATE.plusDays(end, 15) : due;
  },
  dueLabel: () => "Governor's decision due (3 days during the session, Sundays excepted; 15 days after it adjourns)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session), 15),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Waiting to go to the governor", () => "Bills that pass both houses are signed by the Speaker and the Senate's presiding officer and sent to the governor, usually within a few days."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate's presiding officer sign it, and it goes to the governor, who has 3 days (Sundays excepted), or 15 days once the session has adjourned, to sign it or veto it. The governor can veto items in an appropriation bill. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, community or county",
  findReps: "https://openstates.org/find_your_legislator/",
  oneNumber: true,
  diesAfterFloor: () => "Bills that didn't pass died when the session adjourned; a special session takes up only the bills it was called for.",
  outOfTimeLine: "Died when the session adjourned",
  // A withdrawn bill ends there (the sponsor's request, or the house taking it back from the committee to withdraw it).
  heldAction: "Withdrawn from further consideration",
  heldLabel: "Withdrawn",
  heldTip: "Withdrawn from further consideration, usually at the sponsor's request. That ends the bill.",
  heldNote: "withdrawn from further consideration, usually at the sponsor's request, before a committee reported it.",
  // Every committee report goes to the floor, "do not pass" too, so the bills that die mostly fail there: the Statistics
  // charts say so instead of "died in committee" and "died awaiting a floor vote".
  oddsExits: ["Not recommended; died", "Recommended; failed"],
  fateLabels: { committee: "Withdrawn", floor: "Failed on the floor" },
  // A bill voted down on the floor is dead at once, unless the house reconsiders the vote (usually the next day); a withdrawn
  // bill too. What the page says about it, instead of what comes next.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const w = texts.lastIndexOf("Withdrawn from further consideration");
    if (w >= 0 && b.stage === 0) return { status: "Withdrawn", when: `Withdrawn ${fmtDate(acts[w][0])}.`, tail: "That ends it for this session." };
    const i = texts.findLastIndex((t) => /^Failed to pass the (House|Senate)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |^The (House|Senate) voted to reconsider/.test(t))) return null;
    const h = texts[i].match(/the (House|Senate)/)[1];
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `${texts[i].replace(/,.*$/, "")} on ${fmtDate(acts[i][0])}.`,
      tail: "That ends it, unless the house reconsiders the vote.",
    };
  },

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the Legislative Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.adjourns(y);
    if (t > end && t < STATE.opens(y + 2))
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; special sessions take up only the bills they're called for. The next regular session opens ${fmtDate(STATE.opens(y + 2))}, and bills are filed from December.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} Legislative Assembly's session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: one regular session, in the first year.
  calendarDays: 20,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y);
    return {
      leg: [["", o1, a1, "80-day session"], ["light", a1, `${Y + 1}-12-31`, "Interim (no regular session)"]],
      gov: [["light", o1, STATE.plusDays(a1, 15), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The session opens; most bills must be filed in its first weeks."],
        [a1, "down", LEG, MD(a1), "The session adjourns. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The two-year budget starts."],
        [`${Y}-08-01`, "down", LEG, "August 1", "Most new laws take effect."],
        [`${Y + 1}-12-01`, "up", LEG, "December", "The next assembly's organizational session; bills are prefiled."],
      ],
      note: "During the session the governor has 3 days (Sundays excepted) to sign or veto a bill; for bills that arrive at the end, 15 days after adjournment. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members. Laws take effect August 1 unless the bill says otherwise (an emergency clause, passed by two-thirds, makes it effective at once).",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislative Assembly's member list",
  openUntil: (s) => `the ${s} session adjourns`,

  commIntro: [
    ["Every bill gets a hearing and a vote.", "North Dakota's committees can't hold a bill: each one is heard, and the committee reports it to the floor with a recommendation, \"do pass\" or \"do not pass\" (with or without amendments)."],
    ["Then the full house votes on it.", "Bills that spend money usually go on to the Appropriations Committee before the floor vote. A bill the house votes down is dead, unless it reconsiders the vote."],
  ],
  // The current assembly's page between sessions (most of its two years) reads like a finished session's: every bill
  // still at the first stages was withdrawn or voted down.
  between() {
    const t = new Date().toISOString().slice(0, 10), y = +t.slice(0, 4), s = y % 2 ? y : y - 1;
    return t > STATE.adjourns(s) && t < STATE.opens(s + 2);
  },
  stageWords: {
    pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
    long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
    chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
  },
  stageText: {
    get live() { return STATE.between() ? STATE.stageText.final : STATE.stageWords; },
    get prefiled() { return Object.fromEntries(Object.entries(STATE.stageWords).map(([k, v]) => [k, ["Prefiled", ...v.slice(1)]])); },
    final: {
      pipe: ["Withdrawn", "Failed on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Withdrawn", "Failed on the floor", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Withdrawn", "Failed on floor", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "In a committee, which holds a hearing and then reports it to the floor, recommending \"do pass\" or \"do not pass\". Committees can't hold bills.",
    "Reported by its committee, with either recommendation. Every bill gets a vote of the full house; one that fails is dead unless the vote is reconsidered.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate's presiding officer sign it, and it goes to the governor.",
    "Sent to the governor, who has 3 days (Sundays excepted) during the session, or 15 days after it adjourns.",
    "Signed into law, or became law without the governor's signature or over a veto: a chapter of the Session Laws.",
    "Vetoed by the governor. Overriding takes two-thirds of each house's members.",
  ],
  pastStageTips: [
    "Withdrawn before its committee reported it.",
    "Voted down by the house where it started (most had a \"do not pass\" recommendation from the committee).",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Both houses' committees mostly share names; where they differ, the Senate's -> [the House's, the subject].
  commPairs: {
    "Agriculture and Veterans Affairs": ["Agriculture", "Agriculture"],
    "Industry and Business": ["Industry, Business and Labor", "Business"],
    "State and Local Government": ["Political Subdivisions", "Local government"],
    "Workforce Development": ["Government and Veterans Affairs", "Workforce and government"],
  },
  commNotes: {
    "State and Local Government": "The Senate's State and Local Government Committee also takes state agencies and elections; in the House, Government and Veterans Affairs does.",
    "Workforce Development": "The Senate's Workforce Development Committee takes labor bills; in the House, Industry, Business and Labor does. Veterans' bills go to Agriculture and Veterans Affairs in the Senate and Government and Veterans Affairs in the House.",
  },
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that spend money usually go on to the Appropriations Committee after their policy committee.",
};
