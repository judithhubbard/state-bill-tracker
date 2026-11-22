// State Bill Tracker: a relay for Georgia's public documents.
//
// GitHub's runners can't reach www.legis.ga.gov (connections time out), while Cloudflare's network gets the same public
// documents normally. states/ga/daily.py tries the server directly first and comes here only when that fails.
//
//   GET /fetch?path=/api/document/...   with the header X-Relay-Key: <RELAY_KEY>
//
// returns the document's body, status and content type, as www.legis.ga.gov answered them. Only the public document
// path (/api/document/: the Daily Report, agenda PDFs, bill texts) is ever fetched: never /api/meetings, /api/schedule,
// /api/authentication or anything else, and never another host. One upstream request per call (redirects are followed
// by hand, at most 3, and only within the document path); the caller paces its calls 2 seconds apart. The relay's own
// refusals carry the header X-Relay-Error, so the caller can tell them from Georgia's answers.
//
// RELAY_KEY is a secret (wrangler secret put RELAY_KEY), so this isn't an open proxy. No storage.

const ORIGIN = "https://www.legis.ga.gov";
const PREFIX = "/api/document/";
const AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)";
const MAX_BYTES = 30 * 1024 * 1024; // the largest Daily Report seen is under 2 MB
const MAX_REDIRECTS = 3;

function refuse(status, why) {
  return new Response(why + "\n", {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8", "X-Relay-Error": why, "Cache-Control": "no-store" },
  });
}

// The upstream address for a requested path, or null when it isn't a public document on www.legis.ga.gov.
function documentUrl(path, base = ORIGIN) {
  if (typeof path !== "string" || !path || path.length > 2000) return null;
  if (/[\\\u0000-\u001f\u007f]/.test(path)) return null;
  let u;
  try {
    u = new URL(path, base);
  } catch {
    return null;
  }
  // The URL parser resolves "..", "%2e%2e" and the like, so the check is on what would really be fetched.
  if (u.origin !== ORIGIN || !u.pathname.startsWith(PREFIX) || u.search || u.hash || u.username || u.password) return null;
  // Agenda links encode a slash inside a name ("Ways%20and%20Means%2F2.26.26 ... Notice.pdf"), so encoded slashes stay;
  // but a server that decodes them mustn't find a "." or ".." step that leads out of the document folder.
  let plain;
  try {
    plain = decodeURIComponent(u.pathname);
  } catch {
    return null;
  }
  if (plain.split(/[\/\\]/).some((s) => s === "." || s === "..")) return null;
  return u;
}

// Both keys hashed first, so the comparison takes the same time whatever their lengths.
async function sameKey(given, want) {
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(given)),
    crypto.subtle.digest("SHA-256", enc.encode(want)),
  ]);
  return crypto.subtle.timingSafeEqual(a, b);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") return new Response("ok\n", { headers: { "Cache-Control": "no-store" } });
    if (url.pathname !== "/fetch") return refuse(404, "not found");
    if (request.method !== "GET") return refuse(405, "GET only");
    if (!env.RELAY_KEY) return refuse(503, "relay key not set");
    if (!(await sameKey(request.headers.get("X-Relay-Key") || "", env.RELAY_KEY))) return refuse(403, "wrong key");

    let target = documentUrl(url.searchParams.get("path"));
    if (!target) return refuse(400, "only paths under /api/document/ on www.legis.ga.gov");

    let r;
    for (let hops = 0; ; hops++) {
      try {
        r = await fetch(target.href, {
          headers: { "User-Agent": AGENT, Accept: "application/pdf,*/*" },
          redirect: "manual",
          cf: { cacheTtl: 0, cacheEverything: false },
        });
      } catch (e) {
        return refuse(502, "www.legis.ga.gov didn't answer: " + String(e && e.message || e).slice(0, 200));
      }
      if (r.status < 300 || r.status > 399 || !r.headers.get("Location")) break;
      if (hops >= MAX_REDIRECTS) return refuse(508, "too many redirects");
      const next = documentUrl(r.headers.get("Location"), target.href);
      if (!next) return refuse(502, "redirected outside /api/document/");
      target = next;
    }

    const size = +(r.headers.get("Content-Length") || 0);
    if (size > MAX_BYTES) return refuse(502, "document too large");
    const body = await r.arrayBuffer();
    if (body.byteLength > MAX_BYTES) return refuse(502, "document too large");
    return new Response(body, {
      status: r.status,
      headers: {
        "Content-Type": r.headers.get("Content-Type") || "application/octet-stream",
        "Cache-Control": "no-store",
      },
    });
  },
};
