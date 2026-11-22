// District of Columbia: the page's settings and rules that are particular to the District. build_data.py puts this file
// into every page, just before the main script; tracker.html reads it as STATE.
// The Council has one house (`houses` has one entry, "B": its bills are B26-0001 ...), and the Mayor, not a governor,
// signs or vetoes its acts (`executive`). An act the Mayor signs (or that becomes an act without the signature, or over a
// veto) becomes law only after Congress has had it for 30 days of its session (60 for criminal law), unless Congress and
// the President disapprove it: such an act counts as enacted (stage 5, as a law everywhere on the site is counted from the
// signature) and its status says Congress is reviewing it (`lawText`) until its law number is recorded.
const STATE = {
  code: "dc",
  name: "District of Columbia",
  // "How a bill becomes law in the District of Columbia".
  inName: "the District of Columbia",
  abbr: "DC",
  repsWord: "Councilmembers",
  placeTag: "For one place",
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced$|Notice of |Cancellation Notice|Act A[\d-]+ published|Returned from the Mayor|Committee Report Filed|Amendment|Oral Amendment|Mendelson \(|\(R\.? ?White\)|Agendized; not considered|NOT CONSIDERED|Not Considered|Postponed to)/,
  publicSite: "https://statebilltracker.org/dc/",
  listsApi: "https://state-lists.lists-worker.workers.dev",
  houses: { B: "Council" },
  executive: { the: "the Mayor", The: "The Mayor", office: "Mayor's office", title: "Mayor", dear: "Dear Mayor," },
  // The picture at the top of How (tracker.html's renderHowPic()).
  trackVote: ["The Council votes", "twice, 13 days apart"],
  unsigned: [{ law: "No action in 10 days: enacted", tip: "10 days not counting Saturdays, Sundays and holidays." },
    { law: "Then Congress: 30 days to block it", tip: "Every act goes to Congress, which has 30 days of its session (60 for criminal law) to block it with a resolution the President signs. It rarely does; then the act becomes law." }],
  override: { t: "Two-thirds can override", tip: "Two-thirds of the members present and voting, within 30 days: 9 of 13 when all vote." },
  howCap: "The Council has one house, so a bill takes one track. Every act then goes to Congress before it becomes law.",
  titles: { B: "Councilmember" },
  memberWords: { B: "Councilmember" },
  greetings: { B: "Councilmember" },
  bodyName: "the Council",
  // How a session is written: 2025–26 (Council Period 26).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  period: (s) => 26 + (s - 2025) / 2,
  // "Council Period 26"
  ls: (s) => `Council Period ${STATE.period(s)}`,
  // From mayor.dc.gov's footer (checked by program 2026-11-22, not by the owner).
  govReach: `<a href="https://mayor.dc.gov/" target="_blank" rel="noopener" data-contact="online|governor">Office of the Mayor</a> · <a class="phone" href="tel:+12027272643" data-contact="call|governor">(202) 727-2643</a>`,
  noSignatures: false,
  // Wards: "Find your Councilmember" picks a neighborhood or a ward; the five at-large members (district 9 in the data)
  // represent everyone.
  districtWord: "Ward",
  atLarge: 9,
  atLargeLine: (names) => `Everyone in the District also has the five Councilmembers elected at large: ${names.join(", ")}.`,
  seatText: (h, d) => (d === 9 ? "Elected at large" : `Ward ${d}`),
  signedWords: "enacted",
  distPhrase: (h, d) => (d === 9 ? "the District at large" : `Ward ${d}`),
  townWord: "Neighborhood",
  addressLookup: true,
  findReps: "https://planning.dc.gov/whatsmyward",

  // An enacted act's status until its law number: Congress's review (D.C. Code 1-206.02(c)).
  lawText(b) {
    const texts = b.vers[0].actions.map(([, t]) => t);
    if (texts.some((t) => /^Became law \(/.test(t))) return "";
    if (/Federal Portion Budget Request Act/.test(b.title || "")) return "Enacted (a budget request to Congress)";
    const sent = texts.findLast((t) => /^Sent to Congress for review/.test(t));
    if (sent) return DATA.current ? "Enacted; under review by Congress" : "Enacted; sent to Congress (no law number recorded)";
    return DATA.current ? "Enacted; goes to Congress for review" : "Enacted (no law number recorded)";
  },

  // The Council's LIMS page for each bill (a version's `link`), else LegiScan's.
  official: (p, s = DATA.session) => `B${26 + (s - 2025) / 2}-${String(+p.slice(1)).padStart(4, "0")}`,
  billUrl(p) {
    const b = typeof BILLS !== "undefined" && BILLS.find((x) => x.nums.includes(p));
    if (b?.vers?.[0]?.link) return b.vers[0].link;
    return `https://lims.dccouncil.gov/Legislation/${STATE.official(p)}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const own = b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(STATE.official(v.p))} on the Council's LIMS: text, committee report, fiscal impact and votes`));
    // Its emergency and temporary versions (named in its history).
    const comp = [...new Set(b.vers[0].actions.map(([, t]) => (t.match(/^(?:Emergency|Temporary) version, (B\d+-\d+)/) || [])[1]).filter(Boolean))];
    const more = comp.map((n) => link(`https://lims.dccouncil.gov/Legislation/${n}`, `${esc(n)} (its ${/Emergency version, ${n}/.test(b.vers[0].actions.map(([, t]) => t).join("\n")) ? "emergency" : "temporary"} version)`));
    const ls = `https://legiscan.com/DC/bill/${STATE.official(b.vers[0].p)}/${DATA.session}`;
    return [...own, ...more, link(ls, "LegiScan's page for this bill")].join("<br>");
  },
  // The enactment's line in a bill's History: an act isn't law until Congress's review ends (its law number is in "Every
  // action").
  lawLine: (b) => (b.dates.vetoed ? "Enacted over the Mayor's veto" : b.vers[0].actions.some(([, t]) => /^Enacted without the Mayor/.test(t))
    ? "Enacted without the Mayor's signature" : b.vers[0].actions.some(([, t]) => /^Signed by the Mayor/.test(t)) ? "Signed by the Mayor" : "Enacted"),
  voteWhat: (v) => (v.kind === "F" && v.committee ? `${esc(v.committee)}` : ""),

  // A Council Period runs from January 2 of the odd year to December 31 of the next; the Council meets all year, with a
  // summer recess (mid-July to mid-September). Bills not enacted by the end of the period die.
  opens: (year) => `${year}-01-02`,
  sessionEnds: (session) => `${session + 1}-12-31`,
  floorVotesEnd: false,
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The District's legal holidays (D.C. Code 1-612.02 and 28-2701), each moved to Friday or Monday when it falls on a
  // weekend; Inauguration Day (January 20 after a presidential election) too.
  holidays(y) {
    const iso = (m, d) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const nth = (m, wd, n) => { const t = new Date(y, m - 1, 1); t.setDate(1 + ((wd - t.getDay() + 7) % 7) + 7 * (n - 1)); return iso(m, t.getDate()); };
    const last = (m, wd) => { const t = new Date(y, m, 0); t.setDate(t.getDate() - ((t.getDay() - wd + 7) % 7)); return iso(m, t.getDate()); };
    const fixed = (m, d) => { const t = new Date(y, m - 1, d), w = t.getDay(); if (w === 6) t.setDate(d - 1); if (w === 0) t.setDate(d + 1); return iso(t.getMonth() + 1, t.getDate()); };
    const out = [fixed(1, 1), nth(1, 1, 3), nth(2, 1, 3), fixed(4, 16), last(5, 1), fixed(6, 19), fixed(7, 4), nth(9, 1, 1), nth(10, 1, 2), fixed(11, 11), nth(11, 4, 4), fixed(12, 25)];
    if ((y - 1) % 4 === 0) out.push(fixed(1, 20));
    return out;
  },
  // Days counted with Saturdays, Sundays and holidays excepted.
  plusWorkdays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d);
    const day = () => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0 && t.getDay() !== 6 && !STATE.holidays(t.getFullYear()).includes(day())) n--; }
    return day();
  },
  // The Mayor has 10 days, not counting Saturdays, Sundays and holidays, after an act is presented to sign or veto it; an
  // act not returned in time is enacted without the signature (Home Rule Act sec. 404(e), D.C. Code 1-204.04(e)).
  govDeadline: (iso) => (iso ? STATE.plusWorkdays(iso, 10) : null),
  dueLabel: () => "Mayor's decision due (10 days, not counting Saturdays, Sundays and holidays)",

  passedBothText: "Passed the Council",
  passedBothBy: (session) => `${session + 1}-12-31`,
  passedBothNote: (live) => live ? "Not yet sent to the Mayor" : "Never sent to the Mayor",
  passedBothGroup: ["Before the Mayor's deadline", () => "After its final reading an act goes to the Mayor, usually within a few weeks; the Mayor then has 10 working days to sign or veto it."],
  passedBothNext: () => ({
    what: "it goes to the Mayor, who has 10 days (not counting Saturdays, Sundays and holidays) to sign or veto it; an act the Mayor doesn't return is enacted without the signature. Overriding a veto takes two-thirds of the Councilmembers present and voting. Then the act goes to Congress, and becomes law after 30 days of Congress's session (60 for criminal law) unless Congress blocks it.",
    gov: ["sign it", "veto it"],
    reps: ["urge the Mayor to sign it", "urge the Mayor to veto it"],
  }),
  diesAfterFloor: () => "The Council Period has ended, so it died; a bill has to be introduced again in the next Council Period.",
  outOfTimeLine: "Died when the Council Period ended",

  heldLabel: "Held in committee",
  heldTip: "The committee never marked it up. Most bills stay in committee until the Council Period ends.",
  heldNote: "the committee never marked it up.",
  // A bill withdrawn, postponed indefinitely, or voted down at a reading says so.
  endedNote(b) {
    if (b.stage > 1) return null;
    const acts = b.vers[0].actions, texts = acts.map(([, t]) => t);
    const k = texts.findLastIndex((t) => /^(Withdrawn|WITHDRAWN|Postponed Indefinitely|Tabled|(?:First|Final) reading failed)/.test(t));
    if (k < 0) return null;
    const t = texts[k], d = fmtDate(acts[k][0]);
    // (A later reading that passed undoes a failed one.)
    if (/failed/.test(t) && texts.slice(k + 1).some((x) => /^(?:First|Final) reading/.test(x) && !/failed/.test(x))) return null;
    if (/^withdrawn/i.test(t)) return { status: "Withdrawn", when: `Withdrawn on ${d}.`, tail: "That ends it." };
    if (/^(Postponed Indefinitely|Tabled)/.test(t)) return { status: "Postponed indefinitely", when: `Postponed indefinitely by the Council on ${d}.`, tail: "That ends it for this Council Period." };
    return { status: "Voted down", when: `${t} on ${d}.`, tail: "That ends it for this Council Period." };
  },

  committeeNext: {},
  chairAsks: {},

  between: () => false,
  // The note above the bill list once a Council Period has ended (empty while it runs).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session;
    if (t > STATE.sessionEnds(y))
      return `${STATE.ls(y)} ended December 31, ${y + 1}. Bills that weren't enacted died; acts already sent to Congress can still become law.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `${STATE.ls(raw.session)} begins ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Bills you star now stay on your watchlist.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} Council Period</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, o = STATE.opens(Y), e = STATE.sessionEnds(Y);
    const MDY = (d) => `${MD(d)}, ${d.slice(0, 4)}`;
    return {
      leg: [["", o, `${Y}-07-14`, "Meets"], ["light", `${Y}-07-15`, `${Y}-09-14`, "Summer recess"], ["", `${Y}-09-15`, `${Y + 1}-07-14`, "Meets"], ["light", `${Y + 1}-07-15`, `${Y + 1}-09-14`, "Summer recess"], ["", `${Y + 1}-09-15`, e, "Meets"]],
      gov: [["light", o, e, "Signs or vetoes acts (10 working days each)"]],
      events: [
        [o, "up", LEG, MDY(o), "A new Council Period begins; the Council adopts its rules and committees."],
        [`${Y}-03-20`, "down", LEG, `March ${Y}`, "The Mayor sends the budget for the next fiscal year (October to September)."],
        [`${Y}-06-01`, "up", LEG, `May–June ${Y}`, "The Council votes on the budget and its Budget Support Act."],
        [`${Y}-08-01`, "down", LEG, `July–September ${Y}`, "Summer recess; committees hold few hearings."],
        [`${Y + 1}-06-01`, "up", LEG, `May–June ${Y + 1}`, "The second year's budget."],
        [e, "down", LEG, MDY(e), "The Council Period ends. Bills not enacted die; acts already passed go on to the Mayor and Congress."],
      ],
      note: "The Council holds a legislative meeting about once a month, where bills get their first and final readings.",
    };
  },
  waitingHead: "On the way to the Mayor",
  govYearsNote: "",
  partySource: "",
  openUntil: (s) => `${STATE.ls(s)} ends December 31, ${s + 1}`,

  commIntro: [
    ["Most bills go to a committee.", "The Chairman refers each bill to one of the Council's committees (some to two, one after the other). The committee holds a public hearing, then marks it up: it votes on its own version and a report. Most bills never get a mark-up."],
    ["Then the Committee of the Whole.", "Every bill a committee approves goes to the Committee of the Whole, all 13 members with the Chairman presiding, which puts it on the agenda of a legislative meeting for its first reading."],
  ],
  stageWords: {
    pipe: ["In committee", "Before the full Council", "", "Passed the Council", "On the Mayor's desk", "Enacted", "Vetoed"],
    long: ["In committee", "Before the full Council", "", "Passed the Council", "On the Mayor's desk", "Enacted", "Vetoed"],
    chart: ["In committee", "Full Council", "", "Passed", "Mayor's desk", "Enacted", "Vetoed"],
  },
  stageText: {
    get live() { return STATE.stageWords; },
    get prefiled() { return Object.fromEntries(Object.entries(STATE.stageWords).map(([k, v]) => [k, ["Introduced", ...v.slice(1)]])); },
    final: {
      pipe: ["Died in committee", "Died before final reading", "", "Passed the Council", "Sent to the Mayor", "Enacted", "Vetoed"],
      long: ["Died in committee", "Died before final reading", "", "Passed the Council", "Sent to the Mayor, no action recorded", "Enacted", "Vetoed"],
      chart: ["Died in committee", "Died before final reading", "", "Passed", "Sent, no action", "Enacted", "Vetoed"],
    },
  },
  stageTips: [
    "In a committee, which may hold a public hearing and then mark it up (vote on its version and report).",
    "Before the full Council: approved by its committee, or kept by the Council, and waiting for its first or final reading at a legislative meeting. Every bill is read and voted on twice, at least 13 days apart.",
    "",
    "Passed its final reading. It goes to the Mayor next.",
    "With the Mayor, who has 10 days (not counting Saturdays, Sundays and holidays) to sign or veto it.",
    "Enacted: signed by the Mayor, or not returned in 10 days, or passed over a veto. It becomes law after Congress's review: 30 days of Congress's session, 60 for criminal law.",
    "Vetoed by the Mayor. Overriding takes two-thirds of the Councilmembers present and voting.",
  ],
  pastStageTips: [
    "Never marked up by its committee before the Council Period ended.",
    "Approved by its committee, but never passed its final reading.",
    "",
    "Passed the Council but was never sent to the Mayor.",
    "Sent to the Mayor; no signature or veto is recorded.",
  ],
  outOfTime: "This Council Period is over. Bills that weren't enacted have to be introduced again in the next one.",
  oddsExits: ["Died in committee", "Died before final reading"],
  fateLabels: { committee: "Died in committee", floor: "Died before final reading" },

  commPairs: {},
  commNotes: {},
  moneyCommittees: { B: "Committee of the Whole" },
  secondCommittee: "Bills that cost money must have their cost paid for in the budget before they take effect (“subject to appropriations”); the Committee of the Whole handles the budget.",
};
