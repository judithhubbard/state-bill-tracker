// New Jersey: the page's settings and rules that are particular to this state. build_data.py puts
// this file into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  // The public site, and the Worker that keeps published watchlists (none yet for New Jersey).
  publicSite: "https://statebilltracker.org/nj/",
  listsApi: "",
  houses: { S: "Senate", A: "Assembly" },
  // How a session is written: 2026–27.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // The governor's office, wherever it's the one to contact.
  govReach: `<a href="https://www.nj.gov/governor/" target="_blank" rel="noopener" data-contact="online|governor">Governor's website</a> · <a class="phone" href="tel:+16092926000" data-contact="call|governor">(609) 292-6000</a>`,

  billUrl(p, session = DATA.session) {
    return `https://www.njleg.gov/bill-search/${session}/${p}`;
  },
  textLinks(b) {
    // The Legislature's bill page has each version's text and statements.
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return b.vers.map((v) => link(STATE.billUrl(v.p), `${esc(v.p)} on the Legislature's site: text and statements`)).join("<br>");
  },

  // A two-year session ends the second Tuesday of January after its second year (YYYY-MM-DD).
  sessionEnds(session) {
    const jan1 = new Date(session + 2, 0, 1).getDay();
    return `${session + 2}-01-${String(1 + ((9 - jan1) % 7) + 7).padStart(2, "0")}`;
  },
  // The governor has 45 days after a bill is presented (NJ Constitution, Art. V, sec. I, para. 14).
  // The data has no presentation date, so this counts from the day it passed both houses. When the
  // session ends first, the governor has until the seventh day after, or the bill dies (a pocket veto).
  govDeadline(iso, session) {
    if (!iso) return null;
    const ymd = (dt) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
    const [y, m, d] = iso.split("-").map(Number);
    const [ey, em, ed] = STATE.sessionEnds(session).split("-").map(Number);
    const due = ymd(new Date(y, m - 1, d + 45)), last = ymd(new Date(ey, em - 1, ed + 7));
    return due < last ? due : last;
  },

  // Bills that passed both houses go straight to the governor; any others die when the session ends.
  passedBothBy: (session) => STATE.sessionEnds(session),
  passedBothGroup: ["Before the session ends", () => "These go to the governor once they pass both houses. Any still waiting die when the two-year session ends in January."],

  // The Legislature meets, with long breaks, until the session's last day in January.
  floorVotesEnd: false,

  // Stage names (the stage numbers are build_data.py's), and their tips.
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. Most bills never get out of committee.",
    "A committee approved it, and it's waiting for a vote of the full Senate or Assembly. Leaders decide which bills get a vote.",
    "Passed the Senate or the Assembly, but not both. Both houses have to pass the same text.",
    "Passed both houses.",
    "Passed both houses and sent to the governor, who has 45 days to sign it, veto it, or send it back with changes.",
    "Signed into law and given a chapter number.",
    "Vetoed by the governor. A conditional veto sends it back with changes: if both houses agree to them, it goes back to the governor. Overriding a veto takes two-thirds of each house.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the Senate or the Assembly, but not both.",
    "Passed both houses, but the records show it never went to the governor.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "This two-year session is over. Bills that didn't become law have to be reintroduced in the next session.",
};
