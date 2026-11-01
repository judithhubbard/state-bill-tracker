// Arizona: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "az",
  name: "Arizona",
  abbr: "AZ",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled|House First Reading|House Second Reading|Senate First Reading|Senate Second Reading|Transmit to (?:House|Senate)|Referred to committee|House Placed on Consent Calendar|Senate Consent Calendar)/i,
  publicSite: "https://statebilltracker.org/az/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // One regular session a year; bills die when it adjourns.
  years: 1,
  sessionLabel: (s) => String(s),
  govReach: `<a href="https://azgovernor.gov/office-arizona-governor/form/voice-an-opinion" target="_blank" rel="noopener" data-contact="online|governor">Share your opinion with the governor</a> · Phoenix <a class="phone" href="tel:+16025424331" data-contact="call|governor">(602) 542-4331</a>`,

  // Concurrent resolutions proposing constitutional amendments pass each house once, by a majority of its members, then go
  // to the voters at the next general election (even years), never to the governor (Arizona Constitution, Art. XXI, sec. 1;
  // the Legislature can call a special election by two-thirds of each house, which it rarely does).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "a majority of the members of each house",
  ballotEvenYears: true,

  // The Legislature's bill page (apps.azleg.gov, linked from Open States' record) for status, text and votes.
  billUrl(p) {
    const v = (BILLS || []).flatMap((b) => b.vers).find((x) => x.p === p);
    return v?.link || "https://www.azleg.gov/bills/";
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p)}: status, text and votes`)).join("<br>");
  },

  // The session opens the second Monday of January and runs until it adjourns sine die, set by the Legislature (in recent
  // years from April to late June; the past ones are from the bills' last floor votes).
  opens(year) {
    const t = new Date(year, 0, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);
    return `${year}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  dated: {},
  sessionEnds: (year) => STATE.dated[year] || `${year}-06-30`,
  // The governor has 5 days (Sundays excepted) during the session, and 10 days (Sundays excepted) after it adjourns
  // (Arizona Constitution, Art. V, sec. 7).
  govDeadline(iso) {
    if (!iso) return null;
    const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    const plus = (from, n) => { const [a, b, c] = from.split("-").map(Number), t = new Date(a, b - 1, c);
      while (n > 0) { t.setDate(t.getDate() + 1); if (t.getDay() !== 0) n--; } return ymd(t); };
    const end = STATE.sessionEnds(+iso.slice(0, 4)), five = plus(iso, 5);
    return five <= end ? five : plus(end > iso ? end : iso, 10);
  },
  dueLabel: () => "Governor's decision due (5 days during the session, 10 after it, Sundays excepted)",

  passedBothBy: (session) => STATE.govDeadline(STATE.sessionEnds(session)),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses go to the governor."],
  passedBothNext: () => ({
    what: "it goes to the governor, who can sign it or veto it (or veto items in a spending bill). A bill the governor doesn't act on becomes law.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  townWord: "City, town, community or county",
  addressLookup: true,
  findReps: "https://www.azleg.gov/findmylegislator/",
  oneNumber: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again next year.",
  outOfTimeLine: "Died when the session ended",

  // Every bill goes through each house's Rules Committee, which checks it before the floor.
  committeeNext: {
    "Rules": "the Rules Committee decides whether it goes on to the floor.",
  },
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end && t.startsWith(String(y)))
      return `The ${y} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${y + 1} session opens ${fmtDate(STATE.opens(y + 1))}.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're introduced. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.govDeadline(adj);
    return {
      leg: [["", open, adj, "Regular session"]],
      gov: [["light", open, adj, "5 days a bill"], ["", adj, due, "10 days"]],
      events: [
        [open, "up", LEG, MD(open), "The session opens."],
        [adj, "down", LEG, MD(adj), "Sine die: the session adjourns. Bills that didn't pass both houses die."],
      ],
      note: "During the session the governor has 5 days (Sundays excepted) to act on a bill; after it adjourns, 10 days. The governor can veto items in a spending bill. Overriding a veto takes two-thirds of each house. New laws take effect 91 days after the session ends, unless passed as emergency measures.",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from Open States",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill starts in a committee on its subject.", "The Speaker or the Senate President assigns it to one or more standing committees, whose chairs decide whether it gets a hearing."],
    ["Then the Rules Committee and caucuses.", "Each house's Rules Committee checks every bill before the floor, and each party's caucus discusses it."],
    ["Then the Committee of the Whole.", "The full house debates and amends it as the Committee of the Whole, then votes on third reading."],
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
    "Waiting in a committee. The chair decides whether it gets a hearing and a vote.",
    "A committee approved it, and it waits for the Rules Committee, the caucuses and the full house.",
    "Passed the Senate or the House, but not both. Both houses have to pass the same text.",
    "Passed both houses. It goes to the governor.",
    "With the governor, who has 5 days (Sundays excepted) during the session or 10 after it.",
    "Signed into law (or became law without the governor's signature), with a chapter number.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee reported it, but it never got a vote of the full house.",
    "Passed the Senate or the House, but not both.",
    "Passed both houses, but the records show no signature or veto.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  commPairs: {},
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that cost money may also go to an Appropriations Committee.",
};
