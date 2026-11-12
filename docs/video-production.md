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
| `videos/<video>/video.html` | The scenes of one video, with timing anchors. |
| `tools/render_video.py` | Takes stills or films the full MP4. |

The same `video.html` plays live in a browser with its narration: no MP4 needed. Tap the
screen to pause, tap the bar at the bottom to jump, or use Space and the arrow keys. It loads
`timeline.json` and `narration.mp3` next to it, so it must be served over http (any static
server on `videos/`); opening the file directly from disk or from GitHub's file view won't run it.

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
