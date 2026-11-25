// Bill links with their own link previews (2026-11-24, the owner): /<st>/bill/<number> (this session's bill, as the
// state's main page has it) and /<st>/bill/<session>/<number> (another session's). Link previews (Bluesky, Facebook,
// iMessage, Slack) never see what follows a "#", so /ny/#S7421 showed New York's general card; this answers each bill
// with a small page whose preview tags name the bill (number and title, its status in the state page's words, the
// state's card /cards/<st>.png), and sends people on to the bill on its own (/ny/#S7421&share: tracker.html's soloOn()).
//
// It's the site's Cloudflare Pages Function in advanced mode: build_site.sh puts this file at the top of the built site as
// _worker.js, with __ROOT__ (the site's address) and __NAMES__ (each folder's name) filled in, and _routes.json sends it
// only /*/bill/* (every other address is served from the files as before, and costs no Function request). Where a bill
// is comes from the site's own files, as the list pages read them (lists_pages/status.js's statusOf()): /status.json names
// each session's status pieces, and the bill is in piece FNV-1a(number) % pieces (build_data.py's shard_of()).
const ROOT = __ROOT__;
const NAMES = __NAMES__;
const NUM = /^\/([a-z]{2})\/bill\/(?:(\d{4})\/)?([A-Za-z]{1,7}\d{1,6}[A-Za-z]?)\/?$/;
// (Fresh enough for a preview: the status pieces change at most with each publish, every few hours.)
const CACHE = "public, max-age=900, s-maxage=3600";

const baseNum = (n) => n.replace(/[A-Z]$/, "");
// A long sentence cut at a word, with "…".
const cut = (s, n) => { s = String(s || "").replace(/\s+([.,;:)])/g, "$1").replace(/\s+/g, " ").trim(); if (s.length <= n) return s; s = s.replace(/ ?\([^()]{16,}\)/g, "").replace(/\s+([.,;:])/g, "$1"); if (s.length <= n) return s; const c = s.slice(0, n); const i = c.lastIndexOf(" "); return (i > n * 0.6 ? c.slice(0, i) : c).replace(/[,;:.\s]+$/, "") + "…"; };
function hash(num) {
  let h = 0x811c9dc5;
  for (const c of new TextEncoder().encode(baseNum(num))) h = Math.imul(h ^ c, 0x01000193) >>> 0;
  return h;
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const fmtDay = (d) => {
  const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(d || "");
  return m ? `${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m[2] - 1]} ${+m[3]}, ${m[1]}` : "";
};

async function json(env, origin, path) {
  const r = await env.ASSETS.fetch(new Request(origin + path));
  return r.ok ? r.json() : null;
}

// {session, page, row, num} for a bill, or null: the session asked for, else the state's main page's session, then the
// others, newest first.
async function find(env, origin, st, session, num) {
  const index = await json(env, origin, "/status.json");
  const ix = index && index[st];
  if (!ix) return null;
  const order = session ? [session] : [
    ...Object.keys(ix).filter((s) => ix[s].p === "./"),
    ...Object.keys(ix).filter((s) => ix[s].p !== "./").sort().reverse()];
  for (const s of order) {
    const one = ix[s];
    if (!one || !one.h) continue;
    const n = one.h.length / 8;
    const piece = (k) => json(env, origin, `/${st}/data/v/${s}.${one.h.slice(8 * k, 8 * k + 8)}.t${k}.json`);
    let p = await piece(hash(num) % n);
    if (!p) continue;
    let lead = p.bills[num] ? num : p.alias && p.alias[num];
    if (!lead) continue;
    if (!p.bills[lead]) p = await piece(hash(lead) % n);
    if (p && p.bills[lead]) return { session: s, page: one.p, row: p.bills[lead], num: lead };
  }
  return null;
}

function page({ title, desc, image, url, to, name }) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="State Bill Tracker">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${esc(url)}">
${image ? `<meta property="og:image" content="${esc(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="${esc(name)} · State Bill Tracker">
<meta name="twitter:image" content="${esc(image)}">
` : ""}<meta name="twitter:card" content="${image ? "summary_large_image" : "summary"}">
<meta name="twitter:title" content="${esc(title)}">
<meta name="twitter:description" content="${esc(desc)}">
<link rel="canonical" href="${esc(url)}">
<script>location.replace(${JSON.stringify(to)});</script>
<noscript><meta http-equiv="refresh" content="0; url=${esc(to)}"></noscript>
<style>body { font: 16px/1.5 system-ui, sans-serif; color: #132a2e; background: #f5f7f8; margin: 40px auto; max-width: 640px; padding: 0 20px; }
a { color: #00777e; }</style>
</head>
<body>
<p><a href="${esc(to)}">${esc(title)}</a></p>
</body>
</html>
`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const m = NUM.exec(url.pathname);
    if (!m || !NAMES[m[1]]) return env.ASSETS.fetch(request);
    // (?issue=vouchers: a bill on an issue through one of its sections, shared from that issue: its preview names the section,
    // from the issue's parts.json, and it opens with the issue's box; 2026-11-25, the owner.)
    const issue = /^[a-z0-9-]{1,40}$/.test(url.searchParams.get("issue") || "") ? url.searchParams.get("issue") : "";
    const cache = caches.default, key = new Request(url.origin + url.pathname + (issue ? `?issue=${issue}` : ""));
    const hit = await cache.match(key);
    if (hit) return hit;
    const [, st, session, raw] = m;
    const name = NAMES[st], num = baseNum(raw.toUpperCase());
    const image = `${ROOT}cards/${st}.png`;
    const bill = await find(env, url.origin, st, session, num).catch(() => null);
    let html;
    if (bill) {
      // A status row: [full number, title, stage, last action's day, latest news, ..., status words (11)] (build_data.py's
      // write_status()).
      const [full, title, , last, news, , , , , , , label] = bill.row;
      const where = label || news || "";
      const desc = [where, last && `last action ${fmtDay(last)}`].filter(Boolean).join(" · ")
        + `. See where it is, who decides next, and what to ask them.`;
      let t = `${full}: ${title} · ${name}`, d = desc;
      let canon = `${ROOT}${st}/bill/${session ? `${session}/` : ""}${bill.num}`;
      let to = `/${st}/${bill.page === "./" ? "" : bill.page}#${bill.num}&share`;
      const part = issue ? await json(env, url.origin, `/issues/${issue}/parts.json`).catch(() => null) : null;
      const sec = part && part.bills && part.bills[`${st}:${bill.session}:${bill.num}`];
      if (sec) {
        const short = String(part.short || part.name || issue);
        t = `${full} · ${short[0].toUpperCase()}${short.slice(1)} section: ${cut(sec, 140)}`;
        d = `${where || "On the issue"}. One part of a larger bill: ${title}.`;
        canon += `?issue=${issue}`;
        to += `&issue=${issue}`;
      }
      // (No image for a bill: the title and status are the preview, a compact card, not the state's big banner; 2026-11-24,
      // the owner. The state's card stays for an unknown number, which goes to the state's page.)
      html = page({ title: t, desc: d, image: "", url: canon, to, name });
    } else {
      html = page({ title: `${name} bills · State Bill Tracker`, desc: `No ${raw.toUpperCase()} on file for ${name}: see every bill there.`,
                    image, url: `${ROOT}${st}/`, to: `/${st}/`, name });
    }
    const res = new Response(html, { status: bill ? 200 : 404, headers: { "content-type": "text/html; charset=utf-8", "cache-control": CACHE } });
    if (bill) await cache.put(key, res.clone()).catch(() => {});
    return res;
  },
};
