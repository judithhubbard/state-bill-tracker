// The watchlist's rows and groups, in one copy: each state's Watchlist tab (build_data.py puts this file in the page beside
// watchrules.js) and /your-bills/ (onelist.js; build_site.sh puts it inside the page) draw starred bills with it, so a bill
// shows in the same group, with the same deadline, in the same order, in both. The groups: Due soon, Before the session
// ends, the state's year-end group (S.passedBothGroup), Later, Out of time this session, Decided or ended; within a
// group, the soonest deadline first, then the bill furthest along, then the most recent action. Every class name starts
// with "wr-" (lists_pages/rows.css), since the state's page has its own .num, .where and .todo.
// WatchRows.place(b, ctx): a bill's group and deadline (b: stage, due, agenda and what the state's originDeadline() reads;
//   ctx: {S (the state's profile), WR (watchrules.js's rules), current, upcoming, act (WR.canAct()), exec}).
// WatchRows.draw(box, items, opt): the rows (items: {key, st, session, num, full, title, stage, label, last, action, group,
//   date, due, out, later, sessionLabel, old, found, gone, stance, rules, yearGroup, other (the second number, New York's
//   same-as bill, shown under the first as on the state's Bills list)}; label: the status words, from
//   billfacts.js: the state's page works them out, the other pages read them from the status rows).
// WatchRows.newsHtml(entries): "3 with news since you last looked · Mark all as seen", above the list.
const WatchRows = (() => {
  const ORDER = ["soon", "session", "year", "later", "idle", "done"];
  const NAMES = { soon: "Due soon", session: "In the legislature", later: "Later", idle: "Out of time this session", done: "Decided or ended" };
  // (No general note under a heading: the headings say it. A state's own note on a group, with its dates, still shows.)
  const NOTES = {};
  const h = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const today = () => WatchRules.localToday();
  // A bill number as shown (Maine's "HLD307" is "LD 307").
  const numText = BillFacts.numText;  // (billfacts.js, put before this file in every page that has it)
  // A day as a row shows it: "Dec 1", with the year when it isn't this one.
  const day = (d) => { const t = new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)); return t.toLocaleDateString("en-US", { month: "short", day: "numeric", ...(d.slice(0, 4) === today().slice(0, 4) ? {} : { year: "numeric" }) }); };
  const fullDay = (d) => (d ? new Date(`${d.slice(0, 10)}T12:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
  // A bill's group and deadline: {group, date (its deadline, for sorting), due (the deadline in words), out (it can't move
  // this session), yearGroup (the state's name for the year-end group)}.
  function place(b, c) {
    if (b.stage >= 5 || !c.current) return { group: "done" };
    if (c.upcoming) {
      let opens = "";
      try { opens = c.S.opens && c.session ? c.S.opens(c.session) : ""; } catch (e) {}
      return { group: "later", due: opens ? `Session opens ${day(opens)}` : "Prefiled" };
    }
    if (!c.act) return { group: "idle", out: true };
    const dl = c.WR.deadlineOf(b), x = { group: dl.g, date: dl.d || "" };
    const meet = WatchRules.nextMeeting(b.agenda, true, b.stage);
    if (dl.d) {
      if (b.stage === 4) x.due = `${c.exec || "Governor"} by ${day(dl.d)}`;
      else if (dl.origin) x.due = `Must pass its house by ${day(dl.d)}`;
      else if (dl.g === "year") x.due = `Due by ${day(dl.d)}`;
      // (A floor calendar, kind "floor": "Floor vote Mar 2", or "On the Senate calendar Mar 2" for a list of bills that
      // can come up that day, note "listed"; "Likely floor vote Mar 2" for a day guessed from the bill's history, note
      // "likely".)
      else if (meet && dl.d === meet.when.slice(0, 10)) x.due = meet.kind !== "floor" ? `Committee meets ${day(dl.d)}`
        : meet.note === "likely" ? `Likely floor vote ${day(dl.d).replace(" ", "\u00a0")}`
        : meet.note === "listed" ? `On the ${meet.committee.replace(/ floor$/i, "")} calendar ${day(dl.d).replace(" ", "\u00a0")}` : `Floor vote ${day(dl.d).replace(" ", "\u00a0")}`;
      else if (dl.d === c.WR.sessionEnd().date) x.due = c.WR.daysUntil(dl.d) >= 0 ? `Session ends ${day(dl.d)}` : "Session could end any day";
    }
    if (dl.g === "year") x.yearGroup = c.S.passedBothGroup?.[0] || "";
    if (x.group === "later") {
      const k = (b.topics || []).includes("const");
      x.due = c.next?.(b) || (b.ballot || (k && c.S.amendmentOnce) ? "Goes to the voters" : k ? "Next step after this session" : "");
    }
    return x;
  }
  const rank = (g) => { const i = ORDER.indexOf(g); return i < 0 ? 3 : i; };
  const groupOf = (x) => (ORDER.includes(x.group) ? x.group : "later");
  // Within a group: the soonest deadline, then furthest along, then the most recent action (decided bills: the most recent).
  function sortIn(a, b, name = (s) => s) {
    const tail = () => name(a.st).localeCompare(name(b.st)) || String(a.full || a.num).localeCompare(String(b.full || b.num), "en", { numeric: true });
    if (a.group === "done" && b.group === "done") return String(b.last || "").localeCompare(String(a.last || "")) || tail();
    return (a.date || "9999").localeCompare(b.date || "9999") || (b.stage ?? -1) - (a.stage ?? -1) || String(b.last || "").localeCompare(String(a.last || "")) || tail();
  }
  // The groups' order for these bills: Due soon, then the dated groups by their soonest date (with several states, New
  // York's December 31 can come before New Jersey's session end two years off), then Later, Can't move, Decided.
  function orderOf(list) {
    const first = {};
    for (const x of list) { const g = groupOf(x); if (x.date && !(first[g] <= x.date)) first[g] = x.date; }
    return ["soon", ...["session", "year"].sort((a, b) => (first[a] || "9999").localeCompare(first[b] || "9999")), "later", "idle", "done"];
  }
  // The bills in the order the list shows them (a shared list's bills are saved in it too).
  const ordered = (list, name) => { const o = orderOf(list); return [...list].sort((a, b) => o.indexOf(groupOf(a)) - o.indexOf(groupOf(b)) || sortIn(a, b, name)); };
  const idOf = (opt, x) => `${opt.tab}-${x.key.replace(/[^\w]/g, "_")}`;
  // One row. opt: {tab (an id for the rows' ids), byState, oneState (no state badge), stance (show Support too), stName,
  // isNew(x), newText(x), noteOf(x), remove (a Remove button on bills from sessions no longer on the site), buttons(x) (the
  // star and the list button), card(x) (an open bill's card, drawn by the page itself; else the box is filled by someone
  // else: embed.js's Opener), onRow(id, x)}.
  function rowHtml(x, opt) {
    const id = idOf(opt, x), name = opt.stName || ((s) => s.toUpperCase());
    const st = opt.byState || opt.oneState ? "" : `<span class="wr-st" title="${h(name(x.st))}">${x.st === "us" ? "US" : x.st.toUpperCase()}</span>`;
    const yr = x.old || x.upcoming ? ` <small>${h(x.sessionLabel || x.session)}</small>` : "";
    const btns = `<span class="wr-btns">${opt.buttons ? opt.buttons(x) : ""}</span>`;
    if (x.gone) {
      return `<li class="wr-row wr-gone" data-key="${h(x.key)}"><div class="wr-grow"><span class="wr-num">${st}${h(numText(x.st, x.num))}</span>`
        + `<span class="wr-tt">${h(x.sessionLabel || x.session)}: no longer on this site</span>`
        + (opt.remove ? `<button type="button" class="btn quiet small" data-remove="${h(`${x.st}|${x.session}|${x.num}`)}">Remove</button>` : "") + "</div></li>";
    }
    const two = x.other ? `<small class="wr-other">${h(numText(x.st, x.other))}</small>` : "";
    const shown = `<span class="wr-n1">${h(numText(x.st, x.full || x.num))}</span>${two}`, note = opt.noteOf?.(x);
    // The side, when one is chosen (stars start with none, so a missing tag means none chosen, not "support").
    // (A shared or named list marks every bill with a side: Support shows there only when the list uses sides, opt.stance.)
    const stance = x.stance === "oppose" || (x.stance === "support" && opt.stance !== false) ? `<span class="wr-stance ${x.stance}">${x.stance === "oppose" ? "Oppose" : "Support"}</span>` : "";
    // What's new, inside the row (2026-11-24, the owner's design: no separate box above the list): what happened and its
    // day in bold (newText(x)), then the step's odds in grey (oddsOf(x), the state's page only). And what the person did
    // about it ("✓ You wrote to Sens. Amato and Schepisi · Nov 26": wroteOf(x)), and "Take action" on a bill that can
    // still move (the row opens its card, whose "Who to write to" has the emails).
    const fresh = !!opt.isNew?.(x), odds = fresh ? opt.oddsOf?.(x) || "" : "", wrote = opt.wroteOf?.(x) || "";
    const news = fresh ? `<span class="wr-news"><b class="wr-what">${h(opt.newText ? opt.newText(x) : `${x.action || ""}${x.last ? ` · ${fullDay(x.last)}` : ""}`)}</b>${odds ? `<span class="wr-odds">${h(odds)}</span>` : ""}</span>` : "";
    const did = wrote ? `<span class="wr-wrote">${h(wrote)}</span>` : "";
    const go = opt.act !== false && x.found && ["soon", "session", "year", "later"].includes(groupOf(x)) && !x.upcoming ? '<span class="wr-ta">Take action ›</span>' : "";
    // The status column, as on the state's Bills list: the pips, the status label, then the date of the latest action
    // and the deadline (lists_pages/rows.css). A bill out of time this session is greyed, as there.
    const over = (x.out || x.group === "done") && x.stage <= 2 ? " over" : "", uni = opt.uni ? opt.uni(x) : BillFacts.oneHouse(x.st);
    // (A deadline the group's heading already gives isn't repeated on each row: opt.groupDay.)
    const due = x.due && !(opt.groupDay && x.date === opt.groupDay && (x.group === "session" || x.group === "year")) ? x.due : "";
    // (The last action's day is left out when it's the deadline's own day: "Oct 22, 2026 · Floor vote Oct 22" read twice.)
    const sameDay = due && x.last && x.date && String(x.last).slice(0, 10) === String(x.date).slice(0, 10);
    // (With a deadline beside it, the last action's day says what it is: "Last action Oct 22, 2026 · Floor vote Oct 29".)
    // The latest action in the state's words, then its day, as the state's Bills list shows it ("Referred to the Health
    // Committee · Oct 22, 2026"); a "New:" line already says it when the action is new.
    // (Not when it says what the status label beside it says: "Passed both houses · Passed both houses · Jun 4, 2026".)
    const plain = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
    const told = plain(x.action) && plain(x.label).includes(plain(x.action));
    const act = x.action && !told && !fresh ? `${h(x.action)} · ` : "";
    const when = [x.found && x.last && !sameDay ? `<span>${act}${fullDay(x.last).replace(/ /g, "\u00a0")}</span>` : "",
      due ? `<span class="wr-dl">${h(due).replace(/\b([A-Z][a-z]{2}) (\d)/g, "$1 $2")}</span>` : x.out && opt.byState ? '<span class="wr-dl">Out of time this session</span>' : ""].filter(Boolean).join("");
    const where = `<span class="wr-where bstat">${x.found ? BillFacts.pips(x.stage, uni, over.trim(), x.label, x.st) + `<span class="stg s${x.stage}${over}">${h(x.label)}</span>` : ""}`
      + `${when ? `<span class="stw">${when}</span>` : ""}${stance}${x.found ? "" : '<span class="wr-todo">Open</span>'}</span>`;
    const back = x.later && x.later[0] > x.session ? `<p class="wr-again">Back in ${h(x.later[2])} as <a href="${h(x.later[3])}#${h(x.later[1])}">${h(numText(x.st, x.later[1]))}</a>${x.laterStar || ""}</p>` : "";
    if (!x.found) {
      return `<li class="wr-row${yr ? " wr-yr" : ""}${two ? " wr-two" : ""}" data-key="${h(x.key)}"><a class="wr-btn rowbtn" href="${h(x.href || `/${x.st}/`)}"><span class="wr-num">${st}${shown}${yr}</span>`
        + `<span class="wr-tt">Not in ${h(x.sessionLabel || x.session)}'s data</span>${where}</a>${btns}</li>`;
    }
    opt.onRow?.(id, x);
    const card = opt.card ? opt.card(x) : null;
    // (The side down the row's left edge: red for a bill the person opposes, teal for one they support, green for a law
    // they wanted.)
    const side = x.stance === "oppose" ? " wr-opp" : x.stance === "support" ? (x.stage === 5 ? " wr-won" : " wr-sup") : "";
    return `<li class="wr-row${yr ? " wr-yr" : ""}${two ? " wr-two" : ""}${side}${fresh ? " wr-fresh" : ""}" data-key="${h(x.key)}"><button type="button" class="wr-btn rowbtn" data-open="${h(id)}" aria-controls="emb-${h(id)}" aria-expanded="${card != null}">`
      + `<span class="wr-num">${st}${shown}${yr}${fresh ? '<span class="wr-newmark">New</span>' : ""}</span><span class="wr-tt">${h(x.title)}</span>${note ? `<span class="wr-note">${h(note)}</span>` : ""}${news}${did}${go}${where}</button>`
      + `${btns}${back}<div class="wr-emb" id="emb-${h(id)}"${card != null ? "" : " hidden"}>${card || ""}</div></li>`;
  }
  // A group's heading: its name and note (when the group is one state's, that state's note on it), and anything the page
  // adds under it (opt.groupExtra(g, xs): the state's "Copy one email about all 3").
  function groupHead(g, xs, opt) {
    const one = xs.every((x) => x.rules && x.rules === xs[0].rules) ? xs[0].rules : null;
    let name = NAMES[g], sub = "";
    // The dated groups say where the bills are, then the date when the group's bills share one: "In the legislature:
    // session ends January 11, 2028", "Passed both houses: deadline December 31, 2026" (else each row shows its own date).
    const days = new Set(xs.map((x) => x.date || ""));
    const oneDay = days.size === 1 && [...days][0];
    const long = (d) => new Date(`${d}T12:00`).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
    if (g === "session") name = `In the legislature${oneDay ? `: session ends ${long(oneDay)}` : ""}`;
    if (g === "year") name = `Passed both houses${oneDay ? `: deadline ${long(oneDay)}` : ""}`;
    try { if (one && one.WR.groups[g]) sub = one.WR.groups[g][1]() || ""; } catch (e) {}
    // In a list with several states (Your bills), a state's note says which state ("The New Jersey session ends ...").
    if (sub && !opt.oneState && one) { const nm = (opt.stName || ((x) => x.toUpperCase()))(xs[0].st); sub = /^The session/.test(sub) ? sub.replace(/^The session/, `The ${nm} session`) : `${nm}: ${sub}`; }
    if (!sub) sub = NOTES[g] || "";
    // (The heading gives the date: the note doesn't say it again.)
    if (oneDay && (g === "session" || g === "year")) sub = sub.replace(/^The (?:[A-Z][\w.]*(?: [A-Z][\w.]*)* )?session (?:is scheduled to )?ends? [A-Z][a-z]+ \d+(?:, \d{4})?\. /, "");
    // The note is behind an ⓘ on the heading (data-wtip opens it: draw()'s listener).
    const tip = sub ? ` <button type="button" class="wr-tip" data-wtip aria-expanded="false" aria-label="About these bills" title="${h(sub)}">i</button>` : "";
    return `<h2 class="wr-ghd">${h(name)} <span class="wr-n">· ${xs.length} bill${xs.length === 1 ? "" : "s"}</span>${tip}</h2>${sub ? `<p class="wr-gsub" hidden>${h(sub)}</p>` : ""}${opt.groupExtra?.(g, xs) || ""}`;
  }
  // The group's single deadline, when its bills share one (the heading gives it).
  const groupDay = (g, xs) => { const ds = new Set(xs.map((x) => x.date || "")); return ds.size === 1 && (g === "session" || g === "year") ? [...ds][0] : ""; };
  function draw(box, list, opt) {
    box.classList.add("wrows");
    // A group heading's ⓘ shows its note (once per box).
    if (!box.dataset.wrTips) {
      box.dataset.wrTips = "1";
      box.addEventListener("click", (e) => {
        const b = e.target.closest?.("[data-wtip]");
        if (!b) return;
        e.preventDefault(); e.stopPropagation();
        const p = b.closest("h2")?.nextElementSibling;
        if (p?.classList.contains("wr-gsub")) { p.hidden = !p.hidden; b.setAttribute("aria-expanded", String(!p.hidden)); }
      });
    }
    let html = "";
    if (opt.byState) {
      const name = opt.stName || ((s) => s), by = new Map();
      for (const x of list) (by.get(x.st) || by.set(x.st, []).get(x.st)).push(x);
      html = [...by.keys()].sort((a, b) => name(a).localeCompare(name(b))).map((st) => {
        const xs = ordered(by.get(st), name);
        return `<section class="wr-state"><h3><a href="/${st}/">${h(name(st))}</a><a class="wr-wl" href="/${st}/watchlist/">Watchlist ›</a></h3><ol class="wr-list">${xs.map((x) => rowHtml(x, { ...opt, byState: true })).join("")}</ol></section>`;
      }).join("");
    } else {
      html = orderOf(list).map((g) => {
        const xs = list.filter((x) => groupOf(x) === g).sort((a, b) => sortIn(a, b, opt.stName));
        const gd = groupDay(g, xs);
        return xs.length ? `<section class="wr-grp" data-g="${g}">${groupHead(g, xs, opt)}<ol class="wr-list">${xs.map((x) => rowHtml(x, { ...opt, groupDay: gd })).join("")}</ol></section>` : "";
      }).join("");
    }
    box.innerHTML = html;
    for (const n of box.querySelectorAll(".wr-num")) { RO?.observe(n); placeBtns(n); }
  }
  // The star and list button sit under the number, however many lines it takes (a state's badge on its own line at phone
  // width, a second number, a session): placed when the number's column is drawn or changes size.
  function placeBtns(num) {
    const li = num.closest(".wr-row"), b = li?.querySelector(":scope > .wr-btns");
    if (!b || !num.offsetParent) return;
    const pad = parseFloat(getComputedStyle(num).paddingBottom) || 0;
    b.style.top = `${Math.round(num.getBoundingClientRect().bottom - pad - li.getBoundingClientRect().top + 2)}px`;
  }
  const RO = typeof ResizeObserver === "function" ? new ResizeObserver((es) => { for (const e of es) placeBtns(e.target); }) : null;
  // Above the list, one line: "3 with news since you last looked · Mark all as seen" (the news itself is in the rows,
  // 2026-11-24; this was a box listing it). entries: the bills with news. "Mark all as seen" is data-wseenall.
  function newsHtml(entries) {
    if (!entries.length) return "";
    return `<p class="wnews-line"><span>${entries.length} with news since you last looked</span><button type="button" class="linkish" data-wseenall>Mark all as seen</button></p>`;
  }
  return { ORDER, NAMES, place, ordered, sortIn, rowHtml, draw, newsHtml, numText, day, fullDay, idOf };
})();
