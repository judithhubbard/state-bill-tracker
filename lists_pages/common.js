// Shared by /your-bills/ and /list/ (lists_pages/; build_site.sh puts it inside each page, ahead of the page's own script).
// Each state's page keeps its watchlist in this browser under "abt:<st>:watch" (New York's under "abt:watch"):
// {"2025:SB12": {seen: the date of the last action seen, stance}}, keyed by session and the number without its amendment
// letter. Where each bill is comes from the state's data/status_<session>.json (build_data.py): {page, live, bills:
// {number: [full number, title, stage, last action's date, last action, committee, kind]}, alias: {other number: number}}.
// Shared lists live in the lists Worker (lists_worker/): a list across states writes each bill "nj:2026:A1234" ("-" in
// front: opposed).
const LISTS_API = (document.querySelector('meta[name="lists-api"]')?.content || "").replace(/\/$/, "");
const SUPPORT = document.querySelector('meta[name="support"]')?.content || "";
const NAMES = { al: "Alabama", ak: "Alaska", az: "Arizona", ar: "Arkansas", ca: "California", co: "Colorado", ct: "Connecticut",
  de: "Delaware", fl: "Florida", ga: "Georgia", hi: "Hawaii", id: "Idaho", il: "Illinois", in: "Indiana", ia: "Iowa",
  ks: "Kansas", ky: "Kentucky", la: "Louisiana", me: "Maine", md: "Maryland", ma: "Massachusetts", mi: "Michigan",
  mn: "Minnesota", ms: "Mississippi", mo: "Missouri", mt: "Montana", ne: "Nebraska", nv: "Nevada", nh: "New Hampshire",
  nj: "New Jersey", nm: "New Mexico", ny: "New York", nc: "North Carolina", nd: "North Dakota", oh: "Ohio", ok: "Oklahoma",
  or: "Oregon", pa: "Pennsylvania", ri: "Rhode Island", sc: "South Carolina", sd: "South Dakota", tn: "Tennessee",
  tx: "Texas", ut: "Utah", vt: "Vermont", va: "Virginia", wa: "Washington", wv: "West Virginia", wi: "Wisconsin", wy: "Wyoming",
  us: "Congress" };
const stName = (st) => NAMES[st] || st.toUpperCase();
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const $ = (id) => document.getElementById(id);
// Visit counting (GoatCounter, once the site is launched): anonymous events by name, never which bills or lists.
function countUse(name, tries = 0) {
  if (window.goatcounter?.count) { try { window.goatcounter.count({ path: name, title: name, event: true }); } catch (e) {} return; }
  if (document.querySelector("script[data-goatcounter]") && tries < 6) setTimeout(() => countUse(name, tries + 1), 2000);
}
const COUNTED = new Set();
function countOnce(name) { if (!COUNTED.has(name)) { COUNTED.add(name); countUse(name); } }

// ---- Watchlists in this browser ----
const WKEY = (st) => (st === "ny" ? "abt:watch" : `abt:${st}:watch`);
const baseNum = (n) => n.replace(/[A-Z]$/, "");
const spaced = (n) => n.replace(/^([A-Z]+)(\d)/, "$1 $2");
// Maine's records are "HLD307" (the house that has the paper, then its LD number), shown "LD 307".
const numText = (st, n) => (st === "me" ? spaced(n).replace(/^[HS]LD /, "LD ") : spaced(n));
function readWatch(st) {
  try { const o = JSON.parse(localStorage.getItem(WKEY(st)) || "{}"); return o && typeof o === "object" && !Array.isArray(o) ? o : {}; } catch (e) { return {}; }
}
function writeWatch(st, o) { try { localStorage.setItem(WKEY(st), JSON.stringify(o)); } catch (e) {} }
const entryOf = (v) => (typeof v === "string" ? { seen: v, stance: "support" } : v || {});
// Every starred bill in this browser: [{st, session, num, entry}].
function allStarred() {
  const out = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const m = (localStorage.key(i) || "").match(/^abt:(?:([a-z]{2}):)?watch$/);
      if (!m) continue;
      const st = m[1] || "ny";
      if (!NAMES[st]) continue;
      for (const [k, v] of Object.entries(readWatch(st))) {
        const [session, num] = k.split(":");
        if (/^\d{4}$/.test(session) && num) out.push({ st, session: +session, num, entry: entryOf(v) });
      }
    }
  } catch (e) {}
  return out;
}
// A bill in a list across states: "nj:2026:A1234"; "-" in front means oppose.
const CROSS_RE = /^(-?)([a-z]{2}):(\d{4}):([A-Z]{1,7}\d{1,6})$/;
const crossKey = (st, session, num) => `${st}:${session}:${baseNum(num)}`;
function parseCross(code) {
  const m = CROSS_RE.exec(code);
  return m ? { st: m[2], session: +m[3], num: m[4], stance: m[1] ? "oppose" : "support", key: `${m[2]}:${m[3]}:${m[4]}` } : null;
}
// A list's bills in one shape, whether the list is one state's ({state, session, bills: ["A1234"]}) or across states.
function listBills(l) {
  if (l.state === "all") return l.bills.map(parseCross).filter(Boolean);
  return l.bills.map((b) => {
    const m = /^(-?)(.+)$/.exec(b);
    return { st: l.state, session: l.session, num: m[2], stance: m[1] ? "oppose" : "support", key: `${l.state}:${l.session}:${m[2]}` };
  });
}
// Support and oppose are shown when they tell something: on a group's list, or when the list opposes any bill.
const showStance = (l) => !!l.group || l.bills.some((b) => b.startsWith("-"));
const noteOf = (l, b) => (l.notes || {})[l.state === "all" ? b.key : b.num] || "";

// ---- Where each bill is ----
const STATUS = {};
const statusOf = (st, session) => (STATUS[`${st}/${session}`] ||= fetch(`/${st}/data/status_${session}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
const fmtDay = (d) => (d ? new Date(`${d}T12:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
function whereText(st, stage, comm, kind, live) {
  if (stage === 0) return `${live ? "In" : "Died in"} committee${comm ? ` (${comm})` : ""}`;
  if (stage === 3 && kind === "const") return st === "us" ? "Passed both houses; goes to the states" : "Passed both houses; goes to the voters";
  if (!live && stage < 3) return ["", "Died on the floor", "Passed one house; died in the other"][stage];
  return ["In committee", "On the floor", "Passed one house", "Passed both houses", st === "us" ? "On the President's desk" : "On the governor's desk",
    "Became law", "Vetoed"][stage] || "";
}
// A bill's latest step as the state wrote it, in plainer words (home.html's plainAct()).
const titleCase = (t) => t.toLowerCase().replace(/\b([a-z])([a-z]*)/g, (w, a, b, i) => (i && /^(and|of|the|on|for|to|in|a)$/.test(w) ? w : a.toUpperCase() + b));
function plainAct(a) {
  a = String(a).trim();
  let m;
  if ((m = a.match(/^REFERRED TO (.+)$/))) return `Sent to the ${titleCase(m[1])} Committee`;
  if ((m = a.match(/^SIGNED CHAP\.?\s*(\d+)/i))) return `Signed into law (chapter ${m[1]})`;
  if (/^DELIVERED TO GOVERNOR$/i.test(a)) return "Sent to the governor";
  if (/^VETOED/i.test(a)) return "Vetoed";
  if (/^APPROVAL MEMO/i.test(a)) return "Signed into law";
  if (a === a.toUpperCase() && /[A-Z]{3}/.test(a)) a = a.charAt(0) + a.slice(1).toLowerCase();
  return a.length > 140 ? a.slice(0, 140).replace(/\s\S*$/, "") + "…" : a;
}
// The status files cut long titles short (about 140 characters): mark the cut.
const cut = (t) => (t.length >= 120 && !/[.!?)"”']$/.test(t) ? t.replace(/[\s,;:]+$/, "") + "…" : t);
// One bill's status: {found, full, title, stage, last, action, label, href} (href: its card on the state's page).
async function lookUp(st, session, num) {
  const s = await statusOf(st, session);
  const lead = s ? (s.bills[num] ? num : s.alias?.[num]) : null, b = lead && s.bills[lead];
  if (!b) return { found: false, full: num, title: `${session} session`, href: `/${st}/` };
  const [full, title, stage, last, action, comm, kind] = b, page = s.page && s.page !== "./" ? s.page : "";
  return { found: true, full, title: cut(title), stage, last, action, label: whereText(st, stage, comm, kind, s.live !== false), href: `/${st}/${page}#${full}` };
}
const THIS_YEAR = new Date().getFullYear();
// A bill's row: number, title, what's new, where it is and when, the list's note and stance, "What to do".
// x: lookUp()'s answer plus {st, session, fresh, newLine, stance, note, star (the star's HTML), seen (data-seen value)}.
function billRow(x) {
  const yr = x.session < THIS_YEAR - 1 ? ` <small>(${x.session})</small>` : "";
  return `<li${x.star ? "" : ' class="nostar"'}><a href="${esc(x.href)}"${x.seen ? ` data-seen="${esc(x.seen)}"` : ""}>`
    + `<span class="num">${esc(numText(x.st, x.full))}${yr}</span><span class="tt">${esc(x.title)}${x.fresh && !x.newLine ? '<span class="new">New</span>' : ""}</span>`
    + (x.newLine ? `<span class="what"><b>New:</b> ${esc(x.newLine)}</span>` : "")
    + (x.note ? `<span class="note">${esc(x.note)}</span>` : "")
    + `<span class="where">${x.stance ? `<span class="stance ${x.stance}">${x.stance === "oppose" ? "Oppose" : "Support"}</span>` : ""}`
    + (x.found ? `<span class="stg s${x.stage}">${esc(x.label)}</span>${x.last ? `<span>${fmtDay(x.last)}</span>` : ""}` : "")
    + `<span class="todo">${x.found ? "What to do ›" : "Open ›"}</span></span></a>${x.star || ""}</li>`;
}

// ---- The lists Worker ----
async function api(path, opts = {}) {
  if (!LISTS_API) throw new Error("Sharing isn't available here.");
  const r = await fetch(LISTS_API + path, { ...opts, headers: { "Content-Type": "application/json", ...(opts.headers || {}) } });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(body.error || `The list service answered ${r.status}.`); e.status = r.status; throw e; }
  return body;
}
// The list made from "Your bills" in this browser: {slug, editKey, title, group, intro, notes, saved (what was last saved)}.
const PUB = "abt:all:published";
function myList() { try { return JSON.parse(localStorage.getItem(PUB) || "null"); } catch (e) { return null; } }
function setMyList(v) { try { v ? localStorage.setItem(PUB, JSON.stringify(v)) : localStorage.removeItem(PUB); } catch (e) {} }
// Lists followed in this browser: {slug: {title, known: [bill keys seen so far], since}}.
const FOLLOWS = "abt:follows";
function readFollows() { try { const o = JSON.parse(localStorage.getItem(FOLLOWS) || "{}"); return o && typeof o === "object" ? o : {}; } catch (e) { return {}; } }
function writeFollows(o) { try { localStorage.setItem(FOLLOWS, JSON.stringify(o)); } catch (e) {} }
const listLink = (slug) => `${location.origin}/list/#${slug}`;
// Paragraphs from plain text (a group's introduction).
const paras = (t) => String(t || "").split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean).map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("");
