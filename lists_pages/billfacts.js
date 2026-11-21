// Where a bill is, in words, in one copy. Every view that names a bill's status uses BillFacts.words(): each state's page
// (its Bills rows, opened panels and Watchlist tab: build_data.py puts this file in the page beside watchrules.js) works
// it out in the browser from the bill; the build works it out the same way (lists_pages/billlabels.js runs this file in
// Node over every bill) and writes it into the status rows, the issue files and the search files, which the front page,
// the issue pages, /your-bills/, /list/ and the list editor show as written. So a bill reads the same everywhere.
//   BillFacts.make(S, opt): the readings that need a bill's history, for one session of one state (S: its profile; opt:
//     {WR (watchrules.js's rules), facts() ({session, current, upcoming}), today(), fmtDate(d)}): .factsOf(b) gives the
//     facts words() reads, and the page's own helpers (endedOf, isAmendment, secondPassage, toVoters, votersDone,
//     ballotLine, continuedTo, billsDied, gateBack).
//   BillFacts.words(S, f): the status words from those facts.
//   BillFacts.nextStep(S, f): what comes next for an amendment or a measure sent to the voters (the watchlist's "due" line).
//   BillFacts.newsDay(actions, routine): the latest day with an action that isn't paperwork; isNew(seen, day): "New".
//   BillFacts.hash(num): which piece or shard holds a bill (FNV-1a of its number without the version letter; build_data.py's
//     shard_of() is the same, and test/hash_check.py checks the two agree).
//   BillFacts.runProfile(src, session, F): a state's profile.js run outside its page (/your-bills/, the build).
const BillFacts = (() => {
  const commPlain = (n) => (n || "").replace(/ And /g, " and ").replace(/ Committee$/, "");
  const BALLOT_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December";
  // FNV-1a, 32 bits, of the number without its amendment letter ("S1234A" and "S1234" land together).
  function hash(num) {
    let h = 0x811c9dc5;
    for (const c of String(num).replace(/[A-Z]$/, "")) h = Math.imul(h ^ c.charCodeAt(0), 0x01000193) >>> 0;
    return h;
  }
  function make(S, opt) {
    const F = () => opt.facts();
    const today = () => opt.today();
    const fmtDate = (d) => (opt.fmtDate ? opt.fmtDate(d) : d || "");
    const acts = (b) => (b.vers || []).flatMap((v) => v.actions || []);
    // A constitutional amendment that doesn't go to the governor (S.amendments: New York's concurrent resolutions): it
    // passes two separately elected Legislatures (or once, S.amendmentOnce), then the voters. Elsewhere "Constitutional
    // amendments" is just a topic (Virginia's are bills setting up the ballot question, which the governor signs).
    const isAmendment = (b) => !!S.amendments && (b.topics || []).includes("const");
    // A bill the Legislature refers to the voters (Colorado's TABOR questions): it passes both houses and goes on the
    // ballot, not to the governor. The converter marks it `ballot`.
    const toVoters = (b) => !!b.ballot && !isAmendment(b);
    // Its second passage: the version in the session two years earlier passed both houses (or the state decides it per
    // bill, S.amendmentFinal; or one passage is enough, S.amendmentOnce).
    const secondPassage = (b) => (S.amendmentFinal ? !!S.amendmentFinal(b) : !!S.amendmentOnce || (b.earlier || []).some((e) => e[0] === F().session - 2 && e[2] >= 3));
    // After its second passage it goes on the ballot in November: that year's if it passed by July, else the next year's.
    function ballotLine(b) {
      if (S.ballotLine) return S.ballotLine(b);
      const d = [b.dates?.passS, b.dates?.passA].filter(Boolean).sort().pop() || "";
      let y = S.ballotYear ? S.ballotYear(d) : +d.slice(0, 4) + (d.slice(5, 7) > "07" ? 1 : 0);
      if (S.ballotEvenYears && y % 2) y++;
      return today() > `${y}-11-10` ? `It went to the voters in November ${y}. The result isn't shown here.` : `Next: the voters, in November ${y}.`;
    }
    // An amendment (or a measure referred to the voters) whose election has passed: "Went to the voters (November 2025)".
    function votersDone(b) {
      if (b.stage !== 3 || S.amendmentDone || !((isAmendment(b) && secondPassage(b)) || toVoters(b))) return "";
      const line = ballotLine(b);
      if (!/^It went to the voters/.test(line)) return "";
      const m = line.match(new RegExp(`(${BALLOT_MONTHS}) (\\d{4})`));
      return m ? `Went to the voters (${m[1]} ${m[2]})` : "Went to the voters";
    }
    // A bill kept over to the next session (Virginia's continued bills, New Hampshire's retained ones).
    const continuedTo = (b) => S.continuedTo?.(b) || null;
    // How a bill ended before the session did: the state's own reading (S.endedNote: North Dakota's floor defeats,
    // Mississippi's deadlines), or a committee step that ends it (S.heldAction: Massachusetts's study orders).
    function endedOf(b) {
      const own = b.stage <= 2 && S.endedNote?.(b);
      if (own) return own;
      if (b.stage !== 0 || !S.heldAction) return null;
      const held = (x) => (S.heldAction instanceof RegExp ? S.heldAction.test(x) : x === S.heldAction);
      const hit = acts(b).filter(([, x]) => held(x)).pop();
      if (!hit) return null;
      const where = b.comm ? ` by the ${commPlain(b.comm)} Committee` : "";
      return { status: `${S.heldLabel}${where}`, when: `${S.heldLabel}${where}, ${fmtDate(hit[0])}.`, tail: S.heldTip || "" };
    }
    // True once the current session is over and its unpassed bills have died with it (Texas between its odd-year
    // sessions, Virginia after its spring session); not New York's, which can still move until December 31. A state
    // whose bills die only later keeps New York's wording until that day: out of time, but not dead yet.
    const billsDied = () => opt.WR.floorVotesOver() && (S.floorVotesEnd === false || (!!S.diesAfterFloor
      && (/\bdied\b/.test(S.diesAfterFloor(opt.WR.lastYear(F().session))) || !S.sessionEnds || today() > S.sessionEnds(F().session))));
    // Illinois: back in Rules or Assignments after a committee approved it means it missed a deadline: {ok (the
    // approval), back (the referral back)}, or null.
    function gateBack(b) {
      const gv = S.gates && (b.vers || []).find((v) => v.committee === b.comm && S.gates[v.p[0]] === b.comm);
      if (!gv) return null;
      const a = gv.actions, back = a.map(([, x]) => x).lastIndexOf(`REFERRED TO ${(b.comm || "").toUpperCase()}`);
      const ok = a.slice(0, Math.max(back, 0)).filter(([, x]) => x === "REPORTED").pop();
      return ok ? { ok, back: a[back] } : null;
    }
    // The facts words() reads (each step can fail on a profile hook that needs the page: then it's left out).
    function factsOf(b) {
      const f = F(), x = { stage: b.stage, comm: b.comm || "", current: !!f.current, up: !!f.upcoming, passedIn: b.passedIn || "",
        exec: S.executive?.the || "the governor" };
      const tryIt = (fn, d) => { try { return fn(); } catch (e) { return d; } };
      x.alive = x.current && !tryIt(billsDied, false);
      x.carried = b.stage <= 2 ? tryIt(() => continuedTo(b), null) || "" : "";
      const own = b.stage <= 2 && tryIt(() => S.endedNote?.(b), null);
      const ended = own || (b.stage <= 2 ? tryIt(() => endedOf(b), null) : null);
      // (A bill carried over isn't ended by a committee step; a state's own reading still wins.)
      x.ended = own ? own.status : ended && !(b.stage === 0 && x.carried && !x.alive) ? ended.status : "";
      x.stops = !!ended;  // (it can't move again this session: the watchlist's "Out of time")
      x.gate = b.stage === 0 && !x.ended && !!tryIt(() => gateBack(b), null);
      x.amend = isAmendment(b);
      x.ballot = toVoters(b);
      x.second = x.amend && b.stage === 3 && tryIt(() => secondPassage(b), false);
      x.voted = b.stage === 3 ? tryIt(() => votersDone(b), "") : "";
      return x;
    }
    return { factsOf, isAmendment, toVoters, secondPassage, ballotLine, votersDone, continuedTo, endedOf, billsDied, gateBack, commPlain };
  }
  // The status words. f: factsOf()'s, or the same fields from a status row.
  function words(S, f) {
    const T = S.stageText || {}, PB = S.passedBothText || "Passed both houses";
    const k = f.stage;
    const set = (f.up ? T.prefiled : null) || (k <= 2 ? (f.alive ? T.live : T.final) : f.current ? T.live : T.final) || T.live || {};
    const long = (i) => (set.long || [])[i] || ["In committee", "Awaiting a floor vote", "Passed one house", PB, "", "Became law", "Vetoed"][i];
    if (k === 0 && f.up) return (T.prefiled?.long || [])[0] || "Prefiled";
    if (k <= 2 && f.ended) return f.ended;
    if (k === 0) {
      const c = f.comm ? ` in the ${commPlain(f.comm)} Committee` : "";
      if (!f.alive && f.carried) return `Carried over to ${f.carried}${c}`;
      if (f.gate) return f.alive ? `Sent back to ${f.comm}` : `Died in the ${f.comm} Committee`;
      return `${f.alive ? "In" : "Died in"} ${f.comm ? `the ${commPlain(f.comm)} Committee` : "committee"}`;
    }
    if (k === 1) return long(1);
    if (k === 2) return f.passedIn ? `Passed one house${f.alive || f.carried ? "" : " only"} (${f.passedIn})` : long(2);
    if (k === 3) {
      if (f.voted) return f.voted;
      if (f.amend && f.second && S.amendmentDone) return S.amendmentDone;
      // A constitutional amendment that needs two passages, with only the first done (New York: the next Legislature votes again).
      if (f.amend && !f.second) return "Passed the first of two rounds";
      if (f.amend || f.ballot) return `${PB}; goes to the voters`;
      return PB;
    }
    if (k === 4) return f.current ? `On ${f.exec}'s desk` : `Sent to ${f.exec}`;
    if (k === 5) return "Became law";
    if (k === 6) return "Vetoed";
    return "";
  }
  // What comes next for a bill that passed both houses but isn't the governor's: the voters, or a second passage.
  function nextStep(S, f) {
    if (f.ballot) return "Goes to the voters";
    if (!f.amend || f.stage !== 3) return "";
    return f.second ? S.amendmentDone || "Goes to the voters" : `Must pass again${S.amendmentAgain ? "" : " in the next Legislature"}`;
  }
  // "New since you last looked": an action after the day last seen that isn't paperwork (a new print number, the "sent
  // to the other house" that comes with a pass; the state's own list, S.routine, else New York's).
  const ROUTINE = /^(PRINT NUMBER|INTRODUCED|DELIVERED TO (SENATE|ASSEMBLY)|RETURNED TO (SENATE|ASSEMBLY)|\d+(ST|ND) REPORT CAL|\d+RD READING CAL)/;
  const newsDay = (actions, routine = ROUTINE) => (actions || []).reduce((m, [d, t]) => (d > m && !routine.test(t) ? d : m), "");
  const isNew = (seen, day) => !!day && day > (seen || "");
  // A state's profile run in its own scope, with the page helpers it uses (its STATE reads DATA.session for the session).
  // F: the session's facts ({c: current, u: upcoming}).
  function runProfile(src, session, F) {
    let S = null;
    const iso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
    const DATA = { session, current: !!F.c, upcoming: !!F.u };
    const fmtDate = (d) => (d ? new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
    const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const lastYear = (s) => s + ((S && S.years) || 2) - 1;
    const span = (s) => (S && S.sessionLabel ? S.sessionLabel(s) : String(s));
    const monthDay = (d) => new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "long", day: "numeric" });
    try {
      S = new Function("fmtDate", "esc", "isoToday", "lastYear", "span", "monthDay", "DATA", "BILLS", `${src}\n;return STATE;`)(
        fmtDate, esc, iso, lastYear, span, monthDay, DATA, []);
    } catch (e) { return null; }
    return S;
  }
  // A bill's progress as the six steps every bill row shows (five in a one-house legislature: no "passed one house"),
  // filled up to its stage, in the colors of its status label (lists_pages/rows.css's .pips). Nebraska is the one
  // legislature with one house (oneHouse(), for the pages that show several states; a state's page reads its profile).
  const oneHouse = (st) => st === "ne";
  // (more: other classes, "mini" for the compact rows, "over" for a bill out of time. now: the row's status label, and
  // st the state's code, for the hover tip naming the steps: "In committee → ... → Law; now: Passed Senate". The pips
  // stay aria-hidden: the label beside them says the same to a screen reader.)
  const steps = (uni, st) => [...(uni ? ["In committee", "On the floor", "Passed"] : ["In committee", "On the floor", "Passed one house", "Passed both houses"]),
    st === "us" ? "President" : "Governor", "Law"];
  const pipTip = (uni, st, now) => `${steps(uni, st).join(" → ")}${now ? `; now: ${now}` : ""}`;
  function pips(stage, uni, more, now, st) {
    const n = uni ? 5 : 6, k = +stage || 0, filled = k >= 5 ? n : uni && k >= 3 ? k : k + 1;
    let out = "";
    for (let i = 0; i < n; i++) out += i < filled ? '<i class="on"></i>' : "<i></i>";
    const tip = String(pipTip(uni, st, now)).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    return `<span class="pips s${k}${uni ? " uni" : ""}${more ? ` ${more}` : ""}" aria-hidden="true" title="${tip}">${out}</span>`;
  }
  return { make, words, nextStep, newsDay, isNew, ROUTINE, hash, runProfile, commPlain, pips, pipTip, oneHouse };
})();
if (typeof module !== "undefined") module.exports = BillFacts;
