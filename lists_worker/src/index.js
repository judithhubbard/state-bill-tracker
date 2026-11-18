// State Bill Tracker: shared watchlists.
//
// Anyone can share their watchlist: the site creates a list with a random address and keeps it in step with the
// visitor's stars (updates need the private edit key the creator's browser keeps). Anyone with the address can read it
// and follow it. A group with an invite code (issued by the site's owner) can also give its list a readable address, an
// introduction and notes on each bill; revoking the code hides the group's lists. The owner can hide or delete any list.
//
// KV keys:  code:<code>    -> { group, active, created }
//           list:<slug>    -> { slug, state, session, title, bills, intro, notes, group, code, hidden, editHash, created, updated }
//           views:<slug>   -> { total, days: { "2026-10-23": n, ... last 30 days } }  (group lists only: KV allows few writes)
//           rate:<ip>:<day> -> lists created from one address that day (expires after two days)

const ALLOWED_ORIGINS = ["https://statebilltracker.org", "https://www.statebilltracker.org", "https://statebilltracker.pages.dev"];
const allowed = (o) => !!o && (ALLOWED_ORIGINS.includes(o) || /^https:\/\/[a-z0-9-]+\.statebilltracker\.pages\.dev$/.test(o) || /^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(o));
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,60}$/;
const STATE_RE = /^[a-z]{2}$/;
const BILL_RE = /^-?[A-Z]{1,7}\d{1,6}$/; // a bill number without spaces or amendment letter; "-" in front means oppose
const MAX_BILLS = 500;
const MAX_TITLE = 60;        // anyone's list
const MAX_GROUP_TITLE = 120; // a group's
const MAX_INTRO = 3000;
const MAX_NOTE = 1000;
const MAX_CREATES = 10;      // new lists a day from one address
const MIN_UPDATE_GAP = 10e3; // milliseconds between saves of one list (the site saves a minute after the last change)

const enc = new TextEncoder();
async function sha256(s) {
  const d = await crypto.subtle.digest("SHA-256", enc.encode(s));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function randomToken(n) {
  const alphabet = "abcdefghijkmnpqrstuvwxyz23456789"; // no look-alike characters
  const bytes = crypto.getRandomValues(new Uint8Array(n));
  return [...bytes].map((b) => alphabet[b % alphabet.length]).join("");
}
// Compares two strings in constant time, for tokens.
function same(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function corsHeaders(req) {
  const origin = req.headers.get("Origin");
  return {
    "Access-Control-Allow-Origin": allowed(origin) ? origin : ALLOWED_ORIGINS[0],
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Edit-Key, Authorization",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}
const reply = (req, body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...corsHeaders(req) } });
const fail = (req, status, message) => reply(req, { error: message }, status);

// The list fields a client may set, checked. Introductions and notes only for a group's list (group true).
function cleanList(body, group) {
  const title = String(body?.title || "").trim().replace(/\s+/g, " ").slice(0, group ? MAX_GROUP_TITLE : MAX_TITLE);
  const bills = Array.isArray(body?.bills) ? body.bills.map((b) => String(b).toUpperCase().replace(/\s+/g, "")) : [];
  if (bills.length > MAX_BILLS) return { error: `A list can have at most ${MAX_BILLS} bills.` };
  if (bills.some((b) => !BILL_RE.test(b))) return { error: "Bills must look like HB1234 or S1234." };
  const state = String(body?.state || "").toLowerCase();
  if (!STATE_RE.test(state)) return { error: "Unknown state." };
  const session = Number(body?.session);
  if (!Number.isInteger(session) || session < 2009 || session > 2099) return { error: "Unknown session." };
  // Plain text only; the site escapes it when showing it.
  const intro = group ? String(body?.intro || "").trim().slice(0, MAX_INTRO) : "";
  const notes = {};
  if (group) {
    const plain = new Set(bills.map((b) => b.replace(/^-/, "")));
    for (const [k, v] of Object.entries(body?.notes && typeof body.notes === "object" ? body.notes : {})) {
      const key = String(k).toUpperCase();
      const text = String(v || "").trim().slice(0, MAX_NOTE);
      if (plain.has(key) && text) notes[key] = text;
    }
  }
  return { title, bills: [...new Set(bills)], state, session, intro, notes };
}
function slugify(title) {
  return title.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50) || "list";
}
const publicView = (l) => ({ slug: l.slug, state: l.state, session: l.session, title: l.title, group: l.group || "", bills: l.bills,
  intro: l.intro || "", notes: l.notes || {}, updated: l.updated });

async function getJSON(env, key) { return JSON.parse((await env.LISTS.get(key)) || "null"); }
// Counts one opening of a group's list. KV can drop a count when two land at once; close enough for a rough tally.
async function countView(env, slug) {
  const v = (await getJSON(env, `views:${slug}`)) || { total: 0, days: {} };
  const day = new Date().toISOString().slice(0, 10);
  v.total += 1;
  v.days[day] = (v.days[day] || 0) + 1;
  for (const d of Object.keys(v.days).sort().slice(0, -30)) delete v.days[d];
  await env.LISTS.put(`views:${slug}`, JSON.stringify(v));
}
function viewSummary(v) {
  const days = v?.days || {}, cut = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
  return { total: v?.total || 0, week: Object.entries(days).filter(([d]) => d > cut).reduce((s, [, n]) => s + n, 0) };
}
async function codeActive(env, code) { const c = await getJSON(env, `code:${code}`); return c && c.active ? c : null; }
// A list is shown unless the owner hid it or its group's code was revoked.
async function visible(env, l) { return !!l && !l.hidden && (!l.code || !!(await codeActive(env, l.code))); }

export default {
  async fetch(req, env, ctx) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(req) });
    const url = new URL(req.url);
    const parts = url.pathname.split("/").filter(Boolean);
    try {
      // ---- The owner's admin page (/manage): plain HTML; it asks for the admin key, keeps it in that browser, and calls
      // the admin requests below with it. The page itself holds nothing private. ----
      if (parts[0] === "manage" && req.method === "GET") {
        return new Response(ADMIN_PAGE, { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store",
          "X-Robots-Tag": "noindex", "Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'" } });
      }
      // ---- Admin: the site's owner, with the admin token. ----
      if (parts[0] === "admin") {
        const token = (req.headers.get("Authorization") || "").replace(/^Bearer /, "");
        if (!env.ADMIN_TOKEN || !same(token, env.ADMIN_TOKEN)) return fail(req, 401, "Not authorized.");
        if (parts[1] === "codes" && req.method === "POST") {
          const body = await req.json().catch(() => ({}));
          const group = String(body.group || "").trim().slice(0, 100);
          if (!group) return fail(req, 400, "Give the group's name.");
          const code = randomToken(10);
          await env.LISTS.put(`code:${code}`, JSON.stringify({ group, active: true, created: new Date().toISOString() }));
          return reply(req, { code, group });
        }
        if (parts[1] === "codes" && req.method === "GET") {
          const out = [];
          for (const k of (await env.LISTS.list({ prefix: "code:" })).keys) out.push({ code: k.name.slice(5), ...(await getJSON(env, k.name)) });
          return reply(req, out);
        }
        if (parts[1] === "codes" && parts[2] && req.method === "DELETE") {
          const c = await getJSON(env, `code:${parts[2]}`);
          if (!c) return fail(req, 404, "No such code.");
          c.active = false;
          await env.LISTS.put(`code:${parts[2]}`, JSON.stringify(c));
          return reply(req, { revoked: parts[2], group: c.group });
        }
        if (parts[1] === "lists" && req.method === "GET") {
          const out = [];
          let cursor;
          do {
            const page = await env.LISTS.list({ prefix: "list:", cursor });
            for (const k of page.keys) {
              const l = await getJSON(env, k.name);
              if (l) out.push({ slug: l.slug, state: l.state, title: l.title, group: l.group || "", bills: l.bills.length, hidden: !!l.hidden, updated: l.updated,
                ...(l.code ? { views: viewSummary(await getJSON(env, `views:${l.slug}`)) } : {}) });
            }
            cursor = page.list_complete ? null : page.cursor;
          } while (cursor);
          return reply(req, out);
        }
        // Hide a list (it stays stored, and can be shown again): PUT /admin/lists/<slug> {"hidden": true}.
        if (parts[1] === "lists" && parts[2] && req.method === "PUT") {
          const l = await getJSON(env, `list:${parts[2]}`);
          if (!l) return fail(req, 404, "No such list.");
          l.hidden = !!(await req.json().catch(() => ({}))).hidden;
          await env.LISTS.put(`list:${parts[2]}`, JSON.stringify(l));
          return reply(req, { slug: l.slug, hidden: l.hidden });
        }
        if (parts[1] === "lists" && parts[2] && req.method === "DELETE") {
          await env.LISTS.delete(`list:${parts[2]}`);
          await env.LISTS.delete(`views:${parts[2]}`);
          return reply(req, { deleted: parts[2] });
        }
        return fail(req, 404, "Unknown admin request.");
      }

      if (parts[0] !== "lists") return fail(req, 404, "Not found.");
      const slug = parts[1];

      // ---- How often a group's list was opened: its editors only. ----
      if (slug && parts[2] === "views" && req.method === "GET") {
        const l = SLUG_RE.test(slug) && (await getJSON(env, `list:${slug}`));
        if (!l || !same(await sha256(req.headers.get("X-Edit-Key") || ""), l.editHash)) return fail(req, 403, "That edit key doesn't match this list.");
        return reply(req, viewSummary(await getJSON(env, `views:${slug}`)));
      }

      // ---- Read a list: anyone. A group's list counts each opening, except by its own editors. ----
      if (slug && !parts[2] && req.method === "GET") {
        if (!SLUG_RE.test(slug)) return fail(req, 404, "No such list.");
        const l = await getJSON(env, `list:${slug}`);
        if (!(await visible(env, l))) return fail(req, 404, "This list isn't available.");
        const editor = same(await sha256(req.headers.get("X-Edit-Key") || ""), l.editHash);
        if (l.code && !editor) ctx.waitUntil(countView(env, slug).catch(() => {}));
        return reply(req, publicView(l));
      }

      // ---- Create a list: anyone (a few a day from one address), or a group with an active invite code. ----
      if (!slug && req.method === "POST") {
        const body = await req.json().catch(() => null);
        const code = String(body?.code || "").trim().toLowerCase();
        const c = code ? await codeActive(env, code) : null;
        if (code && !c) return fail(req, 403, "That invite code isn't valid.");
        if (!c) {
          const ip = await sha256(req.headers.get("CF-Connecting-IP") || "unknown"), day = new Date().toISOString().slice(0, 10);
          const n = Number((await env.LISTS.get(`rate:${ip}:${day}`)) || 0);
          if (n >= MAX_CREATES) return fail(req, 429, "Too many new lists today. Try again tomorrow.");
          await env.LISTS.put(`rate:${ip}:${day}`, String(n + 1), { expirationTtl: 2 * 86400 });
        }
        const fields = cleanList(body, !!c);
        if (fields.error) return fail(req, 400, fields.error);
        // A group's list gets an address from its name; anyone else's a random one.
        let s;
        if (c && fields.title) {
          const base = slugify(fields.title);
          s = base;
          for (let n = 2; await env.LISTS.get(`list:${s}`); n++) s = `${base}-${n}`;
        } else {
          do s = randomToken(10); while (await env.LISTS.get(`list:${s}`));
        }
        const editKey = randomToken(24), now = new Date().toISOString();
        await env.LISTS.put(`list:${s}`, JSON.stringify({ slug: s, ...fields, group: c ? c.group : "", code: c ? code : "", hidden: false,
          editHash: await sha256(editKey), created: now, updated: now }));
        return reply(req, { slug: s, editKey, group: c ? c.group : "" }, 201);
      }

      // ---- Update or delete a list: needs its edit key (and a group's code still active). ----
      if (slug && (req.method === "PUT" || req.method === "DELETE")) {
        const l = SLUG_RE.test(slug) && (await getJSON(env, `list:${slug}`));
        if (!l) return fail(req, 404, "No such list.");
        if (!same(await sha256(req.headers.get("X-Edit-Key") || ""), l.editHash)) return fail(req, 403, "That edit key doesn't match this list.");
        if (l.code && !(await codeActive(env, l.code))) return fail(req, 403, "This group's invite code has been revoked.");
        if (req.method === "DELETE") { await env.LISTS.delete(`list:${slug}`); await env.LISTS.delete(`views:${slug}`); return reply(req, { deleted: slug }); }
        if (Date.now() - Date.parse(l.updated) < MIN_UPDATE_GAP) return fail(req, 429, "Saved a moment ago; try again shortly.");
        const fields = cleanList(await req.json().catch(() => null), !!l.code);
        if (fields.error) return fail(req, 400, fields.error);
        if (fields.state !== l.state) return fail(req, 400, "A list stays in its state.");
        Object.assign(l, fields, { updated: new Date().toISOString() });
        await env.LISTS.put(`list:${slug}`, JSON.stringify(l));
        return reply(req, publicView(l));
      }
      return fail(req, 405, "Not allowed.");
    } catch (e) {
      return fail(req, 500, "Something went wrong.");
    }
  },
};

// The admin page: shared lists (newest change first) with View, Hide/Show and Delete, and invite codes for groups.
const ADMIN_PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Shared lists · State Bill Tracker</title>
<style>
:root { --paper: #f6f8fb; --sheet: #fff; --ink: #14213d; --ink-2: #4a5878; --rule: #d9dfe9; --navy: #1d3b78; --red: #a3302a; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --paper: #0f1626; --sheet: #172036; --ink: #e6ebf5; --ink-2: #a3b0c9; --rule: #2c3852; --navy: #8fb0f0; --red: #ef8a80; color-scheme: dark; } }
body { margin: 0; background: var(--paper); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 24px 16px 60px; }
main { max-width: 900px; margin: 0 auto; }
h1 { font-size: 24px; margin: 0 0 4px; } h2 { font-size: 18px; margin: 28px 0 8px; }
.muted { color: var(--ink-2); font-size: 13px; }
input { font: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 6px; background: var(--sheet); color: var(--ink); }
button { font: inherit; font-size: 14px; padding: 5px 10px; border: 1px solid var(--navy); border-radius: 6px; background: var(--sheet); color: var(--navy); cursor: pointer; }
button.del { border-color: var(--red); color: var(--red); }
table { width: 100%; border-collapse: collapse; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-size: 13px; color: var(--ink-2); font-weight: 600; }
tr.hid td { opacity: .55; }
td.acts { white-space: nowrap; } td.acts button { margin: 0 4px 4px 0; }
a { color: var(--navy); }
.wrap { overflow-x: auto; }
#msg { min-height: 1.5em; }
</style></head><body><main>
<h1>Shared lists</h1>
<p class="muted">Watchlists people have shared from State Bill Tracker. Hide a list to take it off the site (you can show it again); Delete removes it for good.</p>
<form id="login" hidden><p><label>Admin password <input type="password" id="key" autocomplete="current-password" size="40"></label> <button>Open</button></p></form>
<p id="msg" class="muted"></p>
<div id="app" hidden>
  <div class="wrap"><table><thead><tr><th>List</th><th>State</th><th>Bills</th><th>Changed</th><th></th></tr></thead><tbody id="rows"></tbody></table></div>
  <h2>Invite codes for groups</h2>
  <p class="muted">A group with a code can give its list a name in the address, an introduction and notes on each bill. Revoking a code hides the group's lists.</p>
  <form id="newcode"><p><label>Group name <input id="group" size="36" placeholder="e.g. League of Women Voters of Ohio"></label> <button>Make a code</button></p></form>
  <div class="wrap"><table><thead><tr><th>Code</th><th>Group</th><th>Made</th><th></th></tr></thead><tbody id="codes"></tbody></table></div>
  <p class="muted"><button type="button" id="logout">Forget the password on this computer</button></p>
</div>
<script>
const SITE = "https://statebilltracker.org/";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
let KEY = "";
try { KEY = localStorage.getItem("adminKey") || ""; } catch (e) {}
const msg = (t) => { document.getElementById("msg").textContent = t; };
async function call(method, path, body) {
  const r = await fetch(path, { method, headers: { Authorization: "Bearer " + KEY, "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  const d = await r.json().catch(() => ({}));
  if (r.status === 401) { showLogin("That password didn't work."); throw new Error("401"); }
  if (!r.ok) throw new Error(d.error || "Something went wrong.");
  return d;
}
function showLogin(t) { document.getElementById("login").hidden = false; document.getElementById("app").hidden = true; msg(t || ""); }
async function load() {
  msg("Loading…");
  const [lists, codes] = await Promise.all([call("GET", "/admin/lists"), call("GET", "/admin/codes")]);
  document.getElementById("login").hidden = true; document.getElementById("app").hidden = false;
  lists.sort((a, b) => (b.updated || "").localeCompare(a.updated || ""));
  document.getElementById("rows").innerHTML = lists.length ? lists.map((l) => '<tr class="' + (l.hidden ? "hid" : "") + '"><td><b>' + esc(l.title || "(no title)") + "</b>"
    + (l.group ? '<br><span class="muted">' + esc(l.group) + "</span>" : "") + (l.views ? '<br><span class="muted">opened ' + l.views.total + " times, " + l.views.week + " this week</span>" : "")
    + (l.hidden ? '<br><span class="muted">Hidden</span>' : "") + "</td><td>" + esc((l.state || "").toUpperCase()) + "</td><td>" + l.bills + "</td><td>" + esc((l.updated || "").slice(0, 10)) + '</td><td class="acts">'
    + '<a href="' + SITE + esc(l.state) + "/watchlist/#list=" + esc(l.slug) + '" target="_blank" rel="noopener">View</a> '
    + '<button type="button" data-hide="' + esc(l.slug) + '" data-to="' + (l.hidden ? "0" : "1") + '">' + (l.hidden ? "Show" : "Hide") + "</button>"
    + '<button type="button" class="del" data-del="' + esc(l.slug) + '" data-title="' + esc(l.title) + '">Delete</button></td></tr>').join("")
    : '<tr><td colspan="5" class="muted">No shared lists yet.</td></tr>';
  codes.sort((a, b) => (b.created || "").localeCompare(a.created || ""));
  document.getElementById("codes").innerHTML = codes.length ? codes.map((c) => "<tr><td><code>" + esc(c.code) + "</code></td><td>" + esc(c.group) + (c.active ? "" : ' <span class="muted">(revoked)</span>') + "</td><td>"
    + esc((c.created || "").slice(0, 10)) + '</td><td class="acts">' + (c.active ? '<button type="button" class="del" data-revoke="' + esc(c.code) + '" data-group="' + esc(c.group) + '">Revoke</button>' : "") + "</td></tr>").join("")
    : '<tr><td colspan="4" class="muted">No codes yet.</td></tr>';
  msg(lists.length + " shared list" + (lists.length === 1 ? "" : "s") + ".");
}
document.getElementById("login").addEventListener("submit", (e) => {
  e.preventDefault(); KEY = document.getElementById("key").value.trim();
  try { localStorage.setItem("adminKey", KEY); } catch (err) {}
  load().catch((err) => { if (err.message !== "401") msg(err.message); });
});
document.getElementById("logout").addEventListener("click", () => { try { localStorage.removeItem("adminKey"); } catch (e) {} KEY = ""; showLogin("Forgotten on this computer."); });
document.getElementById("newcode").addEventListener("submit", async (e) => {
  e.preventDefault(); const g = document.getElementById("group").value.trim(); if (!g) return;
  try { const r = await call("POST", "/admin/codes", { group: g }); document.getElementById("group").value = ""; await load(); msg("Code for " + r.group + ": " + r.code + ". Send it to them; they enter it when they share their list."); } catch (err) { if (err.message !== "401") msg(err.message); }
});
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-hide], button[data-del], button[data-revoke]");
  if (!b) return;
  try {
    if (b.dataset.hide) await call("PUT", "/admin/lists/" + b.dataset.hide, { hidden: b.dataset.to === "1" });
    if (b.dataset.del) { if (!confirm("Delete “" + b.dataset.title + "” for good? This can't be undone.")) return; await call("DELETE", "/admin/lists/" + b.dataset.del); }
    if (b.dataset.revoke) { if (!confirm("Revoke the code for " + b.dataset.group + "? Their lists will be hidden.")) return; await call("DELETE", "/admin/codes/" + b.dataset.revoke); }
    await load();
  } catch (err) { if (err.message !== "401") msg(err.message); }
});
if (KEY) load().catch((err) => { if (err.message !== "401") msg(err.message); }); else showLogin();
</script></main></body></html>`;
