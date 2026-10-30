// Illinois: the page's settings and rules that are particular to this state. build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "il",
  name: "Illinois",
  abbr: "IL",
  // Steps that aren't news on a watchlist card.
  routine: /^(INTRODUCED|First Reading|Prefiled with|Filed with|(Added|Removed|Remove) .*Sponsor|Chief (Senate |House )?Sponsor|Alternate Chief|Added as|Arrived? in|Placed on Calendar|Held on Calendar|Second Reading|.*Amendment No\. \d+ (Filed|Referred|Recommends|Rule|Tabled|Assignments|Postponed|Re-assigned|Adopted|Pursuant)|Third Reading Deadline|Committee Deadline|Rule \d+-\d+.*Deadline|Approved for Consideration|To .* Subcommittee|Effective Date|Recalled to Second|Motion Filed|Motion Referred|Postponed - )/i,
  publicSite: "https://statebilltracker.org/il/",
  listsApi: "",
  houses: { S: "Senate", H: "House" },
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "state senator", H: "state representative" },
  greetings: { S: "Senator", H: "Representative" },
  // How a session is written: 2025–26 (the 104th General Assembly).
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  govReach: `<a href="https://gov.illinois.gov/contact-us.html" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · Springfield <a class="phone" href="tel:+12177820244" data-contact="call|governor">(217) 782-0244</a> · Chicago <a class="phone" href="tel:+13128142121" data-contact="call|governor">(312) 814-2121</a>`,

  // The General Assembly's public file repository has each bill's status page and text.
  billUrl(p, session = DATA.session) {
    const ga = (session - 1817) / 2, n = `${p.slice(0, 2)}${p.slice(2).padStart(4, "0")}`;
    return `https://ftp.ilga.gov/Legislation/${ga}/BillStatus/HTML/${ga}00${n}.html`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => {
      const ga = (DATA.session - 1817) / 2, n = `${v.p.slice(0, 2)}${v.p.slice(2).padStart(4, "0")}`;
      return `${link(STATE.billUrl(v.p), `${esc(v.p)}: status and history`)} · ${link(`https://ftp.ilga.gov/Legislation/${ga}/${v.p.slice(0, 2)}/${ga}00${n}.htm`, "text as introduced")}`;
    }).join("<br>");
  },

  // A General Assembly sits from the second Wednesday of January of an odd year until the next one is sworn in.
  opens(session) {
    const t = new Date(session, 0, 1); t.setDate(1 + ((3 - t.getDay() + 7) % 7) + 7);
    return `${session}-01-${String(t.getDate()).padStart(2, "0")}`;
  },
  sessionEnds(session) {
    const [y, m, d] = STATE.opens(session + 2).split("-").map(Number), t = new Date(y, m - 1, d - 1);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  // It meets until the next General Assembly, with long breaks: the spring session ends May 31, the fall veto
  // session is in October and November.
  floorVotesEnd: false,
  // The governor has 60 days after a bill is presented, and bills are presented within 30 days of passing both houses
  // (Illinois Constitution, Art. IV, sec. 9).
  govDeadline(iso) {
    if (!iso) return null;
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + 60);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  dueLabel: () => "Governor's decision due (60 days after it reached the governor)",

  // A bill the governor sent back with changes (an amendatory veto) needs both houses to accept them.
  amended: (b) => b.vers.some((v) => v.actions.some(([, t]) => t === "AMENDATORY VETO")),
  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothNote: (live, b) => !live ? "Never sent to the governor"
    : !b ? "Includes bills sent back with the governor's changes"
    : STATE.amended(b) ? "Sent back with the governor's changes" : "Not yet sent to the governor",
  passedBothGroup: ["Before the General Assembly ends", () => "Bills go to the governor within 30 days of passing both houses. A bill sent back with the governor's changes needs both houses to accept them."],
  passedBothNext(b) {
    if (!STATE.amended(b)) return {
      what: "it goes to the governor within 30 days, who then has 60 days to sign it, veto it, or send it back with changes (an amendatory veto). A bill the governor doesn't act on becomes law.",
      gov: ["sign it", "veto it"],
      reps: ["urge the governor to sign it", "urge the governor to veto it"],
    };
    return {
      what: "both houses vote on whether to accept the governor's changes (usually in the fall veto session). If both accept them, the bill becomes law with the changes; otherwise it fails, unless both houses override the veto by three-fifths.",
      leaders: ["H", "S"],
      leaderAsk: ["bring up the motion to accept the governor's changes", "keep the governor's changes from coming up"],
      reps: ["vote to accept the governor's changes", "vote against the governor's changes"],
    };
  },
  townWord: "City, village or county",
  addressLookup: true,
  findReps: "https://www.elections.il.gov/ElectionOperations/DistrictLocator.aspx",
  oneNumber: true,
  diesAfterFloor: () => "The General Assembly has ended, so it died with it.",
  outOfTimeLine: "Died when the General Assembly ended",

  // Bills that miss a deadline go back to the House Rules Committee or the Senate Assignments Committee.
  heldLabel: "Sent back to Rules",
  heldTip: "Missed a deadline and went back to the House Rules Committee or the Senate Assignments Committee, where most such bills stay.",
  heldNote: "missed a deadline and went back to the Rules (House) or Assignments (Senate) Committee, where most such bills stay.",
  // Every bill starts in the Rules (House) or Assignments (Senate) Committee, which sends it to a committee or keeps it.
  committeeNext: {
    "Rules": "the Rules Committee decides whether to send it to a committee for a hearing.",
    "Assignments": "the Assignments Committee decides whether to send it to a committee for a hearing.",
  },
  chairAsks: {
    "Rules": ["send it to a committee for a hearing", "keep it in the Rules Committee"],
    "Assignments": ["send it to a committee for a hearing", "keep it in the Assignments Committee"],
  },

  // The note above the bill list between the General Assembly's working months (empty while it meets).
  sessionNotice(raw) {
    const t = isoToday(), md = t.slice(5), y = raw.session, end = STATE.sessionEnds(y);
    if (t > end) return "";
    if (md >= "06-01" && md < "10-01")
      return "The General Assembly finished its spring session May 31 and returns for the fall veto session in October and November. Bills it passed go to the governor, who has 60 days to act on each.";
    if (t.startsWith(String(y + 1)) && md >= "11-20")
      return `The ${(y - 1817) / 2}th General Assembly ends ${fmtDate(end)}; bills that haven't passed both houses by then die. Bills for the next one can be filed from December.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${(raw.session - 1817) / 2}th General Assembly is sworn in ${fmtDate(STATE.opens(raw.session))}. Bills appear here as they're filed. Stars you add here carry over.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} session</a>` : ""}`,

  // The two-year calendar.
  calendarDays: 14,
  calendar(Y, end1, end2, MD) {
    const LEG = 112, GOV = 150, open = STATE.opens(Y), close = STATE.sessionEnds(Y);
    return {
      leg: [["", open, `${Y}-05-31`, "Spring session"], ["light", `${Y}-06-01`, `${Y}-10-01`, "Summer"], ["", `${Y}-10-01`, `${Y}-11-30`, "Veto session"],
        ["", `${Y + 1}-01-05`, `${Y + 1}-05-31`, "Spring session"], ["light", `${Y + 1}-06-01`, `${Y + 1}-10-01`, "Summer"], ["", `${Y + 1}-10-01`, `${Y + 1}-11-30`, "Veto session"], ["", `${Y + 2}-01-02`, close, "Lame duck"]],
      gov: [["light", open, close, "60 days to act on each bill"]],
      events: [
        [open, "up", LEG, MD(open), "The General Assembly is sworn in; bills filed since December."],
        [`${Y}-05-31`, "down", LEG, "May 31", "Spring session ends. After this, a bill needs three-fifths to take effect before next June."],
        [`${Y}-10-20`, "up", LEG, "October", "Fall veto session: overrides and the governor's changes."],
        [`${Y + 1}-05-31`, "down", LEG, "May 31", "Spring session ends."],
        [`${Y + 1}-11-01`, "up", LEG, "November", "Veto session (after the election)."],
        [close, "down", LEG, MD(close), "The General Assembly ends. Bills that didn't pass both houses die."],
      ],
      note: "Bills go to the governor within 30 days of passing; the governor then has 60 days to sign, veto, or send a bill back with changes (an amendatory veto), which both houses can accept. Overriding a veto takes three-fifths of each house. New laws usually take effect January 1.",
    };
  },
  waitingHead: "Sent back with the governor's changes",
  govYearsNote: "",
  partySource: "Party from the General Assembly's list of members",
  openUntil: (s) => `the General Assembly ends in January ${s + 2}`,

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
    "Waiting in a committee. Every bill starts in the House Rules or Senate Assignments Committee, which decides whether to send it to a committee for a hearing; most bills never leave.",
    "A committee approved it, and it's on the calendar for a vote of the full House or Senate.",
    "Passed the House or the Senate, but not both. Both houses have to pass the same text.",
    "Passed both houses. It goes to the governor within 30 days; a bill sent back with the governor's changes waits here for both houses to accept them.",
    "Sent to the governor, who has 60 days to sign it, veto it, or send it back with changes.",
    "Signed into law (or became law without the governor's signature) and given a Public Act number.",
    "Vetoed by the governor. Overriding a veto takes three-fifths of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the General Assembly ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This General Assembly is over. Bills that didn't become law have to be filed again in the next one.",

  commPairs: {
    "Executive": ["Executive", "Executive"],
    "Appropriations": ["Appropriations-General Services", "Budget and spending"],
    "Criminal Law": ["Judiciary - Criminal", "Criminal law"],
    "Judiciary": ["Judiciary - Civil", "Courts and civil law"],
    "Revenue": ["Revenue & Finance", "Taxes"],
    "Environment and Conservation": ["Energy & Environment", "Environment and energy"],
    "Education": ["Elementary & Secondary Education: School Curriculum & Policies", "Education"],
    "Health and Human Services": ["Public Health", "Health"],
    "Labor": ["Labor & Commerce", "Labor"],
    "Local Government": ["Counties & Townships", "Local government"],
  },
  commNotes: {},
  moneyCommittees: { S: "Appropriations", H: "Appropriations-General Services" },
  secondCommittee: "Every bill starts in the House Rules Committee or the Senate Assignments Committee, which sends it to a committee for a hearing, or keeps it.",
};
