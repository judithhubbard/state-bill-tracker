// One list of bills from any number of states and sessions (/your-bills/'s tabs; build_site.sh puts it inside the page
// after common.js, embed.js, watchrules.js and watchrows.js), sorted across states by what's due first, in the same groups and
// order as each state's Watchlist tab (watchrows.js draws both). Each bill's group and
// deadline come from the same rules its state's watchlist uses (watchrules.js), run with the state's own profile
// (data/v/profile.<hash>.js, named in /status.json as each session's f.s) and the session's facts (/status.json's f) and
// the bill's status row (common.js's statusOf(): build_data.py's write_status()). A tapped row opens the bill's card in
// place (embed.js's Opener).
// OneList.items(bills) answers each bill ({st, session, num, stance, note?, entry?}) with what the row shows;
// OneList.draw(box, items, opt) draws them. Rows drawn last are kept in this browser (abt:yourbills:rows) so the page can
// show them at once next time (OneList.cached()).
const OneList = (() => {
  const CACHE = "abt:yourbills:rows";
  const SRC = {}, RULES = {};
  // A state's profile, as text (one file per state, whatever the session).
  async function profileText(st) {
    const ix = (await statusIndex())?.[st];
    const h = ix && Object.values(ix).map((x) => x.f?.s).find(Boolean);
    if (!h) return null;
    return (SRC[st] ||= fetch(`/${st}/data/v/profile.${h}.js`).then((r) => (r.ok ? r.text() : null)).catch(() => null));
  }
  const iso = WatchRules.localToday;
  // The rules for one state's session: {S (its profile), WR (watchrules.js), F (the facts)}, or null.
  async function rulesFor(st, session) {
    const k = `${st}/${session}`;
    if (k in RULES) return RULES[k];
    return (RULES[k] = (async () => {
      const f = (await statusIndex())?.[st]?.[session]?.f, src = f && (await profileText(st));
      if (!src) return null;
      const S = BillFacts.runProfile(src, +session, f);
      if (!S) return null;
      const F = { session: +session, current: !!f.c, upcoming: !!f.u, lastVote: f.v || "", lastComm: f.m || "", sessionEnd: f.e || {}, timing: (f.t || []).map((v) => ({ lastVote: v })) };
      const lc = (S.passedBothText || "Passed both houses").replace(/^./, (c) => c.toLowerCase());
      const WR = WatchRules.make(S, () => F, { today: iso, nextMeeting: (b) => WatchRules.nextMeeting(b.agenda, F.current),
        isAmendment: (b) => !!S.amendments && b.topics.includes("const"), toVoters: (b) => !!b.ballot && !(S.amendments && b.topics.includes("const")), passedBothLc: lc });
      return { S, WR, F };
    })());
  }
  const sessionText = (R, session) => { try { return R?.S?.sessionLabel ? R.S.sessionLabel(+session) : String(session); } catch (e) { return String(session); } };
  // Each bill with what its row shows: {key, id, found, gone (its session isn't on the site any more), full, title, stage,
  // label, last, action, group, date (its deadline, for sorting), due (the deadline as words), out (it can't move this
  // session), later ([session, number, label] where it's back), sessionLabel, old (from a session that isn't the newest),
  // href, page}.
  async function itemOf(b) {
    const key = crossKey(b.st, b.session, b.num), x = { ...b, key, num: baseNum(b.num) };
    const index = await statusIndex(), named = index?.[b.st], ix = named?.[b.session];
    const R = named ? await rulesFor(b.st, ix ? b.session : Object.keys(named).sort().pop()) : null;
    x.sessionLabel = sessionText(R, b.session);
    x.old = !!named && Object.keys(named).some((s) => +s > +b.session && !named[s].f?.u);
    if (named && !ix) return { ...x, found: false, gone: true, group: "done", full: x.num, title: "" };
    const s = await statusOf(b.st, b.session, x.num);
    const lead = s ? (s.bills[x.num] ? x.num : s.alias?.[x.num]) : null, r = lead && s.bills[lead];
    if (!r) return { ...x, found: false, gone: !s, group: "done", full: x.num, title: "", href: `/${b.st}/` };
    const { full, title, stage, last, action, comm, kind, deliv, meets, flags, later, label, news } = rowOf(r);
    const page = `/${b.st}/${s.page && s.page !== "./" ? s.page : ""}`, up = !!(ix?.f?.u ?? +b.session > THIS_YEAR);
    // (The status words and the day of the latest news, as the state's page has them: the build wrote them.)
    Object.assign(x, { found: true, full, title: cut(title), stage, last, action, page, href: `${page}#${full}`, label, news });
    if (later) {
      const lp = named?.[later[0]]?.p;
      x.later = [later[0], later[1], sessionText(R, later[0]), `/${b.st}/${lp && lp !== "./" ? lp : ""}`];
    }
    x.upcoming = up;
    if (stage >= 5 || !R) return { ...x, group: stage >= 5 ? "done" : "later" };
    const { S, WR } = R;
    x.rules = R;
    // The group and deadline, by the same rules (watchrows.js's place()) as the state's own Watchlist tab: a stand-in for
    // the state's bill, from the status row, with what only its history tells (worked out by the build, as the state's
    // page works it out: billfacts.js): it ended before the session did ("e"), a veto that can still be overridden ("r"),
    // the voters have decided it ("d"), an amendment ("a") on its second passage ("2").
    const has = (c) => flags.includes(c);
    const bill = { stage, due: null, agenda: meets.map(([when, committee]) => ({ when, committee })), topics: kind === "const" ? ["const"] : [],
      vers: [{ p: full, actions: [], statusDesc: "", committee: comm || "" }], nums: [full], budget: has("b"), ballot: has("v") };
    try {
      if (stage === 4 && R.F.current) bill.due = S.govDeadline(deliv || null, +b.session);
      const act = R.F.current && !R.F.upcoming && WR.canAct(bill, WR.live(WR.standing(bill), has("e")), has("r"), has("d"));
      const next = () => BillFacts.nextStep(S, { stage, amend: has("a"), second: has("2"), ballot: has("v") && !has("a") });
      Object.assign(x, WatchRows.place(bill, { S, WR, current: R.F.current, upcoming: R.F.upcoming, act, exec: S.executive?.title || "Governor", session: +b.session, next }));
    } catch (e) { x.group = "later"; }
    return x;
  }
  async function items(bills) {
    const out = await Promise.all(bills.map(itemOf));
    keep(out);
    return out;
  }
  // ---- Kept in this browser, to show the rows at once next time ----
  const FIELDS = ["key", "st", "session", "num", "found", "gone", "full", "title", "stage", "label", "last", "action", "group", "date", "due", "out", "later", "sessionLabel", "old", "upcoming", "href", "page", "yearGroup", "news"];
  function keep(list) {
    try {
      const o = JSON.parse(localStorage.getItem(CACHE) || "{}");
      for (const x of list) o[x.key] = Object.fromEntries(FIELDS.filter((k) => x[k] !== undefined).map((k) => [k, x[k]]));
      // (Only bills still starred or on a list here are worth keeping: at most a few hundred.)
      const keys = Object.keys(o);
      if (keys.length > 800) for (const k of keys.slice(0, keys.length - 800)) delete o[k];
      localStorage.setItem(CACHE, JSON.stringify(o));
    } catch (e) {}
  }
  // The rows kept from last time for these bills (those not kept are left out), or [].
  function cached(bills) {
    try {
      const o = JSON.parse(localStorage.getItem(CACHE) || "{}");
      return bills.map((b) => { const c = o[crossKey(b.st, b.session, b.num)]; return c && { ...c, ...b, key: c.key, num: c.num }; }).filter(Boolean);
    } catch (e) { return []; }
  }
  // ---- Drawing: watchrows.js's rows (the same as each state's Watchlist tab), each opening its card in place ----
  const shown = (x) => WatchRows.numText(x.st, x.full || x.num);
  const nameOf = (x) => `${x.st === "us" ? "" : `${stName(x.st)} `}${shown(x)}`;
  // A star: in this browser's watchlist or not (data-star "st|session|number"; the page handles the click).
  function star(st, session, num, name) {
    const on = `${session}:${baseNum(num)}` in readWatch(st);
    return `<button type="button" class="star" data-star="${esc(`${st}|${session}|${baseNum(num)}`)}" aria-pressed="${on}" aria-label="${esc(`${on ? "Remove" : "Add"} ${name} ${on ? "from" : "to"} your watchlist`)}" title="${on ? "Remove from your watchlist" : "Add to your watchlist"}">${on ? "★" : "☆"}</button>`;
  }
  // opt: watchrows.js's (tab, byState, stance, isNew, noteOf, remove), onOpen(id, x), and mine (the bills are this
  // browser's own stars: their cards are its own, with its side and its action log).
  function draw(box, list, opt) {
    const open = Opener.parkAll();
    const byId = new Map();
    box._onOpen = opt.onOpen;
    Opener.wire(box, (id) => box._onOpen?.(id, box._rows?.get(id)));
    const rows = list.map((x) => (x.later && x.later[0] > x.session
      ? { ...x, laterStar: star(x.st, x.later[0], x.later[1], `${nameOf({ ...x, full: x.later[1] })} (${x.later[2]})`).replace('class="star"', 'class="star inline"') } : x));
    WatchRows.draw(box, rows, { ...opt, stName, newText: (x) => `${x.action || ""}${x.news ? ` (${fmtDay(x.news)})` : ""}`,
      buttons: (x) => star(x.st, x.session, x.full || x.num, nameOf(x)),  // (the list button is in the opened card)
      onRow: (id, x) => { byId.set(id, x); Opener.row(id, { st: x.st, session: x.session, page: x.page, full: x.full, stance: x.stance, href: x.href, name: nameOf(x), mine: !!opt.mine }); } });
    box._rows = byId;
    Opener.reopen(open);
  }
  // The bills in the order the list shows them.
  const ordered = (list) => WatchRows.ordered(list, stName);
  return { items, cached, draw, rulesFor, ordered };
})();
