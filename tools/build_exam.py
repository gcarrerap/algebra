#!/usr/bin/env python3
"""Build a unit exam from its question bank.

  python3 tools/build_exam.py exams/u00 --check   # validate the bank and the exam rules only
  python3 tools/build_exam.py exams/u00           # validate + write index.html and the Boss solution videos

`exams/<unit>/bank.json` is the source of truth. It is an exercise set (same kinds, same checks as
`tools/build_exercises.py`, which does all the validating) with a few extra fields:

  unit, title, pass (0.9), draw {total, boss_per_block}, video_unit, video_title,
  blocks [{id, name}], and on every exercise: block (a block id) and block_name.

Rules checked here (docs/course-design.md, "Unit exam"):
  - 60-80 questions in the bank; every block has exactly 2 Boss-level (4) questions;
  - the exam is 10-20 questions, one Boss per block plus questions of levels 1-3.

Boss questions get a narrated solution video (videos/<unit>-exam-exNN/). Written step-by-step
solutions for every question are generated into the page from `lines` and `say`; a Boss question's
video is linked in the review only once its narration exists (timeline.json).
"""
import argparse
import copy
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_exercises as B  # noqa: E402

ROOT = B.ROOT


def check_rules(data):
    problems = []
    ex = data["exercises"]
    if not 60 <= len(ex) <= 80:
        problems.append(f"the bank has {len(ex)} questions; it must have 60-80")
    blocks = [b["id"] for b in data["blocks"]]
    for b in blocks:
        boss = [e["id"] for e in ex if e.get("block") == b and e["level"] == 4]
        if len(boss) != 2:
            problems.append(f"block {b} has {len(boss)} Boss-level questions; it must have exactly 2")
        for lv in (1, 2, 3):
            if not any(e.get("block") == b and e["level"] == lv for e in ex):
                problems.append(f"block {b} has no level-{lv} question")
    for e in ex:
        if e.get("block") not in blocks:
            problems.append(f"{e['id']}: block {e.get('block')!r} is not in `blocks`")
    d = data["draw"]
    if not 10 <= d["total"] <= 20:
        problems.append("draw.total must be 10-20")
    if len(blocks) > d["total"]:
        problems.append("more blocks than questions in the exam")
    return problems


def solution(ex):
    """The written step-by-step solution shown in the review (docs/course-design.md)."""
    kind = ex.get("kind", "num")
    hl = lambda t: B.markup(t, hl_at="1")
    if kind == "multi":
        return {"say": ex["say_answer"],
                "items": [{"t": B.choice_text(o["t"]), "ok": bool(o["ok"]), "note": o["say"] if o["ok"] else o["why"]}
                          for o in ex["options"]]}
    if kind == "match":
        return {"say": ex["say_answer"],
                "items": [{"t": B.choice_text(p["l"]) + "  →  " + B.choice_text(p["r"]), "ok": True, "note": p["say"]}
                          for p in ex["pairs"]]}
    if kind == "name":
        return {"steps": [{"line": hl(l), "say": s} for l, s in zip(ex["show"], ex["say"])]}
    steps = [{"line": hl(ex["lines"][k]), "say": ex["say"][k]} for k in range(len(ex["say"]))]
    steps.append({"line": B.markup(ex["lines"][-1]), "say": ""})
    return {"steps": steps}


def build(exam_dir, check_only):
    data = json.loads((exam_dir / "bank.json").read_text(encoding="utf-8"))
    problems = check_rules(data) + B.validate(data)
    if problems:
        print("\n".join("✗ " + p for p in problems))
        sys.exit(f"{len(problems)} problem(s) found")
    boss = [e for e in data["exercises"] if e["level"] == 4]
    print(f"✓ {len(data['exercises'])} questions ({len(boss)} Boss) in {len(data['blocks'])} blocks: "
          "every answer, every step line and every wrong option checked")
    if check_only:
        return
    set_id = f"u{int(data['unit']):02d}-exam"
    questions = []
    pending = []
    for num, ex in enumerate(data["exercises"], 1):
        item = B.quiz_data({**data, "exercises": [ex]})[0]
        item.pop("n", None)
        item["block"], item["blockName"] = ex["block"], ex["block_name"]
        item["solution"] = solution(ex)
        if ex["level"] == 4:
            vid, script, html = B.video_files(data, ex, num, set_id)
            vdir = ROOT / "videos" / vid
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (vdir / "video.html").write_text(html, encoding="utf-8")
            if (vdir / "timeline.json").exists() and (vdir / "narration.mp3").exists():
                item["video"] = vid
            else:
                pending.append(vid)
        questions.append(item)
    payload = {"unit": data["unit"], "title": data["title"], "setId": set_id, "levels": data["levels"],
               "pass": data.get("pass", 0.9), "draw": data["draw"], "blocks": data["blocks"], "questions": questions}
    base = (ROOT / "tools" / "quiz_template.html").read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", base, re.S).group(1)
    tpl = (ROOT / "tools" / "exam_template.html").read_text(encoding="utf-8")
    out = tpl.replace("__BASE_STYLE__", style)
    out = out.replace("__TITLE__", f"Exam · Unit {data['unit']} · {data['title'].replace('Unit ' + data['unit'] + ' ', '')}")
    out = out.replace("__H1__", data.get("h1", "Unit exam"))
    out = out.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    (exam_dir / "index.html").write_text(out, encoding="utf-8")
    print(f"✓ wrote {exam_dir / 'index.html'} and {len(boss)} Boss video pages under videos/{set_id}-ex*/")
    if pending:
        print(f"  ! {len(pending)} Boss videos have no narration yet (written solutions are shown instead): " + ", ".join(pending))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exam_dir", type=pathlib.Path)
    ap.add_argument("--check", action="store_true", help="validate only")
    a = ap.parse_args()
    build(a.exam_dir.resolve(), a.check)
