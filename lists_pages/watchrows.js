// The watchlist's rows and groups, in one copy: each state's Watchlist tab (build_data.py puts this file in the page beside
// watchrules.js) and /your-bills/ (onelist.js; build_site.sh puts it inside the page) draw starred bills with it, so a bill
// shows in the same group, with the same deadline, in the same order, in both. The groups: Due soon, Before the session
// ends, the state's year-end group (S.passedBothGroup), No deadline yet, Can't move right now, Decided or ended; within a
// group, the soonest deadline first, then the bill furthest along, then the most recent action. Every class name starts
// with "wr-" (lists_pages/rows.css), since the state's page has its own .num, .where and .todo.
// WatchRows.place(b, ctx): a bill's group and deadline (b: stage, due, agenda and what the state's originDeadline() reads;
//   ctx: {S (the state's profile), WR (watchrules.js's rules), current, upcoming, act (WR.canAct()), exec}).
// WatchRows.draw(box, items, opt): the rows (items: {key, st, session, num, full, title, stage, label, last, action, group,
//   date, due, out, later, sessionLabel, old, found, gone, stance, rules, yearGroup}).
// WatchRows.newsHtml(entries): "New since you last looked", one box at the top of the list.
const WatchRows = (() => {
  const ORDER = ["soon", "session", "year", "later", "idle", "done"];
  const NAMES = { soon: "Due soon", session: "Before the session ends", later: "No deadline yet", idle: "Can’t move right now", done: "Decided or ended" };
  const NOTES = { soon: "A vote, hearing or deadline is coming up.", idle: "Nothing to ask for on these now. They’re marked New when something changes.",
    done: "Laws, vetoes and bills whose session is over, most recent first." };
  // Paperwork that comes with a real step isn't news (a state's profile can say its own: STATE.routine).
  const ROUTINE = /^(PRINT NUMBER|INTRODUCED|DELIVERED TO (SENATE|ASSEMBLY)|RETURNED TO (SENATE|ASSEMBLY)|\d+(ST|ND) REPORT CAL|\d+RD READING CAL)/;
  const h = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const today = () => WatchRules.localToday();
  // Maine's records are "HLD307" (the house that has the paper, then its LD number), shown "LD 307".
  const numText = (st, n) => { const s = String(n || "").replace(/^([A-Z]+)(\d)/, "$1 $2"); return st === "me" ? s.replace(/^[HS]LD /, "LD ") : s; };
  // A day as a row shows it: "Dec 1", with the year when it isn't this one.
  const day = (d) => { const t = new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)); return t.toLocaleDateString("en-US", { month: "short", day: "numeric", ...(d.slice(0, 4) === today().slice(0, 4) ? {} : { year: "numeric" }) }); };
  const fullDay = (d) => (d ? new Date(`${d.slice(0, 10)}T12:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
  // Where a bill is, in a few words (up: a session not begun, whose bills are prefiled).
  function where(st, stage, comm, kind, live, up) {
    if (stage === 0 && up) return "Prefiled";
    if (stage === 0) return `${live ? "In" : "Died in"} committee${comm ? ` (${comm})` : ""}`;
    if (stage === 3 && kind === "const") return st === "us" ? "Passed both houses; goes to the states" : "Constitutional amendment passed both houses";  // (a first passage in some states: the voters aren't always next)
    if (!live && stage < 3) return ["", "Died on the floor", "Passed one house; died in the other"][stage];
    return ["In committee", "On the floor", "Passed one house", "Passed both houses", st === "us" ? "On the President's desk" : "On the governor's desk",
      "Became law", "Vetoed"][stage] || "";
  }
  // A bill's group and deadline: {group, date (its deadline, for sorting), due (the deadline in words), out (it can't move
  // this session), yearGroup (the state's name for the year-end group)}.
  function place(b, c) {
    if (b.stage >= 5 || !c.current) return { group: "done" };
    if (c.upcoming) return { group: "later" };
    if (!c.act) return { group: "idle", out: true };
    const dl = c.WR.deadlineOf(b), x = { group: dl.g, date: dl.d || "" };
    const meet = WatchRules.nextMeeting(b.agenda, true);
    if (dl.d) {
      if (b.stage === 4) x.due = `${c.exec || "Governor"} by ${day(dl.d)}`;
      else if (dl.origin) x.due = `Must pass its house by ${day(dl.d)}`;
      else if (dl.g === "year") x.due = `Due by ${day(dl.d)}`;
      else if (meet && dl.d === meet.when.slice(0, 10)) x.due = `Committee meets ${day(dl.d)}`;
      else if (dl.d === c.WR.sessionEnd().date) x.due = c.WR.daysUntil(dl.d) >= 0 ? `Session ends ${day(dl.d)}` : "Session could end any day";
    }
    if (dl.g === "year") x.yearGroup = c.S.passedBothGroup?.[0] || "";
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
  // The bills in the order the list shows them (a shared list's bills are saved in it too).
  const ordered = (list, name) => [...list].sort((a, b) => rank(groupOf(a)) - rank(groupOf(b)) || sortIn(a, b, name));
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
    const shown = h(numText(x.st, x.full || x.num)), note = opt.noteOf?.(x);
    // (Support is shown where sides matter, a group's list; Oppose always.)
    const stance = x.stance && (opt.stance || x.stance === "oppose") ? `<span class="wr-stance ${x.stance}">${x.stance === "oppose" ? "Oppose" : "Support"}</span>` : "";
    // (newText(x): what's new, with its day; else the last action and its day.)
    const news = opt.isNew?.(x) ? `<span class="wr-new"><b>New:</b> ${h(opt.newText ? opt.newText(x) : `${x.action || ""}${x.last ? ` (${fullDay(x.last)})` : ""}`)}</span>` : "";
    const where = `<span class="wr-where">${stance}${x.found ? `<span class="wr-stg s${x.stage}">${h(x.label)}</span>` : ""}${x.due ? `<span class="wr-dl">${h(x.due)}</span>` : x.out ? '<span class="wr-dl">Out of time this session</span>' : ""}`
      + `${!x.due && x.found && x.last && x.group === "done" ? `<span>${fullDay(x.last)}</span>` : ""}<span class="wr-todo">${x.found ? "Details" : "Open"}</span></span>`;
    const back = x.later && x.later[0] > x.session ? `<p class="wr-again">Back in ${h(x.later[2])} as <a href="${h(x.later[3])}#${h(x.later[1])}">${h(numText(x.st, x.later[1]))}</a>${x.laterStar || ""}</p>` : "";
    if (!x.found) {
      return `<li class="wr-row" data-key="${h(x.key)}"><a class="wr-btn rowbtn" href="${h(x.href || `/${x.st}/`)}"><span class="wr-num">${st}${shown}${yr}</span>`
        + `<span class="wr-tt">Not in ${h(x.sessionLabel || x.session)}'s data</span>${where}</a>${btns}</li>`;
    }
    opt.onRow?.(id, x);
    const card = opt.card ? opt.card(x) : null;
    return `<li class="wr-row" data-key="${h(x.key)}"><button type="button" class="wr-btn rowbtn" data-open="${h(id)}" aria-controls="emb-${h(id)}" aria-expanded="${card != null}">`
      + `<span class="wr-num">${st}${shown}${yr}</span><span class="wr-tt">${h(x.title)}</span>${note ? `<span class="wr-note">${h(note)}</span>` : ""}${news}${where}</button>`
      + `${btns}${back}<div class="wr-emb" id="emb-${h(id)}"${card != null ? "" : " hidden"}>${card || ""}</div></li>`;
  }
  // A group's heading: its name and note (when the group is one state's, that state's note on it), and anything the page
  // adds under it (opt.groupExtra(g, xs): the state's "Copy one email about all 3").
  function groupHead(g, xs, opt) {
    const one = xs.every((x) => x.rules && x.rules === xs[0].rules) ? xs[0].rules : null;
    let name = NAMES[g], sub = "";
    if (g === "year") name = new Set(xs.map((x) => x.st)).size === 1 && xs[0].yearGroup ? xs[0].yearGroup : "Due later";
    try { if (one && one.WR.groups[g]) sub = one.WR.groups[g][1]() || ""; } catch (e) {}
    if (!sub) sub = NOTES[g] || "";
    return `<h2 class="wr-ghd">${h(name)} <span class="wr-n">${xs.length}</span></h2>${sub ? `<p class="wr-gsub">${h(sub)}</p>` : ""}${opt.groupExtra?.(g, xs) || ""}`;
  }
  function draw(box, list, opt) {
    box.classList.add("wrows");
    let html = "";
    if (opt.byState) {
      const name = opt.stName || ((s) => s), by = new Map();
      for (const x of list) (by.get(x.st) || by.set(x.st, []).get(x.st)).push(x);
      html = [...by.keys()].sort((a, b) => name(a).localeCompare(name(b))).map((st) => {
        const xs = ordered(by.get(st), name);
        return `<section class="wr-state"><h3><a href="/${st}/">${h(name(st))}</a><a class="wr-wl" href="/${st}/watchlist/">Watchlist ›</a></h3><ol class="wr-list">${xs.map((x) => rowHtml(x, { ...opt, byState: true })).join("")}</ol></section>`;
      }).join("");
    } else {
      html = ORDER.map((g) => {
        const xs = list.filter((x) => groupOf(x) === g).sort((a, b) => sortIn(a, b, opt.stName));
        return xs.length ? `<section class="wr-grp" data-g="${g}">${groupHead(g, xs, opt)}<ol class="wr-list">${xs.map((x) => rowHtml(x, opt)).join("")}</ol></section>` : "";
      }).join("");
    }
    box.innerHTML = html;
  }
  // "New since you last looked": entries [{key, kind ("ok" a law, "no" a veto, ""), what, num, title, date, more (how many
  // other changes)}], the biggest news first. A row's button is data-wnews="<key>"; "Mark all as seen" is data-wseenall.
  function newsHtml(entries) {
    if (!entries.length) return "";
    return `<section class="wnews"><div class="wnews-h"><h2>New since you last looked</h2><button type="button" class="linkish" data-wseenall>Mark all as seen</button></div>`
      + `<ul>${entries.map((n) => `<li><button type="button" class="wnewsrow" data-wnews="${h(n.key)}"><span class="nk ${n.kind || ""}">${h(n.what)}</span> <span class="bn">${h(n.num)}</span> ${h(n.title)}`
        + ` <span class="wr-muted">· ${h(n.date)}${n.more ? ` · ${n.more} more change${n.more > 1 ? "s" : ""}` : ""}</span></button></li>`).join("")}</ul></section>`;
  }
  return { ORDER, NAMES, ROUTINE, place, where, ordered, sortIn, rowHtml, draw, newsHtml, numText, day, fullDay, idOf };
})();
