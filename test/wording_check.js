// The lines the site writes in its own words, checked against the official record they stand for. tracker.html's History
// says "Returned to the Assembly's floor calendar for the new year", "Approved by committee and sent to the floor",
// "Approved by the Senate Judiciary Committee · 4–3", "Signed into law"; each is worked out from the record, and each was
// once wrong for some state (2026-11-23: New York's Assembly bills "Sent back to committee" while on the floor calendar;
// California's failed committee votes and votes to reconsider "Approved by"; Alabama's laws "Signed into law" with no
// signature in the record; New York Senate bills discharged from committee "Approved by committee").
// test/data_check.py runs this for each state, with the state's bills as the page sees them on stdin:
//   {"profile": profile.js source, "session": 2025, "current": true, "bills": [{n, stage, dates, vers: [{p, actions:
//   [[day, text]]}], votes: [[house, kind, committee, day, yes, no, result]]}]}
// and prints one JSON object: {"fails": [...], "looks": [...]} (each a sentence; data_check.py says them as FAIL / LOOK).
// The page's own code is run (tracker.html's declarations, by name: decl()), not a copy of it.
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const REPO = path.join(__dirname, "..");
const page = fs.readFileSync(path.join(REPO, "tracker.html"), "utf8");
const BillFacts = require(path.join(REPO, "lists_pages", "billfacts.js"));

// A top-level declaration's text in tracker.html (as test/ports_check.js reads them): "function NAME(...) {" to its
// closing "}" at a line's start, a "const NAME = {" to its "};" at a line's start, or a one-line "const NAME = ...".
function decl(name) {
  const i = page.search(new RegExp(`\\n(?:async )?function ${name}\\(`));
  if (i >= 0) return page.slice(i + 1, page.indexOf("\n}\n", i) + 2);
  const j = page.search(new RegExp(`\\nconst ${name} = \\{\\n`));
  if (j >= 0) return page.slice(j + 1, page.indexOf("\n};\n", j) + 3);
  const m = new RegExp(`\\nconst ${name} = [^\\n]*\\n`).exec(page);
  if (!m) throw new Error(`tracker.html has no top-level ${name}`);
  return m[0].slice(1);
}
const WORDING = ["NO_SIGNATURE", "overriddenLaw", "unsignedLaw", "SIGNATURE", "ENROLL_SIGNED", "hasSignature", "signedLaw", "lawLine", "GOV_KINDS",
  "NO_RECOMMENDATION", "DISCHARGED", "APPROVED", "NO_COMMITTEE", "floorLine", "voteCarried", "voteReconsider"];

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const S = BillFacts.runProfile(input.profile, input.session, { c: !!input.current });
if (!S) { console.log(JSON.stringify({ fails: ["the profile didn't run"], looks: [] })); process.exit(0); }
const ctx = vm.createContext({ STATE: S, EXEC: { the: "the governor", ...(S.executive || {}) } });
vm.runInContext(WORDING.map(decl).join("\n") + `\nglobalThis.T = { ${WORDING.join(", ")} };`, ctx);
const T = ctx.T;
// (unsignedLaw() without its stage and override tests: what stages.py's unsigned() reads.)
T.vers_unsigned = (b) => b.vers.some((v) => v.actions.some(([, t]) => T.NO_SIGNATURE.test(t)));

const fails = [], looks = [];
const s = input.session;
const say = (bad, total, limit, what) => {
  if (!bad.length) return;
  (bad.length > limit * Math.max(1, total) ? fails : looks).push(`${s}: ${bad.length} ${what}, e.g. ${bad.slice(0, 4).join(", ")}`);
};
const bills = input.bills.map((b) => ({
  ...b, nums: b.n,
  votes: b.votes.map(([house, kind, committee, date, yes, no, result]) => ({ house, kind, committee, date, yes, no, result: result || "" })),
}));
const dayLines = (b, d, v = null) => (v ? [v] : b.vers).flatMap((x) => x.actions).filter(([x]) => x === d).map(([, t]) => t);

// 1. The reset line (dates.died: a passage undone between a two-year session's years). Where it says the bill went must be
// what the record says that day: a committee only with a referral, a floor calendar only with an order to third reading.
// A state that resets passages must say where the bill went (STATE.resetLine): the shared default names no place.
const resets = bills.filter((b) => b.dates.died);
if (resets.length && !S.resetLine) fails.push(`${s}: ${resets.length} bills with a reset passage and no STATE.resetLine to say where they went`);
if (resets.length && S.resetLine) {
  const wrong = [], vague = [];
  for (const b of resets) {
    const line = S.resetLine(b), short = S.resetLine(b, true), day = dayLines(b, b.dates.died);
    if (!line || !short) { vague.push(b.n[0]); continue; }
    const text = `${line} | ${short}`;
    if (/committee/i.test(text) && !day.some((t) => /^REFERRED TO |referred to|returned to .*committee/i.test(t))) wrong.push(`${b.n[0]} ("${line}", no referral that day)`);
    else if (/floor calendar/i.test(text) && !day.some((t) => /THIRD READING|calendar/i.test(t))) wrong.push(`${b.n[0]} ("${line}", no floor calendar that day)`);
    // Each committee the line names must be one a version was referred to that day.
    const named = [...line.matchAll(/the (?:Senate|Assembly|House) ([^,]+?) Committee/g)].map((m) => m[1].toUpperCase());
    for (const c of named) if (!day.some((t) => t.toUpperCase().includes(c))) { wrong.push(`${b.n[0]} ("${line}": no referral to ${c} that day)`); break; }
  }
  say(wrong, resets.length, 0, "reset lines that name a place the record doesn't send the bill that day");
  say(vague, resets.length, 0.01, "reset lines that don't say where the bill went");
}

// 2. The floor line: "Approved by committee and sent to the floor" needs a committee's approval that day (a report, a
// recommendation, or a committee vote that carried); otherwise the record should show how it got there.
const floors = bills.filter((b) => b.dates.floor);
const unbacked = floors.filter((b) => {
  if (T.floorLine(b) !== "Approved by committee and sent to the floor") return false;
  if (b.votes.some((v) => v.kind !== "F" && v.kind !== "R" && v.date === b.dates.floor && T.voteCarried(v) && !T.voteReconsider(v))) return false;
  const day = dayLines(b, b.dates.floor);
  return day.length && !day.some((t) => T.APPROVED.test(t) || /placed on|calendar|reading|general file|order|floor|substitut|adopted|advanced|rules/i.test(t));
}).map((b) => `${b.n[0]}@${b.dates.floor}`);
say(unbacked, floors.length, 0.02, `"Approved by committee and sent to the floor" lines with nothing that day about a committee or the floor`);
const noComm = floors.filter((b) => T.floorLine(b) === "Approved by committee and sent to the floor" && dayLines(b, b.dates.floor).some((t) => T.NO_COMMITTEE.test(t)))
  .map((b) => `${b.n[0]}@${b.dates.floor}`);
say(noComm, floors.length, 0, `"Approved by committee" lines on a day the record says the bill went to the calendar without a committee`);
if (floors.length) {
  const kinds = {};
  for (const b of floors) { const l = T.floorLine(b); kinds[l] = (kinds[l] || 0) + 1; }
  looks.push(`${s}: floor lines: ${Object.entries(kinds).sort((x, y) => y[1] - x[1]).map(([l, n]) => `${n} "${l}"`).join(", ")}`);
}

// 3. Committee votes: "Approved by the ... Committee" when the vote carried, "Voted down in" when it didn't. A vote the
// page reads as carried on a day the record says the bill failed there (and nothing says it passed) is read wrongly:
// California's 8-0 with 11 not voting ("Failed passage in committee"), or a vote to reconsider.
const FAILED = /failed passage|failed to (?:pass|be reported|report)|motion to (?:report|pass|recommend)[^.;]* failed|\bdo not pass\b|recommended it not pass|ought not to pass|inexpedient to legislate|reported (?:adversely|unfavorably)/i;
const PASSED = /do pass\b|recommended it pass|ought to pass\b|reported (?:favorably|it)|\bapproved\b|\bpassed\b(?!.*failed)|\breported\b(?! (?:adversely|unfavorably))/i;
const cvotes = bills.flatMap((b) => b.votes.filter((v) => v.kind !== "F" && v.kind !== "R").map((v) => [b, v]));
const upside = cvotes.filter(([b, v]) => T.voteCarried(v) && !T.voteReconsider(v)).filter(([b, v]) => {
  const day = dayLines(b, v.date);
  return day.some((t) => FAILED.test(t)) && !day.some((t) => PASSED.test(t) && !FAILED.test(t));
}).map(([b, v]) => `${b.n[0]}@${v.date} ${v.committee} ${v.yes}-${v.no}`);
say(upside, cvotes.length, 0.005, `committee votes worded "Approved by" on a day the record says the bill failed in committee`);

// 4. Laws: the stage's own name. A profile naming stage 5 "Signed into law" when some of the session's laws weren't signed
// (over a veto, without the signature, or no signature in the record) says it of laws that weren't.
const laws = bills.filter((b) => b.stage === 5);
const notSigned = laws.filter((b) => !T.signedLaw(b));
const T5 = S.stageText || {};
const signedNames = ["live", "final"].flatMap((k) => ["pipe", "long"].map((x) => (T5[k] && T5[k][x] ? T5[k][x][5] : ""))).filter((x) => /^Signed/.test(x || ""));
if (notSigned.length && signedNames.length) {
  fails.push(`${s}: stage 5 is named "${signedNames[0]}" (STATE.stageText) but ${notSigned.length} of ${laws.length} laws weren't signed by the record ` +
    `(${notSigned.slice(0, 4).map((b) => `${b.n[0]}: ${T.lawLine(b)}`).join("; ")})`);
}
// Every law line's claim, against the record: over a veto needs a veto, without the signature a line saying so.
const lawWrong = laws.filter((b) => {
  const l = T.lawLine(b);
  if (/over .*veto/.test(l)) return !b.dates.vetoed;
  if (/without/.test(l)) return !b.vers.some((v) => v.actions.some(([, t]) => T.NO_SIGNATURE.test(t)));
  if (/^Signed/.test(l)) return !T.hasSignature(b);
  return false;
}).map((b) => b.n[0]);
say(lawWrong, laws.length, 0, "law lines the record doesn't bear out");
// The governor's page: each law not made over a veto is in one of Signed, Became law, Without signature, and Signed only
// with a signature in the record. Past sessions are counted by build_data.py's governor_record() with stages.py's copies
// of the same tests (data_check.py sends them as sig: [has_signature, unsigned]): they must agree with the page's.
const kindsOf = (b) => ["signed", "law", "unsigned"].filter((k) => T.GOV_KINDS[k][1](b));
const govWrong = laws.filter((b) => !T.overriddenLaw(b)).filter((b) => kindsOf(b).length !== 1 || (kindsOf(b)[0] === "signed" && !T.hasSignature(b)))
  .map((b) => `${b.n[0]} (${kindsOf(b).join("+") || "none"})`);
say(govWrong, laws.length, 0, "laws the governor's page counts in no kind, two kinds, or as Signed without a signature");
const portWrong = laws.filter((b) => b.sig && (b.sig[0] !== T.hasSignature(b) || b.sig[1] !== T.vers_unsigned(b))).map((b) => b.n[0]);
say(portWrong, laws.length, 0, "laws where stages.py's has_signature()/unsigned() (past sessions on the governor's page) disagree with tracker.html's");

// 5. A bill the status words say ended early (STATE.endedNote: a floor defeat, a deadline; STATE.heldAction: "Held in the
// ... Committee") whose last step sends it on (a report, a floor placement, a passage): the ending was undone.
const BF = BillFacts.make(S, { WR: { floorVotesOver: () => false, lastYear: (x) => x + 1 }, today: () => "9999-12-31", fmtDate: (d) => d,
  facts: () => ({ session: s, current: !!input.current, upcoming: false }) });
const FORWARD = /^(?:REPORTED|PLACED ON FLOOR|PASSED|ADVANCED TO THIRD|ORDERED TO THIRD|Taken off the table|Removed from table|Taken from the table)/;
const undone = bills.filter((b) => b.stage <= 2).filter((b) => {
  let e = null;
  try { e = BF.endedOf(b); } catch (err) { return false; }
  if (!e) return false;
  const acts = b.vers.flatMap((v) => v.actions);
  const lastDay = acts.reduce((m, [d]) => (d > m ? d : m), "");
  const last = acts.filter(([d]) => d === lastDay).map(([, t]) => t);
  return last.length && last.every((t) => FORWARD.test(t));
}).map((b) => `${b.n[0]} ("${BF.endedOf(b).status}")`);
say(undone, bills.length, 1, "bills worded as ended early whose last step sends them on (LOOK only)");

// 6. Labels that count every law: "Signed" there says it of laws made without a signature or over a veto (the Statistics
// tab's sessions table and charts said "Signed into law" until 2026-11-23). Checked in the page's source.
const allLaws = [/<th>Signed/, /k-law"><\/i>Signed/, /\["s5", "Signed"\]/, /\["signed", "Signed", "l"\]/, /Signed into law or vetoed/];
for (const re of allLaws) if (re.test(page)) fails.push(`tracker.html labels every law "Signed" (${re})`);

console.log(JSON.stringify({ fails, looks }));
