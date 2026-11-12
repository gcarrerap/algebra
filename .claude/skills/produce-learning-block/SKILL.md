---
name: produce-learning-block
description: Use when asked to produce, build or continue with a lesson, topic or subtopic of the algebra course (its video, practice set, or both), e.g. "produce 0.3" or "continue with the next topic".
---

# Produce a learning block

The procedure lives in `docs/producing-a-topic.md`; this skill is the order of work. Read that
document and `docs/course-design.md` before starting, and follow the linked docs for each step.

1. **Pick the block.** If the person named one, use it. "Next" or "continue" means the first block
   in `SYLLABUS.md` order whose status in `video-scripts/uNN.md` is not `produced`. Say which one
   in your first sentence.
2. **Check prerequisites.** The script exists and `python3 tools/estimate_scripts.py --check`
   passes; `gh workflow list --repo gcarrerap/api-access` works. If `gh` is refused (403), attach
   `gcarrerap/api-access` yourself as the runbook's "Access" bullet says; only if that fails, ask
   the person to attach it, and stop until it works.
3. **Make a task list** with the nine steps of the runbook; tick them off as you go.
4. **Script → `script.json` → audio** (runbook steps 2–3). Compare the real length with the
   estimate; investigate a gap over ~5%.
5. **`video.html`** (step 4). Use the shared components in `videos/_engine/` (number line, …). If
   the block needs a diagram no component draws yet, build it as a new shared component and
   document it in `docs/video-production.md` instead of drawing one-off SVG.
6. **Check stills** (step 5): every scene at its busiest moment and every pause. Look at them; fix
   overlaps, the caption zone, timing and colors. Repeat until clean. Delete the stills.
7. **Exercises and solution audio** (steps 6–7). If the answers need a kind the checker doesn't
   support, extend the checker first.
8. **Publish and commit** (steps 8–9), then report in a few lines: what was made, real vs.
   estimated length, credit spent (runs and characters), anything left open.

## When you get stuck, report it

Guillermo wants to know every place where the docs or tools were not enough, so the repo can be
fixed. Being stuck means any of these:

- a step the docs don't explain, or explain wrongly, and you had to guess or work it out;
- a command or tool that fails, or a workaround you had to use;
- a missing capability (a diagram with no component, an answer kind the checker can't check);
- access or credit problems (`gh` refused, a failed audio run);
- a rule you could not meet (length, pauses, an overlap you could not fix).

For each one, **tell him explicitly**, in a section of your final message titled
**"Where I got stuck"**: what happened, at which step, what you did about it (resolved, worked
around, or left open), and which doc or tool should change so the next agent doesn't hit it. If
something blocks the work entirely, stop and report it right away instead of guessing. If nothing
went wrong, say so in one line ("Nothing blocked me"); never leave the section out.

Never type numbers from memory into a video or an exercise: compute them, or let the build
validate them. Keep everything the learner sees in English.
