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
    // (What it shows is in its address, set when its turn comes: pump(); a group list's notes and a list's maker go with
    // the first message.)
    Object.assign(el, { _f: f, _q: g.extra ? [ask(g)] : [], _ready: false, _page: g.page, _sig: sig(g), _code: g.code, _ask: ask(g), _src: `${g.page}#embed=${g.code}`, _on: false });
    wrap.querySelector(".eload").hidden = false;
    wrap.appendChild(f);
    ALL.add(el);
  }
  // Frames from this site share one thread with the page, so two states' pages starting at once both take twice as long:
  // one frame starts at a time, the first card on the page first, each once the one before shows its bills (or after 20
  // seconds), and only frames in view (a tab not shown waits until it's shown: pump() again).
  let BUSY = null, TIMER = 0;
  function pump() {
    if (BUSY && (!BUSY.isConnected || !BUSY._f || BUSY._done)) BUSY = null;
    if (BUSY) return;
    const next = [...document.querySelectorAll(".sgrp")].find((el) => el._f && !el._on && el.offsetParent !== null);
    if (!next) return;
    next._on = true;
    next._f.src = next._src;
    BUSY = next;
    clearTimeout(TIMER);
    TIMER = setTimeout(() => { if (BUSY === next) { BUSY = null; pump(); } }, 20000);
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
    pump();
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
    if (e.data.done) { el._f.classList.remove("stale"); el.querySelector(".eload").hidden = true; if (!el._done) { el._done = true; pump(); } }
  });
  // The watchlists changed (a star in another frame or page): every frame shows its bills again, but the one in use.
  function refresh() { for (const el of ALL) if (el._ready && el._f !== document.activeElement) tell(el, el._ask); }
  // The session's page for a state's bills ("/nj/", "/va/2024.html"), from the status index; null when it isn't known.
  async function pageOf(st, session) {
    const ix = (await statusIndex())?.[st]?.[session];
    return ix ? `/${st}/${ix.p && ix.p !== "./" ? ix.p : ""}` : null;
  }
  return { show, pageOf, refresh, pump };
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

// One bill opened in place, below its row: the same card its state's watchlist shows, drawn by the state's page in a frame
// (tracker.html's EMBED, one bill: #embed=<session>, then {sbtShow: "2026.-A1234"}, "-" for an opposed bill). One frame per
// state's session page, loaded when one of its rows is first pointed at, touched, reached with the keyboard or opened, and
// moved under whichever of its bills is open (moveBefore keeps it loaded; without it, the frame is laid over the row's
// slot). Pointing at a row also starts that bill's details downloading ({sbtWarm}). The frame says how tall it is and which
// bill it shows ({sbtEmbed, bill}); it's shown once it shows the bill asked for. One bill per session page is open at a time.
// Opener.wire(box): rows in box are <button class="rowbtn" data-open="<id>" aria-controls="emb-<id>" aria-expanded="false">
// with a <div class="emb" id="emb-<id>" hidden> after them; Opener.row(id, {st, session, page, full, stance, href, name})
// says what each opens. Before a box is drawn again, Opener.parkAll() puts the frames away and answers the open rows' ids;
// Opener.reopen(ids) opens them again once it's drawn.
const Opener = (() => {
  const FRAMES = {};   // a session's page ("/nj/") -> {f (the frame), ready, q (messages until it's ready), row (open row's id), bill, h}
  const ROWS = new Map(), OPEN = new Set(), WARMED = new Set();
  const MOVES = !!Element.prototype.moveBefore;   // (a frame moved with appendChild would load again)
  let HOLD = null, N = 0;
  function hold() {
    if (!HOLD) { HOLD = document.createElement("div"); HOLD.id = "frames"; }
    if (!HOLD.isConnected) (document.querySelector("main") || document.body).appendChild(HOLD);
    return HOLD;
  }
  function frameFor(x) {
    if (FRAMES[x.page]) return FRAMES[x.page];
    const f = document.createElement("iframe");
    f.className = "sframe stale";
    f.id = `oframe${N++}`;
    f.title = `${stName(x.st)}: a bill`;
    f.src = `${x.page}#embed=${x.session}`;
    hold().appendChild(f);
    return (FRAMES[x.page] = { f, ready: false, q: [], row: null, bill: "", h: 0 });
  }
  function tell(F, msg) { if (F.ready) F.f.contentWindow?.postMessage(msg, location.origin); else F.q.push(msg); }
  const btnOf = (id) => document.querySelector(`button.rowbtn[data-open="${CSS.escape(id)}"]`);
  const boxOf = (id) => document.getElementById(`emb-${id}`);
  // (mine: one of this browser's own stars, shown as the person's own card, with their side and their action log.)
  const ask = (x) => ({ sbtShow: `${x.session}.${x.stance === "oppose" ? "-" : ""}${baseNum(x.full)}`, ...(x.mine ? { mine: true } : {}) });
  function park(F) {
    F.row = null;
    F.f.classList.remove("over");
    F.f.classList.add("stale");
    if (F.f.parentElement !== hold()) MOVES ? hold().moveBefore(F.f, null) : hold().appendChild(F.f);
  }
  function close(id) {
    OPEN.delete(id);
    btnOf(id)?.setAttribute("aria-expanded", "false");
    const box = boxOf(id);
    if (box) box.hidden = true;
    for (const F of Object.values(FRAMES)) if (F.row === id) park(F);
    place();
  }
  function warm(id) {
    const x = ROWS.get(id);
    if (!x || !x.page || WARMED.has(id)) return;
    WARMED.add(id);
    tell(frameFor(x), { sbtWarm: baseNum(x.full) });
  }
  function open(id) {
    const x = ROWS.get(id), btn = btnOf(id), box = boxOf(id);
    if (!x || !x.page || !btn || !box) return;
    const F = frameFor(x);
    if (F.row != null && F.row !== id) close(F.row);
    OPEN.add(id);
    btn.setAttribute("aria-expanded", "true");
    box.hidden = false;
    if (!box.firstChild) {
      box.innerHTML = `<p class="eload">Loading…</p><div class="slot"></div>`
        + `<p class="efoot"><a href="${esc(x.href)}">Open ${esc(x.name)} on ${x.st === "us" ? "the Congress page" : `${esc(stName(x.st))}'s page`}</a></p>`;
    }
    box.querySelector(".eload").hidden = false;
    const slot = box.querySelector(".slot");
    // The same bill open again after the rows were drawn again (parkAll(), reopen()): shown as it was, not loaded again.
    const same = F.keep && F.keep.id === id && F.keep.bill === baseNum(x.full) && F.keep.shown && F.keep.h;
    F.row = id; F.bill = baseNum(x.full); F.h = same ? F.keep.h : 0;
    F.keep = null;
    F.f.title = `${x.name}: what to do, and more about it`;
    F.f.classList.toggle("stale", !same);
    F.f.style.height = `${F.h}px`; slot.style.height = "";
    if (MOVES) slot.moveBefore(F.f, null);
    else { slot.setAttribute("aria-owns", F.f.id); F.f.classList.add("over"); }
    if (same) box.querySelector(".eload").hidden = true;
    else tell(F, ask(x));
    place();
  }
  const toggle = (id) => (btnOf(id)?.getAttribute("aria-expanded") === "true" ? close(id) : open(id));
  // Without moveBefore the frames stay in their holder, laid over their row's slot.
  function place() {
    if (MOVES || !HOLD) return;
    const m = (HOLD.offsetParent || document.body).getBoundingClientRect();
    for (const F of Object.values(FRAMES)) {
      if (F.row == null) continue;
      const slot = boxOf(F.row)?.querySelector(".slot");
      if (!slot) continue;
      slot.style.height = `${F.h}px`;
      const r = slot.getBoundingClientRect();
      Object.assign(F.f.style, { top: `${r.top - m.top}px`, left: `${r.left - m.left}px`, width: `${r.width}px` });
    }
  }
  addEventListener("resize", place);
  if (!MOVES && window.ResizeObserver) new ResizeObserver(place).observe(document.body);
  addEventListener("message", (e) => {
    if (e.origin !== location.origin) return;
    const F = Object.values(FRAMES).find((x) => x.f.contentWindow === e.source);
    if (!F) return;
    if (e.data?.sbtReady) {
      // (Ready again: the frame moved to another session's page, or loaded again; asked again for its bill.)
      const again = F.ready;
      F.ready = true;
      for (const m of F.q.splice(0)) tell(F, m);
      if (again && F.row != null && ROWS.get(F.row)) tell(F, ask(ROWS.get(F.row)));
      return;
    }
    if (typeof e.data?.sbtMultiAns === "string") { const done = ASKED.get(e.data.sbtMultiAns); ASKED.delete(e.data.sbtMultiAns); done?.(e.data.lines || []); return; }
    if (typeof e.data?.sbtEmbed !== "number" || F.row == null || e.data.bill !== F.bill) return;
    F.h = Math.max(40, Math.min(e.data.sbtEmbed, 20000));
    F.f.style.height = `${F.h}px`;
    F.f.classList.remove("stale");
    const wait = boxOf(F.row)?.querySelector(".eload");
    if (wait) wait.hidden = true;
    place();
  });
  function wire(box, onOpen) {
    if (box._opener) return;
    box._opener = true;
    box.addEventListener("click", (e) => {
      const b = e.target.closest("button.rowbtn[data-open]");
      if (!b) return;
      const was = b.getAttribute("aria-expanded") === "true";
      toggle(b.dataset.open);
      if (!was) onOpen?.(b.dataset.open);
    });
    const warmAt = (e) => { const b = e.target.closest?.("button.rowbtn[data-open]"); if (b) warm(b.dataset.open); };
    for (const ev of ["pointerover", "focusin", "touchstart"]) box.addEventListener(ev, warmAt, { passive: true });
  }
  const row = (id, x) => ROWS.set(id, x);
  function parkAll() {
    const ids = [...OPEN];
    for (const F of Object.values(FRAMES)) if (F.row != null) { F.keep = { id: F.row, bill: F.bill, h: F.h, shown: !F.f.classList.contains("stale") }; park(F); }
    OPEN.clear();
    return ids;
  }
  function reopen(ids) { for (const id of ids) if (btnOf(id) && ROWS.get(id)) open(id); }
  // Several bills of one state's session that need the same person: the state's page works out whom to ask and the email
  // (tracker.html's embedMulti()). x: {st, session, page}; code: "2025.list.A1.-S2"; mine: this browser's own stars.
  // Answers [{g, n, who, label, text, nums}] ([] after 60 seconds without an answer); each question is asked once a page.
  const ASKED = new Map(), MULTI = new Map();
  function multi(x, code, mine) {
    const k = `${x.page}|${code}|${mine ? 1 : 0}`;
    if (MULTI.has(k)) return MULTI.get(k);
    const id = `m${N++}`;
    const p = new Promise((done) => {
      ASKED.set(id, done);
      setTimeout(() => { if (ASKED.has(id)) { ASKED.delete(id); MULTI.delete(k); done([]); } }, 60000);
    });
    MULTI.set(k, p);
    tell(frameFor(x), { sbtMulti: id, code, ...(mine ? { mine: true } : {}) });
    return p;
  }
  return { wire, row, open, close, parkAll, reopen, place, multi };
})();
