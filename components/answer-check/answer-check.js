/* answer-check.js — checks a typed answer exactly, in the browser, for practice sets and exams.

   <script src="../../components/answer-check/answer-check.js"></script>   // defines AnswerCheck

   AnswerCheck.number(input, answer)        → { ok, value, error }   input must be ONE number: 17, −5, 3/4, 0.75
   AnswerCheck.expression(input, answer)    → { ok, equal, expanded, error }
   AnswerCheck.sameNumber(input, value)     → true when the typed number equals value
   AnswerCheck.sameExpression(input, expr)  → true when both agree at every test point

   Numbers are exact fractions (BigInt), never floats, so 0.75, 3/4 and 6/8 are the same value.
   Expressions are compared at the same six test points tools/build_exercises.py uses: low-degree
   polynomials that agree at all of them are equal. Input may be plain text (−3x − 12, x^2 + 5x,
   2(x+1), x²) or the ascii-math that <equation-editor> gives (getValue("ascii-math")).
*/
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- exact fractions
  const gcd = (a, b) => { a = a < 0n ? -a : a; b = b < 0n ? -b : b; while (b) [a, b] = [b, a % b]; return a; };
  function Q(n, d = 1n) {
    if (d === 0n) throw new Error("division by zero");
    if (d < 0n) { n = -n; d = -d; }
    const g = gcd(n, d) || 1n;
    return { n: n / g, d: d / g };
  }
  const add = (a, b) => Q(a.n * b.d + b.n * a.d, a.d * b.d);
  const sub = (a, b) => Q(a.n * b.d - b.n * a.d, a.d * b.d);
  const mul = (a, b) => Q(a.n * b.n, a.d * b.d);
  const div = (a, b) => Q(a.n * b.d, a.d * b.n);
  const eq = (a, b) => a.n === b.n && a.d === b.d;
  function pow(a, e) {
    if (e.d !== 1n) throw new Error("only whole-number exponents");
    let k = e.n, r = Q(1n);
    const base = k < 0n ? div(Q(1n), a) : a;
    if (k < 0n) k = -k;
    if (k > 64n) throw new Error("exponent too large");
    for (let i = 0n; i < k; i++) r = mul(r, base);
    return r;
  }
  function parseQ(s) {                       // "17", "-3/4", "0.75" (already normalized)
    const m = /^([+-]?)(\d+)(?:\.(\d+))?$/.exec(s);
    if (!m) throw new Error("not a number: " + s);
    const frac = m[3] || "";
    let q = Q(BigInt(m[2] + frac), 10n ** BigInt(frac.length));
    return m[1] === "-" ? Q(-q.n, q.d) : q;
  }

  // ---------------------------------------------------------------- normalizing what was typed
  const SUP = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9" };
  function normalize(s) {
    return String(s)
      .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, (m) => "^" + [...m].map((c) => SUP[c]).join(""))
      .replace(/\\cdot|\\times|·|×|\bxx\b|\*\*?/g, "*")
      .replace(/\\div|÷/g, "/")
      .replace(/[−–—]/g, "-")
      .replace(/\\left|\\right/g, "")
      .replace(/[\[{]/g, "(").replace(/[\]}]/g, ")")
      .replace(/(\d),(?=\d{3}\b)/g, "$1")     // 1,000 → 1000
      .replace(/\s+/g, " ")
      .trim();
  }

  // ---------------------------------------------------------------- parser → tree
  // expr := term (('+'|'-') term)* ; term := unary (('*'|'/'|implied) unary)*
  // unary := ('+'|'-') unary | power ; power := atom ('^' unary)? ; atom := number | letter | '(' expr ')'
  function tokens(s) {
    const out = [], re = /\s*(\d+(?:\.\d+)?|\.\d+|[a-zA-Z]|[-+*/^()])/y;
    let m, i = 0;
    while (i < s.length) {
      re.lastIndex = i;
      if (!(m = re.exec(s))) throw new Error(`can't read "${s.slice(i).trim().slice(0, 8)}"`);
      out.push(m[1].startsWith(".") ? "0" + m[1] : m[1]);
      i = re.lastIndex;
    }
    return out;
  }
  function parse(text) {
    const t = tokens(normalize(text));
    if (!t.length) throw new Error("empty");
    let i = 0;
    const peek = () => t[i], take = () => t[i++];
    const isNum = (x) => /^\d/.test(x || ""), isVar = (x) => /^[a-zA-Z]$/.test(x || "");
    function atom() {
      const x = take();
      if (isNum(x)) return { k: "num", v: parseQ(x) };
      if (isVar(x)) return { k: "var", v: x.toLowerCase() };
      if (x === "(") { const e = expr(); if (take() !== ")") throw new Error("missing )"); return { k: "paren", e }; }
      throw new Error(x === undefined ? "the answer ends too soon" : `unexpected "${x}"`);
    }
    function power() {
      const a = atom();
      if (peek() === "^") { take(); return { k: "pow", a, b: unary() }; }
      return a;
    }
    function unary() {
      if (peek() === "-") { take(); return { k: "neg", a: unary() }; }
      if (peek() === "+") { take(); return unary(); }
      return power();
    }
    function term() {
      let a = unary();
      for (;;) {
        const x = peek();
        if (x === "*" || x === "/") { take(); a = { k: x, a, b: unary() }; }
        else if (isVar(x) || x === "(") a = { k: "*", a, b: power() };          // implied: 3x, 2(x+1), xy
        else if (isNum(x) && (a.k === "var" || a.k === "pow" || a.k === "paren")) throw new Error("write the number first, like 3x");
        else return a;
      }
    }
    function expr() {
      let a = term();
      while (peek() === "+" || peek() === "-") { const op = take(); a = { k: op, a, b: term() }; }
      return a;
    }
    const e = expr();
    if (i < t.length) throw new Error(`unexpected "${t[i]}"`);
    return e;
  }

  function evaluate(n, point) {
    switch (n.k) {
      case "num": return n.v;
      case "var": if (!(n.v in point)) throw new Error(`unknown letter ${n.v}`); return point[n.v];
      case "paren": return evaluate(n.e, point);
      case "neg": { const v = evaluate(n.a, point); return Q(-v.n, v.d); }
      case "pow": return pow(evaluate(n.a, point), evaluate(n.b, point));
      case "+": return add(evaluate(n.a, point), evaluate(n.b, point));
      case "-": return sub(evaluate(n.a, point), evaluate(n.b, point));
      case "*": return mul(evaluate(n.a, point), evaluate(n.b, point));
      case "/": return div(evaluate(n.a, point), evaluate(n.b, point));
    }
    throw new Error("bad tree");
  }

  // Same test points as tools/build_exercises.py (POINTS).
  const POINTS = [
    { x: "2", y: "3", z: "5", a: "4", b: "-3", c: "6" },
    { x: "-5", y: "7", z: "-2", a: "-1", b: "8", c: "3" },
    { x: "7/3", y: "-1/2", z: "4", a: "5/2", b: "2", c: "-7" },
    { x: "11", y: "-6", z: "1/5", a: "3", b: "-2/3", c: "10" },
    { x: "-3/4", y: "13", z: "-9", a: "-6", b: "5", c: "1/2" },
    { x: "17", y: "1/3", z: "8", a: "7", b: "-11", c: "-4/5" },
  ].map((p) => Object.fromEntries(Object.entries(p).map(([k, v]) => {
    const [n, d = "1"] = v.split("/");
    return [k, Q(BigInt(n), BigInt(d))];
  })));

  const values = (tree) => POINTS.map((p) => evaluate(tree, p));
  const sameValues = (a, b) => a.every((v, i) => eq(v, b[i]));

  // ---------------------------------------------------------------- "is it expanded and simplified?"
  // The top-level terms must have no parentheses and no two terms may be like terms (same letters
  // with the same powers; all constants count as one kind).
  const isConst = (n) => n.k === "num" || (n.k === "neg" && isConst(n.a)) || (n.k === "paren" && isConst(n.e));
  function hasParen(n) { return (n.k === "paren" && !isConst(n.e)) || ["a", "b", "e"].some((k) => n[k] && typeof n[k] === "object" && "k" in n[k] && hasParen(n[k])); }
  function terms(n, out = []) {
    if (n.k === "+" || n.k === "-") { terms(n.a, out); terms(n.b, out); } else out.push(n);
    return out;
  }
  function signature(n, acc = {}) {
    if (n.k === "var") acc[n.v] = (acc[n.v] || 0) + 1;
    else if (n.k === "pow" && n.a.k === "var" && n.b.k === "num" && n.b.v.d === 1n) acc[n.a.v] = (acc[n.a.v] || 0) + Number(n.b.v.n);
    else if (n.k === "*" || n.k === "neg") { signature(n.a, acc); if (n.b) signature(n.b, acc); }
    return acc;
  }
  const sigKey = (n) => Object.entries(signature(n)).filter(([, p]) => p).sort().map(([v, p]) => v + p).join("");
  function expanded(tree) {
    if (hasParen(tree)) return false;
    const keys = terms(tree).map(sigKey);
    return new Set(keys).size === keys.length;
  }

  // ---------------------------------------------------------------- public API
  const NUMBER_ONLY = /^[+-]?\s*(\d+(\.\d+)?|\.\d+)(\s*\/\s*[+-]?\s*\d+)?$/;
  function readNumber(input) {
    const s = normalize(input).replace(/^([+-]?)\s*\(([^()]*)\)\s*\/\s*\(([^()]*)\)$/, "$1$2/$3");   // ascii-math fraction
    if (!NUMBER_ONLY.test(s)) return null;
    const [top, bot] = s.replace(/\s+/g, "").split("/");
    const t = parseQ(top.startsWith(".") || top.startsWith("-.") || top.startsWith("+.") ? top.replace(".", "0.") : top);
    return bot === undefined ? t : div(t, parseQ(bot));
  }
  function toQ(v) { return typeof v === "object" && v && "n" in v ? v : readNumber(String(v)); }

  function number(input, answer) {
    if (!String(input).trim()) return { ok: false, error: "Type your answer first." };
    let v;
    try { v = readNumber(input); } catch (e) { v = null; }
    if (!v) return { ok: false, error: "Type just one number, like 17, −5, 3/4 or 0.75." };
    return { ok: eq(v, toQ(answer)), value: v };
  }
  function sameNumber(input, value) {
    try { const v = readNumber(input); return !!v && eq(v, toQ(value)); } catch (e) { return false; }
  }
  function expression(input, answer) {
    if (!String(input).trim()) return { ok: false, error: "Type your answer first." };
    let tree;
    try { tree = parse(input); } catch (e) { return { ok: false, error: "I can't read that: " + e.message + "." }; }
    let equal;
    try { equal = sameValues(values(tree), values(parse(answer))); } catch (e) { return { ok: false, error: "I can't read that: " + e.message + "." }; }
    const exp = expanded(tree);
    return { ok: equal && exp, equal, expanded: exp };
  }
  function sameExpression(input, expr) {
    try { return sameValues(values(parse(input)), values(parse(expr))); } catch (e) { return false; }
  }

  root.AnswerCheck = { number, expression, sameNumber, sameExpression, _parse: parse, _values: values, _expanded: expanded };
})(typeof window !== "undefined" ? window : globalThis);
