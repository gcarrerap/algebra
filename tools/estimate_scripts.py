#!/usr/bin/env python3
"""Estimate the length of every video from its written script (video-scripts/*.md).

    python3 tools/estimate_scripts.py            # check, print the table, update the files
    python3 tools/estimate_scripts.py --check    # check only; exit 1 on a broken rule

Format of a script (see docs/video-scripts.md):

    ## 3.1a · Rate of change                    one section per video
    - **Video:** `u03-l01-rate-of-change`
    - **Estimated length:** …                    rewritten by this tool
    #### S1 · Title                              one heading per scene
    > Spoken text, written as it is read.        one line = one voice block
    [REFLECT 10s] *Screen:* …                    a pause (THINK, REFLECT or TRY IT)

The estimate follows the audio pipeline (docs/audio-production.md §7): speech at the
narrator's measured pace, 0.6 s between blocks, 1.4 s between scenes, 0.8 s lead-in, and
every pause at its full length. Measured on the three produced lesson videos it lands
within 3% of the real narration.
"""
import pathlib
import re
import sys

WPM = 150                      # narrator "Memo - english" at speed 0.95: 147–161 words/min
BLOCK_GAP, SCENE_GAP, LEAD = 0.6, 1.4, 0.8
TARGET = (3 * 60, 7 * 60)      # aim; course-design allows 3–6 min of content, 10 min at most
LIMIT = 10 * 60
MIN_REFLECT, MIN_TRY = 2, 1    # every lesson video has at least these pauses

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "video-scripts"
PAUSE = re.compile(r"\[(THINK|REFLECT|TRY IT) (\d+(?:\.\d+)?)s\]")
HEAD = re.compile(r"^## (\S+) · (.+)$")
VIDEO = re.compile(r"^- \*\*Video:\*\* `([^`]+)`")
STATUS = re.compile(r"^- \*\*Status:\*\* (.+)$")
EST = re.compile(r"^- \*\*Estimated length:\*\*.*$")


def mmss(s):
    s = round(s)
    return f"{s // 60}:{s % 60:02d}"


def sections(lines):
    cur = None
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if m:
            if cur:
                yield cur
            cur = {"num": m.group(1), "title": m.group(2), "start": i, "lines": []}
        elif cur is not None:
            cur["lines"].append((i, line))
    if cur:
        yield cur


def measure(sec):
    words = blocks = scenes = 0
    pauses = {"THINK": 0.0, "REFLECT": 0.0, "TRY IT": 0.0}
    count = {"THINK": 0, "REFLECT": 0, "TRY IT": 0}
    video = status = None
    disclosure = False
    for _, line in sec["lines"]:
        if line.startswith("> "):
            text = line[2:]
            words += len(text.split())
            blocks += 1
            disclosure |= "AI-generated voice" in text
        elif line.startswith("#### S"):
            scenes += 1
        for kind, secs in PAUSE.findall(line):
            pauses[kind] += float(secs)
            count[kind] += 1
        m = VIDEO.match(line)
        if m:
            video = m.group(1)
        m = STATUS.match(line)
        if m:
            status = m.group(1)
    speech = words * 60 / WPM
    pause = sum(pauses.values())
    total = LEAD + speech + BLOCK_GAP * blocks + SCENE_GAP * max(scenes - 1, 0) + pause
    return dict(video=video, status=status, words=words, blocks=blocks, scenes=scenes,
                speech=speech, pause=pause, count=count, total=total, disclosure=disclosure)


def main():
    check_only = "--check" in sys.argv
    rows, problems = [], []
    for path in sorted(DIR.glob("u[0-9][0-9].md")):
        lines = path.read_text(encoding="utf-8").split("\n")
        for sec in sections(lines):
            m = measure(sec)
            where = f"{path.name} {sec['num']}"
            if not m["video"]:
                problems.append(f"{where}: no **Video:** line")
            if m["total"] > LIMIT:
                problems.append(f"{where}: {mmss(m['total'])} is over 10 minutes; split it")
            if m["count"]["REFLECT"] < MIN_REFLECT or m["count"]["TRY IT"] < MIN_TRY:
                problems.append(f"{where}: needs {MIN_REFLECT} REFLECT and {MIN_TRY} TRY IT pauses")
            if not m["disclosure"]:
                problems.append(f"{where}: missing the AI-voice disclosure line")
            note = ""
            if m["total"] > TARGET[1]:
                note = " · long: consider splitting"
            elif m["total"] < TARGET[0]:
                note = " · short"
            est = (f"- **Estimated length:** {mmss(m['total'])} "
                   f"(speech {mmss(m['speech'])} · pauses {round(m['pause'])} s · "
                   f"{m['words']} words · {m['scenes']} scenes){note}")
            for i, line in sec["lines"]:
                if EST.match(line):
                    lines[i] = est
                    break
            else:
                problems.append(f"{where}: no **Estimated length:** line")
            rows.append((path.stem, sec["num"], sec["title"], m))
        if not check_only:
            path.write_text("\n".join(lines), encoding="utf-8")

    table = ["| # | Video | Folder | Status | Length | Pauses |", "|---|---|---|---|---|---|"]
    total = 0
    for unit, num, title, m in rows:
        total += m["total"]
        table.append(f"| {num} | [{title}]({unit}.md) | `{m['video']}` | {m['status'] or ''} | "
                     f"{mmss(m['total'])} | {round(m['pause'])} s |")
    table.append(f"| | **{len(rows)} videos** | | | **{mmss(total)}** "
                 f"(≈ {total / 3600:.1f} h) | |")
    if not check_only:
        readme = DIR / "README.md"
        text = readme.read_text(encoding="utf-8")
        a, b = "<!-- estimates:start -->", "<!-- estimates:end -->"
        if a in text and b in text:
            head, rest = text.split(a, 1)
            _, tail = rest.split(b, 1)
            readme.write_text(head + a + "\n" + "\n".join(table) + "\n" + b + tail, encoding="utf-8")
    print("\n".join(table))
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
