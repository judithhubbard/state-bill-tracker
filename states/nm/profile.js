// New Mexico: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "nm",
  name: "New Mexico",
  abbr: "NM",
  // Steps that aren't news on a watchlist card.
  routine: /^(The (?:House|Senate) vote:|Prefiled before the session|Its committees, in order:|Placed on the (?:House|Senate) calendar|Amended on the floor|The .* Committee reported it|Introduced, but not printed|Withdrawn, printed and sent to a committee|Sent to a different committee|The Committees' Committee found it germane)/i,
  publicSite: "https://statebilltracker.org/nm/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year; bills die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are chapters of each year's session laws ("Laws 2025, chapter 13").
  lawWord: "Chapter",
  // Constitutional amendments are joint resolutions: a majority of each house's members sends one to the voters at the
  // next general election (or a special election the Legislature calls), never to the governor (Constitution, Art. XIX,
  // sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://www.governor.state.nm.us/contact-the-governor/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Santa Fe <a class="phone" href="tel:+15054762200" data-contact="call|governor">(505) 476-2200</a>`,

  // The Legislature's page for each bill: its texts, votes, committee reports and the fiscal impact report.
  billUrl(p, session = DATA.session) {
    const m = p.match(/^([HS])(B|JR)(\d+)$/);
    return m ? `https://www.nmlegis.gov/Legislation/Legislation?chamber=${m[1]}&legType=${m[2]}&legNo=${m[3]}&year=${String(session).slice(2)}` : "https://www.nmlegis.gov/";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const base = `https://www.nmlegis.gov/Sessions/${String(DATA.session).slice(2)}%20Regular`, out = [];
    for (const v of b.vers) {
      const m = v.p.match(/^([HS])(B|JR)(\d+)$/);
      if (!m) continue;
      const file = `${m[1]}${m[2]}${m[3].padStart(m[2] === "JR" ? 2 : 4, "0")}`, folder = m[2] === "JR" ? "resolutions" : "bills";
      out.push(link(STATE.billUrl(v.p), `${esc(v.p)}: the Legislature's page (history, votes, committee reports)`));
      out.push(link(`${base}/${folder}/${m[1] === "H" ? "house" : "senate"}/${file}.pdf`, `${esc(v.p)}: text as introduced (PDF)`));
      if (b.stage >= 3 && m[2] === "B") out.push(link(`${base}/final/${file}.pdf`, `${esc(v.p)}: final version (PDF)`));
      out.push(link(`${base}/firs/${file}.PDF`, `${esc(v.p)}: the Legislative Finance Committee's fiscal impact report (PDF)`));
    }
    return out.join("<br>");
  },

  // A regular session a year from the third Tuesday of January: 60 days in odd years, 30 in even years (Constitution,
  // Art. IV, sec. 5), ending at noon on the last day.
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 14);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
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
  sessionEnds: (year) => STATE.plusDays(STATE.opens(year), year % 2 ? 60 : 30),
  // The governor has 3 days (Sundays excepted) to sign or veto a bill presented during the session; one not returned
  // becomes law without a signature. A bill presented in the session's last 3 days, or after it, has 20 days after
  // adjournment, and one not signed by then is vetoed (a pocket veto). The governor can veto items of an appropriation
  // bill (Constitution, Art. IV, sec. 22).
  govDeadline(iso) {
    if (!iso) return null;
    const end = STATE.sessionEnds(+iso.slice(0, 4));
    if (iso >= STATE.plusDays(end, -3)) return STATE.plusDays(end, 20);
    return STATE.plusWeekdays(iso, 3);
  },
  dueLabel: () => "Governor's decision due (3 days, Sundays excepted, during the session; 20 days after it for bills passed at its close, which die unless signed)",

  passedBothBy: (session) => STATE.plusDays(STATE.sessionEnds(session), 20),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the presiding officers and go to the governor; most pass in the session's last days, and the governor has 20 days after it ends to act on them."],
  passedBothNext: () => ({
    what: "it goes to the governor. During the session the governor has 3 days (Sundays excepted) to sign or veto it, or it becomes law without a signature; for bills passed in the session's last 3 days, which is most of them, the governor has 20 days after it ends, and a bill not signed by then is vetoed (a pocket veto). The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://www.nmlegis.gov/Members/Find_My_Legislator",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session ended",

  // In 30-day sessions every Senate bill goes first to the Senate Committees' Committee (the leaders), which decides
  // whether it's germane: on the budget, on the governor's call or a vetoed bill. House bills that aren't printed go to
  // the House Rules and Order of Business Committee.
  gates: { S: "Committees' Committee", H: "Rules and Order of Business" },
  committeeNext: {
    "Committees' Committee": "the Senate Committees' Committee, made up of its leaders, decides whether it's germane to the 30-day session (the budget, the governor's call or a vetoed bill); if not, it goes no further.",
    "Rules and Order of Business": "the House Rules and Order of Business Committee holds bills that weren't printed; few come out.",
  },
  chairAsks: {
    "Committees' Committee": ["find it germane and send it to a committee", "leave it"],
    "Rules and Order of Business": ["release it to a committee", "leave it"],
  },
  heldLabel: "Held in committee",
  heldTip: "The committee never reported it before the session ended, which ends it (the record says \"action postponed indefinitely\").",
  heldNote: "the committee never reported it, which ends it for the session.",
  // A bill a committee recommended not pass, tabled, or voted down on the floor, ends there.
  endedNote(b) {
    const v = b.vers[0], acts = v.actions, texts = acts.map(([, t]) => t);
    const i = texts.findLastIndex((t) => /^Failed in the (House|Senate)|^Tabled|recommended it not pass/.test(t));
    if (i < 0 || b.stage > 2 || texts.slice(i + 1).some((t) => /^PASSED |voted to reconsider/.test(t))) return null;
    const h = (texts[i].match(/the (House|Senate)/) || [])[1];
    const status = /^Failed/.test(texts[i]) ? `Voted down in the ${h}` : /^Tabled/.test(texts[i]) ? "Tabled in committee" : "Voted down in committee";
    return { status, when: `${texts[i].replace(/, which ends it$/, "")} on ${fmtDate(acts[i][0])}.`, tail: "That ends it for the session." };
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t < `${y + 1}-01-01`)
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}${(y + 1) % 2 ? " and runs 60 days" : " and runs 30 days, for the budget and what the governor puts on the call"}.${y % 2 === 0 ? " Every House seat was on the ballot in November; a new governor takes office January 1, 2027." : ""}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.plusDays(adj, 20);
    const odd = Y % 2 === 1, intro = STATE.plusDays(open, odd ? 29 : 14);
    return {
      leg: [["", open, adj, odd ? "60-day session" : "30-day session"]],
      gov: [["light", open, adj, "3 days a bill"], ["", adj, due, "20 days"]],
      events: [
        [open, "up", LEG, MD(open), odd ? "The 60-day session opens; the governor gives the State of the State." : "The 30-day session opens: the budget, bills on the governor's call and vetoed bills only."],
        [intro, "down", LEG, MD(intro), "The last day to introduce bills (except the budget and bills on the governor's call)."],
        [adj, "up", LEG, MD(adj), "The session ends at noon. Bills that didn't pass both houses die."],
        [due, "down", LEG, MD(due), "The governor's last day on the final bills. A bill not signed by now is vetoed (a pocket veto)."],
        [`${Y}-07-01`, "up", LEG, "July 1", "The budget year starts; laws without an emergency clause take effect 90 days after the session (mid-May or mid-June)."],
      ],
      note: "During the session the governor has 3 days (Sundays excepted) to act on a bill, or it becomes law. Most bills pass in the last days, and for those the governor has 20 days after the session ends: a bill not signed by then is vetoed (a pocket veto). The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member list",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Bills go to one or more committees, in order.", "When a bill is introduced, the presiding officer sends it to the committees on its subject, usually two, and then to a finance committee if it spends money. It has to get out of each, in order."],
    ["Committees report a bill or let it die.", "A committee recommends \"do pass\" (often with amendments, or with a committee substitute for the bill), \"do not pass\", or no recommendation; it can also table a bill. Most bills die in committee when the session ends."],
    ["In 30-day sessions, germaneness comes first.", "In even years the Senate Committees' Committee decides whether each Senate bill is on the budget, the governor's call or a vetoed bill; only those go on."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died on the floor (never brought up for a vote)", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Law", "Vetoed"],
    },
  },
  stageTips: [
    "In one of its committees, which decides whether to report it. Most bills go to two or three committees, one after the other.",
    "Reported by its last committee and waiting for a vote on the floor.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It goes to the governor.",
    "With the governor, who has 3 days to act during the session, or 20 days after it ends for bills passed at its close; a bill not signed then is vetoed.",
    "Became law, with a chapter number in that year's session laws: signed, law without the governor's signature during the session, or over a veto.",
    "Vetoed by the governor, including pocket vetoes (not signed within 20 days after the session). Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "Reported by its committees, but never brought up for a vote.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Finance": ["Appropriations and Finance", "Budget and finance"],
    "Health and Public Affairs": ["Health and Human Services", "Health"],
    "Conservation": ["Energy, Environment and Natural Resources", "Environment and natural resources"],
    "Tax, Business and Transportation": ["Taxation and Revenue", "Taxes"],
    "Indian, Rural and Cultural Affairs": ["Rural Development, Land Grants and Cultural Affairs", "Rural and cultural affairs"],
    "Rules": ["Rules and Order of Business", "Rules"],
  },
  commNotes: {
    "Committees' Committee": "The Senate's leaders. In 30-day sessions it decides whether each Senate bill is germane (the budget, the governor's call or a vetoed bill); it also recommends committee assignments.",
    "Rules and Order of Business": "The House's leaders: it decides the order of business and holds bills that weren't printed.",
    "Appropriations and Finance": "Writes the budget (House Bill 2, the General Appropriation Act, every year) and hears bills that spend money.",
    "Finance": "The Senate's budget committee: it takes up the budget after the House passes it, and bills that spend money.",
  },
  moneyCommittees: { S: "Finance", H: "Appropriations and Finance" },
  secondCommittee: "Bills that spend money usually go last to a finance committee: Appropriations and Finance in the House, Finance in the Senate.",
};
