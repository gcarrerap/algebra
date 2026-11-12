#!/usr/bin/env python3
"""Turn one video's written script (video-scripts/uNN.md) into its script.json.

    python3 tools/script_from_md.py 0.1.2        # -> videos/<video>/script.json

One `> ` line = one block, one `#### S` heading = one scene, a pause mark ([THINK 5s],
[REFLECT 10s], [TRY IT 15s]) = the pause_after_s of the block before it. The first math in
backticks on a `*Screen:*` line since the previous block becomes the block's `display`.
See docs/video-scripts.md. Refuses to overwrite a script.json unless --force.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAUSE = re.compile(r"\[(?:THINK|REFLECT|TRY IT) (\d+(?:\.\d+)?)s\]")


def find(number):
    unit = int(number.split(".")[0])
    path = ROOT / "video-scripts" / f"u{unit:02d}.md"
    lines = path.read_text(encoding="utf-8").split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(f"## {number} · ")), None)
    if start is None:
        sys.exit(f"{number}: no section in {path.name}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start], lines[start + 1:end]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("number", help="learning block, e.g. 0.1.2 or 3.4")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    head, body = find(a.number)
    title = head.split(" · ", 1)[1].strip()
    video = next(re.search(r"`([^`]+)`", l).group(1) for l in body if l.startswith("- **Video:**"))
    scenes, display, n = [], None, 0
    for line in body:
        if line.startswith("#### S"):
            scenes.append({"id": f"s{len(scenes) + 1:02d}", "title": line.split(" · ", 1)[1].strip(), "blocks": []})
        elif line.startswith("> "):
            n += 1
            b = {"id": f"b{n:02d}", "text": line[2:].strip()}
            if display:
                b["display"] = display
            scenes[-1]["blocks"].append(b)
            display = None
        elif line.startswith("*Screen:*") or line.startswith("["):
            m = PAUSE.search(line)
            if m and scenes and scenes[-1]["blocks"]:
                scenes[-1]["blocks"][-1]["pause_after_s"] = float(m.group(1))
            if line.startswith("*Screen:*") and display is None:
                d = re.search(r"`([^`]+)`", line)
                display = d.group(1) if d else None
    out = {"format": "algebra-video-script", "version": 1, "video": video, "title": title,
           "voice": "narrator", "source": f"video-scripts/u{int(a.number.split('.')[0]):02d}.md#{a.number}",
           "scenes": scenes}
    dest = ROOT / "videos" / video / "script.json"
    if dest.exists() and not a.force:
        sys.exit(f"{dest.relative_to(ROOT)} exists; use --force to overwrite")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{dest.relative_to(ROOT)}: {len(scenes)} scenes, {n} blocks")


if __name__ == "__main__":
    main()
