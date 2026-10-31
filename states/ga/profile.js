// Georgia: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ga",
  name: "Georgia",
  abbr: "GA",
  // Steps that aren't news on a watchlist card.
  routine: /^(House Hopper|Senate Hopper|House Second Readers|House Prefiled|Effective Date|Senate Engrossed|House Immediately Transmitted|Senate Transmitted|Act \d+)/i,
  publicSite: "https://statebilltracker.org/ga/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a two-year General Assembly).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  govReach: `<a href="https://gov.georgia.gov/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Atlanta <a class="phone" href="tel:+14046561776" data-contact="call|governor">(404) 656-1776</a>`,
  // A law's number: "Act 696".
  lawWord: "Act",

  // The General Assembly's bill page is addressed by its legislation id ("link", from convert.py), not its number.
  billUrl(p) {
    const v = (BILLS || []).flatMap((b) => b.vers).find((x) => x.p === p);
    return v?.link || "https://www.legis.ga.gov/legislation/all";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text and votes`)).join("<br>");
  },

  // Each year's session opens the second Monday of January and lasts 40 legislative days, to late March or early April
  // (the last day is set each year; the ones past are from the floor votes). The General Assembly ends with the second
  // year's session; bills from the first year carry over.
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  dated: { 2023: "2023-03-29", 2024: "2024-03-28", 2025: "2025-04-04", 2026: "2026-04-02" },
  adjourns: (year) => STATE.dated[year] || `${year}-04-03`,
  sessionEnds: (session) => STATE.adjourns(session + 1),
  // The governor has 6 days (Sundays excepted) during the session, and 40 days after it ends for bills received in its
  // last days (Georgia Constitution, Art. V, sec. II, para. IV).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 6;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    const end = STATE.adjourns(a);
    if (ymd(t) <= end) return ymd(t);
    const [x, y, z] = end.split("-").map(Number);
    return ymd(new Date(x, y - 1, z + 40));
  },
  dueLabel: () => "Governor's decision due (6 days during the session; 40 days after it ends)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses go to the governor, who acts on most within 40 days of the session's end."],
  passedBothNext: () => ({
    what: "it goes to the governor, who can sign it or veto it (or veto items in the budget). A bill the governor doesn't veto becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: true,
  findReps: "https://openstates.org/find_your_legislator/",
  oneNumber: true,
  diesAfterFloor: (y2) => `It can still pass in the ${y2} session; bills that haven't passed by its end die.`,
  outOfTimeLine: "Died when the General Assembly ended",

  committeeNext: {
    "Rules": "the Rules Committee decides whether it gets a floor vote.",
  },
  chairAsks: {
    "Rules": ["schedule it for a floor vote", "keep it off the floor calendar"],
  },

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > STATE.govDeadline(end)) return "";
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The ${y} session ended ${fmtDate(STATE.adjourns(y))}. Bills that didn't pass carry over to the ${y + 1} session, which opens ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > end)
      return `The ${y + 1} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the next General Assembly opens in January ${y + 2}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} General Assembly opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "40-day session"], ["light", a1, o2, "Interim"], ["", o2, a2, "40-day session"]],
      gov: [["light", o1, STATE.govDeadline(a1), "Acts on bills"], ["light", o2, STATE.govDeadline(a2), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The first session opens."],
        [a1, "down", LEG, MD(a1), "Sine die: the session ends. Bills that didn't pass carry over."],
        [o2, "up", LEG, MD(o2), "The second session opens where the first left off."],
        [a2, "down", LEG, MD(a2), "Sine die: bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "July 1", "Most new laws take effect."],
      ],
      note: "During the session the governor has 6 days (Sundays excepted) to act on a bill; bills that arrive in the last days get 40 days after the session ends. The governor can veto items in the budget. Overriding a veto takes two-thirds of each house. Most new laws take effect July 1.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's member records",
  openUntil: (s) => `the ${span(s)} General Assembly ends in ${s + 1}`,

  commIntro: [
    ["Every bill starts in a committee on its subject.", "The Speaker or the Lieutenant Governor sends it to a standing committee, whose chair decides whether it gets a hearing and a vote."],
    ["Then the Rules Committee.", "A bill a committee approves goes to the house's Rules Committee, which decides which bills reach the floor."],
    ["Local bills are different.", "Bills for one city or county (local legislation) need the support of that area's delegation and usually pass on a local calendar without debate."],
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
    "Waiting in a committee. A bill a committee approves goes next to the Rules Committee, which decides which bills reach the floor.",
    "A committee reported it favorably, and it waits for the Rules Committee to put it on the calendar for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It goes to the governor.",
    "Sent to the governor, who has 6 days during the session or 40 days after it ends.",
    "Signed into law (an Act), or became law without the governor's signature.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the General Assembly ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be introduced again in the next one.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "A bill a committee approves goes to the Rules Committee, which decides which bills reach the floor.",
};
