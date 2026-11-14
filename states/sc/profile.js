// South Carolina: the page's settings and rules that are particular to this state. build_data.py puts this file into
// every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "sc",
  name: "South Carolina",
  abbr: "SC",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled$|Introduced$|Received in the|Sponsors (added|removed)|Scrivener's error|Debate requested|Debate requests withdrawn|Third reading set|The (House|Senate) vote|Read a second time|Sent to a subcommittee|Takes effect|Effective date|Act No\.|Ratified|Amended in the|The committee's amendment|Debate adjourned|Debate interrupted|Special order|Committee Amendment|Placed on the)/,
  publicSite: "https://statebilltracker.org/sc/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 126th General Assembly).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  assembly: (s) => 126 + (s - 2025) / 2,
  // "126th General Assembly"
  ga(s) { const n = STATE.assembly(s), t = n % 100; return `${n}${t > 10 && t < 14 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" })[n % 10] || "th"}`; },
  // The governor's contact form and address are from governor.sc.gov (read by program 2026-11-13); the phone, (803)
  // 734-2100, isn't on that page and hasn't been checked by the owner.
  govReach: `<a href="https://contactgovernor.my.site.com/constituents/s/contact-the-governor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · <a class="phone" href="tel:+18037342100" data-contact="call|governor">(803) 734-2100</a>`,
  // Laws are Acts, numbered through each General Assembly ("Act No. 212" of 2026).
  lawWord: "Act",

  // Constitutional amendments are joint resolutions: two-thirds of each house's members, then the voters at the next
  // general election (in even years); if they approve, the next General Assembly ratifies it by an act. Neither goes to
  // the governor (Constitution, Art. XVI, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  ballotEvenYears: true,
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || "";
    let y = +d.slice(0, 4) + (d.slice(5, 7) > "07" ? 1 : 0);
    if (y % 2) y++;
    return (isoToday() > `${y}-11-10` ? `It went to the voters in November ${y}; the records here don't show the result.` : `Next: the voters, in November ${y}.`)
      + " If they approve it, the next General Assembly ratifies it, and then it's part of the constitution.";
  },

  // The bill's page on scstatehouse.gov: the bill search for its number and General Assembly.
  billUrl(p, s) {
    const n = String(p).replace(/^[A-Z]+/, ""), ses = typeof DATA !== "undefined" ? STATE.assembly(s || DATA.session) : 126;
    return `https://www.scstatehouse.gov/billsearch.php?billnumbers=${n}&session=${ses}&summary=B`;
  },
  textLinks(b) {
    const s = DATA.session, ses = STATE.assembly(s), folder = `sess${ses}_${s}-${s + 1}`;
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => {
      const n = v.p.replace(/^[A-Z]+/, "");
      return `${link(STATE.billUrl(v.p, s), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: history, votes and versions`)} · ${link(`https://www.scstatehouse.gov/${folder}/bills/${n}.htm`, "Text")}`;
    }).join("<br>");
  },

  // Each year's session opens the second Tuesday of January and adjourns sine die, by law, on the second Thursday of
  // May (S.C. Code 2-1-180). A sine die resolution lets the houses return for vetoes, conference reports and the
  // budget (June, and in 2026 August). The House's term ends at the November election of the second year.
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sineDie(year) {
    const t = new Date(year, 4, 1); t.setDate(1 + ((4 - t.getDay() + 7) % 7) + 7);
    return `${year}-05-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  election(year) {
    const t = new Date(year, 10, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
    return `${year}-11-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => STATE.sineDie(session + 1),
  floorVotesEnd: false,
  // The governor has 5 days (Sundays excepted) after a bill is presented; a bill not returned becomes law, and when an
  // adjournment prevents its return, the governor has until the second day of the next meeting (Constitution, Art. IV,
  // sec. 21). Bills are presented when they're ratified.
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 5;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (5 days after ratification, Sundays excepted)",

  passedBothBy: (session) => STATE.plusDays(STATE.sineDie(session + 1), 120),
  passedBothNote: (live) => live ? "Waiting to be ratified" : "Never ratified",
  passedBothGroup: ["Waiting to be ratified", () => "A bill that passed both houses is ratified (signed by the President of the Senate and the Speaker), usually within days, and then goes to the governor, who has 5 days (Sundays excepted)."],
  passedBothNext: () => ({
    what: "it's ratified (signed by the President of the Senate and the Speaker) and goes to the governor, who has 5 days (Sundays excepted) to sign it or veto it. A bill the governor doesn't return becomes law; after the General Assembly adjourns, the governor has until the second day it meets again. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of the members present in each house.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town, community or county",
  addressLookup: true,
  findReps: "https://www.scstatehouse.gov/legislatorssearch.php",
  oneNumber: true,
  diesAfterFloor: () => "The General Assembly has ended, so it died with it.",
  outOfTimeLine: "Died when the General Assembly ended",

  // South Carolina's committees don't table bills: a bill they don't take up stays there.
  heldLabel: "Held without a vote",
  heldTip: "South Carolina's committees rarely vote a bill down: a bill the committee doesn't report stays there.",
  heldNote: "a bill the committee never reported. South Carolina's committees rarely vote bills down.",
  // A bill voted down on second reading ends there, unless the house reconsiders.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const i = texts.findLastIndex((t) => /^(Failed in the (House|Senate) on second reading|Rejected by the (House|Senate))/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |voted to reconsider/.test(t))) return null;
    const h = texts[i].match(/(House|Senate)/)[1];
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `${texts[i]} on ${fmtDate(acts[i][0])}.`,
      tail: "That ends it, unless the house votes to reconsider.",
    };
  },

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end1 = STATE.sineDie(y), end2 = STATE.sineDie(y + 1);
    if (t > end1 && t < `${y + 1}-01-01`) return `The ${y} session adjourned ${fmtDate(end1)}. Bills that haven't passed stay alive for the second year, which opens ${fmtDate(STATE.opens(y + 1))}. The governor acts on bills as they're ratified.`;
    if (t > end2) return `The ${STATE.ga(y)} General Assembly's last session adjourned ${fmtDate(end2)} (it came back later only for vetoes, conference reports and the budget). Bills that didn't pass both houses died. The next General Assembly opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${STATE.ga(raw.session)} General Assembly opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled in December. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, each from January to the second Thursday of May.
  calendarDays: 14,
  calendar(Y) {
    const LEG = 112, o1 = STATE.opens(Y), o2 = STATE.opens(Y + 1), e1 = STATE.sineDie(Y), e2 = STATE.sineDie(Y + 1), el = STATE.election(Y + 1);
    const MDt = (iso) => new Date(`${iso}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" });
    return {
      leg: [["", o1, e1, "Session"], ["light", STATE.plusDays(e1, 1), o2, "Recess"], ["", o2, e2, "Session"], ["light", STATE.plusDays(e2, 1), el, "Recess"]],
      gov: [["light", o1, STATE.plusDays(e2, 120), "Acts on bills as they're ratified"]],
      events: [
        [o1, "up", LEG, MDt(o1), "The General Assembly opens. Bills prefiled in December are introduced."],
        [e1, "down", LEG, MDt(e1), "Sine die by law. Bills stay alive for the second year; the houses come back in June for vetoes and the budget's conference report."],
        [o2, "up", LEG, MDt(o2), "The second year's session opens."],
        [e2, "down", LEG, MDt(e2), "The last regular day. Bills that didn't pass both houses die."],
        [el, "up", LEG, MDt(el), "Election day: all 124 House seats (and, in presidential years, all 46 Senate seats)."],
      ],
      note: "A bill that hasn't passed its own house by April 10 needs two-thirds of the other house to be taken up that year. The fiscal year starts July 1, so the budget passes in May or June. The governor has 5 days (Sundays excepted) after a bill is ratified, and can veto items in an appropriation bill. Overriding a veto takes two-thirds of the members present in each house.",
    };
  },
  waitingHead: "Waiting for the governor",
  govYearsNote: "",
  partySource: "Party from the General Assembly's member list",
  openUntil: (s) => `the General Assembly's last session adjourns ${fmtDate(STATE.sineDie(s + 1))}`,

  commIntro: [
    ["Committees report a bill favorably, or not at all.", "A committee (often after a subcommittee hearing) reports a bill favorably, with or without amendments; a bill it doesn't report stays there. A Senate committee's members can also be polled in writing, and either house can recall a bill from committee. Local bills go to the county's legislative delegation instead."],
    ["Then the full house reads it a second and a third time.", "The second reading is the main debate and vote (usually a roll call); the third reading, usually the next day, passes it. In the House, members can object to a bill on the calendar (a \"request for debate\"), which keeps it off the uncontested calendar."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses, waiting to be ratified", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses, never ratified", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee (or a county's legislative delegation). A committee reports a bill favorably, or not at all.",
    "Reported by its committee (or recalled from it) and on the calendar. The house debates it on second reading and passes it on third.",
    "Passed the House or the Senate, but not both. If the second house amends it, the first has to agree.",
    "Passed both houses in the same form (enrolled). It's ratified, then goes to the governor.",
    "Ratified and sent to the governor, who has 5 days (Sundays excepted).",
    "Signed into law, or became law over a veto: an Act.",
    "Vetoed by the governor. Overriding takes two-thirds of the members present in each house.",
  ],
  pastStageTips: [
    "Never reported by its committee before the General Assembly ended.",
    "Reported by its committee, but never passed by the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but never ratified.",
    "Ratified and sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be filed again in the next one.",

  // Each Senate committee's House counterpart (the 126th General Assembly's names) and the subject it's shown under.
  commPairs: {
    "Agriculture and Natural Resources": ["Agriculture, Natural Resources and Environmental Affairs", "Agriculture and natural resources"],
    "Fish, Game and Forestry": ["Agriculture, Natural Resources and Environmental Affairs", "Fish, game and forestry"],
    "Education": ["Education and Public Works", "Education"],
    "Transportation": ["Education and Public Works", "Transportation"],
    "Medical Affairs": ["Medical, Military, Public and Municipal Affairs", "Health"],
    "Family and Veterans' Services": ["Medical, Military, Public and Municipal Affairs", "Families and veterans"],
    "Banking and Insurance": ["Labor, Commerce and Industry", "Banking and insurance"],
    "Finance": ["Ways and Means", "Budget and taxes"],
    "Corrections and Penology": ["Judiciary", "Prisons"],
    "Legislative Oversight": ["Government Efficiency and Legislative Oversight", "Oversight of state agencies"],
  },
  commNotes: {
    "Education": "The House's Education and Public Works Committee also takes highway and transportation bills; in the Senate, the Transportation Committee does.",
    "Medical Affairs": "The House's Medical, Military, Public and Municipal Affairs Committee takes health, veterans', military and local government bills.",
    "Finance": "The House Ways and Means and Senate Finance committees write the budget and take tax bills.",
    "Labor, Commerce and Industry": "The House's Labor, Commerce and Industry Committee also takes banking and insurance bills; the Senate has a separate Banking and Insurance Committee.",
  },
  moneyCommittees: { S: "Finance", H: "Ways and Means" },
  secondCommittee: "Bills that cost money can be sent on to the House Ways and Means or Senate Finance Committee.",
};
