# Unit exams

The rules are in [course-design.md](course-design.md#unit-exam). This file is how an exam is made.

## Files

| File | What it is |
|---|---|
| `exams/<unit>/bank.json` | Source of truth: the question bank (60–80 questions). Same exercise kinds and fields as a practice set ([exercises.md](exercises.md)), plus `blocks`, and `block` / `block_name` on every question. |
| `exams/<unit>/index.html` | The exam page. **Generated**, do not edit by hand. |
| `videos/<unit>-exam-exNN/` | The solution video of each Boss question (`script.json`, `video.html` generated; `narration.mp3`, `timeline.json` from the audio pipeline). |
| `tools/build_exam.py` | Checks the bank against the exam rules and every number with the practice-set validators, then writes the page and the Boss video pages. |
| `tools/exam_template.html` | Template of the exam page (it reuses the practice page's styles). |

`bank.json` header: `unit`, `title`, `levels`, `pass` (0.9), `draw` (`total` 10–20, one Boss per block), `video_unit` and
`video_title` (what the Boss videos call themselves; `{block}` is the block's name), `blocks` (`id`, `name`).

## Bank rules (checked by the build)

- 60–80 questions; **exactly 2 Boss (level 4) questions per learning block**, and at least one question of each level 1–3.
- Ids are `ex01…`, in bank order: the Boss video of the question at position N is `<unit>-exam-exNN`, so keep the ids in order.
- Levels 1–3 need `lines`, `chips` and `say`: they become the written step-by-step solution in the review.
  Boss questions need the same, plus `at` words (hand-picked), because they are also narrated.
- Numbers are computed, never typed: everything goes through `tools/build_exercises.py`'s validators.

```
python3 tools/build_exam.py exams/u00 --check   # validate only
python3 tools/build_exam.py exams/u00           # validate + regenerate the page and the Boss video pages
```

## How the page behaves

- A new attempt draws `draw.total` questions: one Boss per block (the one not used last time, when possible), the rest from
  levels 1–3 spread over the blocks, avoiding last attempt's questions. They are shown in course order.
- No feedback while answering; answers can change until **Review and submit → Submit the exam**. Empty questions count as wrong.
- The attempt in progress is kept under `algebra.exam.<unit>.v1` (so a reload does not lose it) and, on submit, appended to
  `algebra.exams.v1` as `{ "<unit>": [{ date, score, total, questions, answers }] }`, which the home page reads to unlock the next unit.
- The review shows the score, the score per block, and for every question the student's answer. For each wrong answer it shows
  the correct answer, the known mistake and the written steps; Boss questions also link their solution video once it has
  narration (`timeline.json` exists when the page is built — rebuild after producing the audio).

## Audio for the Boss videos

Narration spends Fish Audio credit ([audio-production.md](audio-production.md)); see "Before starting" in
[producing-a-topic.md](producing-a-topic.md). For Unit 0 it is 14 videos. Until it is done the review shows the written steps only.
