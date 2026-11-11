# Audio Production for Algebra Videos

How the narration for every algebra video is written, generated, assembled and
handed to the video. The process reuses what already works in two other repos:

- **`gcarrerap/podcast`** — script as JSON (one block = one voice take), hash-named
  segments so unchanged lines are never paid for twice, loudness normalization
  with ffmpeg, and an AI-content disclosure in every episode.
- **`gcarrerap/noli`** (the *Mari and the Pumpkin Spaceship* book in the Library) —
  Fish Audio voices generated in **one batch run per chapter**, pieces joined with
  fixed gaps, and a **timing file** that says when each sentence and word is
  heard, so the screen can react to the voice.

Voices are generated through the GitHub Actions workflows of
**`gcarrerap/api-access`**. API keys live there as repo secrets and never enter this repo.

---

## 1. Pipeline at a glance

```
script.json ──► batch job ──► FishBatchTextToSpeech ──► audio-temp branch
 (narration +    (one line                              (fish/algebra/<video>/…)
  visual cues)    per block)                                      │
                                                                  ▼
video (HTML/CSS) ◄── timeline.json + narration.mp3 ◄── assemble (trim, level, gaps)
```

1. **Write** the video script (`script.json`): scenes, narration blocks, and the
   visual cue each block triggers.
2. **Plan**: turn every block into a batch line with a hash-based file name; skip
   blocks whose file already exists.
3. **Generate**: one run of `FishBatchTextToSpeech` per video.
4. **Download** the segments from the `audio-temp` branch (it resets after 7 days).
5. **Assemble**: trim, level, add gaps, and write `narration.mp3` + `timeline.json`.
6. **Review**: listen once, fix bad takes by regenerating only those blocks.
7. The video renderer reads `timeline.json` so every animation lands on its words.

---

## 2. Folder layout

```
videos/
  u00-l01-order-of-operations/
    script.json        # source of truth: narration + cues (edited by hand)
    timeline.json      # generated: when each block/word is heard
    narration.mp3      # generated: final narration (mono, small)
    video.html         # the CSS/HTML animation (see the video doc)
  _segments/           # git-ignored cache of downloaded takes, by hash
```

Naming: `u<unit>-l<lesson>-<slug>`, matching `SYLLABUS.md` (unit 0, lesson 1 →
`u00-l01`). Final MP4 files are **not** committed (too large); see §9.

---

## 3. The script (`script.json`)

Adapted from the podcast's audio-script format: every block is one voice take,
and every property belongs explicitly to a block.

```json
{
  "format": "algebra-video-script",
  "version": 1,
  "video": "u00-l01-order-of-operations",
  "title": "Order of Operations",
  "voice": "narrator",
  "scenes": [
    {
      "id": "s01",
      "blocks": [
        {"id": "b01", "text": "What is two plus three times four?", "cue": "show-problem"},
        {"id": "b02", "text": "If you said twenty, you're not alone. But the answer is fourteen.",
         "cue": "reveal-answer", "pause_after_s": 0.8}
      ]
    }
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `voice` | yes | Key in `voices.json` (§5). A block may override it with its own `voice`. |
| `scenes[].id` | yes | Scene id; scenes get a longer gap between them. |
| `blocks[].id` | yes | Unique id (`b01`, `b02`…). |
| `blocks[].text` | yes | Exactly what is spoken, **written the way it is read aloud** (§4). |
| `blocks[].cue` | no | Name of the visual event that starts when this block starts. |
| `blocks[].display` | no | The on-screen math for this block (e.g. `2 + 3 × 4`), when it differs from the spoken text. |
| `blocks[].tone` | no | Delivery tag from §4.3 (`excited`, `calm`…). |
| `blocks[].speed` | no | Overrides the voice speed for this block. |
| `blocks[].pause_after_s` | no | Silence after this block. Default from §6. |

One block = one sentence or a short pair of sentences said in one breath. Keep
blocks short: a bad take is cheaper to redo, and cues land more precisely.

---

## 4. Writing narration for text-to-speech

TTS reads symbols unreliably. The **spoken text never contains math symbols**;
the symbols go in `display`, which is what the video shows.

### 4.1 Reading math aloud

| On screen | Write in `text` |
|---|---|
| `-3` | negative three |
| `3 - 5` | three minus five |
| `2x` | two x |
| `x²` / `x³` | x squared / x cubed |
| `xⁿ` | x to the n-th power |
| `3(x + 2)` | three times the quantity x plus two |
| `¾` | three fourths |
| `a/b` | a over b |
| `√9` | the square root of nine |
| `=` / `≠` | equals / is not equal to |
| `<` / `≤` | is less than / is less than or equal to |
| `f(x)` | f of x |
| `(2, 5)` | the point two, five |
| `|x|` | the absolute value of x |
| `y = mx + b` | y equals m x plus b |

Rules:

- Spell out every number and sign; write `0.5` as "zero point five" or "one half".
- Letters that are variables stand alone: "two x", not "2x" or "two-x".
- Say "the quantity" for a parenthesis whose content is a sum.
- Avoid "x" as "times" — always say "times".
- Read each script aloud once before generating: if it sounds odd to you, it will sound odd from the voice.

### 4.2 Teaching voice

- Second person, short sentences, one idea per block.
- Ask, pause, answer: put a question in its own block with `pause_after_s` of 1–1.5 s so Ana can think.
- Name the common mistake before the rule ("If you said twenty…").
- English throughout, at a Grade 9 level; vocabulary from the syllabus.

### 4.3 Delivery tags

Fish Audio's s2 models accept bracket tags. Scripts use a small neutral set in
`tone`, translated when the batch is built:

| `tone` | Sent as |
|---|---|
| `excited` | `[excited]` |
| `calm` | `[calm]` |
| `curious` | `[curious, rising tone]` |
| `whisper` | `[whispers]` |

Use them rarely; the default delivery should carry most of the video.

---

## 5. Voices

Voices live in `videos/voices.json`, one profile per key (voice + parameters),
like the podcast's voice registry:

```json
{
  "narrator": {
    "platform": "fish-audio",
    "name": "<name in the Fish Audio catalog>",
    "voice_id": "<id from the catalog>",
    "params": {"model": "s2.1-pro", "temperature": "0.5", "top_p": "0.7",
               "speed": "0.95", "language": "en", "mp3_bitrate": "128"}
  }
}
```

- Use only voices from the catalog: `config/fish-audio/voices.json` on `main`
  of `gcarrerap/api-access`. Never invent an id.
- English-capable candidates in the catalog today: **Narrator** (the book's
  narrator) and **Memo - english** (Guillermo's voice in English). The choice is
  pending.
- `temperature` 0.5 keeps a teaching voice steady; `speed` 0.9–0.95 gives room
  to follow the math. `language: en` makes numbers read in English.
- The same voice with other parameters is another profile with another key.

---

## 6. Generating the segments

### 6.1 Plan

For each block, the final text is `tone tag + text`, and its file name is a
hash of what changes the sound:

```
name = sha1(voice_id | model | temperature | top_p | speed | final text)[:12]
file = algebra/<video>/<name>.mp3
```

If `videos/_segments/<name>.mp3` already exists, the block is skipped. Editing one
sentence regenerates only that sentence (the podcast's rule: what didn't change
isn't paid again).

### 6.2 Batch run

One run of **FishBatchTextToSpeech** per video (as the book does per chapter).
`lines` is a JSON array, one entry per block that still needs audio:

```json
[{"f": "algebra/u00-l01-order-of-operations/3f9a1c0e2b7d.mp3",
  "t": "What is two plus three times four?",
  "v": "<voice_id>", "s": 0.95}]
```

```
gh workflow run fish-batch-text-to-speech.yml --repo gcarrerap/api-access --ref main \
  -f lines="$(cat job.json)" -f model="s2.1-pro" -f temperature="0.5" \
  -f top_p="0.7" -f language="en" -f mp3_bitrate="128"
```

Then wait for it: `gh run list --repo gcarrerap/api-access --workflow
fish-batch-text-to-speech.yml --limit 1` and `gh run view <id> --json
status,conclusion` until it is `completed`. On failure the "Generate speech"
step shows the Fish Audio error (402 = no credit, 401 = bad key, bad voice id).
Don't retry blindly. Every run spends credit, so generate only when asked.

The batch workflow takes `model`, `temperature` and `top_p` for the whole run and
`speed` per line, so all blocks of a video share one voice profile. A block with
another voice goes in a second run.

### 6.3 Download

Segments land in `fish/algebra/<video>/` on the throwaway **`audio-temp`** branch,
which resets once its newest commit is 7 days old. Download them right away into
the git-ignored cache:

```
git -C api-access fetch --depth 1 origin audio-temp
git -C api-access show FETCH_HEAD:fish/algebra/<video>/<name>.mp3 > videos/_segments/<name>.mp3
```

---

## 7. Assembling the narration

Same steps as the book's `voces.py armar` and the podcast's `unir_audios.py`:

1. **Decode** each segment to mono float PCM with ffmpeg (44.1 kHz).
2. **Trim** silence at both ends (threshold −38 dB below the segment's peak,
   keep 30 ms), and record pauses longer than 0.12 s inside it.
3. **Level** every segment to −18 LUFS so blocks match each other.
4. **Join** with gaps:

   | Between | Gap |
   |---|---|
   | blocks in the same scene | 0.35 s |
   | scenes | 0.8 s |
   | after a block with `pause_after_s` | that value |
   | before the first block | 0.5 s |

5. **Finish**: whole file to −16 LUFS, true peak −1.5 dBTP, MP3 mono 96 kbps →
   `narration.mp3`.
6. **Write `timeline.json`** (below).

### `timeline.json`

The contract between audio and video. Times are seconds from the start of
`narration.mp3`:

```json
{
  "video": "u00-l01-order-of-operations",
  "duration": 94.2,
  "scenes": [{"id": "s01", "t0": 0.5, "t1": 12.4}],
  "blocks": [
    {"id": "b01", "scene": "s01", "cue": "show-problem", "t0": 0.5, "t1": 2.6,
     "words": [{"w": "What", "t0": 0.5, "t1": 0.68}, {"w": "is", "t0": 0.68, "t1": 0.8}]}
  ]
}
```

Fish Audio returns no word timings, so — as in the book — words are spread
inside each block by syllable count, anchored to the pauses heard after commas
and periods. Blocks are short, so this is accurate enough for captions and
for highlighting a term as it is said.

---

## 8. Review checklist

- [ ] Every number, sign and variable is read correctly (listen with the script open).
- [ ] No block is clipped, mumbled, or has a strange accent shift; regenerate any
      that does by deleting its cached segment.
- [ ] Questions are followed by enough silence to think.
- [ ] Loudness is even from block to block.
- [ ] The outro includes the disclosure: *"This video uses an AI-generated voice."*

---

## 9. Storage

| What | Where |
|---|---|
| `script.json`, `timeline.json`, `narration.mp3` | This repo, in the video's folder (small). |
| Raw segments | `videos/_segments/` (git-ignored) — rebuilt from the script at any time. |
| Final MP4 | Not in the repo. Destination pending (Google Drive or YouTube). |

---

## 10. Prerequisites

- A GitHub token that can run workflows in `gcarrerap/api-access` (`gh` must be
  logged in).
- Fish Audio credit on the account behind `FISH_AUDIO_API_KEY`.
- `ffmpeg` and Python 3 with NumPy for assembly.

## 11. Open decisions

- [x] Narrator voice: **Memo - english**, profile `narrator` in `videos/voices.json`
      (first used in `u00-l01`).
- [ ] Where final MP4s are published.

## 12. Commands

```
python3 tools/plan_audio.py videos/<video>                    # writes job.json, prints the gh command
# run the printed gh command, wait for it to finish, then:
git -C ../api-access fetch --depth 1 origin audio-temp
python3 tools/plan_audio.py videos/<video> --fetch ../api-access
python3 tools/assemble_audio.py videos/<video>                # narration.mp3 + timeline.json
```
