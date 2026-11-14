// Missouri: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "mo",
  name: "Missouri",
  abbr: "MO",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled$|Public hearing held|The (?:House|Senate) vote:|Placed on the (?:informal )?calendar|Placed (?:back )?on |Dropped from calendar|Received in the (?:House|Senate)$|Signed by the (?:Speaker|President Pro Tem)|Delivered to the Secretary of State$|(?:H|S)CS(?:#\d+)? |HS |SS(?:#\d+)? |(?:House|Senate) conferees|The (?:House|Senate)'s conferees|The governor sent a letter of approval|Emergency clause|Objection filed)/i,
  publicSite: "https://statebilltracker.org/mo/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year; bills die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Constitutional amendments are joint resolutions (HJR, SJR): a majority of each house's members (18 senators, 82
  // representatives) sends one to the voters at the next general election, or at a special election the governor calls;
  // never to the governor for a signature (Constitution of Missouri, Art. XII, sec. 2(b)).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of each house's members (18 senators, 82 representatives)",
  ballotEvenYears: true,
  ballotLine: (b) => {
    const d = String(b.last || `${DATA.session}-05-30`);
    let y = +d.slice(0, 4);
    if (y % 2) y++;
    return `It goes to the voters at the November ${y} general election, unless the governor calls a special election for it.`;
  },
  // From governor.mo.gov/contact-us (checked by program 2026-11-13, not by the owner).
  govReach: `<a href="https://governor.mo.gov/contact-us/mo-governor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Jefferson City <a class="phone" href="tel:+15737513222" data-contact="call|governor">(573) 751-3222</a>`,

  // The House's bill page for House bills and the Senate's for Senate bills (a version's `link`, from convert.py).
  billUrl(p, session = DATA.session) {
    const b = typeof BILLS !== "undefined" && BILLS.find((x) => x.nums.includes(p));
    return b?.vers?.[0]?.link || (p.startsWith("H") ? `https://house.mo.gov/Bill.aspx?bill=${p}&year=${session}&code=R` : "https://www.senate.mo.gov/BillTracking/Bills/BillList");
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: ${v.p.startsWith("H") ? "the House's page (texts, summaries, fiscal notes, amendments)" : "the Senate's page (texts, summaries, fiscal notes, amendments)"}`)).join("<br>");
  },

  // A regular session a year from the first Wednesday after the first Monday of January (Constitution, Art. III, sec. 20).
  // No bill can pass after 6 p.m. on the first Friday after the second Monday in May; the session ends May 30. The veto
  // session meets on the first Wednesday after the second Monday in September (Art. III, sec. 32).
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 2);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // The nth weekday (0 Sunday ... 6 Saturday) of a month.
  nthDay(year, month, weekday, n) {
    const t = new Date(year, month - 1, 1); t.setDate(1 + ((weekday - t.getDay() + 7) % 7) + 7 * (n - 1));
    return `${year}-${String(month).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  lastBillDay: (year) => STATE.plusDays(STATE.nthDay(year, 5, 1, 2), 4),
  sessionEnds: (year) => STATE.lastBillDay(year),
  adjourns: (year) => `${year}-05-30`,
  vetoSession: (year) => STATE.plusDays(STATE.nthDay(year, 9, 1, 2), 2),
  // The governor has 15 days to sign or veto a bill delivered during the session; for a bill delivered in the session's
  // last days or after, 45 days from May 30 (Art. III, sec. 31). A bill not returned in time becomes law without a
  // signature. A veto after the session goes to the September veto session.
  govDeadline(iso) {
    if (!iso) return null;
    const y = +iso.slice(0, 4), last = STATE.plusDays(STATE.adjourns(y), 45);
    const d = STATE.plusDays(iso, 15);
    return d >= STATE.adjourns(y) ? last : d;
  },
  dueLabel: () => "Governor's decision due (or it becomes law without a signature)",

  passedBothBy: (session) => STATE.plusDays(STATE.adjourns(session), 45),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that are truly agreed to and finally passed are signed by the Speaker and the President Pro Tem and delivered to the governor, usually within a few weeks."],
  passedBothNext: () => ({
    what: "it's signed by the Speaker and the President Pro Tem and delivered to the governor, who has 15 days to sign or veto it (45 days from May 30 for bills delivered at the end of the session); a bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. A veto is overridden by two-thirds of each house's members (23 senators, 109 representatives), usually at the veto session in September.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  oneNumber: true,
  floorVotesEnd: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session ended",

  heldLabel: "Held in committee",
  heldTip: "The committee never voted it out, which ends it for the session.",
  heldNote: "the committee never voted it out, which ends it for the session.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t < `${y + 1}-01-01`) {
      const veto = STATE.vetoSession(y);
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.${t < veto ? ` The veto session meets ${fmtDate(veto)}.` : ""}${y % 2 === 0 ? " Every House seat and half the Senate's were on the ballot in November, so the new General Assembly chooses its leaders in January." : ""}`;
    }
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled (from December 1). Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), last = STATE.lastBillDay(Y), adj = STATE.adjourns(Y), due = STATE.plusDays(adj, 45), veto = STATE.vetoSession(Y);
    return {
      leg: [["", open, last, "Regular session"], ["light", veto, veto, "Veto session"]],
      gov: [["light", open, last, "15 days a bill"], ["", last, due, "Until mid-July"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens. Bills prefiled since December 1 are read in; the governor gives the State of the State and proposes the budget."],
        [`${Y}-05-08`, "down", LEG, "Early May", "The budget bills have to pass by 6 p.m. on the Friday a week before the last day."],
        [last, "down", LEG, MD(last), "The last day to pass bills (6 p.m.). Bills that didn't pass die."],
        [due, "up", LEG, MD(due), "The governor's last day on the session's bills; any not acted on become law without a signature."],
        [`${Y}-08-28`, "down", LEG, "Aug. 28", "Most new laws take effect."],
        [veto, "up", LEG, MD(veto), "The veto session: overriding a veto takes two-thirds of each house's members."],
      ],
      note: "The governor has 15 days to sign or veto a bill delivered during the session, and until mid-July (45 days after May 30) for bills passed at the end; a bill not acted on becomes law without a signature. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members (23 senators, 109 representatives), usually at the veto session in September.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the House's and Senate's member lists",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["The leaders send bills to committees.", "The Speaker refers House bills to committees, and the President Pro Tem refers Senate bills. Committees hold a public hearing, then vote in an executive session; a bill they don't vote out dies there."],
    ["House bills go through a second committee.", "A bill the House's standing committee votes out goes to one of its Rules committees (Administrative, Legislative or Regulatory Oversight), which votes again before it can reach the floor. Bills that cost more than $100,000 also go to Fiscal Review in the House or Fiscal Oversight in the Senate."],
    ["Two floor votes in each house.", "A bill is first \"perfected\" (debated, amended and approved by voice) and then \"third read and passed\" by a recorded vote of a majority of the house's members (82 representatives, 18 senators)."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died on the floor (never brought up for a final vote)", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Law", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting to be referred, or in a committee, which decides whether to vote it out (House bills go through a standing committee and then a Rules committee).",
    "Voted out of committee and waiting on the floor: it's perfected (the first vote, with amendments), then third read and passed.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Truly agreed to and finally passed: both houses passed the same text. It's signed by the Speaker and the President Pro Tem and delivered to the governor.",
    "Delivered to the governor, who has 15 days (until mid-July for bills passed at the end of the session) to sign or veto it; a bill not acted on becomes law.",
    "Became law: signed by the governor (budget bills often with items vetoed), law without the governor's signature, or law over a veto.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house's members, usually at the September veto session.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "Voted out of committee, but never passed on the floor.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Agriculture, Food Production and Outdoor Resources": ["Agriculture", "Agriculture"],
    "Appropriations": ["Budget", "The budget"],
    "Fiscal Oversight": ["Fiscal Review", "Bills that cost money"],
    "Insurance and Banking": ["Financial Institutions", "Banking and insurance"],
    "Families, Seniors and Health": ["Health and Mental Health", "Health"],
    "Health and Welfare": ["Health and Mental Health", "Health"],
    "Judiciary and Civil and Criminal Jurisprudence": ["Judiciary", "Courts and crime"],
    "Transportation, Infrastructure and Public Safety": ["Transportation", "Transportation"],
    "Veterans and Military Affairs": ["Veterans and Armed Forces", "Veterans"],
    "Commerce, Consumer Protection, Energy and the Environment": ["Commerce", "Commerce, energy and the environment"],
    "Economic and Workforce Development": ["Economic Development", "Economic development"],
    "Local Government, Elections and Pensions": ["Local Government", "Local government"],
    "Rules, Joint Rules, Resolutions and Ethics": ["Rules - Legislative", "Rules"],
  },
  commNotes: {
    "Rules - Administrative": "One of the House's Rules committees: bills voted out of a standing committee come here for a second vote before they can reach the floor.",
    "Rules - Legislative": "One of the House's Rules committees: bills voted out of a standing committee come here for a second vote before they can reach the floor.",
    "Rules - Regulatory Oversight": "One of the House's Rules committees: bills voted out of a standing committee come here for a second vote before they can reach the floor.",
    "Fiscal Review": "House bills that would cost the state more than $100,000 a year go here after they're perfected.",
    "Fiscal Oversight": "Senate bills that would cost the state more than $100,000 a year go here before the final vote.",
    "Budget": "Writes the House's version of the budget bills, which start in the House.",
    "Appropriations": "Writes the Senate's version of the budget bills.",
  },
  moneyCommittees: { S: "Appropriations", H: "Budget" },
  secondCommittee: "House bills voted out of a standing committee go to a Rules committee; bills that cost money go to Fiscal Review (House) or Fiscal Oversight (Senate).",
};
