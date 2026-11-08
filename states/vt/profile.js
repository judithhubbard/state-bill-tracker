// Vermont: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "vt",
  name: "Vermont",
  abbr: "VT",
  // Steps that aren't news on a watchlist card: calendar entries, the other house's messages, procedural motions, who
  // reported or spoke, amendments offered.
  routine: /^(Notice Calendar|Action Calendar|Entered on Notice Calendar|Pending entry on Notice|On Notice Calendar|Read second time|Second Reading|Read 2nd time|New Business\/|Unfinished Business\/|Consideration (?:postponed|resumed|interrupted)|Senate Message|House message|Rules suspended|Rule \d+ suspended|Roll Call|Which was (?:agreed|disagreed)|Division|Reps?\. |Senators? |Sen\. |Senator\(s\)|Motion|Proposal of amendment|Recommendation of amendment|House proposal of amendment(?:; text| to Senate proposal of amendment, text)?$|Title amended|Title revised|As passed by Senate and House|Called up|Point of order|Committee of Conference (?:appointed|report submitted|report; text)|Speaker appointed|Pending third reading|Pending action|Addendum|First division|Second division|Amendment as offered|Delivered to Secretary of State)/i,
  publicSite: "https://statebilltracker.org/vt/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a biennium).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Laws are Acts, numbered through the biennium ("Act 44"); municipal acts (charters, mostly) are "M-3".
  lawWord: "Act",
  // One number through both houses (H.1 stays H.1 in the Senate).
  oneNumber: true,
  // The governor's office (not checked by the owner yet).
  govReach: `<a href="https://governor.vermont.gov/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Montpelier <a class="phone" href="tel:+18028283333" data-contact="call|governor">(802) 828-3333</a>`,

  // Each bill's page on the Legislature's site (v.link, from LegiScan's record) and on LegiScan.
  billUrl: (p, session = DATA.session) => `https://legislature.vermont.gov/bill/status/${session + 1}/${p.replace(/^([HS])/, "$1.")}`,
  padded: (p) => p.replace(/^([A-Z]+)(\d+)$/, (m, k, n) => k + n.padStart(4, "0")),
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => `${link(v.link || STATE.billUrl(v.p), `${esc(v.p.replace(/^([HS])/, "$1."))}: status, text and amendments`)} · ${link(`https://legiscan.com/VT/bill/${STATE.padded(v.p)}/${DATA.session}`, "on LegiScan")}`).join("<br>");
  },

  // The General Assembly convenes the Wednesday after the first Monday of January in odd years (Vermont Constitution,
  // ch. II, sec. 7) and returns for the second year's session in early January; each year's session usually ends in
  // May (`dated` holds the actual last days), with a day in June for vetoes. A biennium lasts until the next one convenes.
  opened: { 2023: "2023-01-04", 2024: "2024-01-03", 2025: "2025-01-08", 2026: "2026-01-06" },
  dated: { 2023: "2023-05-12", 2024: "2024-05-10", 2025: "2025-06-16", 2026: "2026-05-29" },
  opens(year) {
    if (STATE.opened[year]) return STATE.opened[year];
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 2);  // the first Monday, plus two days
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns: (year) => STATE.dated[year] || `${year}-05-15`,
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (session) => STATE.plusDays(STATE.opens(session + 2), -1),
  // The governor has 5 days, Sundays excepted, after a bill is presented to sign or veto it; a bill the governor doesn't
  // return becomes law without a signature, unless the General Assembly adjourns within three days of presenting it and
  // so prevents its return (ch. II, sec. 11).
  govDeadline(iso) {
    if (!iso) return null;
    const [a, b, c] = iso.split("-").map(Number), t = new Date(a, b - 1, c);
    let n = 5;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (5 days, Sundays excepted, after it's delivered)",

  // Bills that pass in the last weeks are delivered to the governor in batches over the following month or so.
  passedBothBy: (session) => STATE.govDeadline(STATE.plusDays(STATE.adjourns(session + 1), 45)),
  passedBothNote: (live) => live ? "Not yet delivered to the governor" : "Never delivered to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses go to the governor, often a few weeks later, in batches."],
  passedBothNext: () => ({
    what: "it's delivered to the governor, who has 5 days (Sundays excepted) to sign it or veto it. A bill the governor doesn't act on becomes law without a signature.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "Town or city",
  addressLookup: false,
  diesAfterFloor: (y2) => `Unless lawmakers return for a special session, it dies when the biennium ends in January ${y2 + 1}.`,
  outOfTimeLine: "Died when the biennium ended",

  // Committees don't vote bills down: a bill a committee doesn't take up stays there until the biennium ends.
  heldLabel: "Held without a vote",
  heldTip: "A committee never took it up. Vermont's committees rarely vote a bill down; one they don't take up stays there until the biennium ends.",
  heldNote: "a committee never took it up. Vermont's committees rarely vote bills down.",

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y)) return "";
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The General Assembly finished its first-year session ${fmtDate(STATE.adjourns(y))}. Bills that didn't pass stay alive for the second year, which starts ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > STATE.adjourns(y + 1))
      return `The General Assembly finished its second-year session ${fmtDate(STATE.adjourns(y + 1))}. Bills that didn't pass both houses died; the next General Assembly convenes ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} General Assembly convenes ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "First year"], ["light", a1, o2, "Adjourned"], ["", o2, a2, "Second year"], ["light", a2, STATE.sessionEnds(Y), "Adjourned"]],
      gov: [["light", o1, STATE.plusDays(a1, 45), "Acts on bills"], ["light", o2, STATE.plusDays(a2, 45), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The General Assembly convenes; bills are introduced from the first day."],
        [a1, "down", LEG, MD(a1), "The first-year session ends. Bills that didn't pass stay alive."],
        [o2, "up", LEG, MD(o2), "The second-year session starts where the first left off."],
        [a2, "down", LEG, MD(a2), "The second-year session ends. Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "Jul 1", "Most new laws take effect July 1."],
      ],
      note: "Bills are delivered to the governor in batches, often weeks after they pass. The governor has 5 days (Sundays excepted) after a bill is delivered to sign or veto it; a bill the governor doesn't act on becomes law. The General Assembly usually returns for a day in June to take up vetoes: overriding one takes two-thirds of the members present in each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from Open States and LegiScan",
  openUntil: (s) => `the ${span(s)} General Assembly ends in January ${s + 2}`,

  commIntro: [
    ["Each house has its own committees.", "A bill goes to a committee of its own house. Committees take testimony and vote to report it favorably, often with amendments; a bill a committee doesn't take up stays there until the biennium ends."],
    ["Bills that cost money go on to the money committees.", "A House bill that spends money goes on to Appropriations, one that raises revenue to Ways and Means (House Rule 35); in the Senate, to Appropriations or Finance (Senate Rule 31)."],
    ["Committees can write their own bills.", "A committee bill starts on the floor: it's read the first time and goes on the notice calendar without another committee."],
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
    "In a committee of the House or the Senate.",
    "A committee reported it, and it's on the House or Senate notice or action calendar.",
    "Passed the House or the Senate, but not both. If the other house passes it with changes (a \"proposal of amendment\"), the first house has to agree.",
    "Passed both houses in the same form. It goes to the governor, often a few weeks later.",
    "Delivered to the governor, who has 5 days (Sundays excepted) to sign or veto it; if the governor does neither, it becomes law.",
    "Became law (signed, without the governor's signature, or over a veto), with an Act number.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of the members present in each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the biennium ended.",
    "A committee reported it, but it never got through the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Delivered to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This biennium is over. Bills that didn't become law have to be introduced again in the next one.",

  // Each Senate committee's House counterpart and the subject it's shown under (2025-26 names).
  commPairs: {
    "Appropriations": ["Appropriations", "Budget"],
    "Finance": ["Ways and Means", "Taxes"],
    "Agriculture": ["Agriculture, Food Resiliency, and Forestry", "Agriculture"],
    "Economic Development, Housing and General Affairs": ["Commerce and Economic Development", "Business and economic development"],
    "Government Operations": ["Government Operations and Military Affairs", "State government"],
    "Health and Welfare": ["Health Care", "Health"],
    "Institutions": ["Corrections and Institutions", "Corrections and state buildings"],
    "Natural Resources and Energy": ["Environment", "Environment and energy"],
  },
  commNotes: {
    "General and Housing": "The House's housing committee; in the Senate, housing goes to Economic Development, Housing and General Affairs.",
    "Energy and Digital Infrastructure": "The House's energy committee since 2025; in the Senate, energy goes to Natural Resources and Energy.",
  },
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that spend money also go to Appropriations in each house; bills that raise revenue, to Ways and Means (House) or Finance (Senate).",
};
