// A shared list's feed (RSS 2.0): GET /lists/<slug>/feed (2026-11-25, the owner: groups send their bills' news through
// their own newsletters: Mailchimp, Substack and Buttondown turn a feed into emails, Slack posts it to a channel).
//
// One item per bill: its latest step, in the site's own words (the status rows' "latest news", which the build writes
// as the state's Watchlist tab says it after "New:", with paperwork left out), newest first. Each step gets its own guid
// (bill, day and words), so a newsletter tool sends a bill again only when it has moved. Where each bill is comes from the
// site's own files, as the list pages read them (lists_pages/status.js's statusOf(), and the bill-link Function,
// lists_pages/bill_worker.js): /status.json names each session's status pieces, and a bill is in piece
// FNV-1a(number) % pieces (build_data.py's shard_of()). A status row: [number, title, stage, last action's day, latest news,
// committee, "const", day sent to the governor, meetings to come [[when, committee]], flags, later version, status words,
// latest day with news ("" when it's the last action's day, "-" when there's none), second number].
//
// Nothing about the list's maker is in it (no group code, edit hash or view counts), and reading it isn't counted as a
// view. Answers are kept 30 minutes at the edge (caches.default); the status files change at most with each publish.

const SITE_DEFAULT = "https://statebilltracker.org";
const CACHE = "public, max-age=1800, s-maxage=1800";
const MAX_PIECES = 40; // (the free plan allows 50 subrequests a call: a huge list shows the bills its first 40 pieces hold)
const NAMES = {
  al: "Alabama", ak: "Alaska", az: "Arizona", ar: "Arkansas", ca: "California", co: "Colorado", ct: "Connecticut",
  de: "Delaware", dc: "District of Columbia", fl: "Florida", ga: "Georgia", hi: "Hawaii", id: "Idaho", il: "Illinois",
  in: "Indiana", ia: "Iowa", ks: "Kansas", ky: "Kentucky", la: "Louisiana", me: "Maine", md: "Maryland",
  ma: "Massachusetts", mi: "Michigan", mn: "Minnesota", ms: "Mississippi", mo: "Missouri", mt: "Montana", ne: "Nebraska",
  nv: "Nevada", nh: "New Hampshire", nj: "New Jersey", nm: "New Mexico", ny: "New York", nc: "North Carolina",
  nd: "North Dakota", oh: "Ohio", ok: "Oklahoma", or: "Oregon", pa: "Pennsylvania", ri: "Rhode Island",
  sc: "South Carolina", sd: "South Dakota", tn: "Tennessee", tx: "Texas", ut: "Utah", vt: "Vermont", va: "Virginia",
  wa: "Washington", wv: "West Virginia", wi: "Wisconsin", wy: "Wyoming", us: "Congress",
};
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const baseNum = (n) => n.replace(/[A-Z]$/, "");
function fnv(num) {
  let h = 0x811c9dc5;
  for (const c of new TextEncoder().encode(baseNum(num))) h = Math.imul(h ^ c, 0x01000193) >>> 0;
  return h;
}
const xml = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
// A title for a feed's headline: the status rows cut long titles mid-phrase, so cut at a word, with "…", near 100.
const shortTitle = (t) => { t = String(t || ""); if (t.length <= 100) return t; const c = t.slice(0, 100); return c.slice(0, c.lastIndexOf(" ") > 60 ? c.lastIndexOf(" ") : 100).replace(/[,;:\s]+$/, "") + "…"; };
const day = (d) => (/^\d{4}-\d\d-\d\d/.test(d || "") ? d.slice(0, 10) : "");
const fmtDay = (d) => { const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(d || ""); return m ? `${MONTHS[+m[2] - 1]} ${+m[3]}, ${m[1]}` : ""; };
// RFC 822, at noon UTC (the records give days, not times).
const rfc822 = (d) => { const t = new Date(`${d}T12:00:00Z`); return `${DAYS[t.getUTCDay()]}, ${String(t.getUTCDate()).padStart(2, "0")} ${MONTHS[t.getUTCMonth()]} ${t.getUTCFullYear()} 12:00:00 GMT`; };
async function shortHash(s) {
  const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(s));
  return [...new Uint8Array(d)].slice(0, 6).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Each of the list's bills as {st, session, num, oppose}, in the list's order. A state's list writes "A1234" ("-" to
// oppose) for its own state and session; a list across states writes "nj:2026:A1234".
function billsOf(l) {
  const out = [];
  for (const b of l.bills || []) {
    const oppose = b.startsWith("-"), s = b.replace(/^-/, "");
    const m = /^([a-z]{2}):(\d{4}):(.+)$/.exec(s);
    if (m) out.push({ st: m[1], session: m[2], num: m[3], oppose, key: s });
    else if (l.state && l.state !== "all") out.push({ st: l.state, session: String(l.session), num: s, oppose, key: s });
  }
  return out;
}

export async function feed(req, env, ctx, l) {
  const site = (env.SITE || SITE_DEFAULT).replace(/\/$/, "");
  const url = new URL(req.url);
  const cache = caches.default, key = new Request(url.origin + url.pathname);
  const hit = await cache.match(key);
  if (hit) return hit;

  // (One more try on a failure: a feed missing a bill for a moment would look as if it had dropped off the list.)
  const get = async (path) => {
    for (let i = 0; i < 2; i++) {
      try {
        const r = await fetch(site + path, { cf: { cacheTtl: 900, cacheEverything: true } });
        if (r.ok) return await r.json();
        if (r.status === 404) return null;
      } catch (e) { /* again */ }
    }
    return null;
  };
  const index = (await get("/status.json")) || {};
  // The pieces each bill needs, fetched once each (an alias's record can be in another piece: a second round).
  const pieces = new Map();
  const pieceOf = (st, session, num) => {
    const one = index[st] && index[st][session];
    if (!one || !one.h) return null;
    const n = one.h.length / 8, k = fnv(num) % n;
    return { id: `${st}/${session}/${k}`, path: `/${st}/data/v/${session}.${one.h.slice(8 * k, 8 * k + 8)}.t${k}.json` };
  };
  const load = async (list) => {
    const want = [...new Set(list.filter(Boolean).filter((p) => !pieces.has(p.id)).map((p) => JSON.stringify(p)))]
      .map((s) => JSON.parse(s)).slice(0, Math.max(0, MAX_PIECES - pieces.size));
    const got = await Promise.all(want.map((p) => get(p.path)));
    want.forEach((p, i) => pieces.set(p.id, got[i]));
  };
  const bills = billsOf(l);
  await load(bills.map((b) => pieceOf(b.st, b.session, b.num)));
  const leads = [];
  for (const b of bills) {
    const p = pieceOf(b.st, b.session, b.num), piece = p && pieces.get(p.id);
    if (!piece) continue;
    const lead = piece.bills[b.num] ? b.num : piece.alias && piece.alias[b.num];
    if (lead) leads.push({ ...b, lead });
  }
  await load(leads.map((b) => pieceOf(b.st, b.session, b.lead)));

  const items = [];
  for (const b of leads) {
    const p = pieceOf(b.st, b.session, b.lead), row = p && pieces.get(p.id)?.bills?.[b.lead];
    if (!row) continue;
    const [full, title, , last, news, , , , meets, , , words, newsDay] = row;
    const when = day(newsDay && newsDay !== "-" ? newsDay : last);
    const what = news || words || "";
    if (!when || !what) continue;
    const page = index[b.st][b.session].p;
    const link = `${site}/${b.st}/bill/${page === "./" ? "" : `${b.session}/`}${b.lead}`;
    const name = NAMES[b.st] || b.st.toUpperCase();
    const next = (Array.isArray(meets) ? meets : []).find((m) => Array.isArray(m) && day(m[0]));
    const note = l.notes && (l.notes[b.key] || l.notes[b.num]);
    const lines = [
      `${what}, ${fmtDay(when)}.`,
      next ? `Coming up: ${next[1] ? `${next[1]}, ` : ""}${fmtDay(next[0])}.` : "",
      b.oppose ? "This list opposes it." : "",
      note ? `Note: ${note}` : "",
    ].filter(Boolean);
    items.push({
      when, title: `${full} · ${shortTitle(title)} (${name})`, link, text: lines,
      guid: `statebilltracker:${b.st}:${b.session}:${b.lead}:${when}:${await shortHash(what)}`,
    });
  }
  items.sort((a, b) => (a.when < b.when ? 1 : a.when > b.when ? -1 : 0));

  const listLink = `${site}/list/#${l.slug}`;
  const channelTitle = `${l.title || "Shared list of bills"} · State Bill Tracker`;
  const desc = (l.intro || "").trim() || "The latest step for each bill on this list, from State Bill Tracker.";
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>${xml(channelTitle)}</title>
<link>${xml(listLink)}</link>
<atom:link href="${xml(url.origin + url.pathname)}" rel="self" type="application/rss+xml"/>
<description>${xml(desc)}</description>
<language>en-us</language>
${items[0] ? `<lastBuildDate>${rfc822(items[0].when)}</lastBuildDate>\n` : ""}<ttl>60</ttl>
${items.map((it) => `<item>
<title>${xml(it.title)}</title>
<link>${xml(it.link)}</link>
<guid isPermaLink="false">${xml(it.guid)}</guid>
<pubDate>${rfc822(it.when)}</pubDate>
<description>${xml(it.text.map((t) => `<p>${xml(t)}</p>`).join(""))}</description>
</item>`).join("\n")}
</channel>
</rss>
`;
  const res = new Response(body, { headers: { "Content-Type": "application/rss+xml; charset=utf-8", "Cache-Control": CACHE, "Access-Control-Allow-Origin": "*" } });
  ctx.waitUntil(cache.put(key, res.clone()).catch(() => {}));
  return res;
}
