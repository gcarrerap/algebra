# Course design rules

The rules every unit, topic, video, exercise set and exam must follow. When the existing pages
disagree with this document, this document wins and the page is the thing to fix
(see [Gaps in the current pages](#gaps-in-the-current-pages)).

## Structure

```
Chapter
└── Unit
    └── Topic
        └── Subtopic   (only when the topic needs it)
```

- Every unit is divided into **topics**.
- A topic is divided into **subtopics** only when it is complex enough to need it; a simple topic
  has none.
- The **learning block** is the topic, or each of its subtopics when it has them. Every learning
  block has exactly one video and one exercise set.

## Videos

- One video per learning block.
- Expected length **3–6 minutes**; **10 minutes at most**. A topic that needs more than 10 minutes
  must be split into subtopics.
- Built and narrated as described in [video-production.md](video-production.md) and
  [audio-production.md](audio-production.md).

## Exercise sets

Every video is followed by exercises that test what the video taught.

### Exercise types

The type depends on the topic. Available types:

| Type | The student… | Notes |
|---|---|---|
| **Solve / find the value** | types the result | **Never multiple choice.** Always shows the work area. |
| **Single choice** | picks the one correct answer | |
| **Multiple select** | picks *all* the answers that apply | Right only if the selection is exactly the correct set. |
| **Matching** | relates concepts in two columns | e.g. property ↔ identity, term ↔ definition. |
| Others | as the topic needs | Add a row here when a new type is created. |

### Solve / find-the-value exercises

- The student **types the value**; there are no options to pick from.
- The page includes a **work area**, the same one exercise set 0.1 has today
  (`<equation-notebook>` from [`components/equation-editor/`](../components/equation-editor/README.md),
  one notebook per exercise, kept on the device).
- Answers are checked exactly (equivalent forms of the same value count as right, e.g. `3/4`,
  `6/8`, `0.75`), never by comparing text.

### Wrong answers

When the answer is wrong:

1. Show **feedback** saying what went wrong (for typed answers, name the likely mistake when the
   value matches a known one).
2. Play a **video explaining the correct solution** step by step.

## Unit exam

Every unit ends with an exam.

- Questions cover **all topics and subtopics of the unit**.
- **10–20 questions** per exam, at a **challenging** level.
- Drawn from a **bank of 60–80 questions** per unit, so the exam is not the same every time.
  Each draw must still cover every topic of the unit.
- Same exercise types as the practice sets; find-the-value questions are typed and have the work
  area.
- **No feedback during the exam.** Nothing says whether an answer is right until the whole exam
  is submitted. Once submitted, answers **cannot be changed**.
- **Passing score: 90% or more.**

## Progression

- A unit is **locked** until the previous unit's exam is passed with 90% or more.
- The exam can be retaken; each attempt draws a new set of questions from the bank.

## Home page navigation

- The course tree on the home page is **collapsible at every level**: chapters, units, topics and
  subtopics.
- Locked units are shown as locked.

## Chapters

The 14 units of [SYLLABUS.md](../SYLLABUS.md) are grouped into six chapters:

| Chapter | Units |
|---|---|
| 1. Foundations | 0 Foundations and Expressions · 1 Linear Equations and Inequalities |
| 2. Functions and Linear Models | 2 Functions · 3 Linear Functions · 4 Sequences |
| 3. Systems and Data | 5 Systems of Equations and Inequalities · 6 Statistics: Two-Variable Data |
| 4. Exponents and Exponential Functions | 7 Exponents and Radicals · 8 Exponential Functions |
| 5. Polynomials and Quadratics | 9 Polynomials · 10 Factoring · 11 Quadratic Functions · 12 Solving Quadratic Equations |
| 6. Modeling | 13 Modeling and Final Review |

Chapters only group units for navigation; locking stays per unit. Unit numbers do not change.

## Exam feedback and solution videos

- **During the exam** there is no feedback of any kind: no right/wrong marks, no correct answers,
  no videos. The student answers every question and submits the exam.
- **After submitting**, the exam shows the **score** and a review of every question: the
  student's answer, the correct one, what was wrong (the mistake, when it is a known one) and,
  for each wrong answer, its **solution video**.
- Submitted answers are final; to improve the score the student takes a new attempt.
- Every question in the bank therefore has a solution video, as practice exercises do.

## Where progress is stored

- Progress (practice results, work areas, exam attempts, unlocked units) stays in the browser's
  `localStorage`, under one key per course. The site is static on GitHub Pages, so there is no
  server to keep it.
- To move it to another device or protect it from a cleared browser, the home page has
  **Export progress** (downloads a `.json` file) and **Import progress** (loads one).
- It is not tamper-proof: someone who knows how can edit it. Accepted for a family course.
- An exam attempt is recorded as: unit, date, questions drawn, answers, score. A unit is unlocked
  when any attempt of the previous unit scored 90% or more.

## Gaps in the current pages

What already exists and does not follow these rules yet:

| Rule | Today |
|---|---|
| Find-the-value is typed, not multiple choice | 0.1 and 0.2 practice sets are multiple choice (`kind: num` shows options). |
| Single choice, multiple select, matching | Only single choice exists. |
| Unit exam with question bank, ≥90% to unlock | No exams, no question banks, no locking. |
| Collapsible chapters / units / topics / subtopics | Home page lists units and lessons; no chapters or subtopics, not collapsible. |
| Work area on every find-the-value exercise | Present in 0.1; missing in 0.2. |
