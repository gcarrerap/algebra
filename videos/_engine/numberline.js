// Number line component. Load it BEFORE player.js; it turns markup into SVG before the player
// collects the animated elements, so marks animate with the usual data-at / data-out / data-dur.
//
//   <div class="numberline" data-from="-10" data-to="10" data-unit="80" data-labels="all">
//     <i class="dot c-blue"    data-n="3" data-label="3°" data-at="b01@three" data-out="b03"></i>
//     <i class="hop c-red"     data-a="3" data-b="-5" data-lift="60" data-at="b01@drops" data-dur="1.6"></i>
//     <i class="span c-purple" data-a="-5" data-b="0" data-at="b04@absolute"></i>
//     <i class="ray c-green"   data-n="2" data-dir="right" data-open data-at="…"></i>
//   </div>
//
// Line:  data-from / data-to (integers), data-unit = pixels per unit (default 80),
//        data-labels = all | even | none (default: all when unit ≥ 60, else even).
// Marks: dot  — a point at n, optional data-label above it, data-open for an open circle.
//        hop  — an arrow from a to b, drawn as the mark appears (data-dur sets how long);
//               data-lift = arc height in px (default 50).
//        span — a bracket under the labels from a to b (a distance, an interval).
//        seg  — a shaded segment from a to b for a between-inequality; data-open-a / data-open-b give an open end.
//        ray  — a thick shaded ray from n to the end of the line, data-dir = left | right,
//               with an open (data-open) or closed circle at n: inequality graphs.
// The color comes from the mark's c-<color> class. See docs/video-production.md.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const KEEP = ["data-at", "data-out", "data-dur"];
  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const num = (n) => String(n).replace("-", "−");

  document.querySelectorAll(".numberline").forEach((box) => {
    const lo = +box.dataset.from, hi = +box.dataset.to, unit = +(box.dataset.unit || 80);
    const labels = box.dataset.labels || (unit >= 60 ? "all" : "even");
    const W = (hi - lo) * unit + 120, Y = 150, H = 250;
    const x = (n) => 60 + (n - lo) * unit;
    const svg = el("svg", { class: "nl", viewBox: `0 0 ${W} ${H}`, width: W, height: H });
    el("line", { x1: 20, y1: Y, x2: W - 20, y2: Y, class: "axis" }, svg);
    el("path", { d: `M${W - 20},${Y} l-18,-11 v22 z`, class: "axis-head" }, svg);
    el("path", { d: `M20,${Y} l18,-11 v22 z`, class: "axis-head" }, svg);
    for (let n = lo; n <= hi; n++) {
      const big = n % 5 === 0, h = big ? 16 : 10;
      el("line", { x1: x(n), y1: Y - h, x2: x(n), y2: Y + h, class: "tick" + (n === 0 ? " zero" : "") }, svg);
      if (labels === "all" || (labels === "even" && n % 2 === 0))
        el("text", { x: x(n), y: Y + 55, class: "num" + (n === 0 ? " z" : "") }, svg).textContent = num(n);
    }
    [...box.children].forEach((m) => {
      const kind = ["dot", "hop", "span", "ray", "seg"].find((k) => m.classList.contains(k));
      if (!kind) return;
      const color = [...m.classList].find((c) => c.startsWith("c-")) || "c-yellow";
      const g = el("g", { class: `mark mark-${kind} ${color} ${kind === "dot" || kind === "ray" || kind === "seg" ? "pop" : kind === "span" ? "fade" : ""}` }, svg);
      KEEP.forEach((k) => m.hasAttribute(k) && g.setAttribute(k, m.getAttribute(k)));
      const d = m.dataset;
      if (kind === "dot") {
        const n = +d.n;
        el("circle", { cx: x(n), cy: Y, r: 15, class: "dot" + ("open" in d ? " open" : "") }, g);
        if (d.label) el("text", { x: x(n), y: Y - 52, class: "dl" }, g).textContent = d.label;
      } else if (kind === "hop") {
        const a = x(+d.a), b = x(+d.b), lift = +(d.lift || 50), s = b > a ? 1 : -1;
        el("path", { d: `M${a},${Y - 6} Q${(a + b) / 2},${Y - 6 - 2 * lift} ${b},${Y - 6}`, class: "arc", pathLength: 1 }, g);
        el("path", { d: `M${b},${Y - 6} l${-s * 22},-18 l${-s * 2},16 z`, class: "head" }, g);
      } else if (kind === "span") {
        const a = x(+d.a), b = x(+d.b);
        el("path", { d: `M${a},${Y + 68} v12 H${b} v-12`, class: "brace" }, g);
      } else if (kind === "seg") {
        const a = x(+d.a), b = x(+d.b);
        el("line", { x1: a, y1: Y, x2: b, y2: Y, class: "ray-line" }, g);
        el("circle", { cx: a, cy: Y, r: 16, class: "dot" + ("openA" in d ? " open" : "") }, g);
        el("circle", { cx: b, cy: Y, r: 16, class: "dot" + ("openB" in d ? " open" : "") }, g);
      } else if (kind === "ray") {
        const n = x(+d.n), end = d.dir === "left" ? 24 : W - 24;
        el("line", { x1: n, y1: Y, x2: end, y2: Y, class: "ray-line" }, g);
        el("circle", { cx: n, cy: Y, r: 16, class: "dot" + ("open" in d ? " open" : "") }, g);
      }
    });
    box.replaceChildren(svg);
  });
})();
