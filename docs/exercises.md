# Practice sets

Each lesson can have a multiple-choice practice set. The first one is
[`exercises/u00-l01/`](../exercises/u00-l01/) (lesson 0.1, order of operations and signed numbers):
20 exercises in four levels (Warm-up, Tricky, Challenging, Boss level).

The second is [`exercises/u00-l02/`](../exercises/u00-l02/) (lesson 0.2, properties of operations), which
adds two kinds of exercise besides "find the value" (see the `_notes` in its `exercises.json`):

| `kind` | The question | How it is checked |
|---|---|---|
| `num` (default) | Find the value. | Exact fractions, as in 0.1. |
| `expr` | Expand an expression, e.g. `−3(x + 4)`. | Every line, the answer and every wrong option are evaluated at six sets of values of the variables (`x`, `y`…); lines must match the question at all of them, wrong options must not match the answer or each other. |
| `name` | Which property does an identity show? | Both sides must be equal, and the stated property must match the identity's shape (same order and same numbers = associative; same numbers in another order = commutative; otherwise distributive). The two other properties are the wrong options. |

Property chips: **COMM blue · ASSOC purple · DIST yellow · CALC green · REWRITE white**.

How it behaves:

- Options are shuffled every time an exercise is shown.
- Every wrong option is the real result of one named mistake (adding first, dropping a sign,
  reading `−3²` as `(−3)²`…). Choosing it says which mistake it was and plays that exercise's
  step-by-step video; the student can then pick again.
- The score counts exercises right on the first try; progress is kept in the browser.

## Files

| File | What it is |
|---|---|
| `exercises/<set>/exercises.json` | Source of truth: question, solution lines, spoken steps, wrong options. |
| `exercises/<set>/index.html` | The practice page. **Generated**, do not edit by hand. |
| `videos/<set>-exNN/` | One solution video per exercise (`script.json`, `video.html` generated; `narration.mp3`, `timeline.json` from the audio pipeline). |
| `tools/build_exercises.py` | Checks every number, then generates the pages. |
| `tools/quiz_template.html` | Template of the practice page. |

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

The 20 videos of 0.1 are 133 blocks, about 11,300 characters, in a single run. All 22 videos of 0.2
(two lessons + 20 solutions) are 162 blocks, about 14,500 characters, also in one run.
