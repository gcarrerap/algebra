# Algebra

Interactive HTML lessons and animated videos for learning Algebra 1 (Grade 9, Kentucky Academic Standards).

- [`docs/producing-a-topic.md`](docs/producing-a-topic.md) — **how to produce a learning block** end to end: script → audio → video → checks → exercises → publish.
- [`SYLLABUS.md`](SYLLABUS.md) — units, topics and subtopics, with each video's estimated length.
- [`docs/course-design.md`](docs/course-design.md) — design rules: structure, videos, exercise types, unit exams and progression.
- [`index.html`](index.html) — home page: the whole course by chapter, unit, topic and subtopic (all collapsible), what is ready, unit locks and Export/Import of progress. To publish something, add its `video` / `practice` link (or a unit's `exam`) in the `COURSE` list at the bottom of the page.
- [`video-scripts/`](video-scripts/README.md) — the written script of every video (objective, topics, transcript, reflection pauses, screen notes) and its estimated length. **Every video starts here**, before any audio or animation; [`docs/video-scripts.md`](docs/video-scripts.md) has the format and the rules.
- [`docs/audio-production.md`](docs/audio-production.md) — how video narration is written, generated and assembled.
- [`docs/exercises.md`](docs/exercises.md) — practice sets (typed answers checked exactly, or picked options) with a solution video for every exercise.
- [`components/equation-editor/`](components/equation-editor/README.md) — reusable Word-style equation editor (`<equation-editor>`, `<equation-notebook>`) for any page.
- [`docs/video-production.md`](docs/video-production.md) — how the animated videos are built and rendered.

## Watch online

Published with GitHub Pages at **https://gcarrerap.github.io/algebra/** (Settings → Pages →
*Deploy from a branch*, `main`, `/ (root)`). `.nojekyll` is required: without it Pages hides
folders that start with `_`, such as `videos/_engine/`.
