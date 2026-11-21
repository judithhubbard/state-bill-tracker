// Starred bills in this browser and where each bill is, in one copy: the front page (home.html) and the list pages
// (/your-bills/, /list/, the list editor, ahead of common.js) have it put inside them by build_site.sh, after billfacts.js.
// Each state's page keeps its watchlist in this browser under "abt:<st>:watch" (New York's too, since moveNewYork()):
// {"2025:SB12": {seen: the date of the last action seen, stance}}, keyed by session and the number without its amendment
// letter (older entries are just the date). Where each bill is comes from the state's data/status_<session>.json
// (build_data.py's write_status()): {page, live, bills: {number: [full number, title, stage, last action's date, its
// latest news in plain words (as the state's page says it after "New:"), committee, kind, the day sent to the governor, meetings, flags, later version, status words, latest day with
// news]}, alias: {other number: number}}, read in pieces (statusOf()).
const WKEY = (st) => `abt:${st}:watch`;
const baseNum = (n) => n.replace(/[A-Z]$/, "");
const spaced = (n) => n.replace(/^([A-Z]+)(\d)/, "$1 $2");
// A bill number as shown ("HB 1005"; Maine's "HLD307" is "LD 307"): billfacts.js's, put before this file.
const numText = BillFacts.numText;
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
  // (action: the latest news in the state page's own words, billfacts.js's latestNews(), run by the build.)
  const [full, title, stage, last, action, comm, kind, deliv, meets, flags, later, label, news] = r;
  return { full, title, stage, last, action, comm, kind, deliv, meets: meets || [], flags: flags || "", later: Array.isArray(later) ? later : null,
    label: label || "", news: news === "-" ? "" : news || last || "" };
}
const fmtDay = (d) => (d ? new Date(`${d}T12:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
// Finding a bill by number or words, in search/<st>.json (search_site.py): the front page's "Find a bill" and the list
// editor's search share these.
const BillSearch = (() => {
  const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const STOP = new Set("a an the of to and or for in on by with at from as is be into its it this that act bill relating relates concerning regarding".split(" "));
  // Two-letter codes that are also everyday words count as a state only when typed in capitals ("IN", "OR").
  const WORDY = new Set(["in", "or", "me", "hi", "ok", "de", "la", "pa", "ma", "co", "al", "id", "oh", "us", "ga", "mo", "ne", "nd", "md"]);
  // A bill number split into its letters and its number without leading zeros or the amendment letter ("S1234A" -> S, 1234).
  const numParts = (n) => { const m = String(n).toUpperCase().replace(/[^A-Z0-9]/g, "").match(/^([A-Z]*)0*(\d+)[A-Z]?$/); return m ? [m[1], m[2]] : null; };
  const stem = (w) => (w.length > 4 && w.endsWith("s") && !w.endsWith("ss") ? w.slice(0, -1) : w);
  // A search file's bill row made searchable: its title folded (low) and its numbers' parts (np).
  function prepRow(r) {
    r.low = " " + fold(String(r[1] || "")).replace(/[^a-z0-9]+/g, " ") + " ";
    r.np = [r[0], ...(Array.isArray(r[4]) ? r[4] : [])].map((n) => [n, numParts(n)]).filter((x) => x[1]);
    return r;
  }
  // Bill numbers in text: letters (dots and spaces allowed) followed by digits, or digits alone. [numbers, the rest].
  function numbersIn(text) {
    const nums = [];
    const rest = text.replace(/\b((?:[A-Za-z]\.?\s?){0,6}?)\s*(\d{1,5}[A-Za-z]?)\b/g, (all, letters, digits) => {
      const p = numParts(letters.replace(/[.\s]/g, "") + digits);
      if (p) nums.push(p);
      return " ";
    });
    return [nums, rest];
  }
  // How well a bill's numbers match: 3 exactly, 2 the same number with letters written another way ("HB" for "H", "LD"
  // for Maine's "HLD"), 1 the number alone (no letters typed). [score, the number that matched].
  function numScore(r, nums) {
    let best = 0, which = null;
    for (const [n, [P, D]] of r.np) for (const [qp, qd] of nums) {
      if (D !== qd) continue;
      const s = !qp ? 1 : P === qp ? 3 : P.replace(/B$/, "") === qp.replace(/B$/, "") || (qp.length >= 2 && P.endsWith(qp)) ? 2 : 0;
      if (s > best) { best = s; which = n; }
    }
    return [best, which];
  }
  return { fold, STOP, WORDY, numParts, stem, prepRow, numbersIn, numScore };
})();
