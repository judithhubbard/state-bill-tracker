// A state's page settings as the build reads them: its profile.js run (BillFacts.runProfile(), as /your-bills/ and
// billlabels.js run it), instead of regular expressions over its text, so a setting written another way (a getter, a
// function, other spacing) is still read. build_data.py's profile_settings() runs it; test/profile_check.py too.
// Usage: node lists_pages/profilefacts.js PROFILE.JS [SESSION ...]   stdout: JSON
//   {hooks: {endedNote, heldAction}: whether the profile has them (they read a bill's history: split_payload()),
//    passedBothText, heldLabel, oddsExits: strings or null (the odds chart's wording, save_compare()),
//    houses, years, titles, dated: as the profile has them (null when it hasn't),
//    sessionLabel: {session: the profile's label for it} for each SESSION given (null without sessionLabel)}
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync(path.join(__dirname, "billfacts.js"), "utf8") + "\n;globalThis.BillFacts = BillFacts;", ctx);
const [file, ...sessions] = process.argv.slice(2);
const src = fs.readFileSync(file, "utf8");
const first = +(sessions[0] || new Date().getFullYear());
const S = ctx.BillFacts.runProfile(src, first, { c: true });
if (!S) { console.error(`profilefacts.js: ${file} didn't run`); process.exit(1); }
const str = (v) => (typeof v === "string" ? v : null);
const plain = (v) => (v === undefined || typeof v === "function" ? null : JSON.parse(JSON.stringify(v)));
const out = {
  hooks: { endedNote: S.endedNote != null, heldAction: S.heldAction != null },
  passedBothText: str(S.passedBothText),
  heldLabel: str(S.heldLabel),
  oddsExits: Array.isArray(S.oddsExits) && S.oddsExits.length === 2 && S.oddsExits.every((x) => typeof x === "string") ? S.oddsExits : null,
  houses: plain(S.houses), years: plain(S.years), titles: plain(S.titles), dated: plain(S.dated),
  sessionLabel: Object.fromEntries(sessions.map((s) => [s, typeof S.sessionLabel === "function" ? String(S.sessionLabel(+s)) : null])),
};
process.stdout.write(JSON.stringify(out));
