// Named lists from any bill row (public site only): a small list button beside a bill's star opens a menu of the lists
// made in this browser with the list editor (/lists/edit/), checked where the bill is on them, and "New list…". Shared by
// the states' pages (build_data.py puts it in each public page), the front page and the list editor (build_site.sh), so
// the list format and the saving rules live in one place. One global name, NamedLists.
// The lists are common.js's NAMED: localStorage "abt:lists" = {slug: {slug, editKey, title, group, intro, notes, bills
// (codes "nj:2026:A1234", "-" in front to oppose, in the list's order), saved (the signature last saved), savedAt, updated}}.
// A change is kept in this browser at once and sent to the lists Worker a few seconds later, at least 10 seconds after the
// list's last save (the Worker refuses saves closer together); a save not sent yet goes out the next time a page with this
// script opens.
window.NamedLists = (() => {
  const KEY = "abt:lists", MAX = 500, GAP = 10500;
  const CROSS = /^(-?)([a-z]{2}):(\d{4}):([A-Z]{1,7}\d{1,6})$/;
  let API = "";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function read() { try { const o = JSON.parse(localStorage.getItem(KEY) || "{}"); return o && typeof o === "object" && !Array.isArray(o) ? o : {}; } catch (e) { return {}; } }
  function write(o) { try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} }
  // What the Worker keeps, and its signature (the editor's too).
  function payload(l) {
    const bills = (l.bills || []).filter((c) => CROSS.test(c)).slice(0, MAX);
    const keep = new Set(bills.map((c) => c.replace(/^-/, ""))), notes = {};
    if (l.group) for (const [k, v] of Object.entries(l.notes || {})) if (keep.has(k) && String(v).trim()) notes[k] = String(v).trim();
    return { state: "all", title: (l.title || "").trim(), bills, intro: l.group ? (l.intro || "").trim() : "", notes };
  }
  const sig = (p) => JSON.stringify([p.title, p.bills, p.intro, p.notes]);
  // A bill's code: state, session, number without its version letter.
  const code = (st, session, num) => `${st}:${session}:${String(num).replace(/[A-Z]$/, "")}`;
  const bare = (c) => c.replace(/^-/, "");
  // The lists this browser can change, newest first.
  const lists = () => Object.values(read()).filter((l) => l && l.slug && l.editKey && Array.isArray(l.bills))
    .sort((a, b) => String(b.updated || "").localeCompare(String(a.updated || "")));
  const onLists = (c) => lists().filter((l) => l.bills.some((x) => bare(x) === c));
  const ready = () => !!API && lists().length > 0;

  // ---- Saving ----
  const TIMERS = {};
  function schedule(slug, soon = 2500) {
    const l = read()[slug];
    if (!l || !API) return;
    clearTimeout(TIMERS[slug]); delete TIMERS[slug];
    if (sig(payload(l)) === l.saved) return;
    TIMERS[slug] = setTimeout(() => save(slug), Math.max(soon, (l.savedAt || 0) + GAP - Date.now()));
  }
  async function save(slug) {
    delete TIMERS[slug];
    const l = read()[slug];
    if (!l) return;
    const p = payload(l), s = sig(p);
    if (s === l.saved) return;
    let r;
    try {
      r = await fetch(`${API}/lists/${encodeURIComponent(slug)}`, { method: "PUT", headers: { "Content-Type": "application/json", "X-Edit-Key": l.editKey }, body: JSON.stringify(p) });
    } catch (e) { return void setTimeout(() => schedule(slug), 30e3); }
    const all = read(), now = all[slug];
    if (!now) return;
    if (r.ok) { now.saved = s; now.savedAt = Date.now(); write(all); schedule(slug); return; }
    // Saved a moment ago (from another page): again after the gap. Gone (deleted elsewhere): forgotten here.
    if (r.status === 429) { now.savedAt = Date.now(); write(all); return schedule(slug); }
    if (r.status === 404) { delete all[slug]; write(all); return refresh(); }
    setTimeout(() => schedule(slug), 60e3);
  }
  // Leaving with a save waiting: send it now (it stays marked unsaved if the Worker turns it away).
  function flush() {
    for (const slug of Object.keys(TIMERS)) {
      clearTimeout(TIMERS[slug]); delete TIMERS[slug];
      const l = read()[slug];
      if (!l || !API || Date.now() - (l.savedAt || 0) < GAP) continue;
      try { fetch(`${API}/lists/${encodeURIComponent(slug)}`, { method: "PUT", keepalive: true, headers: { "Content-Type": "application/json", "X-Edit-Key": l.editKey }, body: JSON.stringify(payload(l)) }); } catch (e) {}
    }
  }
  // Adds the bill to the list or takes it off; false when the list is full.
  function toggle(slug, c) {
    const all = read(), l = all[slug];
    if (!l) return false;
    const i = l.bills.findIndex((x) => bare(x) === c);
    if (i >= 0) l.bills.splice(i, 1);
    else if (l.bills.length >= MAX) return false;
    else l.bills.push(c);
    l.updated = new Date().toISOString();
    write(all);
    schedule(slug);
    return true;
  }

  // A bill on a list (c: its code without "-"): its side ("support", "oppose"), or off the list (null); false if it isn't on it.
  function edit(slug, c, stance) {
    const all = read(), l = all[slug];
    if (!l) return false;
    const i = l.bills.findIndex((x) => bare(x) === c);
    if (i < 0) return false;
    if (stance) l.bills[i] = (stance === "oppose" ? "-" : "") + c; else l.bills.splice(i, 1);
    l.updated = new Date().toISOString();
    write(all);
    schedule(slug);
    refresh(c);
    return true;
  }

  // ---- The button and its menu ----
  const ICON = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false"><rect class="nlbg" x="2" y="2.5" width="16" height="15" rx="3"/>'
    + '<path class="nlln" d="M6 7h8M6 10h8M6 13h5"/></svg>';
  function label(c, name, n) { return n ? `${name}: on ${n === 1 ? "one of your lists" : `${n} of your lists`}` : `Add ${name} to a list`; }
  // name: the bill as people read it ("NJ A 1234"), for the button's spoken name.
  function button(c, name) {
    if (!ready() || !CROSS.test(c)) return "";
    const n = onLists(c).length;
    return `<button type="button" class="nlbtn${n ? " on" : ""}" data-nl="${esc(c)}" data-nlname="${esc(name)}" aria-haspopup="true" aria-expanded="false"`
      + ` aria-label="${esc(label(c, name, n))}" title="${n ? "On your lists" : "Add to a list"}">${ICON}</button>`;
  }
  // Every button for a bill (or every bill) shown again with what the lists hold now.
  function refresh(c) {
    for (const b of document.querySelectorAll(c ? `.nlbtn[data-nl="${CSS.escape(c)}"]` : ".nlbtn[data-nl]")) {
      const n = onLists(b.dataset.nl).length;
      b.classList.toggle("on", n > 0);
      b.setAttribute("aria-label", label(b.dataset.nl, b.dataset.nlname, n));
      b.title = n ? "On your lists" : "Add to a list";
    }
  }
  let MENU = null, FROM = null;
  function close(refocus) {
    if (!MENU) return;
    MENU.remove(); MENU = null;
    if (FROM) { FROM.setAttribute("aria-expanded", "false"); if (refocus && FROM.isConnected) FROM.focus(); }
    FROM = null;
  }
  function items() { return [...MENU.querySelectorAll('[role^="menuitem"]')]; }
  function draw(c) {
    const ls = lists();
    MENU.innerHTML = `<p class="nlhead">Your lists</p>` + ls.map((l) => {
      const on = l.bills.some((x) => bare(x) === c);
      return `<button type="button" role="menuitemcheckbox" aria-checked="${on}" data-nlslug="${esc(l.slug)}" tabindex="-1"><span class="nlck" aria-hidden="true">${on ? "✓" : ""}</span><span class="nlt">${esc((l.title || "").trim() || "Untitled list")}</span><span class="nln">${l.bills.length}</span></button>`;
    }).join("") + `<a role="menuitem" tabindex="-1" href="/lists/edit/#new&amp;add=${encodeURIComponent(c)}">New list…</a>`;
  }
  function place() {
    const r = FROM.getBoundingClientRect(), w = MENU.offsetWidth, h = MENU.offsetHeight, vw = document.documentElement.clientWidth;
    let x = Math.min(Math.max(8, r.right - w), vw - w - 8), y = r.bottom + 4;
    if (y + h > innerHeight - 8 && r.top - h - 4 > 8) y = r.top - h - 4;
    MENU.style.left = `${Math.max(8, x)}px`; MENU.style.top = `${Math.max(8, y)}px`;
  }
  function open(btn) {
    close(false);
    FROM = btn;
    MENU = document.createElement("div");
    MENU.className = "nlmenu"; MENU.setAttribute("role", "menu"); MENU.setAttribute("aria-label", `Lists for ${btn.dataset.nlname}`);
    draw(btn.dataset.nl);
    document.body.appendChild(MENU);
    place();
    btn.setAttribute("aria-expanded", "true");
    items()[0]?.focus();
  }
  function onClick(e) {
    const btn = e.target.closest?.(".nlbtn[data-nl]");
    if (btn) { e.preventDefault(); e.stopPropagation(); return MENU && FROM === btn ? close(true) : open(btn); }
    if (!MENU) return;
    const it = e.target.closest?.("[data-nlslug]");
    if (it && MENU.contains(it)) {
      const c = FROM.dataset.nl;
      if (!toggle(it.dataset.nlslug, c)) return;
      const on = it.getAttribute("aria-checked") !== "true";
      it.setAttribute("aria-checked", String(on));
      it.querySelector(".nlck").textContent = on ? "✓" : "";
      const l = read()[it.dataset.nlslug];
      it.querySelector(".nln").textContent = l ? l.bills.length : "";
      refresh(c);
      return;
    }
    if (!MENU.contains(e.target)) close(false);
  }
  function onKey(e) {
    if (!MENU) return;
    const all = items(), i = all.indexOf(document.activeElement);
    if (e.key === "Escape") { e.preventDefault(); close(true); }
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); all[(i + (e.key === "ArrowDown" ? 1 : all.length - 1)) % all.length]?.focus(); }
    else if (e.key === "Home" || e.key === "End") { e.preventDefault(); all[e.key === "Home" ? 0 : all.length - 1]?.focus(); }
    else if (e.key === "Tab") close(false);
  }
  const STYLE = `.nlbtn { appearance: none; border: 0; background: none; padding: 2px; margin: 0; width: 26px; height: 26px; border-radius: 5px;
  color: var(--ink-2); cursor: pointer; display: inline-grid; place-items: center; line-height: 1; vertical-align: middle; }
.nlbtn svg .nlbg { fill: none; stroke: currentColor; stroke-width: 1.6; }
.nlbtn svg .nlln { fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; }
.nlbtn.on { color: var(--navy); }
.nlbtn.on svg .nlbg { fill: currentColor; }
.nlbtn.on svg .nlln { stroke: var(--sheet); }
.nlbtn:hover { color: var(--navy); background: var(--paper); }
.nlbtn:focus-visible { outline: 3px solid var(--hover, var(--focus, #3a6fd8)); outline-offset: 0; }
.nlmenu { position: fixed; z-index: 50; min-width: 200px; max-width: min(320px, calc(100vw - 16px)); max-height: min(360px, calc(100vh - 16px)); overflow-y: auto;
  background: var(--sheet); color: var(--ink); border: 1px solid var(--rule); border-radius: 8px; box-shadow: 0 6px 24px rgba(20, 33, 61, .18); padding: 4px 0; font: 14px/1.35 var(--body); }
.nlmenu .nlhead { margin: 0; padding: 6px 12px 4px; font-size: 12px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); }
.nlmenu > button, .nlmenu > a { display: grid; grid-template-columns: 16px minmax(0, 1fr) auto; gap: 8px; align-items: baseline; width: 100%; padding: 7px 12px;
  border: 0; background: none; color: var(--ink); font: inherit; text-align: left; text-decoration: none; cursor: pointer; }
.nlmenu > a { display: block; padding-left: 36px; color: var(--navy); font-weight: 600; border-top: 1px solid var(--rule); margin-top: 4px; }
.nlmenu > button:hover, .nlmenu > a:hover, .nlmenu > button:focus-visible, .nlmenu > a:focus-visible { background: var(--paper); outline: none; }
.nlmenu .nlck { color: var(--navy); font-weight: 700; }
.nlmenu .nlt { overflow-wrap: anywhere; }
.nlmenu .nln { color: var(--ink-2); font-size: 12.5px; font-variant-numeric: tabular-nums; }`;
  let WIRED = false;
  // api: the lists Worker's address. Unsaved lists from an earlier page go out now.
  function setApi(api) {
    API = String(api || "").replace(/\/$/, "");
    if (API) for (const l of lists()) if (sig(payload(l)) !== l.saved) schedule(l.slug, 4000);
  }
  function wire() {
    if (WIRED) return;
    WIRED = true;
    const st = document.createElement("style");
    st.textContent = STYLE;
    document.head.appendChild(st);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKey);
    addEventListener("resize", () => close(false));
    addEventListener("scroll", (e) => { if (MENU && !MENU.contains(e.target)) close(false); }, true);
    addEventListener("pagehide", flush);
    // Another tab changed the lists.
    addEventListener("storage", (e) => { if (e.key === KEY) refresh(); });
  }
  return { setApi, wire, ready, button, refresh, code, payload, sig, read, write, lists, edit };
})();
