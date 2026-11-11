#!/usr/bin/env python3
"""Plan the narration of a video: one Fish Audio batch line per block that has no audio yet.

    python3 tools/plan_audio.py videos/<video>              # writes videos/<video>/job.json
    python3 tools/plan_audio.py videos/<video> --fetch DIR  # copies finished segments from an
                                                            # api-access clone (audio-temp fetched)

Segment names are a hash of voice + parameters + final text, so editing one block only
regenerates that block. Cached segments live in videos/_segments/. See docs/audio-production.md.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEGMENTS = ROOT / "videos" / "_segments"
TONES = {"excited": "[excited]", "calm": "[calm]", "curious": "[curious, rising tone]", "whisper": "[whispers]"}


def load(video_dir):
    script = json.loads((video_dir / "script.json").read_text(encoding="utf-8"))
    voices = json.loads((ROOT / "videos" / "voices.json").read_text(encoding="utf-8"))
    return script, voices


def blocks(script, voices):
    """Yield (block, voice profile, final text, speed, segment name) in script order."""
    for scene in script["scenes"]:
        for b in scene["blocks"]:
            key = b.get("voice", script["voice"])
            if key not in voices:
                sys.exit(f"{b['id']}: unknown voice {key!r}")
            prof = voices[key]
            if b.get("tone") and b["tone"] not in TONES:
                sys.exit(f"{b['id']}: unknown tone {b['tone']!r} (use {', '.join(TONES)})")
            text = (TONES[b["tone"]] + " " if b.get("tone") else "") + b["text"].strip()
            speed = float(b.get("speed", prof["params"].get("speed", 1.0)))
            p = prof["params"]
            sig = "|".join([prof["voice_id"], p["model"], p["temperature"], p["top_p"], p.get("language", "auto"),
                            f"{speed:g}", text])
            yield b, prof, text, speed, hashlib.sha1(sig.encode()).hexdigest()[:12]


def plan(video_dir):
    script, voices = load(video_dir)
    lines, profiles, total = [], set(), 0
    for b, prof, text, speed, name in blocks(script, voices):
        total += 1
        profiles.add(json.dumps(prof["params"], sort_keys=True))
        if (SEGMENTS / f"{name}.mp3").exists():
            continue
        lines.append({"f": f"algebra/{script['video']}/{name}.mp3", "t": text, "v": prof["voice_id"], "s": speed})
    if len(profiles) > 1:
        sys.exit("Blocks use voice profiles with different model/temperature/top_p: split them into separate runs.")
    params = json.loads(profiles.pop())
    job = video_dir / "job.json"
    job.write_text(json.dumps(lines, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    chars = sum(len(l["t"]) for l in lines)
    print(f"{total} blocks, {total - len(lines)} cached, {len(lines)} to generate ({chars} characters) -> {job}")
    if lines:
        print("gh workflow run fish-batch-text-to-speech.yml --repo gcarrerap/api-access --ref main "
              f"-f lines=\"$(cat {job})\" -f model={params['model']} -f temperature={params['temperature']} "
              f"-f top_p={params['top_p']} -f language={params.get('language', 'auto')} "
              f"-f mp3_bitrate={params.get('mp3_bitrate', '128')}")


def fetch(video_dir, api_access):
    script, voices = load(video_dir)
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    got = missing = 0
    for b, _, _, _, name in blocks(script, voices):
        dest = SEGMENTS / f"{name}.mp3"
        if dest.exists():
            continue
        r = subprocess.run(["git", "-C", str(api_access), "show", f"FETCH_HEAD:fish/algebra/{script['video']}/{name}.mp3"],
                           capture_output=True)
        if r.returncode == 0 and r.stdout:
            dest.write_bytes(r.stdout)
            got += 1
        else:
            print(f"missing {b['id']} ({name})")
            missing += 1
    print(f"{got} segments fetched, {missing} missing")
    return missing == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video_dir", type=pathlib.Path)
    ap.add_argument("--fetch", type=pathlib.Path, metavar="API_ACCESS_CLONE",
                    help="copy segments from FETCH_HEAD (run `git fetch --depth 1 origin audio-temp` there first)")
    a = ap.parse_args()
    if a.fetch:
        sys.exit(0 if fetch(a.video_dir.resolve(), a.fetch) else 1)
    plan(a.video_dir.resolve())


if __name__ == "__main__":
    main()
