// Nebraska: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
// Nebraska's Legislature has one house (`houses` has one entry, "L"), and its 49 senators are elected without party
// labels (`nonpartisan`): tracker.html leaves out what assumes a second house or parties.
const STATE = {
  code: "ne",
  name: "Nebraska",
  abbr: "NE",
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced$|Public hearing set|Carried over to the second session|Amendment |Sen\. .* moved |Speaker .* moved |The .* (?:Committee|Board) moved |A senator moved |The motion .* failed|Signed by the Speaker and the presiding officer|Includes provisions of|Placed on Select File|Placed on Final Reading|Passed on Final Reading)/,
  publicSite: "https://statebilltracker.org/ne/",
  listsApi: "",
  houses: { L: "Legislature" },
  titles: { L: "Sen." },
  memberWords: { L: "state senator" },
  greetings: { L: "Senator" },
  // One house, and no parties: the page leaves out second-house steps and party statistics (tracker.html's UNI, NOPARTY).
  nonpartisan: true,
  // "Passed both houses" in the shared wording becomes this.
  passedBothText: "Passed the Legislature",
  // How a session is written: 2025–26 (the 109th Legislature).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  legislature: (s) => 109 + (s - 2025) / 2,
  // "109th Legislature"
  ls(s) { const n = STATE.legislature(s), t = n % 100; return `${n}${t > 10 && t < 14 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" })[n % 10] || "th"}`; },
  // From governor.nebraska.gov's contact page and footer (checked by program 2026-11-13, not by the owner).
  govReach: `<a href="https://governor.nebraska.gov/contact-governor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Lincoln <a class="phone" href="tel:+14024712244" data-contact="call|governor">(402) 471-2244</a>`,
  // Laws aren't numbered by chapter in these records: a law is shown as signed (or as law without the signature).
  noSignatures: false,

  // A constitutional amendment is a resolution ("LR 19CA") that passes on Final Reading with three-fifths of the members (30
  // of 49), then goes to the voters at the next general election (or a special election the resolution sets), never to
  // the governor (Constitution, Art. XVI, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "three-fifths of the senators (30 of 49) on Final Reading",
  ballotEvenYears: true,

  // The Legislature's page for each bill, by its DocumentID (a version's `link`, from build_data.py), else the search.
  billUrl(p) {
    const b = typeof BILLS !== "undefined" && BILLS.find((x) => x.nums.includes(p));
    if (b?.vers?.[0]?.link) return b.vers[0].link;
    const m = /^(LB|LR)(\d+)(A|CA)?$/.exec(p) || [];
    return `https://nebraskalegislature.gov/bills/search_by_number.php?Prefix=${m[1] || "LB"}&Number=${m[2] || ""}&Suffix=${m[3] || ""}&Legislature=${STATE.legislature(DATA.session)}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p.replace(/^(LB|LR)/, "$1 "))}: text, statement of intent, committee statement, fiscal note and votes`)).join("<br>");
  },
  // The round each floor vote was in (convert.py puts it where a committee vote has its committee).
  voteWhat: (v) => (v.kind === "F" && v.committee ? `${esc(v.committee)}` : ""),
  // Priority bills: each senator may name one a session, each committee two, the Speaker up to 25. They're the bills that
  // get floor time, so the list tags them.
  // (convert.py writes "Named Sen. X's priority bill", "Named a priority bill of the Judiciary Committee", "Named a Speaker
  // priority bill" or "Named a Speaker major proposal" into the history.)
  priorityBy: (b) => [...new Set(b.vers[0].actions.map(([, t]) => (/^Named a Speaker/.test(t) ? "the Speaker" : /^Named a priority bill of /.test(t) ? "a committee" : /^Named .*'s priority bill$/.test(t) ? "a senator" : "")).filter(Boolean))],
  rowTags: (b) => { const by = STATE.priorityBy(b); return by.length ? `<span class="tag narrow">Priority bill${TIPI(`Named a priority bill by ${andList(by)}. Each senator may name one priority bill a session, each committee two and the Speaker up to 25; priority bills are the ones the Legislature debates first.`)}</span>` : ""; },
  // A bills: each appropriation that pays for a bill is its own "A bill" (LB 304A pays for LB 304), passed and signed with
  // it. convert.py marks them `shell`, so they're left out of the statistics and tagged.
  shellTag: "A bill",
  shellTip: "An “A bill” carries the money for the bill with the same number (LB 304A pays for LB 304). It moves with that bill, so it's left out of the statistics.",
  shellNote: "A bills, which only carry the money for another bill, are left out.",

  // Each session opens the first Wednesday after the first Monday of January: 90 legislative days in odd years (to early
  // June), 60 in even years (to mid-April). `dated` holds each session's last day (add each new one); a year not listed
  // is estimated.
  dated: { 2023: "2023-06-01", 2024: "2024-04-18", 2025: "2025-06-02", 2026: "2026-04-17" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 2);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || (year % 2 ? `${year}-06-05` : `${year}-04-18`),
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
  // Bills die with the second session: every bill still pending is indefinitely postponed on its last day.
  sessionEnds: (session) => STATE.adjourns(session + 1),
  floorVotesEnd: false,
  // The governor has 5 days (Sundays excepted) after a bill is presented to sign or veto it; a bill not returned becomes
  // law. When the Legislature adjourns before then, a veto goes to the Secretary of State within 5 days after adjournment
  // (Constitution, Art. IV, sec. 15). The governor can veto items of appropriation.
  govDeadline(iso) {
    if (!iso) return null;
    const end = STATE.adjourns(+iso.slice(0, 4)), due = STATE.plusWeekdays(iso, 5);
    return iso <= end && due > end ? STATE.plusDays(end, 5) : due;
  },
  dueLabel: () => "Governor's decision due (5 days, Sundays excepted; 5 days after the session ends for bills presented at its close)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session + 1), 5),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass on Final Reading are signed by the Speaker and the presiding officer and presented to the governor, usually the same day or a few days later."],
  passedBothNext: () => ({
    what: "the Speaker and the presiding officer sign it and it goes to the governor, who has 5 days (Sundays excepted) to sign or veto it; a bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. Overriding a veto takes three-fifths of the senators, 30 of 49.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, village or county",
  addressLookup: false,
  findReps: "https://nebraskalegislature.gov/senators/senator_find.php",
  diesAfterFloor: () => "The Legislature has adjourned for its term, so it died; a bill has to be introduced again in the next Legislature.",
  outOfTimeLine: "Died when the Legislature adjourned for its term",

  // Committees kill bills by indefinitely postponing them, but most bills they don't advance just stay there.
  heldLabel: "Held in committee",
  heldTip: "The committee heard it but never advanced it to General File. Every bill gets a public hearing; most stay in committee until the Legislature ends.",
  heldNote: "the committee heard it but never advanced it.",
  // A bill killed before the end (indefinitely postponed by its committee or on the floor, bracketed, withdrawn), or whose
  // text went into another bill, says so.
  endedNote(b) {
    const acts = b.vers[0].actions, texts = acts.map(([, t]) => t);
    const k = texts.findLastIndex((t) => /^(Killed|Indefinitely postponed \(killed\)|Bracketed|Withdrawn by its introducer)/.test(t));
    const into = texts.findLastIndex((t) => /^Its provisions were amended into /.test(t));
    if (into >= 0 && b.stage <= 1) {
      const m = texts[into].match(/into (LB \d+A?)(?:.*\(it ([^)]+)\))?/);
      return { status: `Amended into ${m[1]}`, when: `Its provisions were amended into ${m[1]} on ${fmtDate(acts[into][0])}${m[2] ? `, which ${m[2]}` : ""}.`, tail: "Nebraska often passes a bill's text as part of another bill." };
    }
    if (k < 0 || b.stage > 1) return null;
    const t = texts[k];
    if (/^Withdrawn/.test(t)) return { status: "Withdrawn", when: `Withdrawn by its introducer on ${fmtDate(acts[k][0])}.`, tail: "That ends it." };
    if (/^Bracketed/.test(t)) return { status: "Bracketed (set aside)", when: `Set aside for the session on ${fmtDate(acts[k][0])}.`, tail: "That ends it for this Legislature." };
    if (/Committee \(indefinitely postponed\)$/.test(t)) return { status: "Killed in committee", when: `${t} on ${fmtDate(acts[k][0])}.`, tail: "That ends it for this Legislature." };
    return { status: "Killed on the floor", when: `Indefinitely postponed by the Legislature on ${fmtDate(acts[k][0])}.`, tail: "That ends it for this Legislature." };
  },

  committeeNext: {},
  chairAsks: {},

  // The current Legislature's page between sessions reads like a finished one's.
  between() {
    const t = new Date().toISOString().slice(0, 10), y = +t.slice(0, 4), s = y % 2 ? y : y - 1;
    return t > STATE.adjourns(s + 1) && t < STATE.opens(s + 2);
  },
  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The ${y} session ended ${fmtDate(STATE.adjourns(y))}. Bills that haven't passed carry over to the ${y + 1} session, which opens ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > STATE.adjourns(y + 1))
      return `The ${STATE.ls(y)} Legislature's last session ended ${fmtDate(STATE.adjourns(y + 1))}. Bills that didn't pass died; the ${STATE.ls(y + 2)} Legislature opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${STATE.ls(raw.session)} Legislature opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, 90 and 60 legislative days.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    const intro1 = STATE.plusDays(o1, 14), intro2 = STATE.plusDays(o2, 14);
    return {
      leg: [["", o1, a1, "First session (90 days)"], ["light", a1, o2, "Interim"], ["", o2, a2, "Second session (60 days)"], ["light", a2, `${Y + 1}-12-31`, "Interim"]],
      gov: [["light", o1, STATE.plusDays(a1, 5), "Acts on bills"], ["light", o2, STATE.plusDays(a2, 5), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The Legislature convenes and elects its Speaker and committee chairs."],
        [intro1, "down", LEG, "January", "Senators may introduce bills only in the first 10 legislative days of each session."],
        [`${Y}-03-01`, "up", LEG, "February–March", "Public hearings on every bill; senators and committees name their priority bills."],
        [a1, "down", LEG, MD(a1), "The first session ends with the two-year budget. Bills that didn't pass carry over."],
        [o2, "up", LEG, MD(o2), "The second session starts where the first left off."],
        [intro2, "down", LEG, "January", "The 10-day limit on new bills again."],
        [a2, "down", LEG, MD(a2), "The Legislature ends. Every bill still pending is indefinitely postponed."],
      ],
      note: "The governor has 5 days (Sundays excepted) to act on a bill; a bill not returned becomes law. The governor can veto items in appropriation bills. Overriding a veto takes three-fifths of the senators (30 of 49). Laws without an emergency clause take effect three calendar months after the session adjourns.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "",
  openUntil: (s) => `the ${STATE.ls(s)} Legislature's last session ends in April ${s + 1}`,

  commIntro: [
    ["Every bill gets a hearing.", "The Reference Committee (the Executive Board) sends each bill to one of 14 standing committees, which must hold a public hearing on it. The committee then advances it to General File, often with an amendment, or indefinitely postpones it; most bills just stay in committee."],
    ["Three rounds on the floor.", "General File is the first round of debate, then Select File, then Final Reading, the vote that passes it. The Speaker sets the agenda, and priority bills come first; ending a filibuster takes 33 votes (cloture)."],
  ],
  stageWords: {
    pipe: ["In committee", "On the floor", "", "Passed the Legislature", "On the governor's desk", "Signed into law", "Vetoed"],
    long: ["In committee", "On the floor", "", "Passed the Legislature", "On the governor's desk", "Signed into law", "Vetoed"],
    chart: ["In committee", "On the floor", "", "Passed", "Governor's desk", "Signed", "Vetoed"],
  },
  stageText: {
    get live() { return STATE.between() ? STATE.stageText.final : STATE.stageWords; },
    get prefiled() { return Object.fromEntries(Object.entries(STATE.stageWords).map(([k, v]) => [k, ["Introduced", ...v.slice(1)]])); },
    final: {
      pipe: ["Died in committee", "Died on the floor", "", "Passed the Legislature", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died on the floor", "", "Passed the Legislature", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died on the floor", "", "Passed", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "In a committee, which holds a public hearing on every bill and may advance it to General File, often amended.",
    "On the floor: General File (the first round of debate), Select File (the second) or Final Reading (the vote that passes it). The Speaker decides when bills come up; priority bills come first, and ending a filibuster takes 33 votes.",
    "",
    "Passed on Final Reading. The Speaker and the presiding officer sign it, then it goes to the governor (a constitutional amendment goes to the voters).",
    "Presented to the governor, who has 5 days (Sundays excepted) to sign or veto it.",
    "Became law: signed, or not returned within 5 days, or passed over a veto.",
    "Vetoed by the governor. Overriding takes three-fifths of the senators (30 of 49).",
  ],
  pastStageTips: [
    "Never advanced from committee before the Legislature ended.",
    "Advanced to the floor, but never passed on Final Reading.",
    "",
    "Passed the Legislature, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This Legislature is over. Bills that didn't become law have to be introduced again in the next one.",
  oddsExits: ["Died in committee", "Died on the floor"],
  fateLabels: { committee: "Died in committee", floor: "Died on the floor" },

  commPairs: {},
  commNotes: {},
  moneyCommittees: { L: "Appropriations" },
  secondCommittee: "Bills that spend money get a separate appropriation bill, an “A bill” (LB 304A for LB 304), which the Appropriations Committee's budget work and the floor take up with it.",
};
