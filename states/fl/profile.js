// Florida: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "fl",
  name: "Florida",
  abbr: "FL",
  // Steps that aren't news on a watchlist card.
  routine: /^(Filed in the|Now in the|Then to:|On the .* Committee's agenda|Placed on (?:Calendar|Special Order Calendar|Local Calendar|3rd reading)|Bill (?:released|referred) to House Calendar|Added to (?:Second|Third) Reading Calendar|Bill added to Special Order Calendar|Retained on|Removed from Special Order|The (?:House|Senate) vote:|Received in the (?:House|Senate)$|Took the place of its companion|Back in the (?:House|Senate)$|The .* Committee (?:approved it|recommended it|introduced it)|Amendment.*(?:adopted|failed|withdrawn|filed|ruled|superseded|engrossed|pending|not allowed)|Temporarily postponed|Reported out of|Requests? that the|The (?:House|Senate) received the veto message|Bill placed in Conference|Conference Committee (?:appointed|Report received|Report considered))/i,
  publicSite: "https://statebilltracker.org/fl/",
  listsApi: "https://state-lists.lists-worker.workers.dev",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year; bills die when it ends.
  years: 1,
  sessionLabel: (s) => String(s),
  // Laws are chapters of the Laws of Florida, numbered by year ("Chapter 2025-19").
  lawWord: "Chapter",
  // Joint resolutions propose amendments to the State Constitution: three-fifths of each house's members send one to the
  // voters at the next general election (November of an even year), where it needs 60% of the vote; never the governor
  // (Constitution, Art. XI, sec. 1 and 5).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "three-fifths of each house's members (24 senators, 72 representatives)",
  ballotEvenYears: true,
  govReach: `<a href="https://www.flgov.com/eog/leadership/people/ron-desantis/contact" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Tallahassee <a class="phone" href="tel:+18507179337" data-contact="call|governor">(850) 717-9337</a>`,

  // The Florida Senate's bill pages cover both houses' bills (a House bill's page is /Session/Bill/2025/1195 too).
  billUrl(p, session = DATA.session) {
    return `https://www.flsenate.gov/Session/Bill/${session}/${String(p).replace(/^[A-Z]+/, "")}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    const out = [];
    for (const v of b.vers) {
      const n = String(v.p).replace(/^[A-Z]+/, "");
      out.push(link(STATE.billUrl(v.p), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: the Florida Senate's page (history, each version's text, amendments, staff analyses, votes)`));
      out.push(link(`https://www.flsenate.gov/Session/Bill/${DATA.session}/${n}/?Tab=BillText`, `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: bill text`));
    }
    if (b.chapter) {
      const [y, n] = String(b.chapter).split("-");
      out.push(link(`http://laws.flrules.org/${y}/${n}`, `Chapter ${esc(b.chapter)}, Laws of Florida`));
    }
    return out.join("<br>");
  },

  // A 60-day regular session a year (Constitution, Art. III, sec. 3): odd years from the first Tuesday after the first
  // Monday in March; even years from the second Tuesday after the first Monday in January (s. 11.011). Sessions can be
  // extended: 2025's ran to June 16 for the budget. `dated` holds each year's last day (add each year's).
  dated: { 2024: "2024-03-08", 2025: "2025-06-16", 2026: "2026-03-13" },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  opens(year) {
    const firstMonday = (month) => { const t = new Date(year, month, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7)); return t; };
    const t = year % 2 ? firstMonday(2) : firstMonday(0);
    t.setDate(t.getDate() + (year % 2 ? 1 : 8));
    return `${year}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.dated[year] || STATE.plusDays(STATE.opens(year), 59),
  // The governor has 7 consecutive days after a bill is presented to sign or veto it; if the Legislature adjourns sine
  // die (or recesses more than 30 days) within those 7 days, or the bill is presented after, 15 days from presentation.
  // A bill not acted on becomes law without a signature (Constitution, Art. III, sec. 8). The presiding officers present
  // passed bills in batches, often weeks or months after the session.
  govDeadline(iso) {
    if (!iso) return null;
    const seven = STATE.plusDays(iso, 7), end = STATE.sessionEnds(Number(iso.slice(0, 4)));
    return seven <= end ? seven : STATE.plusDays(iso, 15);
  },
  dueLabel: () => "Governor's decision due (7 days during the session, 15 after it, or it becomes law without a signature)",

  passedBothBy: (session) => STATE.plusDays(STATE.sessionEnds(session), 125),
  passedBothNote: (live) => live ? "Not yet presented to the governor" : "Never presented to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled and signed by the Senate President and the Speaker, who present them to the governor in batches, often weeks or months after the session."],
  passedBothNext: () => ({
    what: "it's enrolled and presented to the governor, whenever the Senate President and the Speaker send it (often weeks after the session). The governor then has 7 days to sign or veto it, or 15 days after the session ends; a bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. A veto goes to the next regular session, where two-thirds of each house can override it.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City or county",
  addressLookup: true,
  findReps: "https://www.flsenate.gov/Senators/Find",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be filed again in a later session.",
  outOfTimeLine: "Died when the session ended",

  heldLabel: "Held in committee",
  heldTip: "The committee never took it up, which ends it for the session.",
  heldNote: "the committee never took it up, which ends it for the session.",

  // Bills that ended before the session did: replaced by the other house's companion (Florida files most bills in both
  // houses, and the one that passes takes the other's place), or voted down on the floor.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const rep = texts.findLastIndex((t) => /^Replaced by its companion, |^Laid on the table: .* passed instead/.test(t));
    if (rep >= 0 && b.stage <= 2) {
      const into = (texts[rep].match(/companion, ([A-Z]+) (\d+)/) || texts[rep].match(/([A-Z]+) (\d+) passed instead/));
      const name = into ? `${into[1]} ${into[2]}` : "its companion";
      return {
        status: `Replaced by ${name}`,
        when: `Its companion, ${name}, passed instead and took its place on ${fmtDate(acts[rep][0])}.`,
        tail: `It goes no further on its own; follow ${name}.`,
      };
    }
    const down = texts.findLastIndex((t) => /^The (?:House|Senate) voted it down/.test(t));
    const again = (i) => texts.slice(i + 1).some((t) => /^PASSED |voted to reconsider|passed it again/.test(t));
    if (down >= 0 && !again(down) && b.stage <= 2) {
      const h = texts[down].match(/House|Senate/)[0];
      return {
        status: b.stage === 2 && b.passedIn && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
        when: `${texts[down]} on ${fmtDate(acts[down][0])}.`,
        tail: "That ends it, unless the house reconsiders the vote.",
      };
    }
    return null;
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y), next = y + 1;
    if (t > end && t < `${next}-01-01`)
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${next} session opens ${fmtDate(STATE.opens(next))}.${y % 2 === 0 ? " Every House seat and half the Senate's were on the ballot in November; the new Legislature chose its leaders at its organization session two weeks later." : ""}`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Bills you star now stay on your watchlist when the session opens.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), late = STATE.plusDays(adj, 110);
    return {
      leg: [["", open, adj, "Regular session"]],
      gov: [["light", open, adj, "7 days a bill"], ["", adj, late, "15 days a bill, as presented"]],
      events: [
        [open, "up", LEG, MD(open), "The 60-day session opens. Bills filed in the months before are introduced; the governor has proposed a budget."],
        [adj, "down", LEG, MD(adj), "The session ends (sine die). Bills that didn't pass both houses die."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The budget year starts; most new laws take effect."],
      ],
      note: "The governor has 7 days to act on a bill presented during the session, and 15 days on one presented after it (most are); a bill not acted on becomes law without a signature. The governor can veto items in an appropriation bill. A veto goes to the next regular session, which can override it by two-thirds of each house.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the House's and the Senate's member lists",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill goes to committees.", "The Senate President or the Speaker refers each bill to its committees, usually two to four in a row (in the House, subcommittees first, then a full committee). A bill has to get through each of them before the floor; most bills die waiting in one."],
    ["Committees can rewrite a bill.", "A committee can report a bill favorably, with amendments, or as a committee substitute (\"CS\"): a rewritten bill that keeps its number. In the Senate each committee vote is recorded."],
    ["The leaders schedule floor votes.", "Bills that clear their committees go on the calendar; the Senate Rules Committee and the House's leaders choose which are put on the special order calendar for a vote."],
    ["Companion bills.", "Most bills are filed in both houses. When one passes, the other house usually takes it up in place of its own version (it's \"substituted\"), and its own is laid on the table."],
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
    "In one of the committees it was referred to; it has to get through each of them.",
    "Through its committees and on the calendar; the leaders decide which bills come up for a vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled, and the Senate President and the Speaker present it to the governor when they choose.",
    "Presented to the governor, who has 7 days during the session or 15 after it to sign or veto it; a bill not acted on becomes law.",
    "Became law, with a chapter number in the Laws of Florida: signed, or law without the governor's signature.",
    "Vetoed by the governor. The next regular session can override a veto by two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got through its committees before the session ended.",
    "Through its committees, but never brought up for a vote (or its companion passed instead).",
    "Passed the House or the Senate, but not both.",
    "Passed both houses but was never sent to the governor.",
    "Sent to the governor; no signature or veto is recorded.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be filed again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Banking and Insurance": ["Insurance and Banking", "Insurance and banking"],
    "Children, Families, and Elder Affairs": ["Human Services", "Children, families and seniors"],
    "Criminal Justice": ["Criminal Justice", "Criminal justice"],
    "Education Pre-K - 12": ["Education Administration", "Schools"],
    "Education Postsecondary": ["Careers and Workforce", "Colleges and universities"],
    "Ethics and Elections": ["Government Operations", "Elections and ethics"],
    "Finance and Tax": ["Ways and Means", "Taxes"],
    "Health Policy": ["Health and Human Services", "Health"],
    "Community Affairs": ["Intergovernmental Affairs", "Local government"],
    "Environment and Natural Resources": ["Natural Resources and Disasters", "Environment"],
    "Appropriations": ["Budget", "The budget"],
  },
  commNotes: {
    "Rules": "The Senate Rules Committee is the last stop for most Senate bills, and its chair sets the special order calendar: which bills come up for a vote.",
    "Fiscal Policy": "The Senate's Fiscal Policy Committee takes many bills that cost money or change taxes, as a last committee before Rules.",
    "Appropriations": "The Senate Appropriations Committee writes the budget; its subcommittees (\"... Appropriations\") review bills that spend money.",
    "Budget": "The House Budget Committee writes the budget; its budget subcommittees review bills that spend money.",
    "Claim Bills Special Master": "Claim bills (\"Relief of ...\") ask the Legislature to pay someone the state or a local government harmed, beyond what the law otherwise allows; a special master hears each one first.",
  },
  moneyCommittees: { S: "Appropriations", H: "Budget" },
  secondCommittee: "Bills that spend money go to an appropriations or budget committee as well.",
};
