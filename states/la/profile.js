// Louisiana: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "la",
  name: "Louisiana",
  abbr: "LA",
  // Steps that aren't news on a watchlist card.
  routine: /^(Prefiled$|The (?:House|Senate) vote|Received in the (?:House|Senate)$|Back from the (?:House|Senate) without changes|Signed by the (?:Speaker|President)|Sent to the Legislative Bureau|The Legislative Bureau reviewed|Read by title|Rules suspended|Called from the calendar|Scheduled for |First appeared in the Interim Calendar|Made Special Order|Read by title; made Special Order|Notice|Effective date|Senate (?:floor|Committee) amendments read and adopted|.*conferees|.*Conference Committee (?:members|membership)|Conference Committee report received|Lies over|By a vote of|Motion to reconsider|The (?:House|Senate) received the governor's veto message)/i,
  publicSite: "https://statebilltracker.org/la/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A session a year: a general session in even years, a fiscal session in odd years; bills die when it ends.
  years: 1,
  sessionLabel: (s) => `${s} ${s % 2 ? "fiscal" : "general"}`,
  // Laws are numbered Acts of each year's session ("Act 28 of 2026"); constitutional amendments get Act numbers too.
  lawWord: "Act",
  // Constitutional amendments are bills (HB, SB): two-thirds of each house's members send one to the voters at the
  // statewide election it names, never to the governor (Constitution, Art. XIII, sec. 1).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house's members (26 senators, 70 representatives)",
  ballotLine: (b) => (DATA.current && isoToday() <= STATE.sessionEnds(DATA.session)
    ? "Next: the voters, at the statewide election the amendment names."
    : "It went to the voters at the statewide election it names; the records here don't show the result."),
  // From gov.louisiana.gov/contact-the-governors-office (read by program 2026-11-14, not checked by the owner).
  govReach: `<a href="https://gov.louisiana.gov/contact-the-governors-office" target="_blank" rel="noopener" data-contact="online|governor">Contact the governor</a> · Constituent Services <a class="phone" href="tel:+12253420991" data-contact="call|governor">(225) 342-0991</a>`,

  // The Legislature's page for each bill (history, texts, digests, votes).
  billUrl(p, session = DATA.session) {
    return `https://legis.la.gov/legis/BillInfo.aspx?s=${String(session).slice(2)}RS&b=${p}&sbi=y`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(v.link || STATE.billUrl(v.p), `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))}: the Legislature's page (each version's text, digests, amendments, votes)`)).join("<br>");
  },

  // A regular session a year (Constitution, Art. III, sec. 2): in even years a general session from noon on the second
  // Monday of March, 60 legislative days within 85 calendar days; in odd years a fiscal session from the second Monday of
  // April, 45 legislative days within 60 calendar days, where each member may introduce no more than five bills that aren't
  // about money (taxes, appropriations, fees, tax exemptions and the like).
  opens(year) {
    const t = new Date(year, year % 2 ? 3 : 2, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 7);
    return `${year}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds: (year) => STATE.plusDays(STATE.opens(year), year % 2 ? 59 : 84),
  // The veto session: the 40th day after the session ends, unless a majority of either house's members declare in
  // writing that it isn't needed (Art. III, sec. 18).
  vetoSession: (year) => STATE.plusDays(STATE.sessionEnds(year), 40),
  // The governor has 10 days after a bill is delivered if the Legislature is still in session on the tenth day, else 20
  // days after delivery; a bill not acted on becomes law without a signature (Art. III, sec. 18).
  govDeadline(iso) {
    if (!iso) return null;
    const ten = STATE.plusDays(iso, 10);
    return ten <= STATE.sessionEnds(Number(iso.slice(0, 4))) ? ten : STATE.plusDays(iso, 20);
  },
  dueLabel: () => "Governor's decision due (10 days during the session, 20 after it ends; or it becomes law without a signature)",

  passedBothBy: (session) => STATE.plusDays(STATE.sessionEnds(session), 23),
  passedBothNote: (live) => live ? "Not yet sent to the governor" : "Never sent to the governor",
  passedBothGroup: ["Before the governor's deadline", () => "Bills that pass both houses are enrolled, signed by the Speaker and the Senate President, and sent to the governor, usually within a few days."],
  passedBothNext: () => ({
    what: "it's enrolled, signed by the Speaker and the President of the Senate and sent to the governor, who has 10 days to sign or veto it while the Legislature is in session, or 20 days after it's delivered when the session ends first; a bill the governor doesn't act on becomes law. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members (26 senators, 70 representatives), during the session or at a veto session 40 days after it.",
    gov: ["sign it", "veto it"],
    reps: ["urge the governor to sign it", "urge the governor to veto it"],
  }),
  // "House House and Governmental Affairs Committee": the committees named for their own house aren't prefixed again.
  voteWhat: (v) => (v.kind === "C" && /^(?:House|Senate) and /.test(v.committee || "") ? `${esc(v.committee)} Committee` : ""),
  townWord: "City, town or parish",
  addressLookup: true,
  findReps: "https://legis.la.gov/legis/FindMyLegislators.aspx",
  oneNumber: true,
  floorVotesEnd: true,
  diesAfterFloor: () => "The session has ended, so it died. It would have to be introduced again in a later session.",
  outOfTimeLine: "Died when the session ended",

  // A committee's deferral ends a bill for the session: "involuntarily" (voted down, counted that way) or at the author's
  // request (voluntarily, known from the committees' vote records, 2026 on).
  heldAction: /^Deferred by the .* Committee (?:\(involuntarily\)|at the author's request)/,
  heldLabel: "Deferred",
  heldTip: "Set aside by the committee at the author's request (voluntarily deferred), which ends it for the session. A bill the committee defers against the author's wishes counts as voted down.",
  heldNote: "set aside by the committee at the author's request (voluntarily deferred), which ends it for the session; recorded from 2026.",
  // Bills that ended before the session did: voted down on the floor, replaced by a committee's substitute (a new bill),
  // or withdrawn by the author. What the page says about one, instead of what comes next.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const down = texts.findLastIndex((t) => /^The (?:House|Senate) voted it down/.test(t));
    const again = (i) => texts.slice(i + 1).some((t) => /^PASSED |^The (?:House|Senate) voted to reconsider|passed it again/.test(t));
    if (down >= 0 && !again(down) && b.stage <= 2) {
      const h = texts[down].match(/House|Senate/)[0];
      return {
        status: b.stage === 2 && b.passedIn && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
        when: `${texts[down]} on ${fmtDate(acts[down][0])}.`,
        tail: "That ends it, unless the house reconsiders the vote.",
      };
    }
    const rep = texts.findLastIndex((t) => /^Replaced by the committee's substitute/.test(t));
    if (rep >= 0 && b.stage <= 1) {
      const into = texts[rep].match(/([HS]B \d+)$/)?.[1] || "a new bill";
      return {
        status: `Replaced by ${into}`,
        when: `The committee wrote a substitute, ${into}, which took its place on ${fmtDate(acts[rep][0])}.`,
        tail: `It goes no further on its own; follow ${into}.`,
      };
    }
    const w = texts.findLastIndex((t) => /^Withdrawn by its author/.test(t));
    if (w >= 0 && b.stage <= 1) {
      return { status: "Withdrawn", when: `Withdrawn by its author on ${fmtDate(acts[w][0])}.`, tail: "That ends it for this session." };
    }
    return null;
  },

  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = STATE.sessionEnds(y), next = y + 1;
    if (t > end && t < `${next}-01-01`)
      return `The ${y} ${y % 2 ? "fiscal" : "general"} session ended ${fmtDate(end)}. Bills that didn't pass both houses died; the ${next} ${next % 2 ? "fiscal" : "general"} session opens ${fmtDate(STATE.opens(next))}.${next % 2 ? " In a fiscal session each member may introduce only five bills that aren't about money." : ""}`;
    if (y % 2 && t <= end)
      return `${y} is a fiscal session: 45 legislative days for the budget and taxes; each member may introduce only five other bills.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${raw.session} session opens ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're prefiled. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  calendarDays: 0,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, open = STATE.opens(Y), adj = STATE.sessionEnds(Y), due = STATE.plusDays(adj, 23), veto = STATE.vetoSession(Y);
    const fiscal = Y % 2 === 1;
    return {
      leg: [["", open, adj, fiscal ? "Fiscal session (45 days in 60)" : "General session (60 days in 85)"], ["light", veto, veto, "Veto session"]],
      gov: [["light", open, adj, "10 days a bill"], ["", adj, due, "20 days"]],
      events: [
        [open, "up", LEG, MD(open), fiscal ? "The fiscal session opens at noon: the budget, taxes and five other bills per member." : "The general session opens at noon; the governor addresses the Legislature."],
        [adj, "down", LEG, MD(adj), "The last day, by 6 p.m. Bills that didn't pass both houses die."],
        [due, "up", LEG, MD(due), "About the governor's last day on bills passed at the end (20 days after each is delivered)."],
        [`${Y}-07-01`, "down", LEG, "July 1", "The budget year starts."],
        [`${Y}-08-01`, "up", LEG, "Aug. 1", "Most new laws take effect."],
        [veto, "down", LEG, MD(veto), "The veto session, unless a majority of either house's members say it isn't needed. Overriding a veto takes two-thirds of each house's members."],
      ],
      note: "The governor has 10 days to sign or veto a bill during the session, and 20 days after it's delivered when the session ends first; a bill not acted on becomes law without a signature. The governor can veto items in an appropriation bill. Overriding a veto takes two-thirds of each house's members (26 senators, 70 representatives).",
    };
  },
  waitingHead: "On the way to the governor",
  govYearsNote: "",
  partySource: "Party from the House's and Senate's member pages",
  openUntil: (s) => `the governor acts on the last bills after the ${s} session`,

  commIntro: [
    ["Every bill goes to a committee.", "Bills are prefiled and provisionally referred before the session, or introduced and referred on the floor. The committee hears it and reports it (favorably, with amendments, or as a substitute: a new bill with its own number), or lets it sit; voting to defer it ends it for the session."],
    ["Money bills go to a second committee.", "A bill that spends money or changes taxes is often sent on to Appropriations or Ways and Means in the House, or Finance or Revenue and Fiscal Affairs in the Senate, before the floor."],
    ["Then the floor.", "The Legislative Bureau reviews each reported bill's wording. Each house then votes on final passage by roll call. Passing a bill takes a majority of each house's members (53 representatives, 20 senators); constitutional amendments and some others need two-thirds."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died on the floor", "Passed one house only", "Passed both houses", "Sent to the governor", "Became law", "Vetoed"],
      long: ["Died in committee", "Died on the floor (never passed by its house)", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died on floor", "Passed one house", "Passed both", "Sent, no action", "Law", "Vetoed"],
    },
  },
  stageTips: [
    "In a committee, which decides whether to report it.",
    "Reported by its committee; waiting for the Legislative Bureau's review and a floor vote.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It's enrolled and sent to the governor.",
    "Sent to the governor, who has 10 days during the session, or 20 days after delivery once it ends, to sign or veto it; a bill not acted on becomes law.",
    "Became law, with an Act number: signed by the governor (budget bills often with items vetoed), or law without the governor's signature.",
    "Vetoed by the governor. Overriding a veto takes two-thirds of each house's members, during the session or at the veto session.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "Reported by its committee, but never passed by its house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This session is over. Bills that didn't become law have to be introduced again in a later session.",

  // Senate committee -> [its House counterpart, the subject], where the names differ.
  commPairs: {
    "Finance": ["Appropriations", "The budget"],
    "Revenue and Fiscal Affairs": ["Ways and Means", "Taxes"],
    "Commerce, Consumer Protection and International Affairs": ["Commerce", "Commerce"],
    "Senate and Governmental Affairs": ["House and Governmental Affairs", "Elections and government"],
    "Local and Municipal Affairs": ["Municipal, Parochial and Cultural Affairs", "Local government"],
    "Judiciary A": ["Civil Law and Procedure", "Civil law"],
    "Judiciary B": ["Judiciary", "Courts"],
    "Judiciary C": ["Administration of Criminal Justice", "Criminal law"],
    "Natural Resources": ["Natural Resources and Environment", "Natural resources and the environment"],
  },
  commNotes: {
    "Appropriations": "Writes the House's version of the budget and takes House bills that spend money, often as their second committee.",
    "Finance": "Writes the Senate's version of the budget and takes bills that spend money, often as their second committee.",
    "Ways and Means": "Takes bills that change taxes, fees and other revenue in the House.",
    "Revenue and Fiscal Affairs": "Takes bills that change taxes, fees and other revenue in the Senate.",
    "Environmental Quality": "Takes Senate bills about pollution and the environment.",
  },
  moneyCommittees: { S: "Finance", H: "Appropriations" },
  secondCommittee: "Bills that spend money often go on to Appropriations (House) or Finance (Senate); bills about taxes to Ways and Means or Revenue and Fiscal Affairs.",
};
