// Kansas: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ks",
  name: "Kansas",
  abbr: "KS",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled$|Introduced$|Received in the|On the (House|Senate) consent calendar|The (House|Senate) voted to take it up at once|Passed over on General Orders|(Re)?[Ee]ngrossed|Enrolled$|(House|Senate) conference committee members changed|The conference committee's report was filed|Takes effect|Adopted by two-thirds|Withdrawn from the .* Committee and sent back to it|Amended on the)/,
  publicSite: "https://statebilltracker.org/ks/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the biennium "b2025_26").
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // The governor's office: governor.ks.gov answers automated requests with "403 Forbidden", so the phone and address
  // haven't been checked by program or by the owner.
  govReach: `<a href="https://www.governor.ks.gov/" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · <a class="phone" href="tel:+17852963232" data-contact="call|governor">(785) 296-3232</a>`,

  // Constitutional amendments are concurrent resolutions ("A PROPOSITION to amend ..."): two-thirds of each house's
  // members, then the voters, at the next general election or at the election the resolution names (SCR 1611 of 2025,
  // the August 2026 primary). They don't go to the governor (Constitution, Art. 14, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members",
  ballotEvenYears: true,
  // Resolutions that name an earlier election than the next general one (from the resolution's text).
  ballotDates: { "2025:SCR1611": "2026-08-04" },
  ballotLine(b) {
    const d = [b.dates.passS, b.dates.passA].sort().pop() || "";
    const named = STATE.ballotDates[`${DATA.session}:${b.nums[0]}`];
    let y = +d.slice(0, 4);
    if (y % 2) y++;
    const when = named || STATE.election(y);
    const label = named ? `the ${new Date(`${named}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })} primary election` : `November ${y}`;
    return isoToday() > when ? `It went to the voters in ${label}; the records here don't show the result.` : `Next: the voters, in ${label}.`;
  },

  // The bill's page on kslegislature.gov (its history, versions, supplemental notes and votes).
  billUrl(p, s) {
    const ses = s || (typeof DATA !== "undefined" ? DATA.session : 2025);
    return `https://kslegislature.gov/b${ses}_${String(ses + 1).slice(2)}/${/CR/.test(p) ? "resolutions" : "bills"}/${String(p).toLowerCase()}/`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p, DATA.session), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: history, text, supplemental notes and votes`)).join("<br>");
  },

  // Each year's session opens the second Monday of January (Constitution, Art. 2, sec. 8). The regular session runs to
  // "first adjournment" in late March or early April; the houses come back for a few days in late April (the veto
  // session) and adjourn sine die. Bills carry over from the first year to the second. The days each year actually
  // used are in `dated` (from the roll calls' journal days); a year not listed is estimated.
  dated: {
    2023: { adjourn: "2023-04-06", veto: "2023-04-26", end: "2023-04-28" },
    2024: { adjourn: "2024-04-05", veto: "2024-04-26", end: "2024-04-30" },
    2025: { adjourn: "2025-03-27", veto: "2025-04-10", end: "2025-04-11" },
    2026: { adjourn: "2026-03-27", veto: "2026-04-09", end: "2026-04-10" },
  },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // A year not in `dated`: first adjournment the first Friday of April, the veto session from the fourth Thursday
  // of April, three days long.
  days(year) {
    if (STATE.dated[year]) return STATE.dated[year];
    const fri = new Date(year, 3, 1); fri.setDate(1 + ((5 - fri.getDay() + 7) % 7));
    const thu = new Date(year, 3, 1); thu.setDate(1 + ((4 - thu.getDay() + 7) % 7) + 21);
    const iso = (t) => `${year}-04-${String(t.getDate()).padStart(2, "0")}`;
    return { adjourn: iso(fri), veto: iso(thu), end: STATE.plusDays(iso(thu), 2) };
  },
  election(year) {
    const t = new Date(year, 10, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
    return `${year}-11-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => STATE.days(session + 1).end,
  floorVotesEnd: false,
  // The governor has 10 calendar days after a bill is presented; a bill not returned becomes law without the
  // signature (Constitution, Art. 2, sec. 14). There's no pocket veto.
  govDeadline(iso) {
    return iso ? STATE.plusDays(iso, 10) : null;
  },
  dueLabel: () => "Governor's decision due (10 days after the bill is presented)",

  passedBothBy: (session) => STATE.plusDays(STATE.days(session + 1).end, 30),
  passedBothNote: (live) => live ? "Waiting to be enrolled" : "Never presented to the governor",
  passedBothGroup: ["Waiting to be enrolled", () => "A bill that passed both houses is enrolled and presented to the governor, usually within days; the governor then has 10 days."],
  passedBothNext: () => ({
    what: "it's enrolled and presented to the governor, who has 10 days to sign it or veto it; a bill the governor doesn't return becomes law without the signature. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of the members of each house: 27 senators and 84 representatives.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, community or county",
  addressLookup: true,
  findReps: "https://kslegislature.gov/b2025_26/legislators/",
  oneNumber: true,
  diesAfterFloor: () => "The biennium has ended, so it died with it.",
  outOfTimeLine: "Died when the biennium ended",

  // Kansas committees don't vote bills down: a bill the committee doesn't report stays there, and dies at the end
  // of the biennium.
  heldLabel: "Held without a vote",
  heldTip: "Kansas committees rarely vote a bill down: a bill the chair doesn't bring up for a vote stays there.",
  heldNote: "a bill the committee never reported. Kansas committees rarely vote bills down.",
  // A bill that failed on final action ends there, unless the house reconsiders; a rejected conference report can
  // kill it.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const i = texts.findLastIndex((t) => /^(Failed in the (House|Senate)|The (House|Senate) rejected the conference committee's report, killing the bill)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |voted to reconsider|adopted the conference/.test(t))) return null;
    const h = texts[i].match(/(House|Senate)/)[1];
    if (/killing/.test(texts[i])) return { status: "Killed in conference", when: `The ${h} rejected the conference committee's report and killed it on ${fmtDate(acts[i][0])}.`, tail: "" };
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `${texts[i]} on ${fmtDate(acts[i][0])}.`,
      tail: "That ends it, unless the house votes to reconsider.",
    };
  },
  // Roll calls are named by what the house voted on: "Senate emergency final action", "House conference report".
  voteWhat: (v) => (v.kind === "F" && v.committee ? `${STATE.houses[v.house]} ${esc(v.committee.toLowerCase())}` : ""),

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end1 = STATE.days(y).end, end2 = STATE.days(y + 1).end;
    if (t > end1 && t < `${y + 1}-01-01`) return `The ${y} session adjourned ${fmtDate(end1)}. Bills that haven't passed stay alive for ${y + 1}, when the Legislature meets again from ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > end2) return `The ${y}–${String(y + 1).slice(2)} Legislature's last session adjourned ${fmtDate(end2)}. Bills that didn't pass both houses died. The next Legislature opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session}–${String(raw.session + 1).slice(2)} Legislature opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, each with its veto session.
  calendarDays: 14,
  calendar(Y) {
    const LEG = 112, d1 = STATE.days(Y), d2 = STATE.days(Y + 1), o1 = STATE.opens(Y), o2 = STATE.opens(Y + 1), el = STATE.election(Y + 1);
    const MDt = (iso) => new Date(`${iso}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" });
    return {
      leg: [["", o1, d1.adjourn, "Session"], ["light", STATE.plusDays(d1.adjourn, 1), STATE.plusDays(d1.veto, -1), "Break"], ["", d1.veto, d1.end, "Veto session"], ["light", STATE.plusDays(d1.end, 1), o2, "Recess"],
        ["", o2, d2.adjourn, "Session"], ["light", STATE.plusDays(d2.adjourn, 1), STATE.plusDays(d2.veto, -1), "Break"], ["", d2.veto, d2.end, "Veto session"], ["light", STATE.plusDays(d2.end, 1), el, "Recess"]],
      gov: [["light", o1, STATE.plusDays(d2.end, 30), "Acts on bills as they're presented"]],
      events: [
        [o1, "up", LEG, MDt(o1), "The Legislature opens. Bills prefiled in December are introduced."],
        [d1.adjourn, "down", LEG, MDt(d1.adjourn), "First adjournment: the regular session ends. The governor acts on the last bills while the Legislature is away."],
        [d1.veto, "up", LEG, MDt(d1.veto), "The veto session: override votes, the budget's last pieces. Bills stay alive for the second year."],
        [o2, "up", LEG, MDt(o2), "The second year's session opens."],
        [d2.veto, "up", LEG, MDt(d2.veto), "The last veto session. Bills that didn't pass both houses die."],
        [el, "up", LEG, MDt(el), "Election day: all 125 House seats (and, every four years, all 40 Senate seats)."],
      ],
      note: "Most bills have to pass their own house by \"turnaround\" in late February, unless they're in an exempt committee (Appropriations, Ways and Means, Taxation, Federal and State Affairs and a few others). The fiscal year starts July 1. The governor has 10 days after a bill is presented, and can veto items in an appropriation bill. Overriding a veto takes two-thirds of the members of each house.",
    };
  },
  waitingHead: "Waiting for the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member list",
  openUntil: (s) => `the Legislature adjourns sine die in ${s + 1}`,

  commIntro: [
    ["Committees report a bill favorably, or not at all.", "A committee holds a hearing, works the bill and recommends it be passed (often with amendments, sometimes as a substitute bill with the same number), or puts an uncontroversial bill on the consent calendar. A bill the chair doesn't bring up stays in committee. Bills are often sent from one committee to another, or back from the calendar to a committee."],
    ["Then the whole house debates it, and votes the next day.", "On General Orders the house sits as the Committee of the Whole, amends the bill and recommends it be passed (a voice vote); the roll call on passage, \"final action\", comes on a later day, or the same day if the house votes to take it up at once (\"emergency final action\")."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses, waiting to be enrolled", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses, never presented", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. A committee reports a bill favorably, or not at all.",
    "Reported by its committee and on the calendar: General Orders (debate in the Committee of the Whole) or the consent calendar. The roll call on passage is \"final action\".",
    "Passed the House or the Senate, but not both. If the second house changes it, the first has to agree, or a conference committee works out one version.",
    "Passed both houses in the same form. It's enrolled and presented to the governor.",
    "Presented to the governor, who has 10 days.",
    "Signed into law, became law without the signature, or became law over a veto.",
    "Vetoed by the governor. Overriding takes two-thirds of the members of each house.",
  ],
  pastStageTips: [
    "Never reported by its committee before the biennium ended.",
    "Reported by its committee, but never passed by the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but never presented to the governor.",
    "Presented to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This biennium is over. Bills that didn't become law have to be introduced again in the next one.",

  // Each Senate committee's House counterpart (2025–26's names) and the subject it's shown under.
  commPairs: {
    "Assessment and Taxation": ["Taxation", "Taxes"],
    "Ways and Means": ["Appropriations", "The budget"],
    "Commerce": ["Commerce, Labor and Economic Development", "Commerce and labor"],
    "Financial Institutions and Insurance": ["Insurance", "Insurance and banking"],
    "Public Health and Welfare": ["Health and Human Services", "Health"],
    "Utilities": ["Energy, Utilities and Telecommunications", "Energy and utilities"],
    "Local Government, Transparency and Ethics": ["Local Government", "Local government"],
    "Government Efficiency": ["Legislative Modernization", "Government"],
    "Select Committee on Veterans Affairs": ["Veterans and Military", "Veterans"],
    "Organization, Calendar and Rules": ["Calendar and Printing", "Scheduling"],
  },
  commNotes: {
    "Ways and Means": "The Senate Ways and Means and House Appropriations committees write the budget; the House also has budget committees for each part of it (K-12 Education Budget, Social Services Budget ...). Bills sent to them aren't held to the turnaround deadline.",
    "Federal and State Affairs": "Each house's Federal and State Affairs Committee takes many kinds of bills (alcohol, gambling, abortion, elections), and isn't held to the turnaround deadline.",
    "Financial Institutions and Insurance": "The House splits these between its Insurance and its Financial Institutions and Pensions committees.",
  },
  moneyCommittees: { S: "Ways and Means", H: "Appropriations" },
  secondCommittee: "Bills that cost money are often sent on to Senate Ways and Means or House Appropriations.",
};
