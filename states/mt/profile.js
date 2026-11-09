// Montana: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "mt",
  name: "Montana",
  abbr: "MT",
  // Steps that aren't news on a watchlist card.
  routine: /^(Hearing in the|Introduced$|Sent to the (?:House|Senate)$|An amendment |The committee's report was read|Passed over for the day|The (?:House|Senate) vote:|Signed by the (?:Speaker|President)|Sent to enrolling|(?:Free c|C)onference committee appointed|Filed with the Secretary of State|Taken off the table|Sent back to second reading|The Secretary of State polled)/,
  publicSite: "https://statebilltracker.org/mt/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A page per two-year Legislature (the 69th is 2025–26), named by its session's year: the Legislature meets in regular
  // session only in odd years.
  sessionLabel: (s) => String(s),
  legislature: (s) => 69 + (s - 2025) / 2,
  govReach: `<a href="https://gov.mt.gov/contact" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Helena <a class="phone" href="tel:+14064443111" data-contact="call|governor">(406) 444-3111</a>`,
  // Laws are chapters of each session's laws ("Chapter 479, Laws of 2025").
  lawWord: "Chapter",
  // The Legislature proposes amendments to the Constitution of Montana with a bill (subject "Constitutional Amendment
  // Proposals") passed by two-thirds of all 150 legislators, both houses' votes counted together (Art. XIV, sec. 8); it
  // goes to the voters at the next general election, never to the governor.
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of all 150 legislators (100 votes, both houses counted together)",
  ballotEvenYears: true,
  ballotLine(b) {
    const y = DATA.session + 1;
    return isoToday() > `${y}-11-10` ? `It went to the voters in November ${y}; the records here don't show the result.` : `Next: the voters, at the November ${y} general election.`;
  },

  // The Legislature's Bill Explorer, by the bill's draft (LC) number: each version's `link`, from convert.py.
  billUrl: () => "https://bills.legmt.gov/",
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: text, history, fiscal note, amendments and votes`)).join("<br>");
  },

  // The regular session meets only in odd years, from the first Monday of January (January 2 when that's New Year's
  // Day), for at most 90 legislative days, to late April or early May. `dated` holds each session's last day (add each
  // new one).
  dated: { 2023: "2023-05-02", 2025: "2025-04-30" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7));
    if (t.getDate() === 1) t.setDate(2);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 116),
  sessionEnds: (session) => STATE.adjourns(session),
  // Bills that didn't pass die when the session adjourns; nothing waits for the second year.
  floorVotesEnd: false,
  // The governor has 10 days after a bill is delivered to sign or veto it, during the session or after it; a bill the
  // governor does neither with becomes law (Constitution, Art. VI, sec. 10). Bills passed at the end reach the governor
  // over the following weeks, as they're enrolled and signed.
  govDeadline: (iso) => (iso ? STATE.plusDays(iso, 10) : null),
  dueLabel: () => "Governor's decision due (10 days after the bill is delivered)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session), 60),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Waiting to go to the governor", () => "Bills that pass both houses are enrolled, signed by the Speaker and the Senate President, and delivered to the governor, sometimes weeks later."],
  passedBothNext: () => ({
    what: "it's enrolled, signed by the Speaker and the Senate President, and delivered to the governor, who has 10 days to sign it, veto it, or send it back with proposed amendments; the governor can veto items in an appropriation bill. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town, community or county",
  addressLookup: true,
  findReps: "https://openstates.org/find_your_legislator/",
  oneNumber: true,
  diesAfterFloor: () => "Bills that didn't pass died when the session adjourned; the Legislature meets again in January of the next odd year.",
  outOfTimeLine: "Died when the session adjourned",
  // Most bills that die are tabled in committee: the committee votes to set it aside, and it stays there unless the
  // committee takes it from the table (or the full house votes to take it from the committee).
  heldAction: "Tabled in committee",
  heldLabel: "Tabled",
  heldTip: "The committee voted to table it, setting it aside. It stays there unless the committee takes it from the table, or a majority of the full house votes to take it from the committee.",
  heldNote: "tabled: the committee voted to set it aside.",
  // Bills that ended before the session did: voted down or killed on the floor (unless the house reconsiders), or past
  // the transmittal deadline for passing their first house. What the page says about one, instead of what comes next.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const tabled = texts.lastIndexOf("Tabled in committee"), untabled = texts.lastIndexOf("Taken off the table in committee");
    if (b.stage === 0 && tabled > untabled) return null; // tabled in committee: the stage says so
    const f = texts.findLastIndex((t) => /^Failed (?:second|third) reading in the (?:House|Senate)|^The (?:House|Senate) killed it on second reading/.test(t));
    const m = texts.findLastIndex((t) => /^Missed the deadline for /.test(t));
    const later = (i) => texts.slice(i + 1).some((t) => /^PASSED |^Approved on second reading|^The (?:House|Senate) voted to reconsider/.test(t));
    if (f >= 0 && !later(f)) {
      const h = texts[f].match(/House|Senate/)[0];
      return {
        status: b.stage === 2 && b.passedIn && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
        when: `${texts[f].replace(/, \d+-\d+$/, "")} on ${fmtDate(acts[f][0])}.`,
        tail: "That ends it, unless the house reconsiders the vote.",
      };
    }
    if (m >= 0 && b.stage <= 1 && !later(m)) {
      return {
        status: "Missed the transmittal deadline",
        when: `${texts[m].replace(/^Missed/, "It missed")}, ${fmtDate(acts[m][0])}.`,
        tail: "That ends it for this session.",
      };
    }
    return null;
  },

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.adjourns(y);
    if (t > end && t < STATE.opens(y + 2))
      return `The ${y} session adjourned ${fmtDate(end)}. Bills that didn't pass both houses died. The Legislature meets again on ${fmtDate(STATE.opens(y + 2))}; bills are drafted and prefiled from the fall before.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: one regular session, in the first year.
  calendarDays: 20,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y);
    return {
      leg: [["", o1, a1, "90-day session"], ["light", a1, `${Y + 1}-12-31`, "Interim (no regular session)"]],
      gov: [["light", o1, STATE.plusDays(a1, 60), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The session opens; most bills are introduced in its first weeks."],
        [STATE.plusDays(o1, 57), "down", LEG, "Early March", "The transmittal deadline: general bills that haven't passed their first house die. Revenue and appropriation bills and referenda have later deadlines."],
        [a1, "down", LEG, MD(a1), "The session adjourns sine die. Bills that didn't pass both houses die."],
        [`${Y}-10-01`, "down", LEG, "October 1", "Most new laws take effect."],
        [`${Y + 1}-11-15`, "up", LEG, "Fall", "Legislators elected in November request bill drafts for the next session."],
      ],
      note: "The governor has 10 days after a bill is delivered to sign it, veto it, or return it with proposed amendments, which the Legislature adopts or rejects before the bill goes back. A bill the governor doesn't act on becomes law. Overriding a veto takes two-thirds of the members present in each house; after the session, the Secretary of State polls the legislators by mail, and it takes two-thirds of each house's members.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member list",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Bills go to a standing committee on their subject.", "The Speaker refers House bills, and the Senate President Senate bills. Every bill gets a public hearing, then the committee votes (\"executive action\"): do pass (be concurred in, in the second house), or to table it, which is where most bills die."],
    ["A majority of the house can take a bill from a committee.", "A motion to take it from the committee and place it on second reading brings a tabled bill to the floor; it seldom succeeds."],
    ["Bills that spend money go on to Appropriations.", "After a policy committee approves a bill that spends money, it usually goes to the House Appropriations or Senate Finance and Claims Committee."],
  ],
  // The current Legislature's page between sessions (most of its two years) reads like a finished session's.
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
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "In a standing committee, which holds a hearing and then votes: do pass, or table it. Most bills that die are tabled.",
    "Its committee approved it (or the house took it from the committee). The full house debates and votes on second reading, then passes it on third reading.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, signed by the Speaker and the Senate President, and delivered to the governor.",
    "Delivered to the governor, who has 10 days to sign it, veto it or send it back with proposed amendments; if the governor does none of these, it becomes law.",
    "Became law: signed, or without the governor's signature, or over a veto. Laws are chapters of the session's laws.",
    "Vetoed by the governor. Overriding takes two-thirds of each house; after the session, by a poll of the legislators by mail.",
  ],
  pastStageTips: [
    "Tabled or left in committee, or it missed the deadline to pass its first house.",
    "Voted down or killed on the floor, or it missed the deadline to pass its first house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Agriculture, Livestock and Irrigation": ["Agriculture", "Agriculture"],
    "Business, Labor and Economic Affairs": ["Business and Labor", "Business and labor"],
    "Education and Cultural Resources": ["Education", "Education"],
    "Finance and Claims": ["Appropriations", "Spending"],
    "Fish and Game": ["Fish, Wildlife and Parks", "Fish and wildlife"],
    "Highways and Transportation": ["Transportation", "Transportation"],
    "Public Health, Welfare and Safety": ["Human Services", "Health and human services"],
  },
  commNotes: {
    "Finance and Claims": "Bills that spend money go to the Senate's Finance and Claims Committee and the House Appropriations Committee, usually after a policy committee.",
    "Public Health, Welfare and Safety": "The Senate's Public Health, Welfare and Safety Committee takes health and human services bills; in the House, Human Services does.",
  },
  moneyCommittees: { S: "Finance and Claims", H: "Appropriations" },
  secondCommittee: "Bills that spend money usually go on to Appropriations (Finance and Claims in the Senate) after their policy committee.",
};
