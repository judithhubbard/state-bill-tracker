// Minnesota: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "mn",
  name: "Minnesota",
  abbr: "MN",
  // Steps that aren't news on a watchlist card.
  routine: /^(Received in the|Second reading|Third reading|The (?:House|Senate) vote:|The (?:House|Senate) committee (?:approved|sent)|The committee (?:approved|sent)|Placed on the (?:Calendar for the Day|Consent Calendar)|Held to compare|For comparison with|(?:House|Senate) conferees|Takes effect|Amendments offered|Taken up as a special order$|Referred to Chief Clerk|Conference committee report|A motion |Point of order|House rule|Rule \d|Joint rule|Senate Concurrent Resolution)/,
  publicSite: "https://statebilltracker.org/mn/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 94th Legislature).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  legislature: (s) => 94 + (s - 2025) / 2,
  // "94th Legislature"
  ls(s) { const n = STATE.legislature(s), t = n % 100; return `${n}${t > 10 && t < 14 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" })[n % 10] || "th"}`; },
  // Laws are chapters of the session laws ("Laws 2025, chapter 39"), numbered through the Legislature's two years.
  lawWord: "Chapter",

  // Constitutional amendments are bills ("... constitutional amendment proposed"): a majority of each house's members
  // sends one to the voters at the next general election (November of an even year), never to the governor; it passes
  // with a majority of everyone voting in that election, so a ballot left blank on the question counts as a no
  // (Minnesota Constitution, Art. IX, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members",
  ballotEvenYears: true,
  // The governor's office (from general knowledge: mn.gov's contact page doesn't answer automated readers; not checked
  // by the owner yet).
  govReach: `<a href="https://mn.gov/governor/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · St. Paul <a class="phone" href="tel:+16512013400" data-contact="call|governor">(651) 201-3400</a>`,

  // The Revisor of Statutes' page for each number: status, every text version, and the House's and Senate's votes.
  billUrl(p) {
    const b = typeof BILLS !== "undefined" && BILLS.find((x) => x.nums.includes(p));
    const v = b?.vers?.find((x) => x.p === p);
    const k = STATE.specialOf(p);
    return v?.link || `https://www.revisor.mn.gov/bills/${STATE.legislature(DATA.session)}/${DATA.session}/${k}/${p.slice(0, 2)}/${p.slice(k ? 3 : 2)}/`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const out = b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(STATE.numText(v.p))}: status, text versions and votes`));
    const y = (b.dates?.signed || "").slice(0, 4);
    if (b.stage === 5 && b.chapter && y) out.push(link(`https://www.revisor.mn.gov/laws/${y}/0/Session+Law/Chapter/${b.chapter}/`, `Laws ${y}, chapter ${b.chapter}`));
    // A special session's law: "Laws 2025, First Special Session chapter 3".
    const sp = b.stage === 5 && STATE.specialOf(b.nums[0]);
    const ch = sp && b.vers.flatMap((v) => v.actions).map(([, t]) => t.match(/Special Session chapter (\d+)$/)).find(Boolean);
    if (sp && ch && y) out.push(link(`https://www.revisor.mn.gov/laws/${y}/${sp}/Session+Law/Chapter/${ch[1]}/`, `Laws ${y}, ${["", "First", "Second", "Third"][sp] || `${sp}th`} Special Session chapter ${ch[1]}`));
    return out.join("<br>");
  },
  // Special sessions' bills are numbered with a letter after the house's ("HFS2": H.F. 2 of the first special session,
  // convert.py's special_num()): which special session, or 0.
  specialOf: (p) => { const m = /^[HS]F([S-Z])\d/.exec(p); return m ? m[1].charCodeAt(0) - 82 : 0; },
  numText: (p) => { const k = STATE.specialOf(p); return k ? `${p.slice(0, 2)} ${p.slice(3)} (${["", "1st", "2nd", "3rd"][k] || `${k}th`} Special Session)` : p.replace(/^([HS]F)/, "$1 "); },

  // Each session opens in January in odd years (the second Tuesday since 2025) and in February in even years (on a date
  // the Legislature sets), and must end by the Monday after the third Saturday in May (Minnesota Statutes 3.05; 120
  // legislative days in the two years). `dated` holds the days each year opened (add each year's).
  dated: { 2023: "2023-01-03", 2024: "2024-02-12", 2025: "2025-01-14", 2026: "2026-02-17" },
  opens(year) {
    if (STATE.dated[year]) return STATE.dated[year];
    const t = new Date(year, year % 2 ? 0 : 1, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7) + 7);
    return `${year}-${year % 2 ? "01" : "02"}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The constitutional deadline: the Monday after the third Saturday in May.
  adjourns(year) {
    const t = new Date(year, 4, 1); t.setDate(1 + ((6 - t.getDay() + 7) % 7) + 14 + 2);
    return `${year}-05-${String(t.getDate()).padStart(2, "0")}`;
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
  // Bills die with the second year's session.
  sessionEnds: (session) => STATE.adjourns(session + 1),
  // The governor has 3 days (Sundays excepted) after a bill is presented to sign or veto it; a bill not returned by then
  // becomes law. A bill passed in the session's last 3 days has 14 days after adjournment, and becomes law only if
  // signed by then (a pocket veto otherwise). The governor can veto items of appropriation (Constitution, Art. IV, sec. 23).
  govDeadline(iso) {
    if (!iso) return null;
    const end = STATE.adjourns(+iso.slice(0, 4));
    if (iso >= STATE.plusDays(end, -3) && iso <= STATE.plusDays(end, 14)) return STATE.plusDays(end, 14);
    return STATE.plusWeekdays(iso, 3);
  },
  dueLabel: () => "Governor's decision due (3 days, Sundays excepted; 14 days after the session ends for bills passed at its close)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session + 1), 14),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are signed by the Speaker and the President of the Senate and presented to the governor, usually within a few days."],
  passedBothNext: () => ({
    what: "the Speaker and the President of the Senate sign it and it goes to the governor, who has 3 days (Sundays excepted) to sign or veto it; a bill the governor doesn't act on becomes law. For bills passed in the session's last 3 days, the governor has 14 days after adjournment, and a bill not signed by then doesn't become law. The governor can veto items in an appropriation bill; overriding a veto takes two-thirds of each house.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: false,
  findReps: "https://gis.lcc.mn.gov/iMaps/districts/",
  diesAfterFloor: () => "The Legislature has adjourned for its term, so it died; only a special session, which takes up the bills the governor and leaders agree on, could pass it now.",
  outOfTimeLine: "Died when the Legislature adjourned for its term",

  // Committees don't vote bills down: a bill a committee doesn't act on stays there. Many are laid over for possible
  // inclusion in an omnibus bill, which the records don't show.
  heldLabel: "Held in committee",
  heldTip: "The committee never acted on it. Minnesota committees often lay a bill over for possible inclusion in an omnibus bill; the records don't show that.",
  heldNote: "the committee never acted on it; Minnesota committees often lay bills over for possible inclusion in an omnibus bill.",
  // A bill its author withdrew, or one voted down on the floor, ends there.
  endedNote(b) {
    const v = b.vers[0], acts = v.actions, texts = acts.map(([, t]) => t);
    const w = texts.findLastIndex((t) => /^Withdrawn and returned to its author/.test(t));
    if (w >= 0 && b.stage <= 1) return { status: "Withdrawn", when: `Withdrawn by its author ${fmtDate(acts[w][0])}.`, tail: "That ends it." };
    const i = texts.findLastIndex((t) => /^Failed in the (House|Senate)/.test(t));
    if (i < 0 || b.stage > 2 || texts.slice(i + 1).some((t) => /^PASSED |voted to reconsider/.test(t))) return null;
    const h = texts[i].match(/the (House|Senate)/)[1];
    return { status: `Voted down in the ${h}`, when: `${texts[i].replace(/,.*$/, "")} on ${fmtDate(acts[i][0])}.`, tail: "That ends it, unless the house reconsiders." };
  },

  committeeNext: {},
  chairAsks: {},

  // Special sessions this page leaves out.
  specials: { 2025: "Most of the 2025 budget passed in a one-day special session on June 9, 2025: its 15 laws are here, numbered HFS and SFS (HFS 2 is H.F. 2 of the special session), and the regular-session omnibus bills they replaced say so in their history." },
  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, sp = STATE.specials[y] ? ` ${STATE.specials[y]}` : "";
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The ${y} session ended ${fmtDate(STATE.adjourns(y))}. Bills that haven't passed stay alive for the ${y + 1} session, which opens ${fmtDate(STATE.opens(y + 1))}.${sp}`;
    if (t > STATE.adjourns(y + 1))
      return `The ${STATE.ls(y)} Legislature's last session ended ${fmtDate(STATE.adjourns(y + 1))}. Bills that didn't pass both houses died; the next Legislature opens in January ${y + 2}.${sp}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${STATE.ls(raw.session)} Legislature opens in January ${raw.session}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar: two sessions, each from January or February to May.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "First session"], ["light", a1, o2, "Interim"], ["", o2, a2, "Second session"], ["light", a2, `${Y + 1}-12-31`, "Interim"]],
      gov: [["light", o1, STATE.plusDays(a1, 14), "Acts on bills"], ["light", o2, STATE.plusDays(a2, 14), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The Legislature convenes."],
        [`${Y}-03-15`, "down", LEG, "March–April", "Committee deadlines: a bill has to clear its policy committees, then its finance committees, by set dates (Joint Rule 2.03), or it waits for the next year."],
        [a1, "down", LEG, MD(a1), "The first session ends: the two-year budget is due. Bills that didn't pass stay alive."],
        [o2, "up", LEG, MD(o2), "The second session starts where the first left off."],
        [a2, "down", LEG, MD(a2), "The constitutional deadline. Bills that didn't pass both houses die."],
        [`${Y}-08-01`, "up", LEG, "Aug 1", "Most new laws take effect August 1; budget laws July 1."],
      ],
      note: "The governor has 3 days (Sundays excepted) to act on a bill during the session; for bills passed in the last 3 days, 14 days after adjournment, and a bill not signed by then doesn't become law. The governor can veto items in appropriation bills. Overriding a veto takes two-thirds of each house (45 senators, 90 representatives). The budget for the two years starting July 1 passes in the odd year; the even year usually brings a bonding (capital investment) bill.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the House's and the Senate's member lists (DFL: the Democratic-Farmer-Labor Party, Minnesota's Democrats)",
  openUntil: (s) => `the ${STATE.ls(s)} Legislature's last session ends in May ${s + 1}`,

  commIntro: [
    ["Every bill has two numbers.", "Most bills are filed in both houses with the same text: a House File (H.F.) and a Senate File (S.F.), its companion. Each goes through its own house's committees; when one passes its house, the other house usually takes it up in place of its own."],
    ["Policy committees, then finance committees.", "A bill goes first to the committee on its subject; one that spends money or raises taxes goes on to a finance committee, the Senate Finance or Taxes Committee, or the House Ways and Means or Taxes Committee. Much of what passes is folded into large omnibus bills, one per budget area."],
    ["In 2025–26, House committees have two co-chairs.", "The House is tied 67–67, and under its power-sharing agreement each committee has a Republican and a DFL co-chair; contact cards name the first listed."],
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
    "In a committee. A bill moves from its policy committee to finance committees; one that misses the committees' deadlines waits for the next year.",
    "Approved by its committees and on the General Register (House) or General Orders (Senate), waiting for a floor vote.",
    "Passed the House or the Senate, but not both. The other house usually votes on it in place of its own companion bill; if it changes the bill, the first house has to agree, or a conference committee works out the differences.",
    "Passed both houses. The Speaker and the President of the Senate sign it, then it goes to the governor.",
    "Sent to the governor, who has 3 days (Sundays excepted), or 14 days after the session for bills passed at its close.",
    "Became law: signed, or (during the session) not returned within 3 days. A chapter of the session laws.",
    "Vetoed by the governor. Overriding takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the Legislature ended.",
    "Approved by its committees, but never passed by the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This Legislature is over. Bills that didn't become law have to be introduced again in the next one.",

  // Each Senate committee's House counterpart (2025-26 names) and the subject it's shown under.
  commPairs: {
    "Agriculture, Veterans, Broadband, and Rural Development": ["Agriculture Finance and Policy", "Agriculture"],
    "Commerce and Consumer Protection": ["Commerce Finance and Policy", "Business and consumers"],
    "Elections": ["Elections Finance and Government Operations", "Elections"],
    "Energy, Utilities, Environment, and Climate": ["Energy Finance and Policy", "Energy"],
    "Environment, Climate, and Legacy": ["Environment and Natural Resources Finance and Policy", "Environment and natural resources"],
    "Finance": ["Ways and Means", "The budget"],
    "Health and Human Services": ["Health Finance and Policy", "Health"],
    "Higher Education": ["Higher Education Finance and Policy", "Higher education"],
    "Housing and Homelessness Prevention": ["Housing Finance and Policy", "Housing"],
    "Human Services": ["Human Services Finance and Policy", "Human services"],
    "Jobs and Economic Development": ["Workforce, Labor, and Economic Development Finance and Policy", "Jobs, labor and economic development"],
    "Judiciary and Public Safety": ["Public Safety Finance and Policy", "Public safety and courts"],
    "Rules and Administration": ["Rules and Legislative Administration", "Rules"],
    "State and Local Government": ["State Government Finance and Policy", "State and local government"],
    "Transportation": ["Transportation Finance and Policy", "Transportation"],
  },
  commNotes: {
    "Finance": "Bills that spend money go to a finance committee, then to the Senate Finance or the House Ways and Means Committee, which sets the spending targets for the omnibus budget bills.",
    "Judiciary and Public Safety": "In the House, civil law goes to the Judiciary Finance and Civil Law Committee.",
    "Jobs and Economic Development": "The Senate also has a Labor Committee; in the House, labor bills go to the Workforce, Labor, and Economic Development Committee.",
  },
  moneyCommittees: { S: "Finance", H: "Ways and Means" },
  secondCommittee: "Bills that spend money go on to a finance committee and then the Senate Finance or House Ways and Means Committee; tax bills go to each house's Taxes Committee. Many end up folded into an omnibus bill.",
};
