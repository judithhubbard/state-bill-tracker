// Kentucky: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "ky",
  name: "Kentucky",
  abbr: "KY",
  // Steps that aren't news on a watchlist card.
  routine: /^(Read the (?:second|third) time|Read and placed on the calendar|The (?:House|Senate) vote:|Posted for passage|Passed over and retained|Placed in the Orders of the Day|Taken from the Rules Committee|Sent to the Rules Committee|Sent to the Enrollment Committee|Received in the (?:House|Senate)$|Signed by the (?:Speaker|Senate President)|The .* Committee reported it favorably|.*\b(?:floor|committee) amendments? .*(?:filed|withdrawn|defeated|ruled|adopted)|Floor Amendments? .*(?:filed|withdrawn|defeated|ruled|adopted)|Committee Substitute .*(?:withdrawn|adopted|ruled))/i,
  publicSite: "https://statebilltracker.org/ky/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year; bills die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are chapters of each year's Acts ("Acts ch. 4").
  lawWord: "Acts ch.",
  // Constitutional amendments are bills: three-fifths of each house's members send one to the voters at the next
  // general election for the House (November of an even year), never to the governor (Constitution of Kentucky, sec. 256).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "three-fifths of each house's members",
  ballotEvenYears: true,
  govReach: `<a href="https://ppc.ky.gov/cservices/constituent-services" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Frankfort <a class="phone" href="tel:+15025642611" data-contact="call|governor">(502) 564-2611</a>`,

  // The Legislative Research Commission's bill record: a page per bill, its texts and its votes (PDFs).
  billUrl(p, session = DATA.session) {
    return `https://apps.legislature.ky.gov/record/${String(session).slice(2)}rs/${p.toLowerCase()}.html`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const yy = String(DATA.session).slice(2), out = [];
    for (const v of b.vers) {
      out.push(link(STATE.billUrl(v.p), `${esc(v.p)}: the Legislature's record (history, amendments, summaries)`));
      out.push(link(`https://apps.legislature.ky.gov/recorddocuments/bill/${yy}RS/${v.p.toLowerCase()}/bill.pdf`, `${esc(v.p)}: current text (PDF)`));
      if (b.votes?.length) out.push(link(`https://apps.legislature.ky.gov/record/${yy}rs/${v.p.toLowerCase()}/vote_history.pdf`, `${esc(v.p)}: how each member voted (PDF)`));
    }
    if (b.chapter) out.push(link(`https://apps.legislature.ky.gov/law/acts/${yy}RS/documents/${String(b.chapter).padStart(4, "0")}.pdf`, `Acts ch. ${b.chapter} (${DATA.session}) (PDF)`));
    return out.join("<br>");
  },

  // A regular session a year from the first Tuesday after the first Monday of January: 60 legislative days in even
  // years, ending by April 15; 30 in odd years (a few days in January, then from early February), ending by March 30
  // (Constitution, sec. 36 and 42). The last two days come after a break of about ten days, for veto overrides.
  // `dated` holds each year's last day (add each year's).
  dated: { 2024: "2024-04-15", 2025: "2025-03-28", 2026: "2026-04-15" },
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
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
  sessionEnds: (year) => STATE.dated[year] || (year % 2 ? `${year}-03-30` : `${year}-04-15`),
  // The governor has 10 days (Sundays excepted) after a bill is delivered to sign or veto it; a bill not returned by then
  // becomes law without a signature, also after the session ends (no pocket veto). A veto after the last day stands
  // (Constitution, sec. 88).
  govDeadline(iso) {
    return iso ? STATE.plusWeekdays(iso, 10) : null;
  },
  dueLabel: () => "Governor's decision due (10 days, Sundays excepted, or it becomes law without a signature)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the Speaker and the President of the Senate, and delivered to the governor, usually the same day or the next."],
  passedBothNext: () => ({
    what: "it's enrolled and delivered to the governor, who has 10 days (Sundays excepted) to sign or veto it; a bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. A veto is overridden by a majority of each house's members (20 senators, 51 representatives); the General Assembly keeps its last two days, after a break, for overrides.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: true,
  findReps: "https://apps.legislature.ky.gov/findyourlegislator/findyourlegislator.html",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session ended",

  // Each house's Committee on Committees (its leaders) assigns every bill to a standing committee; many bills are never
  // assigned. Committees report bills favorably or not at all.
  gates: { H: "Committees", S: "Committees" },
  committeeNext: { "Committees": "the house's Committee on Committees, made up of its leaders, decides whether to assign it to a committee for a hearing." },
  chairAsks: { "Committees": ["assign it to a committee for a hearing", "leave it unassigned"] },
  heldLabel: "Held in committee",
  heldTip: "The committee never reported it, which ends it for the session.",
  heldNote: "the committee never reported it, which ends it for the session.",

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t < `${y + 1}-01-01`)
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.${y % 2 === 0 ? " Every House seat and half the Senate's were on the ballot in November, so the new General Assembly chooses its leaders in January." : ""}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    const feb = (() => { const t = new Date(Y, 1, 1); t.setDate(1 + ((2 - t.getDay() + 7) % 7)); return `${Y}-02-${String(t.getDate()).padStart(2, "0")}`; })();
    const odd = Y % 2 === 1;
    return {
      leg: odd ? [["light", open, STATE.plusDays(open, 3), "Part I"], ["", feb, adj, "Part II"]] : [["", open, adj, "Regular session"]],
      gov: [["light", open, adj, "10 days a bill"], ["", adj, due, "10 days"]],
      events: [
        [open, "up", LEG, MD(open), odd ? "The 30-day session opens with a few organizational days; bills can be introduced." : "The 60-day session opens. The governor proposes the two-year budget."],
        ...(odd ? [[feb, "up", LEG, MD(feb), "The session resumes for its remaining days."]] : []),
        [adj, "down", LEG, MD(adj), "The last day, after a ten-day break: vetoes are taken up. Bills that didn't pass die."],
        [due, "up", LEG, MD(due), "The governor's last day on the final bills. A veto now stands."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The budget year starts. Most new laws take effect 90 days after the session ends."],
      ],
      note: "The governor has 10 days (Sundays excepted) to sign or veto a bill; a bill not acted on becomes law without a signature. The governor can veto items in an appropriation bill. Overriding a veto takes a majority of each house's members (20 senators, 51 representatives); the General Assembly breaks for about ten days before its last two so it can take up vetoes. A veto after the last day stands.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the Legislature's member list",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill starts in the Committee on Committees.", "Each house's Committee on Committees, made up of its leaders, assigns bills to the standing committees. Many bills are never assigned, and die there."],
    ["Committees hear bills on their subject.", "A standing committee hears a bill and reports it favorably (often with a committee substitute or amendments), or doesn't take it up at all."],
    ["The Rules Committee decides which bills reach the floor.", "A reported bill is read and sent to the Rules Committee (also the house's leaders), which posts bills for a vote in the orders of the day. Bills nobody opposes can go on a consent calendar."],
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
    "Waiting for the Committee on Committees to assign it, or in a standing committee, which decides whether to report it.",
    "Reported by its committee; the Rules Committee decides which bills are posted for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, signed by the Speaker and the President of the Senate, and delivered to the governor.",
    "Delivered to the governor, who has 10 days (Sundays excepted) to sign or veto it; a bill not acted on becomes law.",
    "Became law, with a chapter number in that year's Acts: signed, law without the governor's signature, or over a veto.",
    "Vetoed by the governor. Overriding a veto takes a majority of each house's members; a veto after the session's last day stands.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended (many bills were never assigned to one).",
    "Reported by its committee, but never brought up for a vote.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Economic Development, Tourism and Labor": ["Economic Development and Workforce Investment", "Economic development"],
    "Education": ["Primary and Secondary Education", "Education"],
    "Licensing and Occupations": ["Licensing, Occupations and Administrative Regulations", "Licensing"],
    "State and Local Government": ["State Government", "State and local government"],
  },
  commNotes: {
    "Committees": "Each house's Committee on Committees, made up of its leaders, assigns every bill to a standing committee. Bills it never assigns die there.",
    "Rules": "Each house's Rules Committee (its leaders) posts reported bills for a vote, and takes up concurrences, conference reports and vetoes.",
    "Appropriations and Revenue": "Each house's Appropriations and Revenue Committee handles the two-year budget (written in even years) and taxes, with budget review subcommittees for each part of state government.",
  },
  moneyCommittees: { S: "Appropriations and Revenue", H: "Appropriations and Revenue" },
  secondCommittee: "Bills that spend money or change taxes go to Appropriations and Revenue.",
};
