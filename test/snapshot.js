<script>
// Records what each part of the page shows, for comparing a page before and after a change that
// shouldn't change what visitors see. Used by test/same.sh.
(function(){
const out = [];
const strip = (h) => h.replace(/<svg class="net[\s\S]*?<\/svg>/g, "<svg net>");
const grab = (name, el) => out.push("=== " + name + "\n" + (el ? strip(el.innerHTML) : "(none)"));
const tab = (v) => { const t = document.querySelector('.view-tab[data-view=' + v + ']'); t && t.click(); };
setTimeout(() => {
  tab("bills");
  const bills = [...document.querySelectorAll("#list .bill")].slice(0, 25);
  bills.forEach((d) => { if (!d.open) d.querySelector("summary").click(); });
  grab("bills, 25 open", document.getElementById("view-bills"));
  bills.slice(0, 8).forEach((d) => { const s = d.querySelector("[data-watch], .watch, button[aria-label*=atch]"); s && s.click(); });
  for (const v of ["watch", "act", "stats"]) { tab(v); grab(v, document.getElementById("view-" + v)); }
  tab("how");
  const secs = [...new Set([...document.querySelectorAll("[data-how]")].map((e) => e.dataset.how))];
  for (const id of secs) { const b = document.querySelector('[data-how="' + id + '"]'); b && b.click(); grab("how/" + id, document.getElementById("view-how")); }
  const o = document.createElement("pre"); o.id = "SNAP"; o.textContent = out.join("\n"); document.body.prepend(o);
}, 3500);
})();
</script>
