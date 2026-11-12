# Algebra course — notes for agents

Interactive Algebra 1 lessons (Grade 9, Kentucky) for Ana: narrated HTML/CSS videos, practice sets
and unit exams, published with GitHub Pages from `main`. Everything a learner sees is in
**English**; conversations with Guillermo are often in Spanish.

- Rules of the course: `docs/course-design.md`. When a page disagrees with it, the page is wrong.
- Producing a lesson (script → audio → video → checks → exercises → publish):
  `docs/producing-a-topic.md`. The repo skill `produce-learning-block` walks through it.
- Every video starts as a written script in `video-scripts/uNN.md`; change the script before the
  video, and rerun `python3 tools/estimate_scripts.py` after any script change.
- Numbers must be computed, never typed from memory: exercise sets are validated by
  `tools/build_exercises.py`, and generated files (practice `index.html`, solution `script.json`,
  `video-scripts/*-solutions.md`, the script index table) are never edited by hand.
- Audio runs spend Fish Audio credit through `gcarrerap/api-access`; see "Before starting" in the
  runbook for when that is authorized.
- Other sessions push to this repo: pull before committing, keep one commit per piece of work.
