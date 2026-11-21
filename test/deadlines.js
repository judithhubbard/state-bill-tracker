#!/usr/bin/env node
// The governor's deadline in every state's profile (states/<st>/profile.js, STATE.govDeadline(delivered, session)) against
// the rule in the state's constitution: for each state, a few bills delivered mid-session, in the session's last days and
// after it adjourned (and on Saturdays, before Sundays and holidays where the constitution leaves them out), with the day
// the constitution gives. No browser: each profile runs in its own scope as /your-bills/ runs it (lists_pages/billfacts.js's runProfile()).
//   node test/deadlines.js            every state; fails on a state with no cases, or a case the profile gets wrong
//   node test/deadlines.js more.js    only the states in more.js (module.exports = {st: {rule, cases}}), for drafting cases
// A case is [session, delivered, expected, why] or [session, delivered, expected, why, known]: "known" says why the
// profile's answer differs from the constitution's and is printed as KNOWN, not a failure, until the profile is fixed
// (the owner decides each; the profile's code isn't changed here). expected null: no deadline (the bill dies or waits).
// Dates are ISO days. The rule's words are cited in each state's "rule".
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");

const CASES = {
  ak: {
    rule: "Alaska Const. Art. II, sec. 17: \"A bill becomes law if, while the legislature is in session, the governor neither signs nor vetoes it within fifteen days, Sundays excepted, after its delivery to him. If the legislature is not in session and the governor neither signs nor vetoes a bill within twenty days, Sundays excepted, after its delivery to him, the bill becomes law.\" In session or not is read at delivery.",
    cases: [
      [2025, "2025-03-03", "2025-03-20", "in session: 15 days, Sundays excepted"],
      [2025, "2026-02-07", "2026-02-25", "a Saturday, in session: 15 days, Sundays excepted"],
      [2025, "2025-05-20", "2025-06-06", "the adjournment day (2025-05-20), still in session: 15 days"],
      [2025, "2025-07-01", "2025-07-24", "after adjournment: 20 days, Sundays excepted"],
      [2025, "2026-08-15", "2026-09-08", "after the 2026 session, a Saturday: 20 days, Sundays excepted"],
      [2025, "2026-01-05", "2026-01-28", "between sessions (2026's opens 2026-01-20), not in session: 20 days"],
    ],
  },
  al: {
    rule: "Alabama Const. sec. 125: a bill not returned \"within six days, Sundays excepted, after it shall have been presented\" becomes law; \"Every bill presented to the governor within five days before the final adjournment of the legislature, or presented to him after final adjournment, which he does not approve within ten days after such final adjournment, shall not become a law\" (a pocket veto). Ten calendar days counted from the adjournment, whenever the bill arrived.",
    cases: [
      [2025, "2025-03-04", "2025-03-11", "in session: 6 days, Sundays excepted"],
      [2025, "2025-04-05", "2025-04-12", "a Saturday: 6 days, Sundays excepted"],
      [2025, "2025-05-12", "2025-05-24", "within five days before final adjournment (2025-05-14): 10 days after it"],
      [2025, "2025-05-20", "2025-05-24", "after final adjournment: 10 days after the adjournment, not after delivery"],
      [2026, "2026-04-09", "2026-04-19", "on the last day (2026-04-09): 10 days after adjournment"],
    ],
  },
  ar: {
    rule: "Arkansas Const. Art. 6, sec. 15: a bill not returned \"within five days, Sundays excepted, after it shall have been presented\" becomes law, \"unless the General Assembly, by their adjournment, prevent its return, in which case it shall become a law, unless he shall file the same with his objections in the office of the Secretary of State and give notice thereof by public proclamation within twenty days after such adjournment.\" Twenty calendar days from the adjournment (sine die, as the profile models it).",
    cases: [
      [2025, "2025-02-03", "2025-02-08", "in session: 5 days, Sundays excepted (a Saturday counts)"],
      [2025, "2025-02-13", "2025-02-19", "5 days across a Sunday"],
      [2025, "2025-05-01", "2025-05-25", "the 5 days run past sine die (2025-05-05): 20 days after it"],
      [2025, "2025-05-10", "2025-05-25", "presented after sine die: 20 days after the adjournment"],
      [2026, "2026-04-14", "2026-04-20", "fiscal session: 5 days, Sundays excepted"],
    ],
  },
  az: {
    rule: "Arizona Const. Art. V, sec. 7: a bill not returned \"within five days after it shall have been presented to him (Sunday excepted)\" becomes law, \"unless the legislature by its final adjournment prevents its return, in which case it shall be filed with his objections in the office of the secretary of state within ten days after such adjournment (Sundays excepted) or become a law.\" Ten days counted from the final adjournment. Sine die days from the Legislature's session summaries (azleg.gov SummaryComplete.pdf): 2025 June 27, 2026 June 13; a year the profile has no `dated` day for is taken to end June 30.",
    cases: [
      [2025, "2025-02-03", "2025-02-08", "in session: 5 days, Sundays excepted"],
      [2025, "2025-03-01", "2025-03-07", "a Saturday: 5 days, Sundays excepted"],
      [2025, "2025-06-27", "2025-07-09", "2025's sine die day (June 27): 10 days after it, Sundays excepted"],
      [2026, "2026-06-10", "2026-06-25", "5 days run past sine die (June 13): 10 days after it, Sundays excepted"],
      [2026, "2026-06-18", "2026-06-25", "after sine die: 10 days after the adjournment, not after delivery"],
      [2027, "2027-07-02", "2027-07-12", "a year with no sine die day yet (taken as June 30): 10 days after it"],
    ],
  },
  ca: {
    rule: "California Const. Art. IV, sec. 10(b): (1) a bill passed by the joint recess of the biennium's first year and in the governor's possession after it becomes law unless returned \"within 30 days after that date\"; (2) a bill passed before September 1 of the second year and in the governor's possession on or after September 1 unless returned \"on or before September 30\"; (3) \"Any other bill presented to the Governor that is not returned within 12 days becomes a statute\"; (5) \"If the 12th day ... is a Saturday, Sunday, or holiday, the period is extended to the next day that is not a Saturday, Sunday, or holiday.\" 2025's recess date is September 12 (the Legislature's calendar: governor's last day October 12).",
    cases: [
      [2025, "2025-03-05", "2025-03-17", "12 days, a Monday"],
      [2025, "2025-03-03", "2025-03-17", "the 12th day is a Saturday (2025-03-15): extended to Monday"],
      [2025, "2025-09-05", "2025-10-12", "in the governor's hands after the first year's recess (2025-09-12): 30 days after it"],
      [2025, "2026-01-07", "2026-01-20", "the 12th day is Martin Luther King Jr. Day (2026-01-19), a state holiday"],
      [2025, "2026-06-01", "2026-06-15", "the 12th day is a Saturday (2026-06-13): extended to Monday"],
      [2025, "2026-07-02", "2026-07-14", "second year, 12 days, a Tuesday"],
      [2025, "2026-08-25", "2026-09-30", "passed before September 1 of the second year, in hand on September 1: September 30"],
      [2025, "2026-03-19", "2026-04-01", "the 12th day is Cesar Chavez Day (2026-03-31), a day the Legislature's calendar observes"],
    ],
  },
  co: {
    rule: "Colorado Const. Art. IV, sec. 11: a bill not returned \"within ten days after it shall have been presented to him (Sundays excepted)\" becomes law, \"unless the general assembly shall, by their adjournment, prevent its return, in which case it shall be filed with his objections in the office of the secretary of state, within thirty days after such adjournment, or else become a law.\" Thirty days from the adjournment (2025: May 7, so June 6 for every bill after it, as the governor's office counts).",
    cases: [
      [2025, "2025-03-03", "2025-03-14", "in session: 10 days, Sundays excepted"],
      [2025, "2025-04-30", "2025-06-06", "the 10 days run past adjournment (2025-05-07): 30 days after it"],
      [2025, "2025-05-20", "2025-06-06", "presented after adjournment: 30 days after the adjournment"],
      [2026, "2026-02-14", "2026-02-26", "a Saturday: 10 days, Sundays excepted"],
      [2026, "2026-05-13", "2026-06-12", "on the last day (2026-05-13): 30 days after adjournment"],
    ],
  },
  ct: {
    rule: "Connecticut Const. Art. IV, sec. 15: a bill not transmitted \"within five calendar days, Sundays and legal holidays excepted, after the same shall have been presented to him\" becomes law; \"if the general assembly shall then have adjourned any regular or special session, the bill shall be a law unless the governor shall, within fifteen calendar days after the same has been presented to him, transmit it to the secretary with his objections.\" Legal holidays: C.G.S. sec. 1-4 (incl. Lincoln's Birthday, Washington's Birthday, Good Friday).",
    cases: [
      [2025, "2025-03-03", "2025-03-08", "5 days, a Saturday counts"],
      [2025, "2025-02-07", "2025-02-14", "across a Sunday and Lincoln's Birthday (2025-02-12)"],
      [2025, "2025-04-15", "2025-04-22", "across Good Friday (2025-04-18) and a Sunday"],
      [2025, "2025-06-02", "2025-06-17", "the 5 days end after adjournment (2025-06-04): 15 calendar days from presentment"],
      [2025, "2025-06-20", "2025-07-05", "after adjournment: 15 calendar days from presentment"],
      [2026, "2026-05-01", "2026-05-16", "the 5 days end after adjournment (2026-05-06): 15 days"],
      [2026, "2026-05-22", "2026-06-06", "after adjournment: 15 days"],
    ],
  },
  de: {
    rule: "Delaware Const. Art. III, sec. 18: a bill not returned \"within ten days, Sundays excepted, after it shall have been presented\" becomes law, \"unless the General Assembly shall, by final adjournment, prevent its return, in which case it shall not become a law without the approval of the Governor. No bill shall become a law after the final adjournment of the General Assembly, unless approved by the Governor within thirty days after such adjournment.\" The June 30 recess isn't final adjournment (the bills are \"continuously in Session until final adjournment\", sec. 18(b); final adjournment is the second regular session's sine die, Opinion of the Justices, Del. 1961), which comes at election day of the second year, when the General Assembly's term ends (AP, Oct. 26, 2018: Election Day \"marks the formal, final adjournment\").",
    cases: [
      [2025, "2025-03-03", "2025-03-14", "10 days, Sundays excepted"],
      [2025, "2025-06-30", "2025-07-11", "the June 30 recess isn't final adjournment: 10 days"],
      [2025, "2026-08-15", "2026-08-27", "a Saturday, between June and the election: 10 days"],
      [2025, "2026-10-30", "2026-12-03", "the 10 days run past final adjournment (election day, 2026-11-03): signed within 30 days after it, or it dies"],
      [2025, "2026-11-10", "2026-12-03", "presented after final adjournment: 30 days after it"],
    ],
  },
  fl: {
    rule: "Florida Const. Art. III, sec. 8(a): \"The governor shall have seven consecutive days to act on each bill after presentation. If during that period or on the seventh day the legislature adjourns sine die or takes a recess of more than thirty days, the governor shall have fifteen consecutive days from the date of presentation to act on the bill.\" Bills presented after sine die also have 15 days from presentation.",
    cases: [
      [2026, "2026-01-20", "2026-01-27", "in session: 7 days"],
      [2026, "2026-03-06", "2026-03-21", "the 7th day is sine die (2026-03-13): 15 days"],
      [2026, "2026-03-10", "2026-03-25", "the 7 days run past sine die: 15 days"],
      [2026, "2026-05-01", "2026-05-16", "presented after sine die: 15 days"],
      [2025, "2025-04-01", "2025-04-08", "in session (2025 ran to 2025-06-16): 7 days"],
      [2025, "2025-06-10", "2025-06-25", "the 7 days run past sine die (2025-06-16): 15 days"],
    ],
  },
  ga: {
    rule: "Georgia Const. Art. III, sec. V, para. XIII(a): a bill becomes law \"if the Governor approves or fails to veto the same within six days from the date any such bill or resolution is transmitted to the Governor unless the General Assembly adjourns sine die or adjourns for more than 40 days prior to the expiration of said six days. In the case of such adjournment, the same shall become law if approved or not vetoed by the Governor within 40 days from the date of any such adjournment.\" Six calendar days: Sundays are not excepted (the current text, 50constitutions.org's copy, has no exception; georgia.gov's \"Life of a Law\": \"6 consecutive days\").",
    cases: [
      [2025, "2025-02-03", "2025-02-09", "six calendar days (the sixth is a Sunday)"],
      [2025, "2025-03-27", "2025-04-02", "six calendar days across a Sunday"],
      [2025, "2025-03-31", "2025-05-14", "six days run past sine die (2025-04-04): 40 days after it"],
      [2025, "2025-04-20", "2025-05-14", "transmitted after sine die: 40 days after it"],
      [2025, "2026-03-21", "2026-03-27", "a Saturday: six calendar days"],
      [2025, "2026-04-02", "2026-05-12", "on sine die (2026-04-02): 40 days after it"],
    ],
  },
  hi: {
    rule: "Hawaii Const. Art. III, sec. 16: a bill not returned \"within ten days, excluding Saturdays, Sundays, holidays and any days in which the legislature is in recess prior to its adjournment\" becomes law; \"If any bill is presented to the governor less than ten days before adjournment sine die, or is presented to the governor after adjournment, it shall become law on the forty-fifth day\" (same exclusions) unless vetoed, with notice of intent by the 35th day. State holidays: HRS sec. 8-1 (incl. Presidents' Day, Prince Kuhio Day March 26, Good Friday), as the Department of Human Resources Development's yearly lists observe them. Recess days aren't known here and aren't counted out.",
    cases: [
      [2025, "2026-03-03", "2026-03-17", "10 working days, no holiday"],
      [2025, "2026-02-02", "2026-02-17", "10 working days across Presidents' Day (2026-02-16)"],
      [2025, "2026-03-20", "2026-04-07", "10 working days across Prince Kuhio Day (2026-03-26) and Good Friday (2026-04-03)"],
      [2025, "2026-04-28", "2026-07-15", "presented less than ten days before sine die (2026-05-08): the 45th working day after it"],
      [2025, "2026-05-20", "2026-07-15", "presented after sine die: the 45th working day after it"],
      [2025, "2025-05-02", "2025-07-09", "presented on sine die (2025-05-02): the 45th working day"],
    ],
  },
  ia: {
    rule: "Iowa Const. Art. III, sec. 16: a bill not returned \"within three days after it shall have been presented to him, Sundays excepted\" becomes law, unless adjournment prevents its return; \"Any bill submitted to the governor for his approval during the last three days of a session of the general assembly, shall be deposited by him in the office of the secretary of state within thirty days after the adjournment\" (signed, or it doesn't become law). Bills presented after adjournment are treated the same way.",
    cases: [
      [2025, "2025-02-07", "2025-02-11", "3 days, Sundays excepted"],
      [2025, "2025-03-01", "2025-03-05", "a Saturday: 3 days, Sundays excepted"],
      [2025, "2025-05-14", "2025-06-14", "in the last three days (sine die 2025-05-15): 30 days after adjournment"],
      [2025, "2025-06-01", "2025-06-14", "after adjournment: 30 days after it"],
      [2025, "2026-04-20", "2026-04-23", "second year, in session: 3 days"],
      [2025, "2026-05-02", "2026-06-02", "in the last three days (sine die 2026-05-03): 30 days after it"],
    ],
  },
  id: {
    rule: "Idaho Const. Art. IV, sec. 10: a bill not returned \"within five (5) days (Sundays excepted) after it shall have been presented\" becomes law, \"unless the legislature shall, by adjournment, prevent its return, in which case it shall be filed, with his objections, in the office of the secretary of state within ten (10) days after such adjournment (Sundays excepted) or become a law.\" For a bill presented after adjournment the ten days run from presentment (Cenarrusa v. Andrus, 99 Idaho 404, 1978).",
    cases: [
      [2025, "2025-02-03", "2025-02-08", "in session: 5 days, Sundays excepted"],
      [2025, "2025-03-01", "2025-03-07", "a Saturday: 5 days, Sundays excepted"],
      [2025, "2025-04-01", "2025-04-16", "the 5 days run past sine die (2025-04-04): 10 days after it, Sundays excepted"],
      [2025, "2025-04-10", "2025-04-22", "presented after adjournment: 10 days from presentment, Sundays excepted"],
      [2026, "2026-04-02", "2026-04-14", "on sine die (2026-04-02): 10 days after it, Sundays excepted"],
    ],
  },
  il: {
    rule: "Ill. Const. Art. IV, sec. 9(b): \"Any bill not so returned by the Governor within 60 calendar days after it is presented to him shall become law.\" No adjournment or Sunday exception.",
    cases: [
      [2025, "2025-03-10", "2025-05-09", "mid-session, 60 calendar days"],
      [2025, "2025-06-20", "2025-08-19", "after the May 31 spring adjournment"],
      [2025, "2025-12-15", "2026-02-13", "across the new year"],
      [2025, "2026-06-01", "2026-07-31", "second year, after the spring session"],
    ],
  },
  in: {
    rule: "Ind. Const. Art. 5, sec. 14(a)(2): \"the Governor shall have seven days after the day of presentment to act upon such bill\"; calendar days, in session or after; no pocket veto.",
    cases: [
      [2025, "2025-02-01", "2025-02-08", "mid-session, Saturday delivery, Sundays count"],
      [2025, "2025-04-24", "2025-05-01", "the 2025 session's last day"],
      [2025, "2025-04-28", "2025-05-05", "after adjournment: still seven days"],
      [2026, "2026-01-28", "2026-02-04", "short session, mid-session"],
      [2026, "2026-02-27", "2026-03-06", "the 2026 session's last day"],
    ],
  },
  ks: {
    rule: "Kan. Const. Art. 2, sec. 14(a): \"If any bill presented to the governor is not returned within ten calendar days after such presentation, it shall become a law\"; no pocket veto.",
    cases: [
      [2025, "2025-02-14", "2025-02-24", "mid-session"],
      [2025, "2025-03-27", "2025-04-06", "first adjournment day; the tenth day is a Sunday and still counts"],
      [2025, "2025-04-10", "2025-04-20", "veto session"],
      [2025, "2026-03-25", "2026-04-04", "second year, just before first adjournment"],
      [2025, "2026-04-10", "2026-04-20", "the biennium's sine die day"],
    ],
  },
  ky: {
    rule: "Ky. Const. sec. 88: \"If any bill shall not be returned by the Governor within ten days (Sundays excepted) after it shall have been presented to him, it shall be a law ..., unless the General Assembly, by their adjournment, prevent its return, in which case it shall be a law, unless disapproved by him within ten days after the adjournment\" (Sundays excepted after adjournment too: Ky. Court of Appeals, 1956).",
    cases: [
      [2026, "2026-02-02", "2026-02-13", "mid-session, Sundays excepted"],
      [2026, "2026-02-07", "2026-02-19", "Saturday delivery, two Sundays skipped"],
      [2026, "2026-04-14", "2026-04-27", "day before sine die (Apr 15): ten days run from the adjournment"],
      [2026, "2026-04-15", "2026-04-27", "delivered on the last day"],
      [2026, "2026-04-20", "2026-04-27", "delivered after sine die: ten days after the adjournment"],
      [2025, "2025-03-27", "2025-04-09", "day before the 2025 sine die (Mar 28)"],
    ],
  },
  la: {
    rule: "La. Const. Art. III, sec. 18(A): a bill becomes law if the governor \"fails to sign or veto it within ten days after delivery to him if the legislature is in session on the tenth day after such delivery, or within twenty days after delivery if the tenth day after delivery occurs after the legislature is adjourned.\" Session ends: Art. III, sec. 2 (odd years 60 calendar days from the second Monday in April; even years 85 from the second Monday in March).",
    cases: [
      [2025, "2025-05-01", "2025-05-11", "mid-session"],
      [2025, "2025-06-02", "2025-06-12", "tenth day is the session's last day (Jun 12): still ten"],
      [2025, "2025-06-03", "2025-06-23", "tenth day after adjournment: twenty"],
      [2025, "2025-06-20", "2025-07-10", "delivered after adjournment"],
      [2026, "2026-05-22", "2026-06-01", "tenth day is the last day (Jun 1)"],
      [2026, "2026-05-23", "2026-06-12", "tenth day after adjournment"],
    ],
  },
  ma: {
    rule: "Mass. Const. Amend. Art. XC (replacing Part II, c. 1, s. 1, art. II and Amend. Art. LVI): the governor has ten days after a bill is laid before him; not returned in ten days, it is law, unless the general court adjourns within the ten days (then it isn't). Calendar days.",
    cases: [
      [2025, "2025-07-01", "2025-07-11", "mid-session"],
      [2025, "2025-11-15", "2025-11-25", "Saturday delivery, calendar days"],
      [2025, "2026-07-31", "2026-08-10", "last day of formal sessions"],
    ],
  },
  md: {
    rule: "Md. Const. Art. II, sec. 17(b): presented while in session, \"not returned by the Governor with objections within six days (Sundays excepted)\" it is law; 17(c): \"Any Bill presented to the Governor within six days (Sundays excepted), prior to adjournment ... or after such adjournment, shall become law ... unless it is vetoed by the Governor within 30 days after its presentment\"; Art. III, sec. 30: presented within 20 days after adjournment. Session: 90 days from the second Wednesday of January (Art. III, sec. 14).",
    cases: [
      [2026, "2026-02-02", "2026-02-09", "mid-session, six days Sundays excepted"],
      [2026, "2026-04-04", "2026-04-11", "Saturday, seven counted days before sine die (Apr 13): six-day rule"],
      [2026, "2026-04-06", "2026-05-06", "six counted days before sine die: 30 days"],
      [2026, "2026-04-13", "2026-05-13", "sine die day: 30 days"],
      [2026, "2026-04-25", "2026-05-25", "after adjournment: 30 days"],
      [2026, null, "2026-06-02", "no delivery day: presented at the latest 20 days after adjournment, plus 30"],
    ],
  },
  me: {
    rule: "Me. Const. Art. IV, Pt. 3, sec. 2: not returned \"within 10 days (Sundays excepted) after it shall have been presented\", it is law \"unless the Legislature by their adjournment prevent its return, in which case it shall have such force and effect, unless returned within 3 days after their next meeting.\" Only a final adjournment prevents the return, not a temporary one such as the break before veto day (Opinion of the Justices, 2015 ME 107). The first session's adjournment holds bills until 3 days after the second session opens (the governor's release of January 7, 2026: 61 bills held since June 2025, due January 10). The second session's last meeting (veto day) ends the Legislature: no next meeting, so a held bill dies (\"Held by Governor\", then \"Died Upon Conclusion\": the 2024 pocket vetoes).",
    cases: [
      [2025, "2026-02-02", "2026-02-13", "mid-session, Sundays excepted"],
      [2025, "2026-02-07", "2026-02-19", "Saturday delivery"],
      [2025, "2026-04-02", "2026-04-14", "tenth day is the adjournment day (Apr 14)"],
      [2025, "2026-04-10", "2026-04-22", "the break before veto day (Apr 14 to 29) isn't a final adjournment: still 10 days"],
      [2025, "2026-04-28", null, "the day before the 132nd's last meeting (Apr 29): no next meeting, so a held bill dies"],
      [2025, "2025-06-20", "2026-01-10", "the first session adjourns (June 25, 2025) before the tenth day: 3 days after the second session opens (Jan 7, 2026)"],
      [2025, "2025-06-25", "2026-01-10", "enacted on the first session's last day: held to January"],
    ],
  },
  mi: {
    rule: "Mich. Const. Art. IV, sec. 33: \"the governor shall have 14 days measured in hours and minutes from the time of presentation in which to consider it\"; not returned in that period, \"the legislature continuing in session\", it is law. Calendar days: Sundays count (the 1908 constitution's \"Sundays excepted\" was dropped; Attorney General opinions).",
    cases: [
      [2025, "2025-06-02", "2025-06-16", "mid-session, 14 calendar days"],
      [2025, "2025-03-01", "2025-03-15", "Saturday delivery"],
      [2025, "2026-12-18", "2027-01-01", "end of the biennium"],
    ],
  },
  mn: {
    rule: "Minn. Const. Art. IV, sec. 23: not returned \"within three days (Sundays excepted) after it is presented\" it is law; \"Any bill passed during the last three days of a session may be presented to the governor during the three days following the day of final adjournment and becomes law if the governor signs and deposits it ... within 14 days after the adjournment\". Adjournment: Monday after the third Saturday in May (Minn. Stat. 3.05).",
    cases: [
      [2025, "2025-03-14", "2025-03-18", "mid-session Friday, Sunday skipped"],
      [2025, "2025-05-14", "2025-05-17", "before the last three days"],
      [2025, "2025-05-19", "2025-06-02", "last day (May 19): 14 days after adjournment"],
      [2025, "2025-05-21", "2025-06-02", "presented after adjournment, passed in the last days"],
      [2025, "2026-03-14", "2026-03-18", "second year, Saturday delivery"],
      [2025, "2026-05-18", "2026-06-01", "second year's last day"],
    ],
  },
  mo: {
    rule: "Mo. Const. Art. III, sec. 31: the governor returns a bill \"within fifteen days after presentment\"; \"When the general assembly adjourns, or recesses for a period of thirty days or more,\" the governor has forty-five days (from May 30, the constitutional adjournment, Art. III, sec. 20: July 14). Not returned in time, it is law.",
    cases: [
      [2025, "2025-03-03", "2025-03-18", "mid-session"],
      [2025, "2025-05-16", "2025-07-14", "last day to pass bills: 45 days from May 30"],
      [2026, "2026-03-02", "2026-03-17", "mid-session"],
      [2026, "2026-05-14", "2026-05-29", "fifteen days end before the May 30 adjournment"],
      [2026, "2026-06-10", "2026-07-14", "after adjournment"],
    ],
  },
  ms: {
    rule: "Miss. Const. sec. 72: not returned \"within five (5) days (Sundays excepted) after it has been presented\" it is law, unless \"the Legislature, by adjournment, prevented its return\", in which case \"the Governor shall veto it within fifteen (15) days (Sundays excepted) after it is presented to him\".",
    cases: [
      [2026, "2026-02-06", "2026-02-12", "mid-session, Sunday skipped"],
      [2026, "2026-04-09", "2026-04-15", "fifth day is the last day (Apr 15)"],
      [2026, "2026-04-13", "2026-04-30", "adjournment before the fifth day: 15 days, Sundays excepted, from presentment"],
      [2026, "2026-04-14", "2026-05-01", "day before adjournment"],
      [2026, "2026-04-20", "2026-05-07", "presented after adjournment"],
      [2025, "2025-04-01", "2025-04-18", "two days before the 2025 adjournment (Apr 3)"],
    ],
  },
  mt: {
    rule: "Mont. Const. Art. VI, sec. 10(3): \"If he does not sign or veto the bill within 10 days after its delivery to him, it shall become law\"; calendar days, in session or after.",
    cases: [
      [2025, "2025-02-07", "2025-02-17", "mid-session"],
      [2025, "2025-04-30", "2025-05-10", "the session's last day"],
      [2025, "2025-05-20", "2025-05-30", "delivered after adjournment"],
    ],
  },
  nc: {
    rule: "N.C. Const. Art. II, sec. 22(7): a bill not returned \"within 10 days after it shall have been presented\" is law, unless the General Assembly has adjourned (a) for more than 30 days jointly or (b) sine die, \"in which case it shall become a law unless, within 30 days after such adjournment, it is returned\". Calendar days, no Sunday or holiday exception. The 2025-26 session is taken to adjourn sine die December 31, 2026 (adjournments of more than 30 days within it aren't known).",
    cases: [
      [2025, "2025-06-20", "2025-06-30", "mid-session: 10 calendar days"],
      [2025, "2025-07-25", "2025-08-04", "10th day a Monday; weekends count"],
      [2025, "2025-12-27", "2026-01-06", "between the two years: still one session"],
      [2025, "2026-12-15", "2026-12-25", "10th day on Christmas: no holiday exception"],
      [2025, "2026-12-25", "2027-01-30", "10 days run past the Dec 31 adjournment: 30 days after it"],
    ],
  },
  nd: {
    rule: "N.D. Const. Art. V, sec. 9: \"While the legislative assembly is in session, a bill becomes law if the governor neither signs nor vetoes it within three legislative days after its delivery to the governor. If the legislative assembly is not in session, a bill becomes law if the governor neither signs nor vetoes it within fifteen days, Saturdays and Sundays excepted, after its delivery to the governor.\" Legislative days are taken as Monday-Friday (the Assembly's usual week). 2025's session adjourned May 2 (the profile's date). A bill whose three legislative days outrun the adjournment is read as not in session: 15 weekdays from delivery (the Legislative Council's newsletter of May 9, 2025: \"After the Legislative Assembly has adjourned, the Governor has 15 days from the date of delivery to act on a bill, Saturdays and Sundays excepted.\").",
    cases: [
      [2025, "2025-03-10", "2025-03-13", "mid-session, delivered Monday: Tue-Thu"],
      [2025, "2025-04-14", "2025-04-17", "mid-session, delivered Monday"],
      [2025, "2025-03-13", "2025-03-18", "delivered Thursday: Fri, Mon, Tue (Saturday is not a legislative day)"],
      [2025, "2025-04-30", "2025-05-21", "delivered in the last days: 15 days, Saturdays and Sundays excepted, from delivery"],
      [2025, "2025-05-05", "2025-05-26", "delivered after adjournment: 15 weekdays from delivery (Memorial Day not excepted)"],
    ],
  },
  ne: {
    rule: "Neb. Const. Art. IV, sec. 15: a bill not returned \"within five days (Sundays excepted) after it shall have been presented\" becomes law, \"unless the Legislature by their adjournment prevents its return, in which case it shall be filed with his or her objections in the office of the Secretary of State within five days after such adjournment, or become a law.\" The five days after adjournment are calendar days. Each session's sine die adjournment counts (2025-06-02, 2026-04-17).",
    cases: [
      [2025, "2025-03-14", "2025-03-20", "mid-session, delivered Friday: Sunday skipped"],
      [2025, "2025-05-27", "2025-06-02", "fifth day is the adjournment day itself"],
      [2025, "2025-05-29", "2025-06-07", "five days run past the June 2 adjournment: five days after it"],
      [2025, "2026-02-13", "2026-02-19", "second session, mid-session"],
      [2025, "2026-04-16", "2026-04-22", "five days run past the April 17 adjournment"],
    ],
  },
  nh: {
    rule: "N.H. Const. Part II, Art. 44: a bill not returned \"within five days (Sundays excepted) after it shall have been presented\" is law, \"unless the legislature, by their adjournment, prevent its return, in which case it shall not be a law.\" The General Court doesn't adjourn sine die in June (veto days follow in the fall), so the five days apply all year. (The data's date is enrollment, not presentment.)",
    cases: [
      [2025, "2025-03-13", "2025-03-19", "mid-session: Sunday skipped"],
      [2025, "2025-06-26", "2025-07-02", "last floor day: still five days (no sine die)"],
      [2025, "2025-07-01", "2025-07-07", "July 4 counts: only Sundays are excepted"],
    ],
  },
  nj: {
    rule: "N.J. Const. Art. V, sec. I, para. 14(c): the governor's period runs \"from the date of presentation until noon of the forty-fifth day next following\" (or the day the house of origin reconvenes, if in temporary adjournment: not known here), except \"(2) any bill passed between the forty-fifth day and the tenth day preceding the expiration of the second legislative year shall be returned ... not later than noon of the day next preceding the expiration\" and \"(3) any bill passed within 10 days preceding the expiration ... shall become law only if the Governor signs it prior to noon of the seventh day following such expiration\". The 2024-25 Legislature expires the second Tuesday of January 2026 (Jan 13). The data's date is passage, which the rule also counts from for (2) and (3).",
    cases: [
      [2024, "2025-03-03", "2025-04-17", "mid-session: 45 days"],
      [2024, "2025-11-20", "2026-01-04", "passed 54 days before expiration: 45 days, before it"],
      [2024, "2025-12-15", "2026-01-12", "passed 29 days before expiration: by the day before (Jan 12)"],
      [2024, "2026-01-08", "2026-01-20", "passed 5 days before expiration: sign by the 7th day after it (pocket veto)"],
      [2026, "2026-06-30", "2026-08-14", "2026-27 session, mid-session: 45 days"],
    ],
  },
  nm: {
    rule: "N.M. Const. Art. IV, sec. 22: a bill not returned \"within three days, Sundays excepted, after being presented\" becomes law; \"Every bill presented to the governor during the last three days of the session shall be approved or disapproved by him within twenty days after the adjournment ... Unless approved by the governor, such bill shall not become a law.\" Sessions: 60 days from the third Tuesday of January in odd years (2025: Jan 21 to Mar 22), 30 in even (2026: Jan 20 to Feb 19).",
    cases: [
      [2025, "2025-02-20", "2025-02-24", "mid-session, delivered Thursday: Sunday skipped"],
      [2025, "2025-03-20", "2025-04-11", "last three days: 20 days after the March 22 adjournment"],
      [2025, "2025-03-22", "2025-04-11", "last day: 20 days after adjournment"],
      [2026, "2026-02-06", "2026-02-10", "short session, delivered Friday"],
      [2026, "2026-02-18", "2026-03-11", "last three days of the 2026 session: 20 days after Feb 19"],
    ],
  },
  nv: {
    rule: "Nev. Const. Art. 4, sec. 35: a bill not returned \"within five days after it shall have been presented to him (Sunday excepted) exclusive of the day on which he received it\" becomes law, \"unless the Legislature by its final adjournment prevent such return, in which case it shall be a law, unless the Governor, within ten days next after the adjournment (Sundays excepted) shall file such bill, with his objections\". Regular sessions are 120 days from the first Monday of February of odd years (2027: Feb 1 to May 31). Cases use 2027 because the profile returns no deadline once the day has passed (isoToday); from June 2027 they need a fixed 'today'.",
    cases: [
      [2027, "2027-03-05", "2027-03-11", "mid-session, delivered Friday: Sunday skipped"],
      [2027, "2027-04-08", "2027-04-14", "mid-session"],
      [2027, "2027-05-21", "2027-05-27", "near the end, still before adjournment"],
      [2027, "2027-05-27", "2027-06-11", "five days run past the May 31 adjournment: ten days after it, Sundays excepted"],
      [2027, "2027-05-31", "2027-06-11", "delivered on the last day: ten days after adjournment, Sundays excepted"],
    ],
  },
  ny: {
    rule: "N.Y. Const. Art. IV, sec. 7: a bill not returned \"within ten days (Sundays excepted) after it shall have been presented\" is law \"unless the legislature shall, by their final adjournment, prevent its return ... No bill shall become a law after the final adjournment of the legislature, unless approved by the governor within thirty days after such adjournment.\" The Legislature's year ends December 31 (its final adjournment, as the profile estimates).",
    cases: [
      [2025, "2025-11-10", "2025-11-21", "ten days, Sundays excepted"],
      [2025, "2025-12-15", "2025-12-26", "Christmas counts: only Sundays are excepted"],
      [2025, "2025-12-19", "2025-12-31", "tenth day is December 31"],
      [2025, "2025-12-24", "2026-01-30", "ten days run past the year's end: 30 days after it"],
      [2025, "2026-12-28", "2027-01-30", "second year's end: 30 days after it"],
    ],
  },
  oh: {
    rule: "Ohio Const. Art. II, sec. 16: a bill not returned \"within ten days, Sundays excepted, after being presented\" becomes law, \"unless the general assembly by adjournment prevents its return; in which case, it becomes law unless, within ten days after such adjournment, it is filed by him, with his objections in writing, in the office of the secretary of state.\" Only an adjournment sine die prevents the return, and a General Assembly's terms end December 31 of its second year, but the governor's practice counts ten days, Sundays excepted, from delivery even across it: HB 315 of the 135th, sent December 23, 2024, had a reported deadline of Friday, January 3, 2025 (signed January 2); five bills of the 134th sent December 22, 2022 were signed January 2-3, 2023 (the LSC API's to_governor_date and governor_signed_date). So delivery counts, as in session.",
    cases: [
      [2025, "2025-06-30", "2025-07-11", "mid-session: ten days, Sundays excepted"],
      [2025, "2025-12-20", "2026-01-01", "across the first year's end: the same General Assembly"],
      [2025, "2026-12-18", "2026-12-30", "tenth day before the General Assembly ends"],
      [2025, "2026-12-21", "2027-01-01", "ten days run past Dec 31, 2026: still counted from delivery, as the governor does"],
      [2025, "2026-12-28", "2027-01-08", "delivered in the last days: ten days, Sundays excepted, from delivery"],
      [2023, "2024-12-23", "2025-01-03", "HB 315 of the 135th: sent Dec 23, 2024, deadline reported as Jan 3, 2025"],
    ],
  },
  ok: {
    rule: "Okla. Const. Art. VI, sec. 11: a bill not returned \"within five days (Sunday excepted) after it shall have been presented\" is law, \"unless the Legislature shall, by their final adjournment, prevent its return, in which case it shall not become a law without the approval of the Governor. No bill shall become a law after the final adjournment of the Legislature, unless approved by the Governor within fifteen days after such adjournment.\" Each year's session adjourns sine die (2025-05-30, 2026-05-14, the profile's dates).",
    cases: [
      [2025, "2025-04-10", "2025-04-16", "mid-session: Sunday skipped"],
      [2025, "2025-05-28", "2025-06-14", "five days run past the May 30 adjournment: 15 days after it"],
      [2025, "2026-05-08", "2026-05-14", "fifth day is the adjournment day"],
      [2025, "2026-05-12", "2026-05-29", "five days run past the May 14 adjournment"],
      [2025, "2026-05-20", "2026-05-29", "presented after adjournment: 15 days after it"],
    ],
  },
  or: {
    rule: "Or. Const. Art. V, sec. 15b: a bill not returned \"within five days, Saturdays and Sundays excepted\" after presentment becomes law; if the general adjournment prevents its return, the governor has \"thirty days, Saturdays and Sundays excepted, after the adjournment\" to file it with objections (holidays aren't excepted). 2025's session: Jan 13 to June 27.",
    cases: [
      [2025, "2025-04-10", "2025-04-17", "mid-session: weekends skipped"],
      [2025, "2025-06-20", "2025-06-27", "fifth weekday is the adjournment day"],
      [2025, "2025-06-24", "2025-08-08", "five days run past June 27: 30 weekdays after adjournment (July 4 counts)"],
      [2025, "2025-07-01", "2025-08-08", "presented after adjournment: 30 weekdays after the adjournment"],
    ],
  },
  pa: {
    rule: "Pa. Const. Art. IV, sec. 15: a bill not returned \"within ten days after it shall have been presented\" is law, \"unless the General Assembly, by their adjournment, prevent its return, in which case it shall be a law, unless he shall file the same, with his objections ... within thirty days after such adjournment.\" Calendar days, no Sunday or holiday exception. The session ends November 30 of the even year.",
    cases: [
      [2025, "2025-06-02", "2025-06-12", "mid-session: 10 calendar days"],
      [2025, "2025-10-01", "2025-10-11", "tenth day a Saturday: still counts"],
      [2025, "2025-12-28", "2026-01-07", "across the first year's end"],
      [2025, "2026-11-20", "2026-11-30", "tenth day is the session's last"],
      [2025, "2026-11-25", "2026-12-30", "ten days run past Nov 30: 30 days after adjournment"],
    ],
  },
  ri: {
    rule: "R.I. Const. Art. IX, sec. 14: a bill not returned \"within six days (Sundays excepted) after it shall have been presented\" becomes operative \"unless the general assembly, by adjournment, prevents its return, in which case it shall become operative unless transmitted by the governor to the secretary of state, with his disapproval in writing within ten days after such adjournment.\" The General Assembly recesses in June rather than adjourning, so the six days apply all year.",
    cases: [
      [2025, "2025-03-12", "2025-03-19", "mid-session: Sunday skipped"],
      [2025, "2025-06-20", "2025-06-27", "the session's last days: the June recess isn't an adjournment"],
      [2025, "2025-06-30", "2025-07-07", "July 4 counts: only Sundays are excepted"],
    ],
  },
  sc: {
    rule: "S.C. Const. Art. IV §21: a bill not returned \"within five days after it shall have been presented to him, Sundays excepted\" becomes law, \"unless the General Assembly, by adjournment, prevent its return, in which case it shall have such force and effect unless returned within two days after their next meeting.\" Holidays count. The sine die resolution keeps the houses able to receive returns, so the five days apply after the second Thursday of May too.",
    cases: [
      [2025, "2025-03-03", "2025-03-08", "mid-session: 5 days, Sundays excepted"],
      [2025, "2025-05-08", "2025-05-14", "ratified on sine die day (May 8): Sunday May 11 skipped"],
      [2025, "2026-05-13", "2026-05-19", "second year's last days: Sunday May 17 skipped"],
      [2025, "2025-06-02", "2025-06-07", "after sine die, while the houses return under the sine die resolution"],
    ],
  },
  sd: {
    rule: "S.D. Const. Art. IV §4 (as amended Nov. 5, 2002; sdlegislature.gov's text): \"Whenever the Legislature is in session, any bill presented to the Governor for signature shall become law when the Governor signs the bill or fails to veto the bill within five days, not including Saturdays, Sundays, or holidays, of presentation.\" \"Whenever a bill has been presented to the Governor and the Legislature has adjourned sine die or recessed for more than five days within five days from presentation, the bill shall become law when the Governor signs the bill or fails to veto it within fifteen days after such adjournment or start of the recess.\" The recess is from the last regular day to veto day; the fifteen are calendar days from it. Holidays (SDCL 1-5-1) in the session: Martin Luther King Jr. Day, the third Monday in February.",
    cases: [
      [2026, "2026-02-02", "2026-02-09", "mid-session: 5 days, not counting Saturday and Sunday"],
      [2026, "2026-01-15", "2026-01-23", "across a weekend and Martin Luther King Jr. Day (2026-01-19)"],
      [2026, "2026-02-11", "2026-02-19", "across a weekend and the third Monday in February (2026-02-16)"],
      [2026, "2026-03-04", "2026-03-11", "five weekdays end before the last regular day (Mar 12)"],
      [2026, "2026-03-06", "2026-03-27", "five weekdays run past the last day (Mar 12): 15 days after it"],
      [2026, "2026-03-09", "2026-03-27", "five days run past the last day: 15 days after adjournment"],
      [2025, "2025-03-11", "2025-03-28", "2025: last day Mar 13, 15 days after"],
      [2026, "2026-03-16", "2026-03-27", "delivered after the last day: still 15 days after it"],
    ],
  },
  tn: {
    rule: "Tenn. Const. Art. III §18: a bill not returned \"within ten calendar days (Sundays excepted) after it shall have been presented\" becomes law; if the General Assembly's adjournment prevents its return, it becomes law unless the governor files it with objections with the Secretary of State \"within said ten-day period\" (no pocket veto). Holidays count.",
    cases: [
      [2025, "2025-03-03", "2025-03-14", "mid-session: 10 days, Sundays excepted"],
      [2025, "2026-04-20", "2026-05-01", "straddles adjournment (Apr 23): the same ten days"],
      [2025, "2026-05-04", "2026-05-15", "delivered after adjournment"],
      [2025, "2025-05-23", "2025-06-04", "Memorial Day (May 26) counts; Sundays May 25 and Jun 1 skipped"],
    ],
  },
  tx: {
    rule: "Tex. Const. Art. IV §14: a bill not returned \"within ten days after it shall have been presented to him (Sundays excepted)\" becomes law, \"unless the Legislature, by its adjournment, prevent its return, in which case it shall be a law, unless he shall file the same, with his objections, in the office of the Secretary of State and give notice thereof by public proclamation within twenty days after such adjournment.\" The 2025 regular session ended June 2 (day 140); the veto deadline was June 22.",
    cases: [
      [2025, "2025-03-03", "2025-03-14", "mid-session: 10 days, Sundays excepted"],
      [2025, "2025-05-21", "2025-06-02", "ten days end on the session's last day"],
      [2025, "2025-05-22", "2025-06-22", "ten days run past June 2: 20 days after adjournment"],
      [2025, "2025-06-10", "2025-06-22", "delivered after adjournment"],
    ],
  },
  us: {
    rule: "U.S. Const. Art. I §7: a bill not returned \"within ten Days (Sundays excepted) after it shall have been presented\" is law, \"unless the Congress by their Adjournment prevent its Return, in which Case it shall not be a Law\" (pocket veto: the same ten days, then it dies). Holidays count.",
    cases: [
      [2025, "2025-07-03", "2025-07-15", "July 4 counts; Sundays Jul 6 and 13 skipped"],
      [2025, "2025-12-20", "2026-01-01", "over the holidays: Dec 25 and Jan 1 count"],
      [2025, "2026-12-28", "2027-01-08", "presented as the 119th Congress ends (Jan 3, 2027): the ten days still end Jan 8; with Congress gone, a pocket veto"],
    ],
  },
  ut: {
    rule: "Utah Const. Art. VII §8: a bill not returned \"within ten days after it shall have been presented to him (Sundays excepted)\" becomes law, \"unless the Legislature by adjournment prevents its return, in which case it shall become a law unless the governor within twenty days after adjournment\" files it with objections with the Lieutenant Governor. Twenty calendar days from adjournment (2026: Mar 6, so Mar 26).",
    cases: [
      [2026, "2026-02-02", "2026-02-13", "mid-session: 10 days, Sundays excepted"],
      [2026, "2026-02-23", "2026-03-06", "ten days end on the last day"],
      [2026, "2026-03-02", "2026-03-26", "ten days run past adjournment: 20 days after it"],
      [2026, "2026-03-16", "2026-03-26", "delivered after adjournment: still 20 days after adjournment"],
      [2025, "2025-03-06", "2025-03-27", "2025: adjourned Mar 7, 20 days after"],
    ],
  },
  va: {
    rule: "Va. Const. Art. V §6(b)-(c): the governor \"shall have seven days in which to act on the bill after it is presented\" (calendar days; Sundays count); \"When there are fewer than seven days remaining in the regular or special session\", or after it, \"the Governor shall have thirty days from the date of adjournment\". 2025 adjourned Feb 22 (deadline Mar 24); 2026 adjourned Mar 14 (deadline Apr 13).",
    cases: [
      [2025, "2025-01-27", "2025-02-03", "mid-session: 7 days"],
      [2025, "2025-02-20", "2025-03-24", "2 days left: 30 days from adjournment"],
      [2025, "2025-03-01", "2025-03-24", "delivered after adjournment"],
      [2026, "2026-02-02", "2026-02-09", "mid-session: 7 days"],
      [2026, "2026-03-10", "2026-04-13", "4 days left: 30 days from adjournment"],
      [2026, "2026-03-07", "2026-03-14", "exactly seven days left (Mar 8-14), not fewer: the seven-day rule"],
      [2026, "2026-03-04", "2026-03-11", "ten days left: 7 days (LIS's \"Governor's Action Deadline\" line on bills communicated March 4, 2026)"],
      [2024, "2024-03-01", "2024-03-08", "eight days left (2024 adjourned Mar 9): 7 days, as LIS's deadline lines give"],
    ],
  },
  vt: {
    rule: "Vt. Const. ch. II §11: a bill not returned \"within five days (Sundays excepted) after it shall have been presented\" becomes law, \"unless the General Assembly by adjournment within three days after the presentation of such bill shall prevent its return, in which case it shall not become a law\". Holidays count. The General Assembly adjourns to a veto session, so bills delivered after the May/June adjournment still get five days.",
    cases: [
      [2025, "2025-03-14", "2025-03-20", "mid-session: 5 days, Sunday Mar 16 skipped"],
      [2025, "2025-06-20", "2025-06-26", "delivered after the 2025 adjournment (Jun 16)"],
      [2025, "2026-01-30", "2026-02-05", "second year: Sunday Feb 1 skipped"],
      [2025, "2025-07-01", "2025-07-07", "July 4 counts"],
    ],
  },
  wa: {
    rule: "Wash. Const. Art. III §12: a bill not returned \"within five days after it shall have been presented to him (Sundays excepted)\" becomes law, \"unless the legislature, by its adjournment, shall prevent its return, in which case it shall become a law unless the governor, within twenty days next after such adjournment, Sundays excepted, shall file the same, with his objections\". 2025 adjourned Apr 27 (deadline May 20); 2026 adjourned Mar 12 (Apr 4).",
    cases: [
      [2025, "2025-02-03", "2025-02-08", "mid-session: 5 days, Sundays excepted"],
      [2025, "2025-04-21", "2025-04-26", "five days end before adjournment"],
      [2025, "2025-04-24", "2025-05-20", "five days run past Apr 27: 20 days (Sundays excepted) after adjournment"],
      [2025, "2026-03-10", "2026-04-04", "second year: adjourned Mar 12"],
      [2025, "2025-05-01", "2025-05-20", "delivered after adjournment: still 20 days after adjournment"],
    ],
  },
  wi: {
    rule: "Wis. Const. Art. V §10(3): a bill not returned \"within 6 days (Sundays excepted) after it shall have been presented\" becomes law \"unless the legislature, by final adjournment, prevents the bill's return, in which case it shall not become a law\" (final adjournment is the biennium's end, in January of the next odd year). Holidays count.",
    cases: [
      [2025, "2025-07-03", "2025-07-10", "July 4 counts; Sunday Jul 6 skipped"],
      [2025, "2026-03-20", "2026-03-27", "after the last floor period: still 6 days"],
      [2025, "2025-02-14", "2025-02-21", "mid-session: Sunday Feb 16 skipped"],
    ],
  },
  wv: {
    rule: "W. Va. Const. Art. VII §14: a bill not returned \"within five days, Sundays excepted, after it shall have been presented\" becomes law, \"unless the Legislature, by adjournment, prevent its return, in which case it shall be filed with his objections in the office of the secretary of state within fifteen days, Sundays excepted, after such adjournment, or become a law.\" 2026 adjourned Mar 14 (deadline Apr 1); 2025 Apr 12 (Apr 30).",
    cases: [
      [2026, "2026-02-02", "2026-02-07", "mid-session: 5 days, Sundays excepted"],
      [2026, "2026-03-11", "2026-04-01", "five days run past Mar 14: 15 days (Sundays excepted) after adjournment"],
      [2026, "2026-03-20", "2026-04-01", "delivered after adjournment"],
      [2025, "2025-03-03", "2025-03-08", "2025 mid-session"],
      [2025, "2025-04-10", "2025-04-30", "2025: adjourned Apr 12"],
    ],
  },
  wy: {
    rule: "Wyo. Const. Art. 4 §8: a bill not returned \"within three days (Sundays excepted) after its presentation\" becomes law, \"unless the legislature by its final adjournment prevents its return, in which case it shall become a law, unless the governor within fifteen days after such adjournment\" files it with objections with the Secretary of State. Fifteen calendar days from adjournment (2025: Mar 6, so Mar 21).",
    cases: [
      [2025, "2025-02-03", "2025-02-06", "mid-session: 3 days"],
      [2025, "2025-02-07", "2025-02-11", "Sunday Feb 9 skipped"],
      [2025, "2025-03-03", "2025-03-06", "three days end on the last day"],
      [2025, "2025-03-05", "2025-03-21", "three days run past adjournment: 15 days after it"],
      [2026, "2026-03-04", "2026-03-21", "budget session: adjourned Mar 6"],
      [2025, "2025-03-10", "2025-03-21", "delivered after adjournment: still 15 days after adjournment"],
    ],
  },
};

// The profile in its own scope, as BillFacts.runProfile() runs it, but with "today" the day the bill was delivered, so
// a case gives the same answer whenever it's run (Nevada's returns no deadline once the day has passed).
function load(st, session, today) {
  const src = fs.readFileSync(path.join(ROOT, "states", st, "profile.js"), "utf8");
  let S = null;
  const DATA = { session, current: true, upcoming: false };
  const fmtDate = (d) => (d ? new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "");
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const lastYear = (s) => s + ((S && S.years) || 2) - 1;
  const span = (s) => (S && S.sessionLabel ? S.sessionLabel(s) : String(s));
  const monthDay = (d) => new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)).toLocaleDateString("en-US", { month: "long", day: "numeric" });
  S = new Function("fmtDate", "esc", "isoToday", "lastYear", "span", "monthDay", "DATA", "BILLS", `${src}\n;return STATE;`)(
    fmtDate, esc, () => today, lastYear, span, monthDay, DATA, []);
  if (!S || typeof S.govDeadline !== "function") throw new Error(`${st}: profile.js has no govDeadline()`);
  return S;
}

function run(table) {
  let fails = 0, known = 0, ok = 0;
  const states = fs.readdirSync(path.join(ROOT, "states")).filter((d) => fs.existsSync(path.join(ROOT, "states", d, "profile.js")));
  const only = table !== CASES;
  for (const st of states) {
    const t = table[st];
    if (!t) {
      if (!only) { console.log(`FAIL ${st}: no deadline cases in test/deadlines.js`); fails++; }
      continue;
    }
    for (const [session, deliv, want, why, isKnown] of t.cases) {
      let got;
      try { got = load(st, session, deliv).govDeadline(deliv, session); } catch (e) { got = `error: ${e.message}`; }
      got = got ?? null;
      if (got === want) {
        if (isKnown) console.log(`NOW RIGHT ${st} ${session} delivered ${deliv}: ${got} (drop the "known" note: ${isKnown})`);
        ok++;
      } else if (isKnown) {
        console.log(`KNOWN ${st} ${session} delivered ${deliv}: profile ${got}, constitution ${want} (${why}). ${isKnown}`);
        known++;
      } else {
        console.log(`FAIL ${st} ${session} delivered ${deliv}: profile ${got}, constitution ${want} (${why})`);
        fails++;
      }
    }
  }
  console.log(`Governor's deadlines: ${ok} right, ${known} known differences, ${fails} failing.`);
  return fails;
}

if (require.main === module) {
  const extra = process.argv.slice(2);
  const table = extra.length ? Object.assign({}, ...extra.map((f) => require(path.resolve(f)))) : CASES;
  process.exit(run(table) ? 1 : 0);
}
module.exports = { CASES, run };
