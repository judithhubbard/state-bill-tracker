// New York: the page's settings and rules that are particular to this state. build_data.py puts
// this file into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  // The public site, and the Worker that keeps published watchlists.
  publicSite: "https://albanybilltracker.org/",
  listsApi: "https://albany-lists.lists-worker.workers.dev",
  houses: { S: "Senate", A: "Assembly" },
  // How a session is written: 2025–26.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // The governor's office, wherever it's the one to contact.
  govReach: `<a href="https://www.governor.ny.gov/content/governor-contact-form" target="_blank" rel="noopener" data-contact="online|governor">Send a message online</a> · <a class="phone" href="tel:+15184748390" data-contact="call|governor">(518) 474-8390</a>`,

  billUrl(p, session = DATA.session) {
    return `https://www.nysenate.gov/legislation/bills/${session}/${p.replace(/[A-Z]$/, "")}`;
  },
  // The Senate's bill page has the text and, for Senate bills, the sponsor's memo; Assembly memos are on the Assembly's site.
  asmUrl(p, session = DATA.session) {
    return `https://nyassembly.gov/leg/?default_fld=&leg_video=&bn=A${p.slice(1).replace(/^\d+/, (n) => n.padStart(5, "0"))}&term=${session}&Summary=Y&Text=Y&Memo=Y`;
  },
  textLinks(b) {
    // Each house's site has its own version's text and its sponsor's memo.
    const s = b.vers.find((v) => v.p[0] === "S"), a = b.vers.find((v) => v.p[0] === "A");
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return [s && link(STATE.billUrl(s.p), `${esc(s.p)} on the Senate's site: text and sponsor's memo`),
      a && link(STATE.asmUrl(a.p), `${esc(a.p)} on the Assembly's site: text and sponsor's memo`)].filter(Boolean).join("<br>");
  },

  // The governor has 10 days, Sundays excepted, after delivery; after the Legislature's final
  // adjournment, 30 days (NY Constitution, Art. IV, sec. 7).
  govDeadline(iso) {
    if (!iso) return null;
    const [y, m, d] = iso.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    for (let n = 0; n < 10;) { dt.setDate(dt.getDate() + 1); if (dt.getDay() !== 0) n++; }
    // After the Legislature's year ends, the governor has 30 days instead; unsigned bills are
    // pocket-vetoed. Estimated from December 31.
    if (dt.getFullYear() > y) return `${y + 1}-01-30`;
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
  },

  // Bills that passed both houses: the governor's office can request them through the end of the
  // session's second year, and they die if it doesn't.
  passedBothBy: (session) => `${session + 1}-12-31`,
  // The line under "Passed both houses", in the stage list and (with the bill) in its row.
  passedBothNote: (live) => `${live ? "Not yet requested" : "Never requested"} by the governor`,
  passedBothGroup: ["By December 31", () => "The governor's office has to request these and decide on them by the end of the year, or they die."],

  // Stage names (the stage numbers are build_data.py's), and their tips.
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses, not yet requested by the governor", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both, not requested", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses, never requested by the governor", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both, not requested", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. Most bills never get out of committee.",
    "A committee approved it, and it's on the calendar waiting for a vote of the full Senate or Assembly. Leaders decide which bills get a vote.",
    "Passed the Senate or the Assembly, but not both. Both houses have to pass the same text.",
    "Passed both houses and waiting for the governor's office to request it. Her 10-day clock starts only when it's delivered.",
    "Delivered to the governor. She has 10 days, not counting Sundays, to sign or veto it.",
    "Signed into law and given a chapter number.",
    "Vetoed by the governor. The Legislature can override a veto with two-thirds of each house, but rarely does.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the Senate or the Assembly, but not both.",
    "Passed both houses, but the governor's office never requested it, so it never reached her.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "Floor votes for this session are over. A bill that hasn't passed both houses can move only if lawmakers return for a special session; otherwise it dies December 31 and has to be reintroduced.",

  // How a bill becomes law: committees in the two houses that cover the same subject (Senate name ->
  // [Assembly name, label]), notes on some, and which bills need a second committee.
  commPairs: {
    "Finance": ["Ways And Means", "Budget and taxes"],
    "Alcoholism And Substance Use Disorders": ["Alcoholism And Drug Abuse", "Addiction"],
    "Cities 1": ["Cities", "Cities"], "Cities 2": ["Cities", "Cities"],
    "Civil Service And Pensions": ["Governmental Employees", "Public employees and pensions"],
    "Commerce, Economic Development And Small Business": ["Economic Development", "Economic development"],
    "Consumer Protection": ["Consumer Affairs And Protection", "Consumer protection"],
    "Crime Victims, Crime And Correction": ["Correction", "Prisons and crime victims"],
    "Cultural Affairs, Tourism, Parks And Recreation": ["Tourism, Parks, Arts And Sports Development", "Parks, tourism and the arts"],
    "Disabilities": ["People With Disabilities", "Disabilities"],
    "Elections": ["Election Law", "Elections"],
    "Energy And Telecommunications": ["Energy", "Energy"],
    "Ethics And Internal Governance": ["Ethics And Guidance", "Legislative ethics"],
    "Housing, Construction And Community Development": ["Housing", "Housing"],
    "Internet And Technology": ["Science And Technology", "Technology"],
    "Investigations And Government Operations": ["Governmental Operations", "State government"],
    "Libraries": ["Libraries And Education Technology", "Libraries"],
    "Local Government": ["Local Governments", "Local government"],
    "Racing, Gaming And Wagering": ["Racing And Wagering", "Racing and gambling"],
    "Veterans, Homeland Security And Military Affairs": ["Veterans' Affairs", "Veterans"],
  },
  commNotes: {
    codes: "Criminal law and the courts. Any bill that creates a crime or changes a penalty goes here, often after its subject committee.",
    rules: "Chaired by the Senate Majority Leader and the Assembly Speaker. In the last weeks of the session, most bills get to a floor vote through Rules rather than their usual committees, so Rules decides which of them get a vote.",
    "budget and taxes": "Any bill that costs the state money goes here after its subject committee.",
    cities: "The Senate has two: Cities 1 for New York City and Cities 2 for other cities.",
    "budget and revenue": "The Senate's tax committee. In the Assembly, tax bills go to Ways and Means.",
  },
  // The committees bills that cost money go to after their subject committee.
  moneyCommittees: { S: "Finance", A: "Ways And Means" },
  secondCommittee: "Bills that cost money go to Senate Finance or Assembly Ways and Means. Bills that create crimes or change penalties go to Codes. Near the end of the session, many bills go through Rules, which the leaders run.",
  // The two-year calendar: the Legislature's and the governor's bars ([class, from, to, text]), the
  // events marked on it ([date, "up"/"down", row, when, text]; rows are LEG = 112, GOV = 150) and a note.
  // end1 and end2 are the last floor votes of each year; MD formats a date as "June 10".
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150;
    return {
      leg: [["", `${Y}-01-07`, end1, "In session"], ["", `${Y + 1}-01-07`, end2, "In session"]],
      gov: [["light", `${Y}-01-01`, end1, "Signs or vetoes some bills"], ["", end1, `${Y}-12-31`, "Signs or vetoes most bills"],
        ["light", `${Y + 1}-01-01`, end2, "Signs or vetoes some bills"], ["", end2, `${Y + 1}-12-31`, "Signs or vetoes most bills"]],
      events: [
        [`${Y}-01-07`, "up", LEG, `January ${Y}`, "Session opens. Committees meet and floor votes happen only in session."],
        [end1, "up", LEG, MD(end1), "Session ends. Bills that didn't pass carry over to next year."],
        [`${Y + 1}-01-07`, "up", LEG, `January ${Y + 1}`, "Bills that passed only one house go back to committee."],
        [end2, "up", LEG, MD(end2), "Session ends: the last floor votes."],
        [`${Y}-11-20`, "down", GOV, "November–December", "Most vetoes come now, though the governor acts on bills all year."],
        [`${Y + 1}-12-31`, "down", LEG, `December 31, ${Y + 1}`, "Bills not passed by both houses die."],
      ],
      note: "Once a bill reaches her desk, the governor has 10 days, not counting Sundays, to sign or veto it.",
    };
  },
};
