// Each bill's status words and watchlist facts, worked out at build time by the same code the state's page runs
// (billfacts.js with watchrules.js and the state's profile.js), for the views that show a bill without its page: the
// status rows (/your-bills/, /list/, the front page's Your bills), the search files and the issue pages.
// build_data.py's bill_labels() runs it: stdin {profile (profile.js's text), session, facts ({c, u, e, v, t}: the facts
// /status.json carries), bills: [the page's shape: stage, comm, passedIn, topics, ballot, title, summary, nums,
// vers [{p, committee, statusDesc, actions}], dates {passS, passA, ...}, earlier [[session, numbers, stage]]]};
// stdout [[words, flags, newsDay], ...] in the same order. flags: "e" ended before the session did, "a" a constitutional
// amendment that doesn't go to the governor, "2" its second (or only) passage, "d" the voters have decided it, "r" a
// veto the Legislature can still override.
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

// (In a context of its own, as in a page: the profile's regular expressions are that context's.)
const ctx = vm.createContext({ console });
vm.runInContext(["watchrules.js", "billfacts.js"].map((f) => fs.readFileSync(path.join(__dirname, f), "utf8")).join("\n")
  + "\n;globalThis.WatchRules = WatchRules; globalThis.BillFacts = BillFacts;", ctx);
const { WatchRules, BillFacts } = ctx;

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const f = input.facts || {};
const S = BillFacts.runProfile(input.profile, +input.session, f);
if (!S) { console.error("billlabels.js: the profile didn't run"); process.exit(1); }
const F = { session: +input.session, current: !!f.c, upcoming: !!f.u, lastVote: f.v || "", lastComm: f.m || "", sessionEnd: f.e || {}, timing: (f.t || []).map((v) => ({ lastVote: v })) };
const today = WatchRules.localToday;
const WR = WatchRules.make(S, () => F, { today });
const fmtDate = (d) => (d ? new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
const BF = BillFacts.make(S, { WR, facts: () => F, today, fmtDate });
const routine = S.routine || BillFacts.ROUTINE;
const out = input.bills.map((b) => {
  b.dates = b.dates || {};
  b.topics = b.topics || [];
  const x = BF.factsOf(b);
  let veto = false;
  try { veto = !!S.vetoReturns?.(b)?.live; } catch (e) {}
  const flags = (x.stops ? "e" : "") + (x.amend ? "a" : "") + (x.second ? "2" : "") + (x.voted ? "d" : "") + (veto ? "r" : "");
  return [BillFacts.words(S, x), flags, BillFacts.newsDay((b.vers || []).flatMap((v) => v.actions || []), routine)];
});
process.stdout.write(JSON.stringify(out));
