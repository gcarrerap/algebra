/*
 * Equation editor for the algebra site: two reusable custom elements.
 *
 *   <equation-editor>    one editable expression with a button ribbon (fractions, powers, roots…)
 *   <equation-notebook>  several lines of work, one ribbon shared by all, Enter = new line
 *
 * Usage (any page, any folder depth; the component finds its own files):
 *
 *   <script type="module" src="…/components/equation-editor/equation-editor.js"></script>
 *   <equation-notebook placeholder="Write a step…"></equation-notebook>
 *
 * Full API and theming: see README.md in this folder. Built on MathLive (MIT, vendored in ./vendor).
 */
import { MathfieldElement } from "./vendor/mathlive/mathlive.min.mjs";

const HERE = new URL("./", import.meta.url);
MathfieldElement.fontsDirectory = new URL("vendor/mathlive/fonts/", HERE).href;
MathfieldElement.soundsDirectory = null;
MathfieldElement.keypressSound = null;
MathfieldElement.plonkSound = null;

if (!document.querySelector("link[data-eq-css]")) {
  const l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = new URL("equation-editor.css", HERE).href;
  l.dataset.eqCss = "";
  document.head.append(l);
}

const texPlain = (t) => "\\text{" + String(t).replace(/[\\{}$&#^_%~]/g, (c) => "\\" + c) + "}";
const COARSE = matchMedia("(pointer: coarse)").matches;   // touch screen: use our buttons, not the OS keyboard

const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "html") e.innerHTML = v;
    else if (k === "class") e.className = v;
    else e.setAttribute(k, v);
  }
  kids.flat().forEach((c) => e.append(c));
  return e;
};

/* ---------------------------------------------------------------- ribbon */
const ins = (latex) => (f) => f.insert(latex, { format: "latex", selectionMode: "placeholder" });
const cmd = (name) => (f) => f.executeCommand(name);
const type = (s) => (f) => f.insert(s, { format: "latex" });

const GROUPS = [
  {
    name: "Structures",
    keys: [
      ["Fraction", '<span class="eq-ic-frac"><i></i><i></i></span>', ins("\\frac{#@}{#?}")],
      ["Power", "x<sup>▫</sup>", ins("#@^{#?}")],
      ["Square", "x<sup>2</sup>", ins("#@^{2}")],
      ["Square root", "√▫", ins("\\sqrt{#?}")],
      ["Parentheses", "( )", ins("\\left(#?\\right)")],
      ["Absolute value", "|x|", ins("\\left|#?\\right|")],
    ],
  },
  {
    name: "Operations",
    keys: [
      ["Plus", "+", type("+")], ["Minus", "−", type("-")], ["Times", "×", type("\\times")],
      ["Divide", "÷", type("\\div")], ["Equals", "=", type("=")],
    ],
  },
  {
    name: "Edit",
    keys: [["Move left", "←", cmd("moveToPreviousChar")], ["Move right", "→", cmd("moveToNextChar")], ["Delete", "⌫", cmd("deleteBackward")]],
  },
  {
    name: "Numbers",
    cls: "eq-nums",
    keys: [..."1234567890"].map((d) => [d, d, type(d)]).concat([["Decimal point", ".", type(".")], ["x", "x", type("x")], ["y", "y", type("y")]]),
  },
];

function buildRibbon(getField) {
  const bar = h("div", { class: "eq-ribbon", role: "toolbar", "aria-label": "Equation symbols" });
  // keep focus (and the caret) in the field when a button is pressed
  bar.addEventListener("mousedown", (e) => e.preventDefault());
  for (const g of GROUPS) {
    const row = h("div", { class: "eq-group " + (g.cls || ""), role: "group", "aria-label": g.name });
    for (const [label, html, run] of g.keys) {
      const b = h("button", { type: "button", class: "eq-key", "aria-label": label, title: label, html });
      b.addEventListener("click", () => {
        const f = getField();
        if (!f) return;
        f.focus();
        run(f);
        f.dispatchEvent(new InputEvent("input", { bubbles: true, composed: true }));
      });
      row.append(b);
    }
    bar.append(row);
  }
  return bar;
}

// MathLive only accepts options once the field is in the page, so this runs after append().
function configure(f) {
  f.mathVirtualKeyboardPolicy = "manual";
  f.smartMode = false;
  f.menuItems = [];
  if (COARSE) f.setAttribute("inputmode", "none");
  f.inlineShortcuts = { ...f.inlineShortcuts, "*": "\\times" };
}

/* ---------------------------------------------------------------- <equation-editor> */
class EquationEditor extends HTMLElement {
  static observedAttributes = ["value", "placeholder"];

  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    this.classList.add("eq-editor");
    const f = (this._f = new MathfieldElement());
    if (this.getAttribute("toolbar") !== "none") this.append(buildRibbon(() => this._f));
    this.append(f);
    configure(f);
    f.setAttribute("aria-label", this.getAttribute("label") || "Equation");
    if (this.hasAttribute("placeholder")) f.placeholder = texPlain(this.getAttribute("placeholder"));
    if (this._pending != null) f.value = this._pending;
    else if (this.hasAttribute("value")) f.value = this.getAttribute("value");
    f.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.dispatchEvent(new CustomEvent("equation-enter", { bubbles: true }));
      }
    }, true);
  }

  attributeChangedCallback(name, _old, val) {
    if (name === "value" && this._f) this._f.value = val ?? "";
    if (name === "placeholder" && this._f) this._f.placeholder = texPlain(val ?? "");
  }

  /** The expression as LaTeX. Assigning replaces it. */
  get value() { return this._f ? this._f.value : this._pending ?? this.getAttribute("value") ?? ""; }
  set value(v) { if (this._f) this._f.value = v ?? ""; else this._pending = v ?? ""; }
  /** The MathLive field, for anything not wrapped here. */
  get field() { return this._f; }
  get isEmpty() { return !this.value.trim(); }
  /** Other formats: "ascii-math", "math-json", "latex-expanded"… */
  getValue(format = "latex") { return this._f.getValue(format); }
  insert(latex) { this._f.focus(); this._f.insert(latex, { format: "latex", selectionMode: "placeholder" }); }
  clear() { this.value = ""; this.dispatchEvent(new Event("input", { bubbles: true })); }
  focus() { this._f?.focus(); }
}

/* ---------------------------------------------------------------- <equation-notebook> */
class EquationNotebook extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    this.classList.add("eq-notebook");
    this._list = h("ol", { class: "eq-lines" });
    this._add = h("button", { type: "button", class: "eq-add" }, "+ Add line");
    this._add.addEventListener("click", () => { this._focusSoon(this._insertLine("", this.lines.length - 1)); this._changed(); });
    this.append(buildRibbon(() => this._active?.field ?? this.querySelector("equation-editor")?.field), this._list, this._add);
    const start = this._pending ?? [this.getAttribute("value") || ""];
    start.forEach((v) => this._insertLine(v));
    if (!start.length) this._insertLine("");

    this.addEventListener("focusin", (e) => { const ed = e.target.closest?.("equation-editor"); if (ed) this._active = ed; });
    this.addEventListener("equation-enter", (e) => {
      const at = this.lines.indexOf(e.target.closest("equation-editor"));
      this._focusSoon(this._insertLine("", at)); this._changed();
    });
    // Backspace on an empty line removes it and goes back to the one above
    this.addEventListener("keydown", (e) => {
      const ed = e.target.closest?.("equation-editor");
      if (e.key !== "Backspace" || !ed || !ed.isEmpty || this.lines.length < 2) return;
      e.preventDefault();
      this._remove(ed);
    }, true);
  }

  get lines() { return [...this._list.querySelectorAll("equation-editor")]; }
  /** Array of LaTeX strings, one per line. Assigning replaces all lines. */
  get value() { return this._ready ? this.lines.map((l) => l.value) : this._pending ?? [""]; }
  set value(arr) {
    arr = Array.isArray(arr) && arr.length ? arr : [""];
    if (!this._ready) { this._pending = arr; return; }
    this._list.innerHTML = "";
    this._active = null;
    arr.forEach((v) => this._insertLine(v));
  }
  get isEmpty() { return this.value.every((v) => !v.trim()); }
  clear() { this.value = [""]; this._changed(); }
  focus() { this.lines[0]?.focus(); }

  _insertLine(latex, after = -1) {
    const ed = h("equation-editor", { toolbar: "none", label: "Line of work" });
    if (this.getAttribute("placeholder")) ed.setAttribute("placeholder", this.getAttribute("placeholder"));
    ed.value = latex;
    const del = h("button", { type: "button", class: "eq-del", "aria-label": "Delete this line", title: "Delete this line" }, "×");
    del.addEventListener("click", () => this._remove(ed));
    const li = h("li", { class: "eq-line" }, h("span", { class: "eq-num", "aria-hidden": "true" }), ed, del);
    const ref = this._list.children[after];
    ref ? ref.after(li) : this._list.append(li);
    this._number();
    return ed;
  }

  _remove(ed) {
    const ls = this.lines, i = ls.indexOf(ed);
    if (ls.length < 2) { ed.value = ""; ed.focus(); this._changed(); return; }
    ed.closest("li").remove();
    this._number();
    const prev = this.lines[Math.max(0, i - 1)];
    this._active = prev; this._focusSoon(prev); this._changed();
  }

  // a field that was just created is ready for focus one frame later
  _focusSoon(ed) { requestAnimationFrame(() => ed.focus()); }

  _number() { [...this._list.children].forEach((li, i) => { li.querySelector(".eq-num").textContent = String(i + 1); }); }
  _changed() { this.dispatchEvent(new Event("input", { bubbles: true })); }
}

if (!customElements.get("equation-editor")) customElements.define("equation-editor", EquationEditor);
if (!customElements.get("equation-notebook")) customElements.define("equation-notebook", EquationNotebook);
export { EquationEditor, EquationNotebook, MathfieldElement };
