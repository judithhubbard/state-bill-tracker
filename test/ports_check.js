// Page logic the build works out in Python, checked against the page's own code (tracker.html) on what the build wrote.
// The two copies can't be one (the build writes the files; the page reads them, and needs the same walk for each bill),
// so this fails when they disagree:
//   meetings  build_data.py's meeting_days() (the stats part's meetingDays, "who decides") against tracker.html's
//             walkCommittees() run over every bill's history (the rows part), as meetings() does without meetingDays.
//   first     build_data.py's split_payload() puts the titles and histories of the list's first FIRST_ROWS bills in the
//             list part; tracker.html's sortBills() ("recent", the list's first order) must put no other bill in its
//             first PAGE (else the first screen shows rows without titles until the rows part comes).
// (build_data.py's api_names() is the only copy now: the page reads apiName. The profile's settings are read by running
// it: lists_pages/profilefacts.js.)
// Usage: node test/ports_check.js SITE   (a folder build_site.sh wrote; each state's current session)
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const REPO = path.join(__dirname, "..");
const site = process.argv[2];
if (!site) { console.error("usage: node test/ports_check.js SITE"); process.exit(2); }
const page = fs.readFileSync(path.join(REPO, "tracker.html"), "utf8");

// A top-level declaration's text in tracker.html: "function NAME(...) {" to its closing "}" at the line's start, or a
// one-line "const NAME = ...".
function decl(name) {
  let i = page.search(new RegExp(`\\n(?:async )?function ${name}\\(`));
  if (i >= 0) {
    const end = page.indexOf("\n}\n", i);
    return page.slice(i + 1, end + 2);
  }
  const m = new RegExp(`\\nconst ${name} = [^\\n]*\\n`).exec(page);
  if (!m) throw new Error(`tracker.html has no top-level ${name}`);
  return m[0].slice(1);
}
const ctx = vm.createContext({});
vm.runInContext(["SENT_TO", "commKey", "walkCommittees", "dayOf", "PAGE", "sortBills"].map(decl).join("\n")
  + "\nlet state = { sort: 'recent' }; const rankOf = (s) => s, earlierSessions = () => 0, nextMeeting = () => null;"
  + "\nglobalThis.T = { walkCommittees, sortBills, dayOf, PAGE };", ctx);
const { walkCommittees, sortBills, dayOf, PAGE } = ctx.T;

let fails = 0, checked = 0;
const fail = (st, what) => { fails++; console.log(`FAIL ${st}: ${what}`); };
for (const st of fs.readdirSync(site).sort()) {
  const index = path.join(site, st, "index.html");
  if (!/^[a-z]{2}$/.test(st) || !fs.existsSync(index)) continue;
  const tag = /<script type="application\/json" id="bill-data"([^>]*)>/.exec(fs.readFileSync(index, "utf8"));
  if (!tag) { fail(st, "no data tag in index.html"); continue; }
  const attr = (n) => (new RegExp(`${n}="([^"]*)"`).exec(tag[1]) || [])[1] || "";
  const session = attr("data-session"), parts = Object.fromEntries(attr("data-parts").split(" ").filter(Boolean).map((x) => x.split(":")));
  const read = (rel) => JSON.parse(fs.readFileSync(path.join(site, st, rel), "utf8"));
  const list = read(attr("data-src"));
  const cols = list.cols || [];
  if (!cols.length) continue;
  checked++;
  const n = cols[0].length;
  // meetings: the build's days against the page's walk.
  if (parts.rows && parts.stats) {
    const rows = read(`data/v/${session}.${parts.rows}.rows.json`), stats = read(`data/v/${session}.${parts.stats}.stats.json`);
    const mine = new Map();
    for (let j = 0; j < n; j++) {
      cols[17][j].forEach((v, k) => {
        const actions = ((rows.acts[j] || [])[k] || []).map(([dt, t]) => [dayOf(dt), rows.strings[t]]);
        walkCommittees({ p: v[0], actions }, (kind, house, comm, d) => {
          if (kind !== "met" || comm === "rules") return;
          const key = `${house}:${comm}`;
          if (!mine.has(key)) mine.set(key, new Set());
          mine.get(key).add(d);
        });
      });
    }
    const built = stats.meetingDays;
    if (!built) fail(st, "the stats part has no meetingDays");
    else {
      const keys = new Set([...mine.keys(), ...Object.keys(built)]);
      let diff = 0;
      for (const key of keys) {
        const a = [...(mine.get(key) || [])].sort().join(","), b = (built[key] || []).slice().sort().join(",");
        if (a !== b && diff++ < 3) fail(st, `meeting days of ${key}: the page's walk ${a || "(none)"}; the build's ${b || "(none)"}`);
      }
      if (diff > 3) fail(st, `... and ${diff - 3} more committees`);
    }
  }
  // first: the page's first PAGE bills all have their rows in the list part.
  const bills = cols[0].map((_, j) => ({ j, last: dayOf(cols[11][j] || ""), stage: cols[6][j] }));
  const rowsIn = new Set(list.rowsIn || []);
  const missing = sortBills(bills).slice(0, PAGE).filter((b) => !rowsIn.has(b.j));
  if (missing.length) fail(st, `${missing.length} of the list's first ${PAGE} bills have no title in the list part (first: ${cols[17][missing[0].j][0][0]})`);
}
console.log(`ports_check: ${checked} states, ${fails ? `${fails} FAIL` : "no differences"}`);
process.exit(fails ? 1 : 0);
