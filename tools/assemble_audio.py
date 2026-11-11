#!/usr/bin/env python3
"""Assemble a video's narration from its cached segments.

    python3 tools/assemble_audio.py videos/<video>

Reads script.json and videos/_segments/, then writes narration.mp3 and timeline.json in the
video folder: each segment trimmed, leveled to the same loudness, joined with fixed gaps, and
the whole file normalized. timeline.json says when each scene, block and word is heard.
Fish Audio gives no word timings, so words are spread inside each block by syllables and
anchored to the pauses heard after commas and periods (same method as the Noli library book).
See docs/audio-production.md.
"""
import json
import pathlib
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import plan_audio as P  # noqa: E402

SR = 44100
LEAD_S = 0.8
GAP = {"block": 0.6, "scene": 1.4}
SILENCE_DB = -38      # below the segment's peak
EDGE_KEEP_S = 0.03
MIN_PAUSE_S = 0.12
SEGMENT_LUFS = -18.0
FINAL = {"lufs": -16.0, "tp": -1.5, "bitrate": "96k"}


def decode(f):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def energy_db(a, hop):
    n = len(a) // hop
    e = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9
    return 20 * np.log10(e / (np.abs(a).max() + 1e-9))


def trim(a):
    """Cut edge silence; return audio and its inner pauses [(start, end)] in seconds."""
    hop = int(SR * 0.01)
    e = energy_db(a, hop)
    voiced = np.where(e > SILENCE_DB)[0]
    if len(voiced) == 0:
        return a, []
    keep = int(EDGE_KEEP_S / 0.01)
    i0, i1 = max(0, voiced[0] - keep), min(len(e), voiced[-1] + 1 + keep)
    a, e = a[i0 * hop: i1 * hop], e[i0:i1]
    pauses, start = [], None
    for k, v in enumerate(e > SILENCE_DB):
        if not v and start is None:
            start = k
        if v and start is not None:
            if (k - start) * 0.01 >= MIN_PAUSE_S:
                pauses.append((start * 0.01, k * 0.01))
            start = None
    return a, pauses


def lufs(a):
    """Integrated loudness (LUFS) of a PCM buffer, measured by ffmpeg's ebur128 filter."""
    pad = np.concatenate([a, a]) if len(a) < SR * 0.5 else a   # ebur128 needs >400 ms
    r = subprocess.run(["ffmpeg", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
                        "-af", "ebur128", "-f", "null", "-"], input=pad.astype(np.float32).tobytes(),
                       capture_output=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr.decode())
    return float(m[-1]) if m else -70.0


def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    n = len(re.findall(r"[aeiouy]+", w)) - (1 if w.endswith("e") and not w.endswith(("le", "ee")) and len(w) > 3 else 0)
    return max(1, n)


def word_times(text, dur, pauses, t0):
    words = text.split()
    if not words:
        return []
    weights = [syllables(w) for w in words]
    total = sum(weights)
    speech = dur - sum(b - a for a, b in pauses)
    acc, ideal = 0, []
    for w in weights:
        acc += w
        ideal.append(speech * acc / total)
    anchors, free, shift = {}, list(pauses), 0.0
    for k, w in enumerate(words[:-1]):
        if re.search(r"[,.!?;:]['\"”’)]*$", w) and free:
            expect = ideal[k] + shift
            best = min(free, key=lambda p: abs(p[0] - expect))
            if abs(best[0] - expect) < 0.8:
                anchors[k] = best
                shift += best[1] - best[0]
                free = [p for p in free if p[0] > best[0]]
    cuts = [(-1, (0.0, 0.0))] + [(k, anchors[k]) for k in sorted(anchors)] + [(len(words) - 1, (dur, dur))]
    out, start = [None] * len(words), 0.0
    for (ka, _), (kb, pause) in zip(cuts, cuts[1:]):
        end = pause[0]
        group = range(ka + 1, kb + 1)
        sub = sum(weights[i] for i in group) or 1
        t = start
        for i in group:
            d = (end - start) * weights[i] / sub
            out[i] = {"w": words[i], "t0": round(t0 + t, 2), "t1": round(t0 + t + d, 2)}
            t += d
        start = pause[1]
    return out


def finish(pcm, dest):
    raw = pcm.astype(np.float32).tobytes()
    base = ["ffmpeg", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0"]
    ln = f"loudnorm=I={FINAL['lufs']}:TP={FINAL['tp']}:LRA=11"
    r = subprocess.run(base + ["-af", ln + ":print_format=json", "-f", "null", "-"], input=raw, capture_output=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr.decode()).group(0))
    ln2 = (f"{ln}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    tmp = dest.with_name(dest.stem + ".tmp.mp3")
    subprocess.run(base + ["-af", ln2, "-ar", str(SR), "-codec:a", "libmp3lame", "-b:a", FINAL["bitrate"], "-y", str(tmp)],
                   input=raw, capture_output=True, check=True)
    tmp.replace(dest)


def assemble(video_dir):
    script, voices = P.load(video_dir)
    order = list(P.blocks(script, voices))
    missing = [b["id"] for b, *_, name in order if not (P.SEGMENTS / f"{name}.mp3").exists()]
    if missing:
        sys.exit(f"Missing segments for {', '.join(missing)}: run plan_audio.py, generate and --fetch first.")
    scene_of = {b["id"]: s["id"] for s in script["scenes"] for b in s["blocks"]}
    parts, t = [np.zeros(int(LEAD_S * SR), np.float32)], LEAD_S
    tl_blocks, scenes, prev = [], {}, None
    for b, _, _, _, name in order:
        sc = scene_of[b["id"]]
        if prev is not None:
            gap = prev.get("pause_after_s", GAP["scene"] if scene_of[prev["id"]] != sc else GAP["block"])
            parts.append(np.zeros(int(gap * SR), np.float32))
            t += gap
        a, pauses = trim(decode(P.SEGMENTS / f"{name}.mp3"))
        gain = 10 ** ((SEGMENT_LUFS - lufs(a)) / 20)
        a = np.clip(a * min(gain, 8.0), -1, 1)
        dur = len(a) / SR
        tl_blocks.append({"id": b["id"], "scene": sc, "cue": b.get("cue"), "display": b.get("display"),
                          "t0": round(t, 2), "t1": round(t + dur, 2), "words": word_times(b["text"], dur, pauses, t)})
        scenes.setdefault(sc, [round(t, 2), None])[1] = round(t + dur, 2)
        parts.append(a)
        t += dur
        prev = b
    tail = prev.get("pause_after_s", 1.0)
    parts.append(np.zeros(int(tail * SR), np.float32))
    t += tail
    finish(np.concatenate(parts), video_dir / "narration.mp3")
    timeline = {"video": script["video"], "duration": round(t, 2),
                "scenes": [{"id": k, "t0": v[0], "t1": v[1]} for k, v in scenes.items()],
                "blocks": tl_blocks}
    (video_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"narration.mp3: {t:.1f} s, {len(tl_blocks)} blocks -> {video_dir}")


if __name__ == "__main__":
    assemble(pathlib.Path(sys.argv[1]).resolve())
