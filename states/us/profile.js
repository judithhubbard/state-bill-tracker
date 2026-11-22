// Congress: the page's settings and rules for the federal jurisdiction (/us/). build_data.py puts this file into every
// page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  code: "us",
  name: "Congress",
  abbr: "US",
  bodyName: "Congress",
  // Committee meetings (states/us/meetings.py) are given in Washington's time.
  meetZone: "ET",
  // The President signs or vetoes bills, not a governor. The White House's contact page and comments line are from
  // general knowledge (whitehouse.gov wasn't read by program); not checked by the owner.
  executive: { the: "the President", The: "The President", office: "The White House", title: "President", dear: "Dear Mr. President," },
  // Steps that aren't news on a watchlist card.
  routine: /^(Introduced in the|Received in the|Referred to the Subcommittee|Read the (first|second) time|Read twice|Held at the desk|Placed on|(Sub)?[Cc]ommittee Consideration and Mark-up|Forwarded by Subcommittee|.*Hearings held|The Clerk was authorized|Rule H\. Res\. \d+ passed|See also|Senate ordered measure printed|By Senator .* filed written report|The Speaker named|Conference held|Conferees agreed|Presented to the President$|Became (Public|Private) Law \d+-\d+$)/,
  // The converter writes the steps the shared code reads in capitals ("PASSED HOUSE: On motion to suspend the rules
  // ...", "FAILED IN THE SENATE: ...", "SIGNED BY THE PRESIDENT"); the page says them plainly.
  actionWords(t, d, acts, short) {
    let m = t.match(/^PASSED (HOUSE|SENATE)(?:: (.*))?$/);
    if (m) return `Passed the ${m[1][0] + m[1].slice(1).toLowerCase()}` + (short || !m[2] ? "" : `: ${m[2].replace(/^Passed (?:House|Senate) /, "")}`);
    m = t.match(/^FAILED IN THE (HOUSE|SENATE)(?:: (.*))?$/);
    if (m) return `Failed in the ${m[1][0] + m[1].slice(1).toLowerCase()}` + (short || !m[2] ? "" : `: ${m[2]}`);
    if (t === "SIGNED BY THE PRESIDENT") return "Signed by the President";
    if (/^VETOED by the President/.test(t)) return t.replace(/^VETOED/, "Vetoed");
    // In a bill's row, a committee's report in a few words ("Approved by the Commerce Committee, with changes"); the
    // full line ("... Reported by Senator Cruz with an amendment in the nature of a substitute. With written report No.
    // 119-161.") is under "Every action".
    if (short) {
      const comm = (n) => n.split(",")[0].replace(/^the /, "");
      const changed = (x) => (/with an amendment|with amendments|in the nature of a substitute|\(Amended\)/.test(x) ? ", with changes" : "");
      m = t.match(/^Committee on ([^.]+?)\. (?:Ordered to be )?[Rr]eported\b(.*)$/);
      if (m) return `Approved by the ${comm(m[1])} Committee${changed(m[2])}`;
      m = t.match(/^Reported( \(Amended\))? by the Committee on ([^.]+?)\./);
      if (m) return `Approved by the ${comm(m[2])} Committee${changed(m[1] || "")}`;
      m = t.match(/^Ordered to be Reported( \(Amended\))?/);
      if (m) return `Committee voted to approve it${changed(m[1] || "")}`;
    }
    return null;
  },
  publicSite: "https://statebilltracker.org/us/",
  listsApi: "https://state-lists.lists-worker.workers.dev",
  houses: { S: "Senate", H: "House" },
  // The picture at the top of How (tracker.html's renderHowPic()): how bills move ("twins": the same bill filed in
  // both houses moves in each until both pass the same text; "relay": one bill goes house to house), what a bill the
  // governor doesn't sign does ("law" or "dies" lines, each with an optional ⓘ tip), and who can override a veto.
  tracks: "relay",
  unsigned: [{ law: "Not signed in 10 days: becomes law", tip: "Sundays excepted." }, { dies: "Not signed when Congress adjourns: pocket veto", tip: "If Congress adjourns before the 10 days are up, so the President can't send a veto back, the bill dies, with no veto to override. In practice that means the end of a session: during shorter breaks, Congress names someone to receive vetoes." }],
  override: "Two-thirds can override",
  titles: { S: "Sen.", H: "Rep." },
  memberWords: { S: "senator", H: "representative" },
  greetings: { S: "Senator", H: "Representative" },
  // A page is a two-year Congress: 2025–26 is the 119th.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  congress: (s) => (s - 1789) / 2 + 1,
  govReach: `<a href="https://www.whitehouse.gov/contact/" target="_blank" rel="noopener" data-contact="online|governor">Contact the White House</a>`,  // no phone: the comments line, (202) 456-1111, closes at times (the 2025 shutdown) and whitehouse.gov lists only the form
  lawWord: "Public Law",

  // Seats: the Senate's by state (both senators), the House's by district ("California's 12th"), with their names from
  // data/us/district_names.json.
  distPhrase: (h, d, name) => (h === "S" ? `${name || "the state"} (both senators)` : name ? `${name} District` : ""),
  seatText: (h, d, name) => (h === "S" ? `Senator from ${name || "?"}` : name ? `Representative for ${/at large|delegate|Commissioner/.test(name) ? name : `${name} District`}` : ""),
  // "Where you live": the state first, then the place (about 35,000 cities, towns, communities and counties).
  townRegions: true,
  regionWord: "State",
  townWord: "Place",
  addressLookup: true,
  lookupWhere: "the United States",
  // The Census geocoder's "119th Congressional Districts" layer: GEOID "0612" is California's 12th ("00" at large, "98"
  // a delegate).
  lookupDistricts(g) {
    const k = Object.keys(g).find((x) => /Congressional Districts/.test(x));
    const cd = k && g[k][0];
    if (!cd || !/^\d{4}$/.test(cd.GEOID || "")) return [null, null];
    const fips = +cd.GEOID.slice(0, 2), d = +cd.GEOID.slice(2);
    const region = DATA.towns?.find((t) => t[3].some(([x]) => Math.floor(x / 100) === fips))?.[1];
    return [fips, fips * 100 + (d === 98 ? 0 : d), region];
  },
  findReps: "https://www.house.gov/representatives/find-your-representative",

  // Constitutional amendments are joint resolutions: two-thirds of each house, then three-fourths of the states. They
  // don't go to the President (Article V).
  amendments: true,
  amendmentOnce: true,
  amendmentVote: "two-thirds of each house",
  amendmentDone: "Sent to the states",
  ballotLine: () => "Next: the states. Three-fourths of them (38) have to ratify it, usually within seven years.",

  // The bill's page on congress.gov (its actions, text, cosponsors and the Congressional Research Service's summary).
  billUrl(p, s) {
    const ses = s || (typeof DATA !== "undefined" ? DATA.session : 2025);
    const kind = { HR: "house-bill", S: "senate-bill", HJRES: "house-joint-resolution", SJRES: "senate-joint-resolution" }[String(p).match(/^[A-Z]+/)[0]];
    const c = (ses - 1789) / 2 + 1;
    return `https://www.congress.gov/bill/${c}th-congress/${kind}/${String(p).replace(/^[A-Z]+/, "")}`;
  },
  textLinks(b) {
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => {
      const u = v.link || STATE.billUrl(v.p, DATA.session);
      return `${link(u, `${esc(v.p.replace(/^([A-Z]+)/, "$1 "))} on congress.gov`)} · ${link(`${u}/text`, "Text")} · ${link(`${u}/all-actions`, "All actions")}`;
    }).join("<br>");
  },

  // A Congress meets from January 3 of an odd year to January 3 two years later (the 20th Amendment), in two sessions;
  // there's no fixed adjournment and no deadline for passing bills. Bills that don't become law die when it ends.
  opens: (year) => `${year % 2 ? year : year + 1}-01-03`,
  sessionEnds: (session) => `${session + 2}-01-03`,
  plusDays(iso, n) {
    const [y, m, d] = iso.split("-").map(Number), t = new Date(y, m - 1, d + n);
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
  },
  election(year) {
    const t = new Date(year, 10, 1); t.setDate(1 + ((1 - t.getDay() + 7) % 7) + 1);
    return `${year}-11-${String(t.getDate()).padStart(2, "0")}`;
  },
  floorVotesEnd: false,
  // The President has 10 days, Sundays excepted, after a bill is presented (Article I, section 7). A bill not returned
  // becomes law without the signature, unless Congress has adjourned so that it can't be returned: a pocket veto.
  govDeadline(iso) {
    if (!iso) return null;
    let d = iso, n = 0;
    while (n < 10) { d = STATE.plusDays(d, 1); if (new Date(`${d}T12:00`).getDay() !== 0) n++; }
    return d;
  },
  dueLabel: () => "President's decision due (10 days, Sundays excepted)",

  passedBothBy: (session) => `${session + 2}-01-03`,
  passedBothNote: (live) => live ? "Waiting to be presented to the President" : "Never presented to the President",
  passedBothGroup: ["Waiting to be presented", () => "A bill that passed both houses is enrolled, signed by the Speaker and the President of the Senate, and presented to the President, usually within days or weeks; the President then has 10 days, Sundays excepted."],
  passedBothNext: () => ({
    what: "it's enrolled and presented to the President, who has 10 days (Sundays excepted) to sign it or veto it. A bill the President doesn't return becomes law without a signature, unless Congress has adjourned and can't receive a veto, which makes it a pocket veto. Overriding a veto takes two-thirds of each house.",
    gov: ["sign it", "veto it"],
    reps: ["urge the President to sign it", "urge the President to veto it"],
  }),
  oneNumber: true,
  diesAfterFloor: () => "It died when this Congress ended.",
  outOfTimeLine: "Died when the Congress ended",

  // Committees in Congress rarely vote a bill down: most bills are never taken up.
  heldLabel: "Never taken up",
  heldTip: "Congressional committees rarely vote a bill down: most bills are simply never taken up. Only about one in ten is reported to the floor.",
  heldNote: "a bill its committee never reported. Committees in Congress rarely vote bills down.",
  // A bill whose text went into another (it passed as part of that one), or one that failed on the floor and wasn't
  // passed later.
  endedNote(b) {
    const acts = b.vers.flatMap((v) => v.actions), texts = acts.map(([, t]) => t);
    const into = texts.findLastIndex((t) => /^Its text went into /.test(t));
    if (into >= 0 && b.stage < 3) {
      const host = texts[into].match(/went into (\S+?),/)[1];
      return { status: `Passed as part of ${host}`, when: `${texts[into]}.`, tail: "" };
    }
    const i = texts.findLastIndex((t) => /^FAILED IN THE (HOUSE|SENATE)/.test(t));
    if (i < 0 || texts.slice(i + 1).some((t) => /^PASSED |agreed to/.test(t))) return null;
    const H = texts[i].match(/(HOUSE|SENATE)/)[1], h = H[0] + H.slice(1).toLowerCase();
    return {
      status: b.stage === 2 && b.passedIn !== h ? `Passed the ${b.passedIn}; voted down in the ${h}` : `Voted down in the ${h}`,
      when: `Failed in the ${h} on ${fmtDate(acts[i][0])}${/2\/3 required|suspend the rules/.test(texts[i]) ? ", where it needed two-thirds under suspension of the rules" : ""}.`,
      tail: /suspend the rules/.test(texts[i]) ? "A bill that fails under suspension can come back under a rule, which needs only a majority." : "",
    };
  },
  voteWhat: (v) => (v.kind === "F" && v.committee ? `${STATE.houses[v.house]} ${esc(v.committee[0].toLowerCase() + v.committee.slice(1))}` : ""),

  committeeNext: {},
  chairAsks: {},

  // The note above the bill list: from the election to the end of the Congress.
  sessionNotice(raw) {
    const t = isoToday(), y = raw.session, end = `${y + 2}-01-03`, el = STATE.election(y + 1);
    const n = (y - 1789) / 2 + 1;
    if (t >= el && t < end) return `The ${n}th Congress ends ${fmtDate(end)}. Bills that haven't become law by then die; the ${n + 1}th Congress, elected ${fmtDate(el)}, starts over with new bills.`;
    if (t >= end) return `The ${n}th Congress ended ${fmtDate(end)}. Bills that didn't become law died then.`;
    return "";
  },
  upcomingNotice: (raw, cur) => `The ${(raw.session - 1789) / 2 + 1}th Congress convenes ${fmtDate(`${raw.session}-01-03`)}.${cur?.url ? ` <a href="${esc(cur.url)}">Back to the ${span(LATEST)} Congress</a>` : ""}`,

  // The two-year calendar: two sessions, the August recess, the election.
  calendarDays: 30,
  calendar(Y) {
    const LEG = 112, el = STATE.election(Y + 1), end = `${Y + 2}-01-03`;
    const MDt = (iso) => new Date(`${iso}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" });
    return {
      leg: [["", `${Y}-01-03`, `${Y}-07-31`, "First session"], ["light", `${Y}-08-01`, `${Y}-09-05`, "August recess"], ["", `${Y}-09-06`, `${Y}-12-31`, "First session"],
        ["", `${Y + 1}-01-03`, `${Y + 1}-07-31`, "Second session"], ["light", `${Y + 1}-08-01`, `${Y + 1}-09-08`, "August recess"], ["", `${Y + 1}-09-09`, `${Y + 1}-10-15`, "Second session"],
        ["light", `${Y + 1}-10-16`, el, "Campaign recess"], ["", STATE.plusDays(el, 1), end, "Lame duck"]],
      gov: [["light", `${Y}-01-03`, end, "Acts on bills as they're presented"]],
      events: [
        [`${Y}-01-03`, "up", LEG, MDt(`${Y}-01-03`), "The new Congress convenes. Every bill starts over with a new number."],
        [`${Y}-10-01`, "down", LEG, MDt(`${Y}-10-01`), "The federal fiscal year begins: appropriations bills, or a stopgap, are due."],
        [`${Y + 1}-01-03`, "up", LEG, MDt(`${Y + 1}-01-03`), "The second session convenes. Bills carry over from the first."],
        [el, "up", LEG, MDt(el), "Election day: all 435 House seats and a third of the Senate."],
        [end, "down", LEG, MDt(end), "The Congress ends. Bills that haven't become law die."],
      ],
      note: "The President has 10 days (Sundays excepted) to act once a bill is presented.",
    };
  },
  waitingHead: "Waiting for the President",
  govYearsNote: "",
  partySource: "Party from public records of members of Congress",
  openUntil: (s) => `the ${(s - 1789) / 2 + 1}th Congress ends on January 3, ${s + 2}`,

  commIntro: [
    ["Most bills go to a committee and stay there.", "A committee or its subcommittee holds hearings, marks the bill up (amends it) and votes to report it. The House often refers a bill to several committees; each has to report it or be discharged. Fewer than one bill in ten is reported."],
    ["Then the leaders decide which bills reach the floor.", "In the House the Speaker and the majority leader schedule bills, most of them under \"suspension of the rules\" (no amendments, two-thirds of those voting), the rest under a rule from the Rules Committee. In the Senate the majority leader moves to take a bill up; most pass by unanimous consent, and others need 60 votes to end debate (cloture)."],
  ],
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the President's desk", "Became law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses, waiting to be presented", "On the President's desk", "Became law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "President's desk", "Became law", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the President", "Became law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses, never presented", "Sent to the President, no action recorded", "Became law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Became law", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. Most bills never leave one.",
    "Reported by its committees (or discharged from them) and on a calendar, waiting for the leaders to bring it to the floor.",
    "Passed the House or the Senate, but not both. If the second house changes it, the first has to agree, or a conference committee works out one version.",
    "Passed both houses in the same form. It's enrolled and presented to the President.",
    "Presented to the President, who has 10 days (Sundays excepted) to sign or veto it.",
    "Signed by the President, became law without the signature, or became law over a veto.",
    "Vetoed by the President. Overriding takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never reported by its committee before the Congress ended.",
    "Reported by its committee, but never passed by the full house.",
    "Passed the House or the Senate, but not both.",
    "Passed both houses, but never presented to the President.",
    "Presented to the President; no signature or veto is recorded.",
  ],
  outOfTime: "This Congress is over. Bills that didn't become law have to be introduced again in the next one, with new numbers.",

  // Each Senate committee's House counterpart and the subject it's shown under (the 119th Congress's names).
  commPairs: {
    "Finance": ["Ways and Means", "Taxes, trade, Medicare and Social Security"],
    "Agriculture, Nutrition, and Forestry": ["Agriculture", "Agriculture"],
    "Banking, Housing, and Urban Affairs": ["Financial Services", "Banking and housing"],
    "Commerce, Science, and Transportation": ["Energy and Commerce", "Commerce"],
    "Energy and Natural Resources": ["Natural Resources", "Energy and public lands"],
    "Environment and Public Works": ["Transportation and Infrastructure", "Infrastructure and the environment"],
    "Health, Education, Labor, and Pensions": ["Education and Workforce", "Education and labor"],
    "Homeland Security and Governmental Affairs": ["Homeland Security", "Homeland security"],
    "Foreign Relations": ["Foreign Affairs", "Foreign affairs"],
    "Rules and Administration": ["House Administration", "Elections and Congress's own business"],
  },
  commNotes: {
    "Appropriations": "The Appropriations committees write the twelve yearly spending bills, due before the fiscal year starts October 1; when they're late, Congress passes a stopgap \"continuing resolution\".",
    "Rules": "The House Rules Committee writes the rule under which a bill is debated and amended on the floor: it's the Speaker's gatekeeper.",
    "Finance": "Senate Finance handles taxes, trade, Medicare, Medicaid and Social Security; in the House, Ways and Means has most of these and Energy and Commerce has health.",
  },
  moneyCommittees: { S: "Appropriations", H: "Appropriations" },
  secondCommittee: "Bills that touch several subjects are often sent to several House committees at once.",
};
