// Starred bills in this browser and where each bill is, in one copy: the front page (home.html) and the list pages
// (/your-bills/, /list/, the list editor, ahead of common.js) have it put inside them by build_site.sh, after billfacts.js.
// Each state's page keeps its watchlist in this browser under "abt:<st>:watch" (New York's too, since moveNewYork()):
// {"2025:SB12": {seen: the date of the last action seen, stance}}, keyed by session and the number without its amendment
// letter (older entries are just the date). Where each bill is comes from the state's data/status_<session>.json
// (build_data.py's write_status()): {page, live, bills: {number: [full number, title, stage, last action's date, last
// action, committee, kind, the day sent to the governor, meetings, flags, later version, status words, latest day with
// news]}, alias: {other number: number}}, read in pieces (statusOf()).
const WKEY = (st) => `abt:${st}:watch`;
const baseNum = (n) => n.replace(/[A-Z]$/, "");
const spaced = (n) => n.replace(/^([A-Z]+)(\d)/, "$1 $2");
// Maine's records are "HLD307" (the house that has the paper, then its LD number), shown "LD 307".
const numText = (st, n) => (st === "me" ? spaced(n).replace(/^[HS]LD /, "LD ") : spaced(n));
function readWatch(st) {
  try { const o = JSON.parse(localStorage.getItem(WKEY(st)) || "{}"); return o && typeof o === "object" && !Array.isArray(o) ? o : {}; } catch (e) { return {}; }
}
function writeWatch(st, o) { try { localStorage.setItem(WKEY(st), JSON.stringify(o)); } catch (e) {} }
const entryOf = (v) => (typeof v === "string" ? { seen: v, stance: "support" } : v || {});
// The pages read the status file in pieces (build_data.py's write_status_shards()): /status.json names each state's
// sessions' pieces ({st: {session: {p: page, l: live, h: an 8-character hash per piece, f: the session's facts}}}), and a
// bill is in piece BillFacts.hash(number) of data/v/<session>.<hash>.t<k>.json ({bills, alias}); an alias's record may be
// in another piece. The whole file is the fallback (a state or session /status.json doesn't name, or a piece gone after
// a deploy). statusOf(st, session, num) answers {page, live, bills, alias} holding at least that bill, or null.
const STATUS = {}, PIECES = {};
let STATUS_INDEX;
const statusIndex = () => (STATUS_INDEX ||= fetch("/status.json").then((r) => (r.ok ? r.json() : null)).catch(() => null));
const wholeStatus = (st, session) => (STATUS[`${st}/${session}`] ||= fetch(`/${st}/data/status_${session}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
const pieceOf = (num, n) => BillFacts.hash(num) % n;
async function statusOf(st, session, num) {
  const index = await statusIndex();
  if (!index || !index[st]) return wholeStatus(st, session);
  const ix = index[st][session];
  if (!ix) return null;
  const n = ix.h.length / 8;
  const piece = (k) => (PIECES[`${st}/${session}/${k}`] ||= fetch(`/${st}/data/v/${session}.${ix.h.slice(8 * k, 8 * k + 8)}.t${k}.json`)
    .then((r) => (r.ok ? r.json() : null)).catch(() => null));
  const p = await piece(pieceOf(num, n));
  if (!p) return wholeStatus(st, session);
  const out = { session: +session, page: ix.p, live: ix.l, bills: p.bills, alias: p.alias };
  const lead = !p.bills[num] && p.alias[num];
  if (!lead || p.bills[lead]) return out;
  const q = await piece(pieceOf(lead, n));
  if (!q) return wholeStatus(st, session);
  return { ...out, bills: q.bills[lead] ? { [lead]: q.bills[lead] } : {} };
}
// A status row's parts by name. label: the status words, as the bill's state page words them (BillFacts.words(), run by
// the build); news: the latest day with news (an action that isn't paperwork; the row leaves it out when it's the last
// action's day, and writes "-" when there's none); flags: see build_data.py's write_status().
function rowOf(r) {
  const [full, title, stage, last, action, comm, kind, deliv, meets, flags, later, label, news] = r;
  return { full, title, stage, last, action, comm, kind, deliv, meets: meets || [], flags: flags || "", later: Array.isArray(later) ? later : null,
    label: label || "", news: news === "-" ? "" : news || last || "" };
}
const fmtDay = (d) => (d ? new Date(`${d}T12:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
// A bill's latest step as the state wrote it, in plainer words: "REFERRED TO LAW AND PUBLIC SAFETY" -> "Sent to the Law
// and Public Safety Committee"; other capitals in sentence case.
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
