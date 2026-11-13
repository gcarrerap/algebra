# Practice sets

Each lesson can have a practice set. The first one is
[`exercises/u00-l01/`](../exercises/u00-l01/) (lesson 0.1, order of operations and signed numbers):
20 exercises in four levels (Warm-up, Tricky, Challenging, Boss level).

Topic 0.3 (parts of an expression) has [`exercises/u00-l03/`](../exercises/u00-l03/) (14 exercises).
Topic 0.4 (combining like terms) has [`exercises/u00-l04/`](../exercises/u00-l04/) (14 exercises).
Topic 0.5 (translating words into expressions) has [`exercises/u00-l05/`](../exercises/u00-l05/) (12 exercises).
Topic 1.1 (one-step and multi-step equations) has [`exercises/u01-l01/`](../exercises/u01-l01/) (17 exercises).
Topic 1.2 (variables on both sides) has [`exercises/u01-l02/`](../exercises/u01-l02/) (16 exercises).
Topic 1.3 (justifying each step) has [`exercises/u01-l03/`](../exercises/u01-l03/) (14 exercises).
Topic 1.4 (linear inequalities and their graphs) has [`exercises/u01-l04/`](../exercises/u01-l04/) (14 exercises).
Topic 1.5 (compound inequalities) has [`exercises/u01-l05/`](../exercises/u01-l05/) (14 exercises).

Topic 0.2 (properties of operations) has [`exercises/u00-l02/`](../exercises/u00-l02/) (24 exercises),
shared by its two subtopics 0.2.1 (commutative and associative) and 0.2.2 (distributive): within each
level, 0.2.1's exercises come first. A set's folder is always `u<unit>-l<topic>`: a topic with
subtopics has one set for all of them. Kinds of exercise:

| `kind` | The question | How it is checked |
|---|---|---|
| `num` (default) | Find the value. | Exact fractions, as in 0.1. |
| `num` + `derive` | Name a part of an expression: how many terms, the coefficient of a term, the constant, how many factors in a term (0.3). The answer is a typed number. | The answer is computed from `q` (`derive`: `terms` · `constant` · `coef:<term>` · `factors:<term>`); each wrong value names its mistake in `m` (`one`, `pieces`, `tokens`, `flat`, `variable-terms`, `distinct-vars`, `drop-sign`, `hidden-zero`, `constant`, `coef-of:<term>`, `sum-numbers`) and the build recomputes it. Steps, chips and `at` work as in 0.1; chips `TERM` blue, `FACTOR` purple, `COEF` yellow, `CONST` green. |
| `num` + `derive` (equations, 1.3) | Name what a step does or solve: `operand:<Property>` (`q` = `A → B`; the answer is the number the step adds, subtracts, multiplies by or divides by), `solve` (the solution of the equation `q`) or `first-error` (`q` = a student's work, one line per row; the answer is the number of the first line whose solution differs from line 1). | Computed by `tools/build_exercises.py` (`step_kind` reads the property from the two equations, so a step can't be mislabeled). Mistakes `m`: operand `sign`, `result`, `start`, `coef`; solve `sign-k`, `sign-x`, `no-divide`, `ignore-k`, `order`; first-error `last`, `before`, `after`, `first`. `a_read` / `a_show` say and show an answer that is not just the number (e.g. “line three”). Chips: ADD blue · SUBTRACT purple · MULTIPLY yellow · DIVIDE green · DIST yellow · COMBINE green; for a student's work OK green · ERROR red · CARRY ink. |
| `expr` | Expand an expression, e.g. `−3(x + 4)`. | Every line, the answer and every wrong option are evaluated at six sets of values of the variables (`x`, `y`…); lines must match the question at all of them, wrong options must not match the answer or each other. |
| `name` | Which property does an identity show? | Both sides must be equal, and the stated property must match the identity's shape (same order and same numbers = associative; same numbers in another order = commutative; otherwise distributive). The two other properties are the wrong options. |
| `multi` | Select **all** that apply (4–6 options, at least one right and one wrong). | With `"check": "property:<Name>"`, `"equals:<expr>"`, `"term-of:<expr>"` (option is a term of `<expr>`, sign included), `"terms:<n>"` (option has exactly `<n>` terms) or `"coefficient:<n>"` (option is one term with coefficient `<n>`) `"like:<term>"` (option is one term with the same variable part as `<term>`: `2yx` is like `5xy`, `x` is not like `x²`; 0.4) or `"true"` (option is an identity `L = R` that holds for every value of the letters; 0.2), every option's `ok` is verified with code. Each option has `t` (shown), `ok`, `why` (shown when it is picked wrongly) and `say` (narration in the video); the exercise has `prompt`, `read` and `say_answer`. |
| `match` | Match every left item with a right item (3–6 pairs; right items may repeat, to sort items into groups). | With `"check": "property"` (left = identity, right = its property), `"equal"` (left equals right, and equals no other right item), `"coefficient"` (left = a term, right = its coefficient) or `"terms"` (left = an expression, right = its number of terms), every pair is verified with code. Each pair has `l`, `r`, `why`, `say`; the exercise has `prompt`, `read` and `say_answer`. |
| `linear` | Solve a linear equation whose answer may be a fraction (1.2), e.g. `4x + 5 = x + 12` → `7/3`. `q` is the equation, `var` its letter (default `x`); with `"param": "k"` the question is the value of `k` that makes the equation true for every `x`. | The answer is **computed** by solving `q` with exact fractions (`solve_in`); every solution line must have the same solution; each wrong option `e` is the arithmetic of one named mistake (it may be a fraction) and must differ from the answer and from the others. The learner types `4`, `−3`, `7/3` or `12.5` (same checker as `num`). The video has no check line. Chips: COLLECT yellow, ISOLATE blue, DIST yellow, COMBINE green. Use `solve` instead when the answer is a whole number and the video should end with the check. |
| `words` | Write an expression for a sentence (0.5), e.g. “five less than a number”. The sentence is in `prompt` (no `q`); the page hides the math line. | The answer is pinned by a `test`: `{"var": "x", "value": 20, "means": "20 − 5"}`, where `means` is arithmetic written from the sentence. The answer must give that value at that number, every wrong option a different one. Any equal form is accepted on the page (`anyForm`: `2x + 6` is right for `2(x + 3)`). Only the letters `x y z a b c` can be checked. Chips: VAR blue, WORDS yellow, ORDER purple, GROUP green, TEST ink. |
| `solve` | Solve a linear equation with one variable (1.1), e.g. `3(2x − 4) + 6 = 24`. The learner types the value (`x = 5` is not accepted: one number). The page says "Type the value of x." in `prompt`. | The build solves `q` exactly (`solve_one_var`: the difference of the two sides is evaluated at several values, so only linear equations with one integer solution pass). Every line of the work must be an equation with that same solution, the last line must read `<var> = <solution>`, and every wrong option (`e`, an arithmetic expression) must be an integer that does **not** solve the equation. The video ends with the check, computed by the build: the answer is put back into `q` (`3(2(5) − 4) + 6 = 24 ✓`). Chips are operations written with their number — `−7`, `+8`, `÷3`, `×6`, `÷(−2)` — colored by the operation (+ blue, − purple, × yellow, ÷ green), plus `DIST` yellow and `COMBINE` / `CALC` green. `⟨…⟩` marks what the next step works on, as in 0.1. |

`match` (`"check": "count"`: left = a linear equation in `x`, right = `One solution`, `No solution` or `Infinitely many solutions`) and `multi` (`"check": "count:one|none|all"`: each option is an equation with exactly one / no / infinitely many solutions), both verified by `solve_linear` (1.2), and `match` (`"check": "solves"`: left = an equation, right = its solution `x = 4`) and `multi` (`"check": "solution:<equation>"`: each option is a value, right when it solves the equation) are verified by substituting; with `solves`, no right value may solve another pair's equation.

`match` and `multi` also take `"check": "step"` / `"step:<Property>"` (left or option = `A → B`; the step's property is computed: Addition, Subtraction, Multiplication, Division, Distributive or Combine; `match` right items are `<Property> property` / `Combine like terms`) and `"valid-from:<equation>"` (`multi`: the option is an equation with the same solution as `<equation>`; 1.3) besides `"check": "operation"` (`match` only: left = phrase such as “less than”, right = `addition`, `subtraction`, `multiplication` or `division`; the key words are `OPERATION_WORDS` in `tools/build_exercises.py`, and each phrase must match exactly one operation).

Inequalities (1.4): the checker reads an inequality as its solution set (`ineq_set`: `x op b`, with the symbol flipped when the coefficient of `x` is negative), so a flip, a boundary or an open/closed circle cannot be wrong. `num` + `derive`: `smallest-int` / `largest-int` (the smallest / largest whole number that solves `q`; the boundary itself counts only for ≤ and ≥), `boundary`, `operand:<Property>` and `first-error` as in 1.3 but flip-aware. Mistakes `m`: `edge` (open/closed circle swapped), `noflip`, `sign`, `wrongway`; the other kinds as in 1.3. `match` checks `"symbol"` (phrase → ≥ ≤ > <; words in `SYMBOL_WORDS`), `"graph"` (inequality → “Open circle at 2, shaded right”) and `"same-solution"` (inequality → its solution); `multi` checks `"flip"` (moves that flip the symbol), `"solution:<inequality>"` (numbers that make it true) and `"valid-from:<inequality>"` (also for inequalities). Compound inequalities (1.5): `and` chains (`a < x ≤ b`) and `or` pairs are read as interval unions (`comp_set`). `num` + `derive` adds `count-int` (whole numbers inside the set) and `count-out` (whole numbers in a window outside it, for `or` sets), plus `smallest-int` / `largest-int` / `boundary` on compounds; mistakes `closed`, `open`, `gap`, `inner`, `edge`, `other`, `sign`, `neighbors`. `match` adds check `"join:<and|or>"` and `"graph"` for any set (short form, e.g. “Closed at −2, open at 3, shaded between”); `multi` accepts compounds in `"solution:"` and `"valid-from:"`. Chips **SOLVE blue** (solve each part of an or/and) and **LIST green** (list the whole numbers; the list must be the exact integers). Chip **FLIP red** (multiplying or dividing by a negative number); `<` and `>` are escaped by `markup()`.

Property chips: **COMM blue · ASSOC purple · DIST yellow · CALC green · REWRITE white**.
Like-terms chip (0.4): **COMBINE green**, next to DIST yellow.

How it behaves:

- **Typed answers** (`num` and `expr`): there are no options. The student types the answer in an
  `<equation-editor>` and it is checked exactly by
  [`components/answer-check/`](../components/answer-check/answer-check.js): a number must be one
  number (`17`, `−5`, `3/4`, `0.75` are read exactly, so `6/8 = 3/4`); an expression must equal the
  answer at the six test points **and** be finished (no parentheses, like terms combined). Something
  equal but unfinished, or unreadable, gets a hint and does not count as a try.
- The three `wrong` entries of a typed exercise are its **known mistakes**: typing one of their
  values names the mistake. Any other wrong value gets a general message. Either way the
  step-by-step video plays and the student can fix the answer.
- **Picked answers** (`name`): options are shuffled every time; every wrong option is the result of
  one named mistake, and choosing it says which and plays the video; the student can pick again.
- **Select all that apply** (`multi`): the student ticks options and presses Check. It is right only
  when the ticked set is exactly the right set. Wrong ticks are marked with their `why`; missed
  answers are only counted ("one more answer applies"), so the student still has to find them.
- **Matching** (`match`): a drop-down per left item. Every item must be matched before Check. Wrong
  rows are marked with their `why`. Both kinds play the video on a wrong check; their videos go
  through the options or pairs one block each and end with the full answer.
- The score counts exercises right on the first try; progress is kept in the browser.

## Files

| File | What it is |
|---|---|
| `exercises/<set>/exercises.json` | Source of truth: question, solution lines, spoken steps, wrong options. |
| `exercises/<set>/index.html` | The practice page. **Generated**, do not edit by hand. |
| `videos/<set>-exNN/` | One solution video per exercise (`script.json`, `video.html` generated; `narration.mp3`, `timeline.json` from the audio pipeline). |
| `tools/build_exercises.py` | Checks every number, then generates the pages. |
| `tools/quiz_template.html` | Template of the practice page. |
| `video-scripts/<set>-solutions.md` | The solution videos' scripts, for review (`python3 tools/solution_scripts.py exercises/<set>`). |

## Why the numbers can be trusted

`build_exercises.py` evaluates each question, each line of each solution and each wrong option with
exact fractions. It fails if a solution line does not equal the answer, if a wrong option equals the
answer, if two options coincide, or if a narration anchor word is missing. The narration of the
"common traps" block is built from the computed values, so spoken numbers cannot drift.

```
python3 tools/build_exercises.py exercises/u00-l01 --check   # validate only
python3 tools/build_exercises.py exercises/u00-l01           # validate + regenerate pages
```

## Adding or changing an exercise

1. Edit `exercises.json` (the `_notes` field explains the syntax: `⟨…⟩` marks what the next step computes,
   fractions are `[[top | bottom]]`, `at` is the word where each new line appears).
2. Run the build; fix whatever it reports.
3. Audio, as in [audio-production.md](audio-production.md). Only changed blocks cost anything
   (segments are cached by hash). One batch run can carry the lines of many videos:

```
for d in videos/u00-l01-ex*; do python3 tools/plan_audio.py $d; done      # one job.json each
# merge the job.json files into one JSON array, run the printed gh command once, then:
git -C ../api-access fetch --depth 1 origin audio-temp
for d in videos/u00-l01-ex*; do python3 tools/plan_audio.py $d --fetch ../api-access; python3 tools/assemble_audio.py $d; done
```

The 20 videos of 0.1 are 133 blocks, about 11,300 characters, in a single run. All 26 videos of 0.2
(two lessons + 24 solutions) are 162 blocks, about 14,500 characters, also in one run.
