// New York: the page's settings and rules that are particular to this state. build_data.py puts
// this file into every page, just before the main script; tracker.html reads it as STATE.
const STATE = {
  // The public site, and the Worker that keeps published watchlists.
  publicSite: "https://albanybilltracker.org/",
  listsApi: "https://albany-lists.lists-worker.workers.dev",
  houses: { S: "Senate", A: "Assembly" },
  // How a session is written: 2025–26.
  sessionLabel: (s) => `${s}–${String(s + 1).slice(2)}`,
  // The governor's office, wherever it's the one to contact.
  govReach: `<a href="https://www.governor.ny.gov/content/governor-contact-form" target="_blank" rel="noopener" data-contact="online|governor">Send a message online</a> · <a class="phone" href="tel:+15184748390" data-contact="call|governor">(518) 474-8390</a>`,

  billUrl(p, session = DATA.session) {
    return `https://www.nysenate.gov/legislation/bills/${session}/${p.replace(/[A-Z]$/, "")}`;
  },
  // The Senate's bill page has the text and, for Senate bills, the sponsor's memo; Assembly memos are on the Assembly's site.
  asmUrl(p, session = DATA.session) {
    return `https://nyassembly.gov/leg/?default_fld=&leg_video=&bn=A${p.slice(1).replace(/^\d+/, (n) => n.padStart(5, "0"))}&term=${session}&Summary=Y&Text=Y&Memo=Y`;
  },
  textLinks(b) {
    // Each house's site has its own version's text and its sponsor's memo.
    const s = b.vers.find((v) => v.p[0] === "S"), a = b.vers.find((v) => v.p[0] === "A");
    const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener" data-out="bill-text">${text} ↗</a>`;
    return [s && link(STATE.billUrl(s.p), `${esc(s.p)} on the Senate's site: text and sponsor's memo`),
      a && link(STATE.asmUrl(a.p), `${esc(a.p)} on the Assembly's site: text and sponsor's memo`)].filter(Boolean).join("<br>");
  },

  // The governor has 10 days, Sundays excepted, after delivery; after the Legislature's final
  // adjournment, 30 days (NY Constitution, Art. IV, sec. 7).
  govDeadline(iso) {
    if (!iso) return null;
    const [y, m, d] = iso.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    for (let n = 0; n < 10;) { dt.setDate(dt.getDate() + 1); if (dt.getDay() !== 0) n++; }
    // After the Legislature's year ends, the governor has 30 days instead; unsigned bills are
    // pocket-vetoed. Estimated from December 31.
    if (dt.getFullYear() > y) return `${y + 1}-01-30`;
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
  },

  // Bills that passed both houses: the governor's office can request them through the end of the
  // session's second year, and they die if it doesn't.
  passedBothBy: (session) => `${session + 1}-12-31`,
  passedBothGroup: ["By December 31", () => "The governor's office has to request these and decide on them by the end of the year, or they die."],

  // Stage names (the stage numbers are build_data.py's), and their tips.
  stageText: {
    live: {
      pipe: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses", "On the governor's desk", "Signed into law", "Vetoed"],
      long: ["In committee", "Awaiting a floor vote", "Passed one house", "Passed both houses, not yet requested by the governor", "On the governor's desk", "Signed into law", "Vetoed"],
      chart: ["In committee", "Awaiting floor vote", "Passed one house", "Passed both, not requested", "Governor's desk", "Signed", "Vetoed"],
    },
    final: {
      pipe: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses", "Sent to the governor", "Signed into law", "Vetoed"],
      long: ["Died in committee", "Died awaiting a floor vote", "Passed one house only", "Passed both houses, never requested by the governor", "Sent to the governor, no action recorded", "Signed into law", "Vetoed"],
      chart: ["Died in committee", "Died awaiting vote", "Passed one house", "Passed both, not requested", "Sent, no action", "Signed", "Vetoed"],
    },
  },
  stageTips: [
    "Waiting in a committee. Most bills never get out of committee.",
    "A committee approved it, and it's on the calendar waiting for a vote of the full Senate or Assembly. Leaders decide which bills get a vote.",
    "Passed the Senate or the Assembly, but not both. Both houses have to pass the same text.",
    "Passed both houses and waiting for the governor's office to request it. Her 10-day clock starts only when it's delivered.",
    "Delivered to the governor. She has 10 days, not counting Sundays, to sign or veto it.",
    "Signed into law and given a chapter number.",
    "Vetoed by the governor. The Legislature can override a veto with two-thirds of each house, but rarely does.",
  ],
  pastStageTips: [
    "Never got out of committee before the session ended.",
    "A committee approved it, but it never got a vote of the full house.",
    "Passed the Senate or the Assembly, but not both.",
    "Passed both houses, but the governor's office never requested it, so it never reached her.",
    "Sent to the governor, but the records show no signature or veto.",
  ],
  outOfTime: "Floor votes for this session are over. A bill that hasn't passed both houses can move only if lawmakers return for a special session; otherwise it dies December 31 and has to be reintroduced.",
};
