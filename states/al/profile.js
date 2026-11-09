// Alabama: the page's settings and rules that are particular to this state. build_data.py puts this file into every page,
// just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "al",
  name: "Alabama",
  abbr: "AL",
  // Steps that aren't news on a watchlist card.
  routine: /^(Read the second time|The (?:House|Senate) vote:|The (?:House|Senate) adopted a budget isolation resolution|Read the third time|Engrossed|Enrolled$|Sent for the presiding officer's signature|Local bill: notice certified|Carried over|The .* Committee reported it favorably|Reported favorably by the committee|.* (?:\d+(?:st|nd|rd|th) )?(?:Amendment|Substitute)(?: Offered)?$|.*motion to (?:Adopt|Table)|.*Add Cosponsor|.*Petition to (?:Cease|Close) Debate|.*Previous Question)/i,
  publicSite: "https://statebilltracker.org/al/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year; bills die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are numbered Acts of each year ("Act 2025-312"; shown as Act 312 of that year's page).
  lawWord: "Act",
  // Constitutional amendments are bills: three-fifths of each house's members send one to the voters (statewide, or for a
  // local amendment the county's), never to the governor (Constitution of Alabama of 2022, sec. 284).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "three-fifths of each house's members",
  ballotLine: () => "Next: the voters, at the election the amendment names (statewide, or only in the county a local amendment concerns).",
  govReach: `<a href="https://governor.alabama.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Montgomery <a class="phone" href="tel:+13342427100" data-contact="call|governor">(334) 242-7100</a>`,

  // ALISON has no address for one bill's page (its search is built in the browser), so a bill links to its newest text
  // (each version's `link`, a PDF) and the Act's page at the Secretary of State.
  billUrl(p, session = DATA.session) {
    return `https://alison.legislature.state.al.us/files/pdf/SearchableInstruments/${session}RS/${p}-int.pdf`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const out = [];
    for (const v of b.vers) {
      if (v.link && !/-int\.pdf$/.test(v.link)) out.push(link(v.link, `${esc(v.p)}: newest text (PDF)`));
      out.push(link(STATE.billUrl(v.p), `${esc(v.p)}: as introduced, with the synopsis (PDF)`));
    }
    if (b.chapter) out.push(link(`https://arc-sos.state.al.us/cgi/actdetail.mbr/detail?page=act&year=${DATA.session}&act=${b.chapter}`, `Act ${DATA.session}-${b.chapter} at the Secretary of State`));
    out.push(link("https://alison.legislature.state.al.us/bill-search", "Search ALISON for its status, votes and amendments"));
    return out.join("<br>");
  },

  // A regular session a year: 30 legislative days within 105 calendar days, from the first Tuesday of February; in an
  // election year (2026, 2030) from the second Tuesday of January, and in the year after one (2027) from the first
  // Tuesday of March (Constitution, sec. 48.01). `dated` holds each year's last day (add each year's).
  dated: { 2024: "2024-05-09", 2025: "2025-05-14", 2026: "2026-04-09" },
  nth(year, month, weekday, nth) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (nth - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens: (year) => year % 4 === 2 ? STATE.nth(year, 1, 2, 2) : year % 4 === 3 ? STATE.nth(year, 3, 2, 1) : STATE.nth(year, 2, 2, 1),
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
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 98),
  // The governor has 6 days (Sundays excepted) after a bill is delivered while the Legislature is in session; a bill not
  // returned by then becomes law without a signature. A bill delivered within the session's last days, or after it ends,
  // has to be signed within 10 days after adjournment, or it dies: a pocket veto (Constitution, sec. 125).
  govDeadline(iso) {
    if (!iso) return null;
    const end = STATE.sessionEnds(+iso.slice(0, 4)), six = STATE.plusWeekdays(iso, 6);
    return six <= end ? six : STATE.plusDays(end > iso ? end : iso, 10);
  },
  dueLabel: () => "Governor's decision due (6 days during the session, Sundays excepted; 10 days after it ends, or it dies)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the presiding officers and delivered to the governor, usually within a few days."],
  passedBothNext: () => ({
    what: "it's enrolled and delivered to the governor, who has 6 days (Sundays excepted) to sign it, veto it or send it back with an amendment; after the session ends, 10 days to sign it, or it dies (a pocket veto). The governor can veto items in an appropriation bill. A veto is overridden by a majority of each house's members.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://myinfo.alabamavotes.gov/voterview",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session ended",

  // Alabama's committees report bills favorably or not at all: a bill the committee doesn't take up dies there.
  heldLabel: "Held in committee",
  heldTip: "The committee never reported it, which ends it for the session.",
  heldNote: "the committee never reported it, which ends it for the session.",
  // A bill voted down or indefinitely postponed on the floor (often because its companion bill passed instead) is dead
  // for the session.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const i = texts.findLastIndex((t) => /^Failed to pass the (House|Senate)|^Indefinitely postponed in the (House|Senate)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |^The (House|Senate) voted to reconsider/.test(t))) return null;
    const h = texts[i].match(/the (House|Senate)/)[1], ip = /^Indefinitely/.test(texts[i]);
    return {
      status: (b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; ` : "") + (ip ? `indefinitely postponed in the ${h}` : `voted down in the ${h}`).replace(/^./, (c) => b.stage === 2 && b.passedIn !== h ? c : c.toUpperCase()),
      when: `${texts[i].replace(/ \(.*$/, "").replace(/, \d+-\d+$/, "")} on ${fmtDate(acts[i][0])}.`,
      tail: ip ? "That ends it for the session (often because a companion bill passed instead)." : "That ends it, unless the house reconsiders the vote.",
    };
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t < `${y + 1}-01-01`)
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.${y % 4 === 2 ? " Every legislator's seat was on the ballot in November, so the new Legislature chooses its leaders before then." : ""}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.plusDays(adj, 10), last = STATE.plusDays(open, 104);
    return {
      leg: [["", open, adj, "Regular session"]],
      gov: [["light", open, adj, "6 days a bill"], ["", adj, due, "10 days"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens: 30 legislative days within 105 calendar days. Bills can be prefiled before it."],
        [adj, "down", LEG, MD(adj), "The session ends (sine die). Bills that didn't pass both houses die."],
        [due, "down", LEG, MD(due), "The governor's last day to sign bills delivered at the end of the session; unsigned ones die (a pocket veto)."],
        ...(adj < last ? [] : [[last, "down", LEG, MD(last), "The 105th calendar day: the latest the session can run."]]),
        [`${Y}-10-01`, "down", LEG, "October 1", "The state's budget year starts."],
      ],
      note: "During the session the governor has 6 days (Sundays excepted) to sign or veto a bill, or to send it back with an amendment; a bill not acted on becomes law. After the session ends, a bill not signed within 10 days dies (a pocket veto). The governor can veto items in an appropriation bill. Overriding a veto takes a majority of each house's members (18 senators, 53 representatives).",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member records",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Bills go to a standing committee on their subject.", "Each house sends a bill to one of its standing committees when it's read the first time. Local bills, for one county or city, go to the house's Local Legislation Committee or to the county's own delegation committee (Jefferson, Mobile, Madison and others), made up of the members from that county."],
    ["The committee reports it, or not.", "Alabama's committees report a bill favorably (often with amendments or a substitute) or don't report it at all; a bill the committee doesn't take up dies there."],
    ["Reported bills go on the calendar.", "A reported bill is read a second time and placed on the calendar. Each house's Rules Committee sets the special order calendars that decide which bills come up for a vote."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died on the floor (never voted on, voted down or postponed)", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "In a standing committee (or a local legislation committee). The committee decides whether to report it.",
    "Reported by its committee and on the calendar; the Rules Committee's special order calendars decide which bills come up for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, signed by the presiding officers and delivered to the governor.",
    "Delivered to the governor, who has 6 days (Sundays excepted) to sign it, veto it or propose an amendment; after the session ends, a bill not signed within 10 days dies.",
    "Became law, with an Act number: signed, or law without the governor's signature or over a veto.",
    "Vetoed by the governor, or not signed within 10 days after the session ended (a pocket veto). Overriding a veto takes a majority of each house's members.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "Reported by its committee, but never passed its house: not brought up, voted down or indefinitely postponed (often because a companion bill passed instead).",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto (the governor may have proposed an amendment the Legislature didn't take up).",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Agriculture, Conservation, and Forestry": ["Agriculture and Forestry", "Agriculture"],
    "Banking and Insurance": ["Insurance", "Banking and insurance"],
    "Children and Youth Health": ["Children and Senior Advocacy", "Children"],
    "Finance and Taxation Education": ["Ways and Means Education", "The education budget and taxes"],
    "Finance and Taxation General Fund": ["Ways and Means General Fund", "The general fund budget and taxes"],
    "Fiscal Responsibility and Economic Development": ["Economic Development and Tourism", "Economic development"],
    "Healthcare": ["Health", "Health"],
    "State Governmental Affairs": ["State Government", "State government"],
    "Transportation and Energy": ["Transportation, Utilities and Infrastructure", "Transportation"],
    "Veterans, Military Affairs and Public Safety": ["Public Safety and Homeland Security", "Public safety"],
  },
  commNotes: {
    "Finance and Taxation Education": "Alabama has two budgets, the Education Trust Fund and the General Fund, and each house has a committee for each: the Senate's Finance and Taxation committees and the House's Ways and Means committees.",
    "Local Legislation": "Local bills (for one county or city) go to the Local Legislation Committee or to a county's own delegation committee; they usually pass if the county's delegation agrees, and the rest of the house abstains.",
  },
  moneyCommittees: { S: "Finance and Taxation General Fund", H: "Ways and Means General Fund" },
  secondCommittee: "Each house has two budget committees: the Senate's Finance and Taxation committees (Education, General Fund) and the House's Ways and Means committees.",
};
