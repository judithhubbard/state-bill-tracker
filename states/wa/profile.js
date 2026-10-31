// Washington: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "wa",
  name: "Washington",
  abbr: "WA",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled for introduction|First reading|INTRODUCED|.*Executive action taken|Minority;|Rules suspended|\d\w+ substitute bill substituted|Floor amendment|Committee amendment|Amendment ruled|Speaker signed|President signed|Effective date|By resolution, reintroduced|Public hearing|Scheduled for|Held on calendar|Placed on second reading consent|.*Majority; .*proposed by)/i,
  publicSite: "https://statebilltracker.org/wa/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (a biennium).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // Constitutional amendments (joint resolutions, HJR and SJR) pass both houses once, by two-thirds of the members, and
  // go to the voters at the next general election, held every November; never to the governor (Washington
  // Constitution, Art. XXIII, Sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "both houses, by two-thirds of their members",
  govReach: `<a href="https://governor.wa.gov/contacting-governor/contacting-governors-office/send-gov-ferguson-e-message" target="_blank" rel="noopener" data-contact="online|governor">Message the governor</a> · Olympia <a class="phone" href="tel:+13609024111" data-contact="call|governor">(360) 902-4111</a>`,

  // The Legislature's bill summary page, and the bill as introduced.
  billUrl: (p, session = DATA.session) => `https://app.leg.wa.gov/billsummary?BillNumber=${p.replace(/^\D+/, "")}&Year=${session}`,
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const bien = `${DATA.session}-${String(DATA.session + 1).slice(2)}`;
    return b.vers.map((v) => `${link(STATE.billUrl(v.p), `${esc(v.p)}: status and history`)} · ${link(`https://lawfilesext.leg.wa.gov/biennium/${bien}/Htm/Bills/${v.p[0] === "H" ? "House" : "Senate"} ${v.p.includes("JR") ? "Joint Resolutions" : "Bills"}/${v.p.replace(/^\D+/, "")}.htm`, "text as introduced")}`).join("<br>");
  },

  // Each year's session starts the second Monday of January: 105 days in the first year, 60 in the second
  // (Washington Constitution, Art. II, sec. 12). The biennium runs until the next one starts.
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  adjourns(year) {
    const [y, m, d] = STATE.opens(year).split("-").map(Number), t = new Date(y, m - 1, d + (year % 2 ? 104 : 59));
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds(session) {
    const [y, m, d] = STATE.opens(session + 2).split("-").map(Number), t = new Date(y, m - 1, d - 1);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // Floor votes end when the second year's session adjourns (the page's default rule: no floor votes for three weeks).
  // The governor has 5 days, Sundays excepted, while the Legislature is in session; a bill delivered in the last five
  // days or after it adjourns gets 20 days, Sundays excepted, after adjournment (Art. III, sec. 12).
  govDeadline(iso) {
    if (!iso) return null;
    const y = +iso.slice(0, 4), end = STATE.adjourns(y);
    const plus = (from, n) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; }
      return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`; };
    const five = plus(iso, 5);
    return five <= end ? five : plus(end > iso ? end : iso, 20);
  },
  dueLabel: () => "Governor's decision due (5 days, Sundays excepted, during the session; 20 after it ends)",

  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the session ends", () => "Bills that pass both houses are signed by the Speaker and the Senate President, then delivered to the governor."],
  passedBothNext: () => ({
    what: "the Speaker and the Senate President sign it, and it goes to the governor, who can sign it, veto it, or veto parts of it. A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://app.leg.wa.gov/districtfinder",
  oneNumber: true,
  diesAfterFloor: (y2) => `Unless lawmakers return for a special session, it dies when the biennium ends in January ${y2 + 1}.`,
  outOfTimeLine: "Died when the biennium ended",

  // Bills a committee approves go to the Rules Committee, which decides which reach the floor; bills it won't move go
  // in its "X file".
  heldLabel: "Put in the Rules X file",
  heldTip: "The Rules Committee put it in its \"X file\": bills it doesn't plan to bring to the floor.",
  heldNote: "the Rules Committee put it in its \"X file\" of bills it doesn't plan to bring to the floor.",
  committeeNext: {
    "Rules": "the Rules Committee decides whether it gets a floor vote.",
  },
  chairAsks: {
    "Rules": ["schedule it for a floor vote", "keep it off the floor calendar"],
  },

  // The note above the bill list between sessions (empty while the Legislature meets).
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end) return "";
    if (t > STATE.adjourns(y) && t < STATE.opens(y + 1))
      return `The Legislature finished its first session ${fmtDate(STATE.adjourns(y))}. Bills that didn't pass stay alive for the second session, which starts ${fmtDate(STATE.opens(y + 1))}.`;
    if (t > STATE.adjourns(y + 1))
      return `The Legislature finished its second session ${fmtDate(STATE.adjourns(y + 1))}. Bills that didn't pass both houses died; the next biennium starts ${fmtDate(STATE.opens(y + 2))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${span(raw.session)} biennium starts ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, o1 = STATE.opens(Y), a1 = STATE.adjourns(Y), o2 = STATE.opens(Y + 1), a2 = STATE.adjourns(Y + 1);
    return {
      leg: [["", o1, a1, "105-day session"], ["light", a1, o2, "Interim"], ["", o2, a2, "60-day session"], ["light", a2, STATE.sessionEnds(Y), "Interim"]],
      gov: [["light", o1, STATE.govDeadline(a1), "Acts on bills"], ["light", o2, STATE.govDeadline(a2), "Acts on bills"]],
      events: [
        [o1, "up", LEG, MD(o1), "The first session starts; bills prefiled since December."],
        [a1, "down", LEG, MD(a1), "The 105-day session ends. Bills that didn't pass stay alive."],
        [o2, "up", LEG, MD(o2), "The second session starts where the first left off."],
        [a2, "down", LEG, MD(a2), "The 60-day session ends. Bills that didn't pass both houses die."],
      ],
      note: "During a session the governor has five days (Sundays excepted) to act on a bill; bills that arrive at the end get 20 days after the session ends. The governor can veto whole sections of a bill. Overriding a veto takes two-thirds of each house. Most new laws take effect 90 days after the session ends.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's list of members",
  openUntil: (s) => `the ${span(s)} biennium ends in January ${s + 2}`,

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
    "The Rules Committee placed it on the calendar for a vote of the full House or Senate.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. The Speaker and the Senate President sign it, then it goes to the governor.",
    "Delivered to the governor, who has five days (Sundays excepted) during a session, or 20 after it ends.",
    "Signed into law (or became law without the governor's signature), with a chapter number in the session laws.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the biennium ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This biennium is over. Bills that didn't become law have to be introduced again in the next one.",

  // Each Senate committee's House counterpart and the subject it's shown under (2025-26 names).
  commPairs: {
    "Ways & Means": ["Appropriations", "Budget and taxes"],
    "Early Learning & K-12 Education": ["Education", "Schools"],
    "Higher Education & Workforce Development": ["Postsecondary Education & Workforce", "Colleges and job training"],
    "Health & Long-Term Care": ["Health Care & Wellness", "Health"],
    "Human Services": ["Early Learning & Human Services", "Human services"],
    "Law & Justice": ["Civil Rights & Judiciary", "Courts and civil law"],
    "Labor & Commerce": ["Labor & Workplace Standards", "Labor"],
    "Environment, Energy & Technology": ["Environment & Energy", "Environment and energy"],
    "Business, Trade & Economic Development": ["Consumer Protection & Business", "Business"],
    "State Government, Tribal Affairs & Elections": ["State Government & Tribal Relations", "State government and elections"],
  },
  commNotes: {},
  moneyCommittees: { S: "Ways & Means", H: "Appropriations" },
  secondCommittee: "Bills that cost money also go to Appropriations (House) or Ways & Means (Senate); tax bills to Finance in the House. Then every bill goes to the Rules Committee, which decides which reach the floor.",
};
