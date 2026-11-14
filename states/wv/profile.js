// West Virginia: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "wv",
  name: "West Virginia",
  abbr: "WV",
  // Steps that aren't news on a watchlist card.
  routine: /^(Read the (?:first|second|third) time|The (?:House|Senate) vote:|On \d\w+ reading|On second reading|Placed on House Calendar|From House\w? Calendar|Received in the (?:House|Senate)$|The .* Committee discussed it|Sent to the .* Subcommittee|Acts chapter|.*\(voted\)$|(?:Committee |Floor |Title )?amendments? .*(?:adopted|rejected|withdrawn|reported)|.*\bamend\w*\.? .*(?:adopted|rejected|withdrawn|reported)|Amendment reported by the Clerk|Laid over|Postponed on \d|Deferred|Immediate consideration|Constitutional Rule|Dispensed with Constitutional Rule|Motion for previous question)/i,
  publicSite: "https://statebilltracker.org/wv/",
  listsApi: "",
  houses: { S: "Senate", H: "House of Delegates" },
  titles: { S: "Sen.", H: "Del." },
  memberWords: { S: "state senator", H: "delegate" },
  greetings: { S: "Senator", H: "Delegate" },
  // A session a year; bills die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are chapters of each year's Acts of the Legislature ("Acts ch. 46").
  lawWord: "Acts ch.",
  // Constitutional amendments are joint resolutions: two-thirds of each house's members send one to the voters, at the
  // next general election unless the resolution sets a special election, never to the governor (Constitution, Art. XIV,
  // sec. 2).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members (23 senators, 67 delegates)",
  ballotEvenYears: true,
  govReach: `<a href="https://wv.accessgov.com/governor/Forms/Page/submitcomment-governor/contact-governor" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Charleston <a class="phone" href="tel:+13045582000" data-contact="call|governor">(304) 558-2000</a>`,

  // The Legislature's bill status pages: a page per bill (history, texts, roll calls).
  billUrl(p, session = DATA.session) {
    const m = String(p).match(/^([HS])(B|JR)(\d+)$/);
    if (!m) return "https://www.wvlegislature.gov/Bill_Status/bill_status.cfm";
    return m[2] === "B"
      ? `https://www.wvlegislature.gov/Bill_Status/Bills_history.cfm?input=${m[3]}&year=${session}&sessiontype=RS&btype=bill`
      : `https://www.wvlegislature.gov/Bill_Status/Resolution_History.cfm?input=${m[3]}&year=${session}&sessiontype=RS&btype=res&billtype=jr&houseorig=${m[1].toLowerCase()}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const out = [];
    for (const v of b.vers) out.push(link(STATE.billUrl(v.p), `${esc(v.p)}: the Legislature's page (history, each version's text, roll calls)`));
    return out.join("<br>");
  },

  // One 60-day session a year (Constitution, Art. VI, sec. 18 and 22), from the second Wednesday of January, or of
  // February in a year a governor is inaugurated (2025, 2029; the Legislature meets for a day in January to organize).
  // The governor can extend it for the budget. `dated` holds each year's last day (add each year's when it differs).
  dated: { 2024: "2024-03-09", 2025: "2025-04-12", 2026: "2026-03-14" },
  opens(year) {
    const mo = year % 4 === 1 ? 1 : 0, t = new Date(year, mo, 1);
    t.setDate(1 + ((3 - t.getDay() + 7) % 7) + 7);
    return `${year}-${String(mo + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
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
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 59),
  // The governor has 5 days (Sundays excepted) to sign or veto a bill during the session; when the session ends first,
  // 15 days (Sundays excepted) after it ends. A bill not returned in time becomes law without a signature (Constitution,
  // Art. VII, sec. 14).
  govDeadline(iso) {
    if (!iso) return null;
    const end = STATE.sessionEnds(Number(iso.slice(0, 4))), five = STATE.plusWeekdays(iso, 5);
    return five <= end ? five : STATE.plusWeekdays(end, 15);
  },
  // Crossover: the 50th day is the last for a bill to pass its own house (the Joint Rules), except the budget, supplementary
  // appropriation and expiring-funds bills (`budget`), which pass in the last days (checked against 2024-26's votes).
  originDeadline: (b) => b.budget || b.topics.includes("const") ? null : STATE.plusDays(STATE.opens(DATA.session), 49),
  originWord: "crossover day (the 50th day, the last for a bill to pass its own house)",
  dueLabel: () => "Governor's decision due (5 days, Sundays excepted, during the session; 15 days after it ends; or it becomes law without a signature)",

  passedBothBy: (session) => STATE.plusWeekdays(STATE.sessionEnds(session), 15),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled and presented to the governor, often days or weeks after the vote, especially at the end of the session."],
  passedBothNext: () => ({
    what: "it's enrolled and presented to the governor, who has 5 days (Sundays excepted) to sign or veto it during the session, or 15 days after the session ends; a bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. A veto during the session can be overridden by a majority of each house's members (18 senators, 51 delegates; two-thirds for the budget and supplementary appropriation bills), or met by amending the bill. A veto after the session ends stands.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town or county",
  addressLookup: true,
  findReps: "https://www.wvlegislature.gov/districts/maps.cfm",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session ended",

  heldLabel: "Held in committee",
  heldTip: "The committee never reported it, which ends it for the session.",
  heldNote: "the committee never reported it, which ends it for the session.",
  // Bills that ended before the session did: voted down on the floor, folded by a committee into another bill's
  // substitute, or withdrawn by the sponsor. What the page says about one, instead of what comes next.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const down = texts.findLastIndex((t) => /^The (?:House|Senate) voted it down/.test(t));
    const again = (i) => texts.slice(i + 1).some((t) => /^PASSED |^The (?:House|Senate) voted to reconsider|passed it again/.test(t));
    if (down >= 0 && !again(down)) {
      const h = texts[down].match(/House|Senate/)[0];
      return {
        status: b.stage === 2 && b.passedIn && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
        when: `${texts[down].replace(/^The (House|Senate) voted it down/, "The $1 voted it down")} on ${fmtDate(acts[down][0])}.`,
        tail: "That ends it, unless the house reconsiders the vote.",
      };
    }
    const folded = texts.findLastIndex((t) => /folded it into its substitute for/.test(t));
    if (folded >= 0 && b.stage === 0) {
      const into = texts[folded].match(/for (\S+ \d+)/)?.[1] || "another bill";
      return {
        status: `Folded into ${into}`,
        when: `The committee put its text into its substitute for ${into} on ${fmtDate(acts[folded][0])}.`,
        tail: `It goes no further on its own; follow ${into}.`,
      };
    }
    const w = texts.findLastIndex((t) => /^Withdrawn by its lead sponsor/.test(t));
    if (w >= 0 && b.stage <= 1) {
      return { status: "Withdrawn", when: `Withdrawn by its lead sponsor on ${fmtDate(acts[w][0])}.`, tail: "That ends it for this session." };
    }
    return null;
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t < `${y + 1}-01-01`)
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.${y % 2 === 0 ? " Every House of Delegates seat and half the Senate's were on the ballot in November." : ""}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.plusWeekdays(adj, 15);
    const late = open.slice(5, 7) === "02", org = (() => { const t = new Date(Y, 0, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7) + 7); return `${Y}-01-${String(t.getDate()).padStart(2, "0")}`; })();
    return {
      leg: [...(late ? [["light", org, org, "Organizes"]] : []), ["", open, adj, "Regular session (60 days)"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "15 days"]],
      events: [
        ...(late ? [[org, "up", LEG, MD(org), "The newly elected Legislature meets for a day to organize; the governor is inaugurated."]] : []),
        [open, "up", LEG, MD(open), "The 60-day session opens with the governor's State of the State address and budget."],
        [adj, "down", LEG, MD(adj), "The last day, at midnight. Bills that didn't pass both houses die (the governor can extend the session for the budget)."],
        [due, "up", LEG, MD(due), "The governor's last day on bills passed at the end. A veto now stands."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The budget year starts. Most new laws take effect 90 days after they pass."],
      ],
      note: "The governor has 5 days (Sundays excepted) to sign or veto a bill during the session, and 15 days (Sundays excepted) after the session ends; a bill not acted on becomes law without a signature. The governor can veto items in an appropriation bill. A veto during the session can be overridden by a majority of each house's members (two-thirds for the budget); a veto after the session ends stands.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member list",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Bills go to one or two committees.", "The Speaker or the Senate President refers each bill, often to a committee on its subject and then a second one (\"To Health and Human Resources then Judiciary\"); the second reference can be dispensed with. Since 2025 the House's committees also work through subcommittees."],
    ["Committees report bills or let them die.", "A committee recommends a bill (\"do pass\"), often as a committee substitute or with amendments, sometimes without a recommendation, or never takes it up. A committee can also fold several bills into one substitute."],
    ["Then the floor.", "Each bill is read on three days (the rule can be suspended by four-fifths). In the House, the Rules Committee moves bills from the House Calendar to the Special Calendar, where they're voted on."],
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
    "In a committee, which decides whether to recommend it.",
    "Recommended by its committee; waiting to be read on three days and voted on.",
    "Passed the House of Delegates or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled and presented to the governor.",
    "Presented to the governor, who has 5 days (Sundays excepted) during the session, or 15 days after it ends, to sign or veto it; a bill not acted on becomes law.",
    "Became law, with a chapter number in that year's Acts: signed, or law without the governor's signature.",
    "Vetoed by the governor. A veto during the session can be overridden by a majority of each house's members; a veto after the session ends stands.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "Recommended by its committee, but never passed by its house.",
    "Passed the House of Delegates or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Energy, Industry, and Mining": ["Energy and Public Works", "Energy"],
    "School Choice": ["Educational Choice", "School choice"],
  },
  commNotes: {
    "Rules": "Each house's Rules Committee (the Speaker's in the House, the President's in the Senate) decides which bills come up and when; in the House it moves bills from the House Calendar to the Special Calendar.",
    "Finance": "Each house's Finance Committee writes the budget and takes bills that spend money or change taxes, often as their second committee.",
    "Judiciary": "Each house's Judiciary Committee takes many bills as their first or second committee; the House's works through its Courts and Legal Services subcommittees.",
  },
  moneyCommittees: { S: "Finance", H: "Finance" },
  secondCommittee: "Bills that spend money or change taxes often go to Finance as their second committee.",
};
