# Equation editor

Reusable, Word-style equation editor for any page in the repo. Fractions, powers, roots and
parentheses are inserted as **boxes you fill in**, using a button ribbon or the keyboard.
Built on [MathLive](https://cortexjs.io/mathlive/) (MIT), vendored in `vendor/mathlive/` — no CDN, no build step.

## Use it

```html
<script type="module" src="../../components/equation-editor/equation-editor.js"></script>

<equation-notebook placeholder="Write a step…"></equation-notebook>   <!-- several lines -->
<equation-editor   placeholder="Type or tap…"></equation-editor>      <!-- one expression -->
```

Adjust only the relative path to `equation-editor.js`. The component finds its own CSS, fonts and
MathLive from its own location, so it works from any folder depth. Live example: `demo.html`.

## Keyboard (like Word)

| Type | Result |
|------|--------|
| `/` | fraction (caret goes to the denominator; press **→** to leave it) |
| `^` | power |
| `*` | × |
| `sqrt` | square root |
| **Enter** (notebook) | new line · **Backspace** on an empty line removes it |

## API

| `<equation-editor>` | |
|---|---|
| attributes | `value` (LaTeX), `placeholder`, `toolbar="none"` (hide ribbon), `label` (aria-label) |
| `.value` | LaTeX string (get / set) |
| `.getValue(format)` | `"ascii-math"`, `"math-json"`, `"latex-expanded"`… |
| `.isEmpty`, `.clear()`, `.focus()` | |
| `.insert(latex)` | insert at caret; `#?` = empty box, `#@` = current selection |
| `.field` | the underlying MathLive `<math-field>` |
| events | `input` (bubbles), `equation-enter` (Enter pressed) |

| `<equation-notebook>` | |
|---|---|
| attributes | `value`, `placeholder` |
| `.value` | array of LaTeX strings, one per line (get / set) |
| `.isEmpty`, `.clear()`, `.focus()` | |
| events | `input` (bubbles) whenever any line changes |

Both elements are light-DOM custom elements; set `.value` before or after they are connected.

## Theme

Set CSS variables on the element or any ancestor:

`--eq-bg`, `--eq-fg`, `--eq-panel`, `--eq-line`, `--eq-accent`, `--eq-muted`, `--eq-size` (math size), `--eq-key` (button size).

## Touch screens

On touch devices the OS keyboard is suppressed (`inputmode="none"`) so the ribbon is the input; buttons grow to 44 px.

## Add or change a ribbon button

Edit `GROUPS` in `equation-editor.js`: `[aria-label, html, action]` where the action is `ins(latex)`,
`type(latex)` or `cmd(mathliveCommand)`.

## Updating MathLive

Replace `vendor/mathlive/mathlive.min.mjs` and `vendor/mathlive/fonts/` with the new release
(from the `mathlive` npm package, `dist/`) and update `VERSION`. Current: see `vendor/mathlive/VERSION`.
