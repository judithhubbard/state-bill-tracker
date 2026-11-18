// A list's bills on /list/ and /your-bills/ (lists_pages/; build_site.sh puts it inside each page after common.js), shown
// by each state's own page: its watchlist view (the same cards, groups and order, each card opening in place), in a frame
// per state's session at #embed=<what> (tracker.html's EMBED: "2026.list.A1234.-S12" for a list's bills, "-" opposed;
// "2026.mine" for this browser's own watchlist), with the page's header, tabs and footer hidden. The frame loads only what
// the watchlist needs and says how tall it is ({sbtEmbed, bill: what it shows, done}), so it fits; it's shown once it shows
// what was asked. A list that changes is sent to its frame ({sbtShow: what, notes, group, own}) without loading it again.
// Frames.show(box, groups) draws a container's groups, each a state's card: {key (unique on the page), head (the card's
// heading HTML, or ""), page ("/nj/", the session's page; none: no frame), code (what it shows), extra ({notes, group}: a
// group list's notes; {own: slug}: a list made in this browser, whose cards then set its stances and remove its bills),
// rest (HTML below the frame: bills not in the state's data), title (the frame's name)}. Cards already drawn are kept with
// their frames (drawn again with the same key, they aren't loaded again).
const Frames = (() => {
  const ALL = new Set();   // the groups' elements with a frame
  const MOVES = !!Element.prototype.moveBefore;   // (a frame moved with insertBefore would load again)
  const sig = (g) => JSON.stringify([g.code, g.extra || null]);
  const ask = (g) => ({ sbtShow: g.code, ...(g.extra || {}) });
  function tell(el, msg) { if (el._ready) el._f.contentWindow?.postMessage(msg, location.origin); else el._q.push(msg); }
  function make(g) {
    const el = document.createElement("div");
    el.className = "mst sgrp";
    el.dataset.key = g.key;
    el.innerHTML = `<div class="ghead"></div><div class="fwrap" hidden><p class="eload">Loading…</p></div><ol class="rest"></ol>`;
    return el;
  }
  function frameIn(el, g) {
    const wrap = el.querySelector(".fwrap");
    if (!g.page) {
      if (el._f) { el._f.remove(); el._f = null; ALL.delete(el); }
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    if (el._f && el._page === g.page) {
      if (sig(g) !== el._sig) { el._sig = sig(g); el._code = g.code; el._ask = ask(g); tell(el, el._ask); }
      return;
    }
    el._f?.remove();
    const f = document.createElement("iframe");
    f.className = "sframe stale";
    f.title = g.title || "Bills";
    f.loading = "lazy";
    f.src = `${g.page}#embed=${g.code}`;
    // (What it shows is in its address; a group list's notes and a list's maker go with the first message.)
    Object.assign(el, { _f: f, _q: g.extra ? [ask(g)] : [], _ready: false, _page: g.page, _sig: sig(g), _code: g.code, _ask: ask(g) });
    wrap.querySelector(".eload").hidden = false;
    wrap.appendChild(f);
    ALL.add(el);
  }
  function show(box, groups) {
    const have = new Map([...box.querySelectorAll(":scope > .sgrp")].map((el) => [el.dataset.key, el]));
    const want = new Set(groups.map((g) => g.key));
    for (const [k, el] of have) if (!want.has(k)) { ALL.delete(el); el.remove(); have.delete(k); }
    for (const x of [...box.children]) if (!x.classList.contains("sgrp")) x.remove();
    let at = box.firstElementChild;
    for (const g of groups) {
      let el = have.get(g.key);
      if (!el) { el = make(g); box.insertBefore(el, at); }
      else if (el !== at) MOVES ? box.moveBefore(el, at) : box.insertBefore(el, at);
      at = el.nextElementSibling;
      const head = el.querySelector(".ghead"), rest = el.querySelector(".rest");
      if (head._html !== (g.head || "")) { head.innerHTML = g.head || ""; head._html = g.head || ""; }
      if (rest._html !== (g.rest || "")) { rest.innerHTML = g.rest || ""; rest._html = g.rest || ""; }
      head.hidden = !g.head; rest.hidden = !g.rest;
      frameIn(el, g);
    }
  }
  addEventListener("message", (e) => {
    if (e.origin !== location.origin) return;
    const el = [...ALL].find((x) => x._f?.contentWindow === e.source);
    if (!el) return;
    if (e.data?.sbtReady) {
      // (Ready again: the frame was loaded again, and is asked again what it shows.)
      const again = el._ready;
      el._ready = true;
      for (const m of el._q.splice(0)) tell(el, m);
      if (again) tell(el, el._ask);
      return;
    }
    if (typeof e.data?.sbtEmbed !== "number" || e.data.bill !== el._code) return;
    el._f.style.height = `${Math.max(0, Math.min(e.data.sbtEmbed, 50000))}px`;
    if (e.data.done) { el._f.classList.remove("stale"); el.querySelector(".eload").hidden = true; }
  });
  // The watchlists changed (a star in another frame or page): every frame shows its bills again, but the one in use.
  function refresh() { for (const el of ALL) if (el._ready && el._f !== document.activeElement) tell(el, el._ask); }
  // The session's page for a state's bills ("/nj/", "/va/2024.html"), from the status index; null when it isn't known.
  async function pageOf(st, session) {
    const ix = (await statusIndex())?.[st]?.[session];
    return ix ? `/${st}/${ix.p && ix.p !== "./" ? ix.p : ""}` : null;
  }
  return { show, pageOf, refresh };
})();
// A list's bills ([{st, session, num, stance}], in the list's order) as one #embed= code per state's session:
// [{st, session, code, bills}] ("-": opposed), each state's sessions newest first, states by name.
function listCodes(bills) {
  const by = new Map();
  for (const b of bills) {
    const k = `${b.st}:${b.session}`;
    if (!by.has(k)) by.set(k, { st: b.st, session: b.session, bills: [] });
    by.get(k).bills.push(b);
  }
  return [...by.values()].sort((a, b) => stName(a.st).localeCompare(stName(b.st)) || b.session - a.session)
    .map((g) => ({ ...g, code: `${g.session}.list.${g.bills.map((b) => (b.stance === "oppose" ? "-" : "") + baseNum(b.num)).join(".")}` }));
}
// A list's groups for Frames.show(): a card per state's session, its bills shown by the state's page; bills its data
// doesn't have (rows: lookUp()'s answers, once known) listed below as links. key: the tab's id; opt: {heads (always a
// heading), wl (its Watchlist link), code(g) (what the frame shows, else the list's bills), extra(g), row(x) (a row's extras)}.
async function listGroups(key, bills, rows, opt = {}) {
  const codes = listCodes(bills), many = codes.length > 1 || opt.heads;
  const twice = new Set(codes.filter((g, i) => codes.findIndex((h) => h.st === g.st) !== i).map((g) => g.st));
  return Promise.all(codes.map(async (g) => {
    const missing = rows ? rows.filter((x) => x.st === g.st && x.session === g.session && !x.found) : [];
    const page = rows && missing.length === g.bills.length ? null : await Frames.pageOf(g.st, g.session) || rows?.find((x) => x.st === g.st && x.session === g.session && x.found)?.page || null;
    const name = `${esc(stName(g.st))}${twice.has(g.st) ? ` <small>(${g.session})</small>` : ""}`;
    return { key: `${key}|${g.st}:${g.session}`, page, code: opt.code ? opt.code(g) : g.code, extra: opt.extra?.(g) || null,
      head: many ? `<h3><a href="/${g.st}/">${name}</a>${opt.wl ? `<a class="wl" href="/${g.st}/watchlist/">Watchlist ›</a>` : ""}</h3>` : "",
      rest: missing.map((x) => billRow({ ...x, ...(opt.row?.(x) || {}) })).join(""), title: `${stName(g.st)}: the list's bills` };
  }));
}
