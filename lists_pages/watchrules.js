// The watchlist's deadline rules, in one copy: each state's page (build_data.py puts this file in it, just before the
// state's profile) and /your-bills/ (build_site.sh puts it inside the page) group starred bills with them.
// WatchRules.make(S, facts, hooks) answers the rules for one session of one state:
//   S: the state's profile (its STATE object: govDeadline, passedBothBy, sessionEnds, originDeadline, floorVotesEnd,
//     passedBothGroup, originWord, years).
//   facts(): the session's facts, read each time a rule runs: {session, current, upcoming, lastVote (the last floor vote's
//     day), lastComm (the last or next committee vote or scheduled meeting's day), sessionEnd ({year: the scheduled last session day}), timing (past sessions' [{lastVote}])}.
//   hooks: {today() (ISO date), nextMeeting(b) (the next committee meeting with the bill on its agenda, {when, committee},
//     or null), isAmendment(b), toVoters(b), passedBothLc ("passed both houses")}.
// A bill (b) here needs stage and due (the governor's deadline, stage 4), plus whatever the state's originDeadline() reads
// (topics, vers, budget: the page's own bill, or /your-bills/'s stand-in for one).
const WatchRules = (() => {
  const SOON_DAYS = 14;
  const localToday = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
  const monthDay = (d) => new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "long", day: "numeric" });
  const shortDay = (d) => new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  // The groups, in order; the "year" group's name and note are the state's (S.passedBothGroup).
  const ORDER = ["soon", "session", "year", "later"];
  function make(S, facts, hooks = {}) {
    const today = hooks.today || localToday;
    const YEARS = S.years || 2;
    const lastYear = (s) => s + YEARS - 1;
    const daysUntil = (d) => (new Date(d.slice(0, 10)) - new Date(today())) / 864e5;
    // This year's scheduled last session day (data/session_calendar.json), or when past sessions ended.
    function sessionEnd() {
      const F = facts();
      // States whose Legislature meets until the session's last day: bills die only then.
      if (S.floorVotesEnd === false) return { date: S.sessionEnds(F.session), last: true };
      const y = today().slice(0, 4), date = F.sessionEnd?.[y];
      if (date) return { date };
      const past = (F.timing || []).map((t) => t.lastVote.slice(5)).sort();
      return past.length ? { from: `${y}-${past[0]}`, to: `${y}-${past[past.length - 1]}` } : {};
    }
    // True once the current session's second year has had no floor votes for three weeks.
    function floorVotesOver() {
      // States whose Legislature meets until the session's last day: over once that day has passed (Texas, Montana,
      // Nevada and North Dakota between their odd-year sessions; California after August 31 of its second year).
      const F = facts();
      if (!F.current) return false;
      if (S.floorVotesEnd === false) return !F.upcoming && today() > S.sessionEnds(F.session);
      const lv = F.lastVote || "", t = today();
      return lv.startsWith(String(lastYear(F.session))) && (new Date(t) - new Date(lv)) / 864e5 > 21;
    }
    // Where the session stands for a bill: {today, y2 (the session's last year), lv (the last floor vote), quiet (no floor
    // votes for three weeks), adjourned (the session is over), recess (between a two-year session's years), missed (the
    // day of the deadline to pass its own house it missed)}.
    // (Quiet only when committees haven't met for three weeks either, and none is scheduled to: New Jersey's committees
    // meet in November and December with no floor votes.)
    function standing(b) {
      const F = facts(), t = today(), y2 = lastYear(F.session);
      const lv = F.lastVote || "", lc = F.lastComm || "";
      const quiet = !!lv && (new Date(t) - new Date(lv)) / 864e5 > 21 && !(lc && (new Date(t) - new Date(lc.slice(0, 10))) / 864e5 <= 21);
      const adjourned = S.floorVotesEnd === false ? t > S.sessionEnds(F.session)
        : t > `${y2}-12-31` || (quiet && lv.startsWith(String(y2)));
      const recess = !adjourned && quiet && t.startsWith(String(F.session));
      // A state's deadline for passing a bill's own house (Virginia's crossover), once it has gone by.
      const origin = !adjourned && b.stage <= 1 && F.current && S.originDeadline?.(b);
      const missed = origin && t > origin ? origin : null;
      return { today: t, y2, lv, quiet, adjourned, recess, missed };
    }
    // Whether anything can move on the bill before the session ends (s: standing(b); ended: the bill ended before the
    // session did, a floor defeat or a withdrawal, as the state's page reads its history).
    const live = (s, ended) => !!(s.recess || (!(ended && !s.adjourned) && !s.missed && !s.adjourned));
    // Whether there's something to ask for on it now (the watchlist's "Needs action"; else "Can't move right now" or
    // "Decided"). vetoLive: a veto the Legislature can still override (Nevada's); votersDone: the voters have decided it.
    const canAct = (b, isLive, vetoLive, votersDone) => (b.stage <= 4 || !!vetoLive) && (isLive || b.stage >= 3) && !votersDone;
    // The deadline a bill faces: {g: its group, d: the day, origin: the deadline to pass its own house}.
    function deadlineOf(b) {
      const F = facts();
      const soon = (d) => daysUntil(d) <= SOON_DAYS;
      if (b.stage === 4 && b.due) return { g: "soon", d: b.due };
      const meet = hooks.nextMeeting?.(b);
      if (meet && soon(meet.when)) return { g: "soon", d: meet.when.slice(0, 10) };
      if (b.stage === 3 && (hooks.isAmendment?.(b) || hooks.toVoters?.(b))) return { g: "later" };
      if (b.stage === 3) {
        const end = S.passedBothBy(F.session);
        return { g: soon(end) ? "soon" : "year", d: end };  // (in a two-year session's first year too: the date is real)
      }
      // A state's deadline for passing a bill's own house (Virginia's crossover).
      const origin = b.stage <= 1 && S.originDeadline?.(b);
      if (origin && daysUntil(origin) >= 0) return { g: soon(origin) ? "soon" : "session", d: origin, origin: true };
      if (b.stage <= 2 && !floorVotesOver()) {
        const e = sessionEnd();
        return { g: e.date && daysUntil(e.date) >= 0 && soon(e.date) ? "soon" : "session", d: e.date };
      }
      return { g: "later" };
    }
    // What a watchlist card adds after the bill's status: " · due Dec 1, 2026", " · session ends Jun 4, 2026".
    // (fmt: the page's way of writing a day.)
    function dueText(b, dl, fmt = shortDay) {
      if (!facts().current || !dl.d) return "";
      if (b.stage === 4) return ` · due ${fmt(dl.d)}`;
      const fl = dl.g === "soon" && hooks.nextMeeting?.(b);
      if (dl.g === "soon" && b.stage < 3) return ` · ${dl.origin ? S.originWord || "deadline to pass its house" : dl.d === sessionEnd().date ? "session ends"
        : fl?.kind === "floor" && fl.when.slice(0, 10) === dl.d ? (fl.note === "listed" ? "on the calendar" : "floor vote") : "meets"} ${fmt(dl.d)}`;
      return "";
    }
    // Each group's name and its note.
    const groups = {
      soon: ["Due soon", () => "A vote, hearing or deadline is coming up."],
      session: ["By the end of the session", () => {
        const e = sessionEnd(), then = e.last || today().startsWith(String(lastYear(facts().session)))
          ? `Bills that haven't ${hooks.passedBothLc || "passed both houses"} by then die.` : "After that, nothing moves until January.";
        if (e.last) return `The session ends ${monthDay(e.date)}, ${e.date.slice(0, 4)}. ${then}`;
        if (e.date && daysUntil(e.date) >= 0) return `The session is scheduled to end ${monthDay(e.date)}. ${then}`;
        if (e.date) return `The session was scheduled to end ${monthDay(e.date)}; it could end any day. ${then}`;
        return e.from ? `The session usually ends between ${monthDay(e.from)} and ${monthDay(e.to)}. ${then}` : then;
      }],
      year: S.passedBothGroup,
      later: ["No deadline yet", () => "Nothing is due soon on these."],
    };
    return { daysUntil, sessionEnd, floorVotesOver, standing, live, canAct, deadlineOf, dueText, groups, lastYear };
  }
  // The next committee meeting with the bill on its agenda ([{when, committee, kind, note}]), in the current session (or
  // floor day: kind "floor", the house as committee, "Senate floor").
  // (stage: the bill's; a floor day counts only while it still needs a floor vote, stage 2 or less.)
  function nextMeeting(agenda, current, stage) {
    if (!current || !agenda || !agenda.length) return null;
    // A meeting with a time counts until 6 hours after it starts; a day with no time (California's and New York's
    // calendars, "T00:00:00") counts all that day (it vanished from the morning of the vote).
    const now = new Date(Date.now() - 6 * 36e5).toISOString().slice(0, 16), day = localToday();
    const ahead = (w) => (w.slice(11, 16) === "00:00" ? w.slice(0, 10) >= day : w >= now);
    return agenda.filter((a) => ahead(a.when) && !(a.kind === "floor" && stage > 2)).sort((x, y) => (x.when < y.when ? -1 : 1))[0] || null;
  }
  return { make, nextMeeting, SOON_DAYS, monthDay, shortDay, ORDER, localToday };
})();
