// The odds chart: how bills move from introduction to law, as a Sankey diagram. Shared by each state's Statistics tab
// (tracker.html's sankey(), which build_data.py puts this file in front of) and /compare/ (compare_site.py).
// odds: {step: [bills, of them law]} (build_data.py's insights() "odds"); fate: {where bills died: [died, back next
// session, later law]}; cfate: how bills that died in committee died there. o: the state's settings: {uni (one house),
// passedBoth (its words for it), exits (two names for the first exits, or null), heldLabel, linked (a function: are
// sessions linked, so "reintroduced next session" can be said), exec ("the governor"), num, esc}. Its styles are the
// pages' own (.sankey, .sk-*).
// How bills move: a Sankey diagram. Bills flow left to right through each step; at each step a band
// drops down to the bills that stopped there, labeled with how many were reintroduced the next session.
// Bills that died in committee are split by what happened to them there.
function drawSankey(odds, fate, cfate, o) {
  const { uni: UNI, passedBoth: PASSED_BOTH, exits, heldLabel, linked, exec, num, esc } = o;
  const n = (k) => (odds[k] || [0, 0])[0];
  const N = UNI ? [n("intro"), n("floor"), n("both")] : [n("intro"), n("floor"), n("house"), n("both")], law = (odds.intro || [0, 0])[1], vetoed = n("vetoed");
  const L3 = N.length - 1;  // the "passed" step
  if (!N[0] || !N[2]) return "";
  const W = 960, top = 30, H0 = 170, k = H0 / N[0], nodeW = 10, gap = 34;
  // When there were vetoes, the veto is a step of its own: two narrower columns after "Passed both houses".
  const over = n("overridden"), allVetoes = vetoed + over, signed = law - over;
  const xs = [0, 1, 2, 3, 4].map((i) => 6 + i * 196);
  if (allVetoes) xs.splice(L3 + 1, 1, xs[L3] + 150, xs[L3] + 300);
  const h = (v) => Math.max(1.5, v * k);
  const band = (x0, a0, b0, x1, a1, b1, cls) => { const m = (x0 + x1) / 2;
    return `<path class="${cls}" d="M${x0},${a0} C${m},${a0} ${m},${a1} ${x1},${a1} L${x1},${b1} C${m},${b1} ${m},${b0} ${x0},${b0} Z"/>`; };
  const pct = (v, d = N[0]) => (v > 0 && v / d < 0.005 ? "&lt;1%" : `${Math.round((v / d) * 100)}%`);
  const back = (key) => { const f = fate?.[key]; return f && f[0] && linked() ? `${pct(f[1], f[0])} reintroduced next session` : ""; };
  const STEPS = UNI ? ["Introduced", "Approved by a committee", PASSED_BOTH] : ["Introduced", "Approved by a committee", "Passed one house", "Passed both houses"];
  // A state where every bill gets a floor vote (North Dakota) names the first two exits itself, and has no committee breakdown.
  const EXITS = [[exits?.[0] || "Died in committee", "committee"], [exits?.[1] || "Died awaiting a floor vote", "floor"], ["Passed one house only", "oneHouse"]];
  // Each exit sits just under the step it leaves to, so the exits step down instead of sharing one line.
  let exitTop = 0, bottom = 0;
  const label = (x, y, lines) => lines.filter(Boolean).map((l, i) => `<text class="sk-l${i ? "" : " sk-b"}" x="${x}" y="${y + i * 15}">${l}</text>`).join("");
  let g = "", labels = "";
  // The two shares at a split: the upper one centred on its band, the lower one just under it. On a thin band the lower
  // one is pushed down so the two never overlap (Congress's "Passed one house": 33% and 67% were drawn on top of each other).
  const split = (x, hUp, upper, lower) => { const y1 = top + Math.max(hUp / 2 + 4, 12), y2 = Math.max(top + hUp + 16, y1 + 15);
    return `<text class="sk-p" x="${x}" y="${y1}">${upper}</text><text class="sk-p" x="${x}" y="${y2}">${lower}</text>`; };
  for (let i = 0; i <= L3; i++) {
    g += `<rect class="sk-node" x="${xs[i]}" y="${top}" width="${nodeW}" height="${h(N[i])}"/>`;
    labels += `<text class="sk-l" x="${xs[i]}" y="${top - 10}"><tspan class="sk-b">${STEPS[i]}</tspan> ${num(N[i])}</text>`;
    if (i === L3) break;
    g += band(xs[i] + nodeW, top, top + h(N[i + 1]), xs[i + 1], top, top + h(N[i + 1]), "sk-go");
    // On each band: the share of the bills at this step that went this way.
    labels += split(xs[i] + nodeW + 6, h(N[i + 1]), pct(N[i + 1], N[i]), pct(N[i] - N[i + 1], N[i]));
    const out = N[i] - N[i + 1], ex = xs[i + 1];
    exitTop = top + h(N[i + 1]) + gap;
    bottom = Math.max(bottom, exitTop + Math.max(h(out), i === 0 && cfate ? 137 : 50));
    g += band(xs[i] + nodeW, top + h(N[i + 1]), top + h(N[i]), ex, exitTop, exitTop + h(out), "sk-out");
    const [name, key] = EXITS[i];
    if (i === 0 && cfate && !exits) {
      // Died in committee, in four parts.
      const PARTS = [["none", "Never acted on", "sk-c0"], ["amended", "Revised by the sponsor, never voted on", "sk-c1"], ["held", heldLabel || "Held without a vote", "sk-c2"], ["defeated", "Voted down", "sk-c4"], ["passed", "Passed one committee, died in the next", "sk-c3"]]
        .filter(([pk]) => (cfate[pk] || [0])[0] > 0);
      const tot = PARTS.reduce((a, [pk]) => a + ((cfate[pk] || [0])[0]), 0) || 1;
      let y = exitTop;
      PARTS.forEach(([pk, , cls]) => { const hh = h(out) * ((cfate[pk] || [0])[0] / tot); g += `<rect class="${cls}" x="${ex}" y="${y}" width="${nodeW}" height="${hh}"/>`; y += hh; });
      labels += label(ex + nodeW + 8, exitTop + 11, [name, `${num(out)} · ${pct(out)} of bills`, back(key)]);
      labels += PARTS.map(([pk, pl, cls], j) => { const [cn, , claw] = cfate[pk] || [0, 0, 0];
        return `<rect class="${cls}" x="${ex + nodeW + 8}" y="${exitTop + 50 + j * 17}" width="9" height="9"/><text class="sk-l" x="${ex + nodeW + 22}" y="${exitTop + 58 + j * 17}">${pl} ${cn && cn / tot < 0.005 ? `(${num(cn)} bills)` : pct(cn, tot)}</text>`; }).join("");
    } else {
      g += `<rect class="sk-exit" x="${ex}" y="${exitTop}" width="${nodeW}" height="${h(out)}"/>`;
      labels += label(ex + nodeW + 8, exitTop + 11, [name, `${num(out)} · ${pct(out)} of bills`, back(key)]);
    }
  }
  // Passed both houses: signed, or vetoed. A veto is a step of its own (the governor said no); from it, the legislature
  // overrides it (back into "Became law") or the veto stands. Without vetoes the chart keeps five columns.
  if (!allVetoes) {
    const x4 = xs[L3 + 1];
    g += band(xs[L3] + nodeW, top, top + h(law), x4, top, top + h(law), "sk-law");
    labels += `<text class="sk-p" x="${xs[L3] + nodeW + 6}" y="${top + Math.max(h(law) / 2 + 4, 12)}">${pct(law, N[L3])}</text>`;
    g += `<rect class="sk-lawn" x="${x4}" y="${top}" width="${nodeW}" height="${h(law)}"/>`;
    labels += label(x4 + nodeW + 8, top + 11, ["Became law", `${num(law)} · ${pct(law)} of bills`]);
  } else {
    // Six columns: the vetoed node in the fifth, "Became law" and "Veto stood" in the sixth.
    // The veto band runs level under its label ("14% vetoed (874)") and bends down to the vetoed node only past the
    // label's end, so the band never crosses it (about 6.8px a character at the label's bold 11.5px).
    const vetoText = `${pct(allVetoes, N[L3])} vetoed (${num(allVetoes)})`, vetoEnd = xs[L3] + nodeW + 6 + vetoText.length * 6.8 + 6;
    const x4 = Math.max(xs[L3 + 1], vetoEnd + 34), x5 = xs[L3 + 2];
    const vy = top + h(signed) + 26;                                   // the vetoed node, under the signed band
    const sy = Math.max(top + h(law) + 46, vy + h(over) + 30);         // "Veto stood", under the law label
    g += band(xs[L3] + nodeW, top, top + h(signed), x5, top, top + h(signed), "sk-law");
    g += `<rect class="sk-veto" x="${xs[L3] + nodeW}" y="${top + h(signed)}" width="${vetoEnd - xs[L3] - nodeW}" height="${h(allVetoes)}"/>`
      + band(vetoEnd, top + h(signed), top + h(signed) + h(allVetoes), x4, vy, vy + h(allVetoes), "sk-veto");
    g += band(x4 + nodeW, vy, vy + h(over), x5, top + h(signed), top + h(law), "sk-law");
    if (vetoed) g += band(x4 + nodeW, vy + h(over), vy + h(allVetoes), x5, sy, sy + h(vetoed), "sk-veto");
    labels += split(xs[L3] + nodeW + 6, h(signed), `${pct(signed, N[L3])} signed`, vetoText);
    g += `<rect class="sk-veton" x="${x4}" y="${vy}" width="${nodeW}" height="${h(allVetoes)}"/>`;
    // On the veto's two branches: how many the legislature overrode, and how many stood.
    if (over) labels += `<text class="sk-p" x="${x4 + nodeW + 6}" y="${vy - 6}">${num(over)} overridden</text>`;
    g += `<rect class="sk-lawn" x="${x5}" y="${top}" width="${nodeW}" height="${h(law)}"/>`;
    labels += label(x5 + nodeW + 8, top + 11, ["Became law", `${num(law)} · ${pct(law)} of bills`,
      over ? `${num(over)} over ${exec}'s veto` : ""]);
    g += `<rect class="sk-veton" x="${x5}" y="${sy}" width="${nodeW}" height="${h(vetoed)}"/>`;
    labels += label(x5 + nodeW + 8, sy + 8, ["Veto stood", `${num(vetoed)} · ${pct(vetoed)} of bills`, back("vetoed")]);
    bottom = Math.max(bottom, sy + 45, vy + h(allVetoes) + 50);
  }
  const height = Math.max(bottom, top + H0) + 12;
  // The chart's numbers for a screen reader: each step's count and share, then laws and vetoes.
  const said = `How bills move from introduction to law: ${STEPS.map((t, i) => `${t.toLowerCase()} ${num(N[i])}${i ? ` (${pct(N[i])})` : ""}`).join(", ")}; became law ${num(law)} (${pct(law)})${allVetoes ? `; vetoed ${num(allVetoes)}${over ? `, ${num(over)} of them overridden` : ""}` : ""}.`;
  return `<div class="sankey"><svg viewBox="0 0 ${W + 150} ${height}" role="img" aria-label="${esc(said.replace(/&lt;/g, "<"))}">${g}${labels}</svg></div>`;
}
