# Video scripts

Every video starts as a **written script** (in `video-scripts/`), before any `script.json`,
audio or animation exists. The script is where the lesson is decided: what it must achieve,
what it covers, every word the narrator says, every pause, and what the screen shows.
Because it has every word and every pause, it also gives the video's **length before it is
made**, and that length decides whether a topic is one video or is split into subtopics.

```
video-scripts/uNN.md ─► script.json ─► narration.mp3 + timeline.json ─► video.html ─► video.mp4
   (this doc)            (audio-production.md)                          (video-production.md)
```

## Files

| File | What it is |
|---|---|
| `video-scripts/README.md` | Index of every video with its estimated length (table generated). |
| `video-scripts/uNN.md` | Scripts of every lesson video of unit NN, in syllabus order. |
| `video-scripts/<set>-solutions.md` | Scripts of the solution videos of a practice set (generated from their `script.json`). |
| `tools/estimate_scripts.py` | Checks the rules below and writes each video's estimated length. |

## Format of a lesson video script

```markdown
## 3.1 · Rate of change
- **Video:** `u03-l01-rate-of-change`
- **Status:** script
- **Estimated length:** 5:40 (…)

**Objective.** What Ana can do after watching, in one or two sentences.

**Topics.**
- Each idea the video covers, in order.

#### S1 · The hook
*Screen:* what is on screen when the scene starts.
> Spoken text, one voice block per line, written the way it is read aloud.
*Screen:* what appears or changes, and on which word.
> Here's a question. Why does the line get steeper?
[REFLECT 10s] *Screen:* the question stays; a countdown ring fills.
```

- `## <number> · <title>`: the number is the learning block (`3.1` for a topic, `3.1.1`,
  `3.1.2` for its subtopics, as in the syllabus).
- Lines starting with `> ` are the **transcript**. Each one becomes one block of
  `script.json`, so it follows the rules of [audio-production.md §4](audio-production.md):
  no math symbols, numbers spelled out, "the quantity" for a parenthesized sum.
- `*Screen:*` lines are the **notes for the video**: the math shown (with symbols), colors,
  highlights, diagrams and graphs. They become `display`, `cue` and the scenes of `video.html`.
- `#### S<n> · <title>` starts a scene (the video crossfades and the audio leaves a longer gap).
- Every video ends with the line `> This video uses an AI-generated voice.`

## Pauses for reflection

The videos are meant to be watched slowly. A question is followed by **real silence**, long
enough to think, with the question still on screen and a countdown ring (`timer` class) that
fills during the pause. Three kinds:

| Mark | Length | When |
|---|---|---|
| `[THINK 5s]` | 5 s | After a quick question ("What is three times four?"). |
| `[REFLECT 10s]` | 10–12 s | After a *why* question, a prediction, or a new idea worth turning over. The narration says what to think about before the pause. |
| `[TRY IT 15s]` | 15–20 s | "Pause the video and try it": a full problem. The ring runs; the student can also pause. |

Rules every lesson video follows (checked by the tool):

- At least **two `REFLECT`** and **one `TRY IT`** pause.
- The pause belongs to the block before it: in `script.json` it is that block's
  `pause_after_s`; in `video.html` it is a `timer` from `bNN.end` to `bNN.end+<seconds>`.
- Pauses count in the length. In a typical video they are 50–80 s of 5–7 minutes.

## Length and splitting

The estimate uses the narrator's measured pace (150 words per minute) plus the same gaps the
audio assembly adds (0.6 s between blocks, 1.4 s between scenes) and every pause. On the three
produced lesson videos it is within 3% of the real narration.

| Estimated length | Decision |
|---|---|
| under 3 min | Fine for a small idea; consider merging it with a neighbour. |
| 3–7 min | **Target.** |
| 7–10 min | Allowed, but look for a natural split. |
| over 10 min | **Must** be split into subtopics (the tool fails). |

When a topic is split, each subtopic gets its own script, video and exercise set
([course-design.md](course-design.md)), and the split goes into [SYLLABUS.md](../SYLLABUS.md)
and the course tree in [index.html](../index.html).

```
python3 tools/estimate_scripts.py           # update every estimate and the index table
python3 tools/estimate_scripts.py --check   # only check the rules
```

## Statuses

| Status | Meaning |
|---|---|
| `script` | Written; no audio yet. |
| `produced` | `script.json`, audio and `video.html` exist in `videos/`. A note says if the produced video differs from the script (for example shorter pauses). |

## From script to `script.json`

1. Copy the transcript lines in order: one `> ` line = one block (`b01`, `b02`…), one
   `#### S` heading = one scene.
2. Put each pause's seconds in the `pause_after_s` of the block before it.
3. Take `display` (the math on screen) and `cue` from the `*Screen:*` notes.
4. Read the transcript aloud once; then follow [audio-production.md](audio-production.md).

## Solution videos

Solution videos of practice sets are built from `exercises/<set>/exercises.json`
([exercises.md](exercises.md)), which is their source of truth. Their scripts
(`video-scripts/<set>-solutions.md`) are generated from the produced `script.json` files
so they can be reviewed with the lesson scripts:

```
python3 tools/solution_scripts.py exercises/u00-l01
```
