// Iowa: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ia",
  name: "Iowa",
  abbr: "IA",
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced in the|On the (?:House|Senate) calendar|On file in the|Received in the (?:House|Senate)$|Back in the (?:House|Senate)$|The (?:House|Senate) vote:|Subcommittee meeting:|The subcommittee recommends|Took the place of its companion|Amendment.*(?:adopted|lost|withdrawn|filed|out of order|deferred)|Motion |Deferred|Tabled|Committee vote:|Filed with the Secretary of State)/i,
  publicSite: "https://statebilltracker.org/ia/",
  listsApi: "https://state-lists.lists-worker.workers.dev",
  houses: { S: "Senate", H: "House" },
  // The picture at the top of How (tracker.html's renderHowPic()): how bills move ("twins": the same bill filed in
  // both houses moves in each until both pass the same text; "relay": one bill goes house to house), what a bill the
  // governor doesn't sign does ("law" or "dies" lines, each with an optional ⓘ tip), and who can override a veto.
  tracks: "relay",
  unsigned: [{ law: "Not signed in 3 days: becomes law", tip: "Sundays excepted, during the session." }, { dies: "Not signed 30 days after the session: pocket veto", tip: "A bill sent in the session's last 3 days or after it, as most are, dies if not signed within 30 days after the session ends, with no veto to override." }],
  override: { t: "Two-thirds can override", tip: "Two-thirds of each house's members (34 senators, 67 representatives)." },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A two-year General Assembly (2025–26 is the 91st), with a session each year; bills carry over from the first to the second.
  years: 2,
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Laws are chapters of each year's Iowa Acts ("Chapter 46 of 2025"; the second year's chapters are numbered from 1001).
  lawWord: "Chapter",
  // Joint resolutions propose amendments to the Constitution of the State of Iowa: a majority of each house's members in
  // two General Assemblies in a row (the second with the same text), then the voters at a general election; never the
  // governor (Constitution, Art. X, sec. 1).
  amendments: true,
  amendmentVote: "a majority of each house's members (26 senators, 51 representatives) in two General Assemblies in a row",
  amendmentFinal: (b) => b.vers.some((v) => v.actions.some(([, t]) => /^Second passage: /.test(t))),
  amendmentAgain: () => `Next: the General Assembly elected in November ${DATA.session + 1} has to pass it again, unchanged; then it goes to the voters.`,
  ballotEvenYears: true,
  // The governor's main line and contact page, from search results for governor.iowa.gov (which answers automated
  // requests with 403; not checked by the owner).
  govReach: `<a href="https://governor.iowa.gov/contact-us" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Des Moines <a class="phone" href="tel:+15152815211" data-contact="call|governor">(515) 281-5211</a>`,

  // The General Assembly's bill history page (every related bill's history, versions, fiscal notes, the signed Act).
  // Visitors follow these links; the tracker doesn't read the site from here.
  billUrl(p, session = DATA.session) {
    const ga = Math.floor((session - 1845) / 2) + 1;
    return `https://www.legis.iowa.gov/legislation/BillBook?ga=${ga}&ba=${encodeURIComponent(String(p).replace(/^([A-Z]+)(\d+)$/, "$1 $2"))}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const ga = Math.floor((DATA.session - 1845) / 2) + 1;
    const out = b.vers.map((v) => link(`https://www.legis.iowa.gov/legislation/billTracking/billHistory?billName=${encodeURIComponent(v.p.replace(/^([A-Z]+)/, "$1 "))}&ga=${ga}`,
      `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: the General Assembly's bill history (every related bill, its versions, fiscal notes)`));
    out.push(link(STATE.billUrl(b.nums[0]), `${esc(b.nums[0].replace(/^([A-Z]+)/, "$1 "))}: the bill text`));
    return out.join("<br>");
  },

  // Each year's session opens the second Monday of January (Iowa Code 2.1). Legislators are paid daily expenses for 110
  // days in the first year and 100 in the second, and sessions usually end near then; `dated` holds each year's last day
  // (sine die), from the floor votes and the news (add each year's). A special session can follow (July 2023, October 2026).
  dated: { 2023: "2023-05-04", 2024: "2024-04-20", 2025: "2025-05-15", 2026: "2026-05-03" },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  yearEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), year % 2 ? 109 : 99),
  sessionEnds: (session) => STATE.yearEnds(session + 1),
  // The governor has 3 days (Sundays excepted) to act on a bill presented while the Legislature is in session; for a bill
  // presented in its last 3 days or after it (most are), 30 days after adjournment, and a bill not signed by then doesn't
  // become law (a pocket veto). The governor can veto items in an appropriation bill (Constitution, Art. III, sec. 16).
  govDeadline(iso) {
    if (!iso) return null;
    const y = Number(iso.slice(0, 4)), end = STATE.yearEnds(y);
    let d = iso, k = 0;
    while (k < 3) { d = STATE.plusDays(d, 1); if (new Date(`${d}T12:00`).getDay() !== 0) k++; }
    return d < end ? d : STATE.plusDays(end, 30);
  },
  dueLabel: () => "Governor's decision due (30 days after the session for most bills; one not signed by then dies)",

  passedBothBy: (session) => STATE.plusDays(STATE.sessionEnds(session), 30),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Not yet sent to the governor", () => "A bill that passed both houses gets its final copy, signed by the Speaker and the Senate President and sent to the governor, usually within days."],
  passedBothNext: () => ({
    what: "its final copy is prepared and sent to the governor. For a bill sent in the session's last 3 days or after it (most are), the governor has 30 days after the session ends; a bill not signed by then doesn't become law. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members (34 senators, 67 representatives).",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: true,
  findReps: "https://www.legis.iowa.gov/legislators",
  oneNumber: true,
  floorVotesEnd: true,
  diesAfterFloor: () => "The General Assembly's two years are over, so it died. It would have to be introduced again.",
  outOfTimeLine: "Died when the General Assembly's two years ended",

  heldLabel: "Held in committee",
  heldTip: "The committee never reported it. Iowa's committees rarely vote a bill down; a bill not out of committee by the session's \"funnel\" deadlines is usually done for the year.",
  heldNote: "the committee never reported it, which usually ends it.",

  // Bills that ended before the General Assembly did: replaced by the other house's companion, withdrawn, or voted down.
  endedNote(b) {
    const acts = b.vers[0].actions, texts = acts.map(([, t]) => t);
    const rep = texts.findLastIndex((t) => /^Replaced by its companion, /.test(t));
    if (rep >= 0 && b.stage <= 2) {
      const name = (texts[rep].match(/companion, ([A-Z]+ \d+)/) || [])[1] || "its companion";
      return {
        status: `Replaced by ${name}`,
        when: `Its companion, ${name}, took its place on ${fmtDate(acts[rep][0])}.`,
        tail: `It goes no further on its own; follow ${name}.`,
      };
    }
    const w = texts.findLastIndex((t) => /^Withdrawn in the /.test(t));
    if (w >= 0 && b.stage <= 2) {
      return {
        status: "Withdrawn",
        when: `Withdrawn on ${fmtDate(acts[w][0])}.`,
        tail: "A withdrawn bill goes no further; often another bill took up its subject.",
      };
    }
    const down = texts.findLastIndex((t) => /^The (?:House|Senate) voted it down/.test(t));
    const again = (i) => texts.slice(i + 1).some((t) => /^PASSED |voted to reconsider|passed it again/.test(t));
    if (down >= 0 && !again(down) && b.stage <= 2) {
      const h = texts[down].match(/House|Senate/)[0];
      return {
        status: `Voted down in the ${h}`,
        when: `${texts[down]} on ${fmtDate(acts[down][0])}.`,
        tail: "That ends it, unless the house reconsiders the vote.",
      };
    }
    return null;
  },

  // The note above the bill list between sessions (empty while the General Assembly meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end1 = STATE.yearEnds(y), end2 = STATE.yearEnds(y + 1);
    if (t > end1 && t < `${y + 1}-01-01`) return `The ${y} session ended ${fmtDate(end1)}${t <= STATE.plusDays(end1, 30) ? `; the governor has until ${fmtDate(STATE.plusDays(end1, 30))} to act on the bills it passed` : ""}. Bills that haven't passed carry over to ${y + 1}, when the General Assembly meets again from ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > end2) return `The ${y}–${String(y + 1).slice(2)} General Assembly's last session ended ${fmtDate(end2)}${t <= STATE.plusDays(end2, 30) ? `; the governor has until ${fmtDate(STATE.plusDays(end2, 30))} to act on the bills it passed` : ""}. Bills that didn't pass both houses died. The next General Assembly opens ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session}–${String(raw.session + 1).slice(2)} General Assembly opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Bills you star now stay on your watchlist when the session opens.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, each followed by the governor's 30 days.
  calendarDays: 14,
  calendar(Y) {
    const LEG = 112, e1 = STATE.yearEnds(Y), e2 = STATE.yearEnds(Y + 1), o1 = STATE.opens(Y), o2 = STATE.opens(Y + 1);
    const g1 = STATE.plusDays(e1, 30), g2 = STATE.plusDays(e2, 30);
    const MDt = (iso) => new Date(`${iso}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" });
    const el = (() => { const t = new Date(Y + 1, 10, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1); return `${Y + 1}-11-${String(t.getDate()).padStart(2, "0")}`; })();
    return {
      leg: [["", o1, e1, "Session"], ["light", STATE.plusDays(e1, 1), o2, "Interim"], ["", o2, e2, "Session"], ["light", STATE.plusDays(e2, 1), el, "Interim"]],
      gov: [["light", o1, e1, "3 days a bill"], ["", e1, g1, "30 days"], ["light", o2, e2, "3 days a bill"], ["", e2, g2, "30 days"]],
      events: [
        [o1, "up", LEG, MDt(o1), "The General Assembly opens. Committees take up study bills and members' bills."],
        [e1, "down", LEG, MDt(e1), "The session ends (sine die). Bills that haven't passed carry over to next year."],
        [g1, "up", LEG, MDt(g1), "The governor's last day: bills not signed by now don't become law."],
        [o2, "up", LEG, MDt(o2), "The second year's session opens; carried-over bills pick up where they were."],
        [e2, "down", LEG, MDt(e2), "The last session ends. Bills that didn't pass both houses die."],
        [el, "up", LEG, MDt(el), "Election day: every House seat and half the Senate's."],
      ],
      note: "Each session has \"funnel\" deadlines set by the joint rules: about the sixth week, a bill has to be out of committee in its own house, and about the tenth week out of committee in the other house; bills from the appropriations, ways and means and government oversight committees, and the leaders', are exempt. The governor has 3 days (Sundays excepted) for a bill sent during the session, and 30 days after it for the rest; a bill not signed by then doesn't become law. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members. The budget year starts July 1, when most new laws take effect.",
    };
  },
  waitingHead: "Waiting for the governor",
  govYearsNote: "",
  partySource: "Party from the House's and the Senate's member lists",
  openUntil: (s) => `the governor acts on the last bills after the ${s + 1} session`,

  commIntro: [
    ["Most bills start in a subcommittee.", "Each bill (or study bill, a committee's draft) is sent to a committee, whose chair names a subcommittee of three members to hold a public meeting on it; the subcommittee recommends passage, amendments, or nothing."],
    ["Committees report bills, often under a new number.", "A committee that approves a study bill, or rewrites a member's bill, introduces it as its own bill with a new number (\"renumbered as HF 581\"); the new bill goes on the calendar or to the next committee. Committees don't vote bills down on the record: a bill not reported by the funnel deadlines is usually done."],
    ["The money committees come last.", "Bills that spend money go to Appropriations, and tax bills to Ways and Means; their own bills go straight to the floor and aren't held to the funnels."],
    ["Companion bills.", "Many bills are filed in both houses. When one passes, the other house usually takes it up in place of its own version (\"substituted for\"), and its own is withdrawn."],
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
    "In a committee (or its subcommittee); the committee has to report it, often as a new bill with a new number.",
    "Reported by its committee and on the calendar; the majority leader decides which bills come up for debate.",
    "Passed the House or the Senate, but not both. If the second house changes it, the first has to agree and pass it again.",
    "Passed both houses in the same form. Its final copy is prepared and sent to the governor.",
    "Sent to the governor, who has 3 days during the session, or 30 days after it; a bill not signed by then doesn't become law.",
    "Became law, as a chapter of the year's Iowa Acts.",
    "Vetoed by the governor. Overriding takes two-thirds of each house's members.",
  ],
  pastStageTips: [
    "Never got out of committee before the General Assembly's two years ended.",
    "Reported by its committee, but never passed by the full house (or its companion passed instead).",
    "Passed the House or the Senate, but not both.",
    "Passed both houses but was never sent to the governor.",
    "Sent to the governor; no signature or veto is recorded.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be introduced again in a later one.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Natural Resources and Environment": ["Natural Resources", "Natural resources and the environment"],
    "Workforce": ["Labor and Workforce", "Labor"],
    "Technology": ["Economic Growth and Technology", "Technology and economic growth"],
    "Rules and Administration": ["Administration and Rules", "The legislature's own rules"],
  },
  commNotes: {
    "Appropriations": "Appropriations writes the budget, with joint subcommittees of both houses for each area; its own bills go straight to the floor (the Appropriations calendar).",
    "Ways and Means": "Ways and Means handles taxes; its own bills go straight to the floor (the Ways and Means calendar).",
    "Government Oversight": "Government Oversight reviews state agencies; its bills aren't held to the funnel deadlines.",
  },
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that spend money go to Appropriations, and tax bills to Ways and Means, as well.",
};
