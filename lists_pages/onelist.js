// One list of bills from any number of states and sessions (/your-bills/'s tabs; build_site.sh puts it inside the page
// after common.js, embed.js and watchrules.js), sorted across states by what's due first: Due soon, Before the session
// ends, a later deadline (bills that passed both houses), No deadline yet, then Decided or ended. Each bill's group and
// deadline come from the same rules its state's watchlist uses (watchrules.js), run with the state's own profile
// (data/v/profile.<hash>.js, named in /status.json as each session's f.s) and the session's facts (/status.json's f) and
// the bill's status row (common.js's statusOf(): build_data.py's write_status()). A tapped row opens the bill's card in
// place (embed.js's Opener).
// OneList.items(bills) answers each bill ({st, session, num, stance, note?, entry?}) with what the row shows;
// OneList.draw(box, items, opt) draws them. Rows drawn last are kept in this browser (abt:yourbills:rows) so the page can
// show them at once next time (OneList.cached()).
const OneList = (() => {
  const ORDER = ["soon", "session", "year", "later", "done"];
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
  // The profile run in its own scope, with the page helpers it uses (its STATE reads DATA.session for the session).
  function runProfile(src, session, F) {
    let S = null;
    const DATA = { session, current: F.c, upcoming: F.u };
    const fmtDate = (d) => (d ? WatchRules.shortDay(d) : "");
    const escH = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const lastYear = (s) => s + ((S && S.years) || 2) - 1;
    const span = (s) => (S && S.sessionLabel ? S.sessionLabel(s) : String(s));
    try {
      S = new Function("fmtDate", "esc", "isoToday", "lastYear", "span", "monthDay", "DATA", "BILLS", `${src}\n;return STATE;`)(
        fmtDate, escH, iso, lastYear, span, WatchRules.monthDay, DATA, []);
    } catch (e) { return null; }
    return S;
  }
  // The rules for one state's session: {S (its profile), WR (watchrules.js), F (the facts)}, or null.
  async function rulesFor(st, session) {
    const k = `${st}/${session}`;
    if (k in RULES) return RULES[k];
    return (RULES[k] = (async () => {
      const f = (await statusIndex())?.[st]?.[session]?.f, src = f && (await profileText(st));
      if (!src) return null;
      const S = runProfile(src, +session, f);
      if (!S) return null;
      const F = { session: +session, current: !!f.c, upcoming: !!f.u, lastVote: f.v || "", sessionEnd: f.e || {}, timing: (f.t || []).map((v) => ({ lastVote: v })) };
      const lc = (S.passedBothText || "Passed both houses").replace(/^./, (c) => c.toLowerCase());
      const WR = WatchRules.make(S, () => F, { today: iso, nextMeeting: (b) => WatchRules.nextMeeting(b.agenda, F.current),
        isAmendment: (b) => !!S.amendments && b.topics.includes("const"), toVoters: (b) => !!b.ballot && !(S.amendments && b.topics.includes("const")), passedBothLc: lc });
      return { S, WR, F };
    })());
  }
  const sessionText = (R, session) => { try { return R?.S?.sessionLabel ? R.S.sessionLabel(+session) : String(session); } catch (e) { return String(session); } };
  // A day as a row shows it: "Dec 1", with the year when it isn't this one.
  const day = (d) => { const t = new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)); return t.toLocaleDateString("en-US", { month: "short", day: "numeric", ...(d.slice(0, 4) === iso().slice(0, 4) ? {} : { year: "numeric" }) }); };
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
    const [full, title, stage, last, action, comm, kind, deliv, meets, flags, later] = r;
    const page = `/${b.st}/${s.page && s.page !== "./" ? s.page : ""}`, up = !!(ix?.f?.u ?? +b.session > THIS_YEAR);
    Object.assign(x, { found: true, full, title: cut(title), stage, last, action, page, href: `${page}#${full}`,
      label: whereText(b.st, stage, comm, kind, s.live !== false, up) });
    if (later && Array.isArray(later)) {
      const lp = named?.[later[0]]?.p;
      x.later = [later[0], later[1], sessionText(R, later[0]), `/${b.st}/${lp && lp !== "./" ? lp : ""}`];
    }
    const exec = b.st === "us" ? "President" : "Governor";
    if (stage >= 5 || !R || !R.F.current) return { ...x, group: stage >= 5 || (R && !R.F.current) ? "done" : "later" };
    // Prefiled bills (a session not begun): nothing is due yet, as their state's watchlist shows them.
    if (R.F.upcoming) return { ...x, group: "later" };
    const { S, WR } = R;
    const bill = { stage, due: null, agenda: (meets || []).map(([when, committee]) => ({ when, committee })), topics: kind === "const" ? ["const"] : [],
      vers: [{ p: full, actions: [], statusDesc: "", committee: comm || "" }], nums: [full], budget: (flags || "").includes("b"), ballot: (flags || "").includes("v") };
    try {
      if (stage === 4) bill.due = S.govDeadline(deliv || null, +b.session);
      const live = WR.live(WR.standing(bill), false);
      if (!WR.canAct(bill, live, false, false)) return { ...x, group: "done", out: true };
      const dl = WR.deadlineOf(bill);
      x.group = dl.g; x.date = dl.d || "";
      const meet = WatchRules.nextMeeting(bill.agenda, true);
      if (dl.d) {
        if (stage === 4) x.due = `${exec} by ${day(dl.d)}`;
        else if (dl.origin) x.due = `Must pass its house by ${day(dl.d)}`;
        else if (dl.g === "year") x.due = `Due by ${day(dl.d)}`;
        else if (meet && dl.d === meet.when.slice(0, 10)) x.due = `Committee meets ${day(dl.d)}`;
        else if (dl.d === WR.sessionEnd().date) x.due = WR.daysUntil(dl.d) >= 0 ? `Session ends ${day(dl.d)}` : "Session could end any day";
      }
      if (dl.g === "year") x.yearGroup = S.passedBothGroup?.[0] || "";
      x.rules = R;
    } catch (e) { x.group = "later"; }
    return x;
  }
  async function items(bills) {
    const out = await Promise.all(bills.map(itemOf));
    keep(out);
    return out;
  }
  // ---- Kept in this browser, to show the rows at once next time ----
  const FIELDS = ["key", "st", "session", "num", "found", "gone", "full", "title", "stage", "label", "last", "action", "group", "date", "due", "out", "later", "sessionLabel", "old", "href", "page", "yearGroup"];
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
  // ---- Drawing ----
  const rank = (g) => { const i = ORDER.indexOf(g); return i < 0 ? 3 : i; };
  function sortIn(a, b) {
    if (a.group === "done" && b.group === "done") return String(b.last || "").localeCompare(String(a.last || "")) || stName(a.st).localeCompare(stName(b.st));
    return (a.date || "9999").localeCompare(b.date || "9999") || stName(a.st).localeCompare(stName(b.st)) || String(a.full).localeCompare(String(b.full), "en", { numeric: true });
  }
  const shown = (x) => numText(x.st, x.full || x.num);
  const nameOf = (x) => `${x.st === "us" ? "" : `${stName(x.st)} `}${shown(x)}`;
  // A star: in this browser's watchlist or not (data-star "st|session|number"; the page handles the click).
  function star(st, session, num, name) {
    const on = `${session}:${baseNum(num)}` in readWatch(st);
    return `<button type="button" class="star" data-star="${esc(`${st}|${session}|${baseNum(num)}`)}" aria-pressed="${on}" aria-label="${esc(`${on ? "Remove" : "Star"} ${name}`)}" title="${on ? "Remove from your bills" : "Star it"}">${on ? "★" : "☆"}</button>`;
  }
  const listBtn = (x) => (window.NamedLists?.ready() ? NamedLists.button(NamedLists.code(x.st, x.session, x.full || x.num), nameOf(x)) : "");
  // opt: {tab (an id for the rows' ids), byState, stance (show each bill's side), isNew(x), noteOf(x), onOpen(id), remove (a
  // Remove button on bills from sessions no longer on the site)}.
  function rowHtml(x, opt) {
    const id = `${opt.tab}-${x.key.replace(/[^\w]/g, "_")}`;
    const st = opt.byState ? "" : `<span class="stn" title="${esc(stName(x.st))}">${x.st === "us" ? "US" : x.st.toUpperCase()}</span>`;
    const yr = x.old || +x.session > THIS_YEAR ? ` <small>${esc(x.sessionLabel || x.session)}</small>` : "";
    const btns = `<span class="rbtns">${x.found ? listBtn(x) : ""}${x.gone ? "" : star(x.st, x.session, x.full || x.num, nameOf(x))}</span>`;
    if (x.gone) {
      return `<li class="brow gone" data-key="${esc(x.key)}"><div class="grow"><span class="num">${st}${esc(shown(x))}</span>`
        + `<span class="tt">${esc(x.sessionLabel || x.session)}: no longer on this site</span>`
        + (opt.remove ? `<button type="button" class="btn quiet small" data-remove="${esc(`${x.st}|${x.session}|${x.num}`)}">Remove</button>` : "") + "</div></li>";
    }
    const note = opt.noteOf?.(x);
    // (Support is shown where sides matter, a group's list; Oppose always.)
    const stance = x.stance && (opt.stance || x.stance === "oppose") ? `<span class="stance ${x.stance}">${x.stance === "oppose" ? "Oppose" : "Support"}</span>` : "";
    const news = opt.isNew?.(x) ? `<span class="what"><b>New:</b> ${esc(plainAct(x.action || ""))}${x.last ? ` (${fmtDay(x.last)})` : ""}</span>` : "";
    const where = `<span class="where">${stance}${x.found ? `<span class="stg s${x.stage}">${esc(x.label)}</span>` : ""}${x.due ? `<span class="dl">${esc(x.due)}</span>` : x.out ? '<span class="dl">Out of time this session</span>' : ""}`
      + `${!x.due && x.found && x.last && x.group === "done" ? `<span>${fmtDay(x.last)}</span>` : ""}<span class="todo">${x.found ? "Details" : "Open"}</span></span>`;
    const back = x.later && x.later[0] > x.session ? `<p class="again">Back in ${esc(x.later[2])} as <a href="${esc(x.later[3])}#${esc(x.later[1])}">${esc(numText(x.st, x.later[1]))}</a>`
      + `${star(x.st, x.later[0], x.later[1], `${nameOf({ ...x, full: x.later[1] })} (${x.later[2]})`).replace('class="star"', 'class="star inline"')}</p>` : "";
    if (!x.found) {
      return `<li class="brow" data-key="${esc(x.key)}"><a class="rowbtn" href="${esc(x.href || `/${x.st}/`)}"><span class="num">${st}${esc(shown(x))}${yr}</span>`
        + `<span class="tt">Not in ${esc(x.sessionLabel || x.session)}'s data</span>${where}</a>${btns}</li>`;
    }
    Opener.row(id, { st: x.st, session: x.session, page: x.page, full: x.full, stance: x.stance, href: x.href, name: nameOf(x) });
    return `<li class="brow" data-key="${esc(x.key)}"><button type="button" class="rowbtn" data-open="${esc(id)}" aria-controls="emb-${esc(id)}" aria-expanded="false">`
      + `<span class="num">${st}${esc(shown(x))}${yr}</span><span class="tt">${esc(x.title)}</span>${note ? `<span class="note">${esc(note)}</span>` : ""}${news}${where}</button>`
      + `${btns}${back}<div class="emb" id="emb-${esc(id)}" hidden></div></li>`;
  }
  // A group's heading: its name and, when it's one state's, that state's note on it.
  function groupHead(g, xs) {
    const one = xs.every((x) => x.rules && x.rules === xs[0].rules) ? xs[0].rules : null;
    const names = { soon: "Due soon", session: "Before the session ends", later: "No deadline yet", done: "Decided or ended" };
    const sts = new Set(xs.map((x) => x.st));
    let name = names[g], sub = "";
    if (g === "year") name = sts.size === 1 && xs[0].yearGroup ? xs[0].yearGroup : "Due later";
    try { if (one && g !== "done") sub = one.WR.groups[g]?.[1]?.() || ""; } catch (e) {}
    if (!sub && g === "soon") sub = "A vote, hearing or deadline is coming up.";
    return `<h2 class="ghd">${esc(name)} <span class="n">${xs.length}</span></h2>${sub ? `<p class="gsub">${esc(sub)}</p>` : ""}`;
  }
  function draw(box, list, opt) {
    const open = Opener.parkAll();
    Opener.wire(box, opt.onOpen);
    let html = "";
    if (opt.byState) {
      const by = new Map();
      for (const x of list) (by.get(x.st) || by.set(x.st, []).get(x.st)).push(x);
      html = [...by.keys()].sort((a, b) => stName(a).localeCompare(stName(b))).map((st) => {
        const xs = by.get(st).sort((a, b) => rank(a.group) - rank(b.group) || sortIn(a, b));
        return `<section class="mst"><h3><a href="/${st}/">${esc(stName(st))}</a><a class="wl" href="/${st}/watchlist/">Watchlist ›</a></h3><ol>${xs.map((x) => rowHtml(x, { ...opt, byState: true })).join("")}</ol></section>`;
      }).join("");
    } else {
      html = ORDER.map((g) => {
        const xs = list.filter((x) => (ORDER.includes(x.group) ? x.group : "later") === g).sort(sortIn);
        return xs.length ? `<section class="bgrp" data-g="${g}">${groupHead(g, xs)}<ol class="mst">${xs.map((x) => rowHtml(x, opt)).join("")}</ol></section>` : "";
      }).join("");
    }
    box.innerHTML = html;
    Opener.reopen(open);
  }
  return { items, cached, draw, rulesFor };
})();
