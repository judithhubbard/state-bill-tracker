// Nevada: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "nv",
  name: "Nevada",
  abbr: "NV",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled$|Introduced$|Read the (first|second) time|The (Assembly|Senate) vote:|The .* Committee recommended|Amended in the|Placed on the (Chief Clerk|Secretary)'s desk|Exempt from the session's deadlines|Granted a waiver|Declared an emergency|Set as a special order|A conference committee was requested|File No\. |Action of |SIGNED CHAPTER)/,
  publicSite: "https://statebilltracker.org/nv/",
  listsApi: "",
  houses: { S: "Senate", A: "Assembly" },
  titles: { S: "Sen.", A: "Asm." },
  memberWords: { S: "state senator", A: "Assembly member" },
  greetings: { S: "Senator", A: "Assemblymember" },
  // How a session is written: 2025–26 (the 83rd session met in 2025; nothing but special sessions meets in 2026).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  number: (s) => 83 + (s - 2025) / 2,
  // "83rd session"
  nth(s) { const n = STATE.number(s), t = n % 100; return `${n}${t > 10 && t < 14 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" })[n % 10] || "th"}`; },
  // From gov.nv.gov's contact page and footer (checked by program 2026-11-09, not by the owner).
  govReach: `<a href="https://gov.nv.gov/constituent-services/contacting-the-governor/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Carson City <a class="phone" href="tel:+17756845670" data-contact="call|governor">(775) 684-5670</a> · Las Vegas <a class="phone" href="tel:+17024862500" data-contact="call|governor">(702) 486-2500</a>`,
  // Laws are chapters of the Statutes of Nevada, numbered from 1 each session ("Chapter 60").
  lawWord: "Chapter",

  // Joint resolutions proposing amendments to the Nevada Constitution pass each house by a majority of its members in two
  // sessions in a row, then go to the voters at the next general election (Art. 16, sec. 1); never to the governor.
  amendments: true,
  amendmentVote: "a majority of each house's members in two sessions in a row",
  // A resolution passed again carries its first session's name ("SJR 7 of the 82nd Session"); the records read here have
  // only each session's new resolutions, so every one shown is a first passage.
  amendmentFinal: (b) => /\bof the \d+(?:st|nd|rd|th) Session\b/i.test(`${b.title} ${b.summary}`),
  amendmentAgain: (b) => `Next: the Legislature has to pass it again, unchanged, in the ${DATA.session + 2} session; then it goes to the voters at the November ${DATA.session + 3} general election.`,
  ballotLine: () => `It goes to the voters at the next general election.`,

  // NELIS's page for the bill, by its bill key (a version's `link`, from convert.py).
  billUrl(p) {
    const b = typeof BILLS !== "undefined" && BILLS.find((x) => x.nums.includes(p));
    return b?.vers?.[0]?.link || "https://www.leg.state.nv.us/App/NELIS/REL/";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: text, amendments, hearings, fiscal notes and votes`)).join("<br>");
  },

  // The regular session meets only in odd years: 120 days from the first Monday of February (Constitution, Art. 4, sec. 2).
  // Special sessions (left out here) meet when the governor calls them.
  opens(year) {
    const t = new Date(year, 1, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7));
    return `${year}-02-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The session's nth day (the first Monday of February is day 1).
  day: (year, n) => STATE.plusDays(STATE.opens(year), n - 1),
  adjourns: (year) => STATE.day(year, 120),
  sessionEnds: (session) => STATE.adjourns(session),
  floorVotesEnd: false,
  // Joint Standing Rule 14.3: a bill has to pass its first committee by day 68 and its own house by day 79, then the
  // other house's committee by day 102 and the other house by day 109. Bills that spend money or affect revenue are
  // exempt, and a waiver can lift a deadline.
  originDeadline: (b) => b.topics.includes("const") || b.vers.some((v) => v.actions.some(([, x]) => /^Exempt from the session's deadlines|^Granted a waiver/.test(x))) ? null : STATE.day(DATA.session, 79),
  originWord: "the deadline to pass its own house",
  // The governor has 5 days (Sundays excepted) after a bill is delivered during the session; when the Legislature
  // adjourns first, 10 days after it adjourns (Art. 4, sec. 35). A bill not acted on becomes law.
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    const end = STATE.adjourns(a % 2 ? a : a - 1);
    if (iso >= end) return STATE.plusDays(end, 10) < isoToday() ? null : STATE.plusDays(end, 10);
    let n = 5;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const due = ymd(t), last = due > end ? STATE.plusDays(end, 10) : due;
    // Past due with no decision recorded (convert.py says "The records show no decision by the governor"): no deadline.
    return last < isoToday() ? null : last;
  },
  dueLabel: () => "Governor's decision due (5 days during the session, Sundays excepted; 10 days after it adjourns)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session), 10),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Waiting to go to the governor", () => "Bills that pass both houses are enrolled and delivered to the governor, usually within a few days."],
  passedBothNext: () => ({
    what: "it's enrolled and delivered to the governor, who has 5 days (Sundays excepted) to sign it or veto it, or 10 days after the session adjourns. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  // A veto after the session goes back to the next regular session, which can override it by two-thirds of each house
  // (Art. 4, sec. 35): until that session ends, the veto isn't final (convert.py adds a line saying so to the history).
  vetoReturns(b) {
    const line = b.stage === 6 && b.vers[0].actions.map(([, t]) => t).find((t) => /^Vetoed after the session ended: the veto goes back to the Legislature's \d{4} session/.test(t));
    const y = line ? +line.match(/(\d{4}) session/)[1] : 0;
    if (!y) return null;
    if (isoToday() > STATE.adjourns(y))
      return { live: false, short: `went back to the ${y} session`, what: `Vetoed after the session ended, so it went back to the Legislature's ${y} session, which could have overridden the veto; the records here don't show an override.`, reason: `Vetoed after the session ended. The ${y} session could have overridden the veto.` };
    return {
      live: true, short: `goes back to the Legislature in ${y}`,
      what: `Vetoed after the session ended, so it goes back to the Legislature when the ${y} session opens (${fmtDate(STATE.opens(y))}). The Legislature can override the veto there: it takes two-thirds of each house, 28 Assembly members and 14 senators. If it doesn't, the veto stands.`,
      reason: `Vetoed after the session ended. The ${y} session can override the veto by two-thirds of each house.`,
    };
  },
  townWord: "City, town, community or county",
  addressLookup: true,
  findReps: "https://openstates.org/find_your_legislator/",
  oneNumber: true,
  diesAfterFloor: () => "Bills that didn't pass died when the session adjourned; a special session takes up only the bills it was called for.",
  outOfTimeLine: "Died when the session adjourned",
  heldTip: "Heard by a committee that never voted on it. Nevada's committees don't vote bills down; a bill they don't approve by the deadline dies there.",
  heldNote: "heard by a committee that never voted on it.",
  // A bill that missed a deadline (Joint Standing Rule 14.3) or lost its floor vote is dead for the session: its status
  // and "what's next" say so.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const d = texts.findLastIndex((t) => /^Missed a deadline/.test(t));
    if (d >= 0) {
      const rule = (texts[d].match(/Rule ([\d.]+)/) || [])[1] || "";
      const which = { "14.3.1": "its first committee's deadline", "14.3.2": "the deadline to pass its own house", "14.3.3": "the other house's committee deadline", "14.3.4": "the other house's deadline" }[rule] || "a deadline";
      return { status: b.stage === 2 ? `Passed the ${b.passedIn}; missed the next deadline` : b.stage === 1 ? "Missed the deadline for a floor vote" : "Missed the committee deadline", when: `Missed ${which} on ${fmtDate(acts[d][0])} (Joint Standing Rule ${rule}).`, tail: "That ends it for this session." };
    }
    const i = texts.findLastIndex((t) => /^Failed in the (Assembly|Senate)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |^The (Assembly|Senate) voted to reconsider/.test(t))) return null;
    const h = texts[i].match(/the (Assembly|Senate)/)[1];
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `${texts[i].replace(/,.*$/, "")} on ${fmtDate(acts[i][0])}.`,
      tail: "That ends it, unless the house reconsiders the vote.",
    };
  },

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.adjourns(y);
    if (t > end && t < STATE.opens(y + 2))
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died. Bills the governor vetoed after it ended go back to the Legislature when the ${y + 2} session opens ${fmtDate(STATE.opens(y + 2))}, which can override them by two-thirds of each house. Bills for ${y + 2} are prefiled from the fall before.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The Legislature's ${STATE.nth(raw.session)} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: one regular session, in the first year.
  calendarDays: 20,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), c1 = STATE.day(Y, 68), h1 = STATE.day(Y, 79), c2 = STATE.day(Y, 102), h2 = STATE.day(Y, 109);
    return {
      leg: [["", o1, a1, "120-day session"], ["light", a1, `${Y + 1}-12-31`, "Interim (no regular session)"]],
      gov: [["light", o1, STATE.plusDays(a1, 10), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The session opens. Most bills were prefiled; members' bills must be filed in the first weeks."],
        [c1, "down", LEG, MD(c1), "Deadline: a bill has to pass a committee in its own house (day 68)."],
        [h1, "up", LEG, MD(h1), "Deadline: a bill has to pass its own house (day 79)."],
        [c2, "down", LEG, MD(c2), "Deadline: a committee in the other house (day 102)."],
        [h2, "up", LEG, MD(h2), "Deadline: the other house (day 109)."],
        [a1, "down", LEG, MD(a1), "The session adjourns (day 120). Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "up", LEG, "July 1", "The two-year budget starts."],
        [`${Y}-10-01`, "down", LEG, "October 1", "Most new laws take effect."],
      ],
      note: "During the session the governor has 5 days (Sundays excepted) to sign or veto a bill; after it adjourns, 10 days. A bill the governor doesn't act on becomes law. A veto during the session goes back to the bill's house; one after it goes to the next session. Overriding a veto takes two-thirds of each house. Bills that spend money or affect revenue are exempt from the deadlines.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member list",
  openUntil: (s) => `the ${s} session adjourns`,

  commIntro: [
    ["A committee decides whether a bill moves.", "Each bill goes to a standing committee of its house, which hears it and may recommend \"do pass\" (with or without amendments). Committees don't vote bills down: a bill they don't act on by the deadline dies there."],
    ["Then the full house votes on it.", "Bills that cost money go on to Ways and Means (Assembly) or Finance (Senate) first. Most bills need a majority of each house's members; bills that raise taxes need two-thirds."],
  ],
  // The current session's page between sessions (most of its two years) reads like a finished session's.
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
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "In a committee, which may hear it and recommend \"do pass\". A bill the committee doesn't approve by the deadline dies there.",
    "Approved by its committee and waiting for a vote of the full house.",
    "Passed the Assembly or the Senate, but not both. If the second house amends it, the first has to agree.",
    "Passed both houses; it's enrolled and delivered to the governor.",
    "Delivered to the governor, who has 5 days (Sundays excepted) during the session, or 10 days after it adjourns.",
    "Signed into law, or became law without the governor's signature or over a veto: a chapter of the Statutes of Nevada.",
    "Vetoed by the governor. Overriding takes two-thirds of each house; a veto after the session goes to the next one.",
  ],
  pastStageTips: [
    "Never approved by a committee before the deadline.",
    "Approved by a committee, but never passed by the full house.",
    "Passed the Assembly or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Delivered to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Each Senate committee's Assembly counterpart where the names differ, and the subject it's shown under.
  commPairs: {
    "Finance": ["Ways and Means", "Budget and spending"],
    "Revenue and Economic Development": ["Revenue", "Taxes and revenue"],
  },
  commNotes: {
    "Finance": "Bills that cost money go to the Assembly Ways and Means or Senate Finance Committee after their policy committee; the two committees also write the budget, often meeting together.",
    "Revenue and Economic Development": "The Senate's Revenue and Economic Development Committee also takes economic development bills; in the Assembly, Commerce and Labor or Government Affairs often does.",
  },
  moneyCommittees: { S: "Finance", A: "Ways and Means" },
  secondCommittee: "Bills that cost money go on to the Assembly Ways and Means or Senate Finance Committee after their policy committee.",
};
