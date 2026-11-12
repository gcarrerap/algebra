# Video Production

Each algebra video is an HTML/CSS page driven by its narration's `timeline.json`
(see [audio-production.md](audio-production.md)), filmed frame by frame into an MP4.
It starts from the video's written script in `video-scripts/` ([video-scripts.md](video-scripts.md)),
whose `*Screen:*` notes say what each scene shows and on which words.

```
video-scripts/uNN.md ─► script.json ─► narration.mp3 + timeline.json ─► video.html ─► stills ─► video.mp4
```

## Files

| File | What it is |
|---|---|
| `videos/_engine/player.js` | Draws the video at any time `t` from `timeline.json`. Shared by all videos. |
| `videos/_engine/player.css` | Shared look: 1920×1080 stage, colors, type, effects. |
| `videos/_engine/numberline.js` | Number-line component (below). Load it before `player.js`. |
| `videos/<video>/video.html` | The scenes of one video, with timing anchors. |
| `tools/render_video.py` | Takes stills or films the full MP4. |

The same `video.html` plays live in a browser with its narration: no MP4 needed. Tap the
screen to pause, tap the bar at the bottom to jump, or use Space and the arrow keys. It loads
`timeline.json` and `narration.mp3` next to it, so it must be served over http (any static
server on `videos/`); opening the file directly from disk or from GitHub's file view won't run it.

## Player controls

Rules from [course-design.md](course-design.md#videos); **not built yet** (see its "Gaps" table):

- A visible control bar shows the **current time and the total duration** (`timeline.json`'s
  `duration`) and a **full-screen** button (the stage scales to the screen).
- **First viewing: no seeking.** The progress bar is display-only, taps on it and the arrow keys
  do nothing; play and pause still work.
- **After the video has played to the end once**, the bar is a slider again: tap or drag to jump,
  arrow keys to step. Remember "watched" per video in the browser (`localStorage`, one entry per
  video id, in the same spirit as the exam results `algebra.exams.v1`); clearing the browser's
  data starts again at the first viewing.
- Pausing, and resuming, are always allowed.

## Web version (no MP4)

```
python3 tools/build_web.py videos/<video>      # -> dist/<video>/ (git-ignored)
```

`dist/<video>/` holds `index.html` plus `player.css`, `player.js`, `timeline.json` and
`narration.mp3`, ready to publish as a page (a claude.ai artifact, or any static host).

## Writing a video page

One `<section class="scene" data-scene="sNN">` per scene in `script.json`. Scenes
crossfade by themselves just before their first word.

Any element with `data-at` appears at that moment; `data-out` makes it go away.
Times are **anchors in the narration**, never seconds from the start, so a regenerated
take or a longer pause never breaks the sync:

| Anchor | Moment |
|---|---|
| `b07` | block b07 starts |
| `b07.end` | block b07 ends |
| `b07@nine` | the word "nine" in b07 is said |
| `b07@six#2` | the second "six" in b07 |
| `b07@nine+0.5` | half a second after it (any anchor ± seconds) |

The class decides what the element does when it appears:

| Class | Effect |
|---|---|
| `fade` / `pop` / `slide` | appears (rises, grows, slides in) |
| `hl` + `c-<color>` | highlight box around part of an expression |
| `tint` + `c-<color>` | text turns that color |
| `strike` | red line across |
| `dim` | fades to 35% |
| `glow` | colored outline and glow (cards) |
| `timer` | countdown ring that fills from `data-at` to `data-out` |

Layout helpers: `math` (`md`, `sm`, `xs`), `say`, `label`, `card`, `chip`, `row`, `col`,
`stack` (children share one spot, for swapping content in place), `layer`.

### Shared components

Draw recurring diagrams with the shared components instead of new SVG in each video, so every
video looks the same and fixes reach all of them.

**Number line** (`numberline.js`, styles in `player.css`). Marks are `<i>` children; each one
animates with the usual `data-at` / `data-out` / `data-dur`, and its color comes from `c-<color>`:

```html
<div class="numberline" data-from="-10" data-to="10" data-unit="80">
  <i class="dot c-blue"    data-n="3" data-label="3°" data-at="b01@three"></i>
  <i class="hop c-red"     data-a="3" data-b="-5" data-lift="60" data-at="b01@drops" data-dur="1.6"></i>
  <i class="span c-purple" data-a="-5" data-b="0" data-at="b04@absolute"></i>
  <i class="ray c-green"   data-n="2" data-dir="right" data-open data-at="b09"></i>
</div>
```

`dot` is a point (`data-open` for an open circle), `hop` an arrow drawn over `data-dur` seconds,
`span` a bracket under the labels, `ray` a shaded ray for inequality graphs. Width is
`(to − from) × unit + 120` px: keep it under ~1750. First used in `u00-l01-signed-numbers`.

Still to build, before the units that need them: a coordinate plane (points, lines, parabolas,
shaded half-planes; units 2–13), a table with difference/ratio arrows (units 4, 8, 13) and an
area model (units 9–10). Add each one as an `_engine/*.js` component documented here.

### Pitfalls

- **Repeated words.** `b21@two` matches the *first* "two" in the block, even at the start of a
  sentence ("Two times…"). Count the occurrences in the block's text and use `#2`, `#3`.
- **One offset only.** `b14@jumps+0.7` works; `b14@jumps+0.7+0.6` is an error. Compute the sum.
- **Pauses.** A timer during a pause goes from `bNN.end` to the next block (`data-out="bMM"`).
- **Caption zone.** The caption covers the bottom ~170 px of the stage; keep content above it.
- **Changing in place.** To swap one value for another in the same spot (`?` → `4`), put both in a
  `stack` and fade one out on the word the other fades in.
- **CSS inheritance.** `--p` is set on the element with `data-at` and inherits to its children,
  so a group can animate several parts (like a hop's arc and head) from one anchor.

### Reflection pauses

A pause from the script (`[REFLECT 10s]`, `[TRY IT 15s]`) is the `pause_after_s` of the block
before it. Keep the question on screen and show a countdown ring for the whole silence:
`<div class="timer" data-at="b07.end" data-out="b07.end+10"></div>`.

### Visual conventions

- One step of the order of operations = one color, in every video:
  **P blue · E purple · MD yellow · AS green**. Wrong paths are red.
- Show each step of a calculation **on the word that says its result**
  (`data-at="b15@nine"` for "three squared is nine").
- Show symbols on screen; the narration says them in words.
- The bottom caption follows the narration word by word automatically.

## Rendering

```
python3 tools/render_video.py videos/<video> --stills 20.5 41 63   # check the busiest moments first
python3 tools/render_video.py videos/<video>                       # full render -> video.mp4
```

The renderer refuses to run if an anchor doesn't match the timeline (for example a word
that isn't in the block). Frames are 1920×1080 at 30 fps, encoded with H.264 (CRF 18),
chunk by chunk in parallel, then joined with the narration (AAC 160 kb/s).

`video.mp4` is not committed (see `.gitignore`).
