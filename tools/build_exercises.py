#!/usr/bin/env python3
"""Build a practice set: check every number with code, then generate the videos' scripts + pages
and the practice page.

    python3 tools/build_exercises.py exercises/u00-l01            # validate + generate everything
    python3 tools/build_exercises.py exercises/u00-l01 --check    # validate only (writes nothing)

Source of truth: <set>/exercises.json (see its _notes). For each exercise this script
  * evaluates the question and every step line with exact fractions and fails if any line
    does not equal the answer (so a solution can never contradict itself);
  * evaluates every wrong option, so each distractor is the real result of its named mistake;
  * writes videos/<set-id>-exNN/script.json and video.html (narration still comes from
    plan_audio.py / assemble_audio.py, see docs/audio-production.md);
  * writes <set>/index.html from tools/quiz_template.html. "num" and "expr" exercises are typed
    (checked exactly in the browser by components/answer-check; the wrong options become the
    known mistakes that get named feedback); other kinds are picked from shuffled options.
"""
import argparse
import json
import pathlib
import re
import sys
from fractions import Fraction as F

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHIP_COLOR = {"P": "blue", "E": "purple", "MD": "yellow", "AS": "green", "SUB": "ink",
              # lesson 0.2: one color per property (commutative = order, associative = grouping)
              "COMM": "blue", "ASSOC": "purple", "DIST": "yellow", "CALC": "green", "REWRITE": "ink"}
CHIP_NAME = {"P": "parentheses and groups", "E": "exponents", "MD": "multiply and divide",
             "AS": "add and subtract", "SUB": "substitute", "COMM": "commutative property",
             "ASSOC": "associative property", "DIST": "distributive property", "CALC": "calculate",
             "REWRITE": "rewrite"}
PROPERTIES = {"Commutative": "blue", "Associative": "purple", "Distributive": "yellow"}
# exact test points for expressions with variables: two expressions are treated as equal when they
# agree at every point (all exercises are low-degree polynomials, so this cannot be fooled)
POINTS = [{"x": "2", "y": "3", "z": "5", "a": "4", "b": "-3", "c": "6"},
          {"x": "-5", "y": "7", "z": "-2", "a": "-1", "b": "8", "c": "3"},
          {"x": "7/3", "y": "-1/2", "z": "4", "a": "5/2", "b": "2", "c": "-7"},
          {"x": "11", "y": "-6", "z": "1/5", "a": "3", "b": "-2/3", "c": "10"},
          {"x": "-3/4", "y": "13", "z": "-9", "a": "-6", "b": "5", "c": "1/2"},
          {"x": "17", "y": "1/3", "z": "8", "a": "7", "b": "-11", "c": "-4/5"}]


# ---------------------------------------------------------------- math checking
def to_py(expr, sub=None, point=None):
    s = expr.replace("⟨", "").replace("⟩", "")
    for k, v in (sub or {}).items():
        s = re.sub(rf"(?<![A-Za-z]){k}(?![A-Za-z])", v, s)
    if point is not None:                                    # every single letter is a variable
        s = re.sub(r"[a-z]", lambda m: f"({point[m.group(0)]})", s)
    s = s.replace("·", "×")
    s = re.sub(r"\[\[(.+?) \| (.+?)\]\]", r"((\1)/(\2))", s)
    s = s.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    s = s.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    out, opened = [], False
    for ch in s:
        if ch == "|":
            out.append(")" if opened else "abs(")
            opened = not opened
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"(\d|\))\s*(abs\(|\()", r"\1*\2", s)          # 3(−4), 2|x|, (a)(b)
    return re.sub(r"\d+", lambda m: f"F({m.group(0)})", s)


def ev(expr, sub=None, point=None):
    return eval(to_py(expr, sub, point), {"F": F, "abs": abs, "__builtins__": {}})


def same(e1, e2):
    """True when two expressions with variables agree at every test point."""
    return all(ev(e1, point=pt) == ev(e2, point=pt) for pt in POINTS)


def classify(eq):
    """Which property an identity shows, read from its shape (a sanity check of the stated answer)."""
    left, right = (x.strip() for x in eq.split("="))
    bare = lambda t: re.sub(r"[()\s×·]", "", t)            # written multiplication = implied
    toks = lambda t: sorted(re.findall(r"\d+|[a-z]|[+−]", t))
    if bare(left) == bare(right):
        return "Associative"
    if toks(left) == toks(right):
        return "Commutative"
    return "Distributive"


def spoken_last(text):
    return clean(text.split()[-1])


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n):
    n = int(n)
    if n < 0:
        return "negative " + words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return ONES[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    if n < 1000000:
        return words(n // 1000) + " thousand" + (" " + words(n % 1000) if n % 1000 else "")
    raise ValueError(n)


def money(v):
    return f"{int(v)}".replace("-", "−")


def clean(w):
    return re.sub(r"^[-']+|[-']+$", "", re.sub(r"[^a-z0-9'-]", "", w.lower()))


def check_steps(ex, problems, n_lines_extra=1):
    i = ex["id"]
    n = len(ex["chips"])
    if not (len(ex["lines"]) == n + n_lines_extra and len(ex["say"]) == n and len(ex["at"]) == n):
        problems.append(f"{i}: lines/chips/say/at lengths do not match (lines = chips + 1)")
        return False
    for c in ex["chips"]:
        if c not in CHIP_COLOR:
            problems.append(f"{i}: unknown chip {c!r}")
    for k, (text, at) in enumerate(zip(ex["say"], ex["at"])):
        m = re.fullmatch(r"([a-z0-9'-]+)(?:#(\d+))?", at)
        ws = [clean(w) for w in text.split()]
        if not m or ws.count(m.group(1)) < int(m.group(2) or 1):
            problems.append(f"{i}: step {k + 1}: word {at!r} is not in its narration")
    for k, line in enumerate(ex["lines"]):
        has_hl = "⟨" in line
        if k < n and not has_hl:
            problems.append(f"{i}: line {k} has no ⟨…⟩ to say what the next step computes")
        if k == n and has_hl:
            problems.append(f"{i}: the last line must have no ⟨…⟩")
    return True


def validate_expr(ex, problems):
    """kind "expr": the answer is an expression. Every line must equal the question for every value of
    the variables; every wrong option must differ from the answer and from the other wrong options."""
    i = ex["id"]
    try:
        if not same(ex["q"], ex["a"]):
            problems.append(f"{i}: answer {ex['a']!r} is not equal to {ex['q']!r}")
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: cannot evaluate: {e}")
        return
    if not check_steps(ex, problems):
        return
    for k, line in enumerate(ex["lines"]):
        if not same(line, ex["q"]):
            problems.append(f"{i}: line {k} {line!r} is not equal to the question")
    if ex["lines"][-1] != ex["a"]:
        problems.append(f"{i}: the last line must be the answer {ex['a']!r}")
    if len(ex["wrong"]) != 3:
        problems.append(f"{i}: needs exactly 3 wrong options")
    seen = [ex["a"]]
    for w in ex["wrong"]:
        if any(same(w["e"], o) for o in seen):
            problems.append(f"{i}: wrong option {w['e']!r} equals the answer or another option")
        seen.append(w["e"])
        for f in ("why", "say", "read"):
            if not w.get(f):
                problems.append(f"{i}: wrong option {w['e']!r} has no {f!r}")


def validate_name(ex, problems):
    """kind "name": which property does an identity show? Both sides must really be equal, the stated
    property must match the identity's shape, and every on-screen step must stay equal too."""
    i = ex["id"]
    left, right = ex["q"].split("=")
    try:
        if not same(left, right):
            problems.append(f"{i}: the two sides of {ex['q']!r} are not equal")
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: cannot evaluate: {e}")
        return
    if ex["a"] not in PROPERTIES:
        problems.append(f"{i}: answer {ex['a']!r} is not one of {list(PROPERTIES)}")
    elif classify(ex["q"]) != ex["a"]:
        problems.append(f"{i}: {ex['q']!r} looks {classify(ex['q'])}, not {ex['a']}")
    if not (len(ex["say"]) == len(ex["show"]) == len(ex["notes"])):
        problems.append(f"{i}: say/show/notes lengths do not match")
    for sh in ex["show"]:
        l2, r2 = sh.split("=")
        if not same(l2, r2):
            problems.append(f"{i}: shown identity {sh!r} is not true")
    if ex["a"].lower() not in [clean(w) for w in ex["say"][-1].split()]:
        problems.append(f"{i}: the last narration block must say {ex['a'].lower()!r}")
    others = sorted(set(PROPERTIES) - {ex["a"]})
    if sorted(w["a"] for w in ex["wrong"]) != others:
        problems.append(f"{i}: wrong options must be exactly {others}")
    for w in ex["wrong"]:
        if not (w.get("why") and w.get("say")):
            problems.append(f"{i}: wrong option {w['a']!r} needs 'why' and 'say'")


def validate(data):
    problems = []
    for ex in data["exercises"]:
        kind = ex.setdefault("kind", "num")
        if kind == "expr":
            validate_expr(ex, problems)
            continue
        if kind == "name":
            validate_name(ex, problems)
            continue
        i, sub = ex["id"], ex.get("sub")
        try:
            ans = ev(ex["q"], sub)
        except Exception as e:  # noqa: BLE001
            problems.append(f"{i}: cannot evaluate q: {e}")
            continue
        if ans.denominator != 1:
            problems.append(f"{i}: answer {ans} is not an integer")
        ex["_answer"] = int(ans)
        n = len(ex["chips"])
        if not (len(ex["lines"]) == n + 1 and len(ex["say"]) == n and len(ex["at"]) == n):
            problems.append(f"{i}: lines/chips/say/at lengths do not match (lines = chips + 1)")
            continue
        for k, line in enumerate(ex["lines"]):
            try:
                v = ev(line, sub)
            except Exception as e:  # noqa: BLE001
                problems.append(f"{i}: line {k} cannot be evaluated: {e}")
                continue
            if v != ans:
                problems.append(f"{i}: line {k} {line!r} = {v}, but the answer is {ans}")
            has_hl = "⟨" in line
            if k < n and not has_hl:
                problems.append(f"{i}: line {k} has no ⟨…⟩ to say what the next step computes")
            if k == n and has_hl:
                problems.append(f"{i}: the last line must have no ⟨…⟩")
        for c in ex["chips"]:
            if c not in CHIP_COLOR:
                problems.append(f"{i}: unknown chip {c!r}")
        for k, (text, at) in enumerate(zip(ex["say"], ex["at"])):
            m = re.fullmatch(r"([a-z0-9'-]+)(?:#(\d+))?", at)
            ws = [clean(w) for w in text.split()]
            if not m or ws.count(m.group(1)) < int(m.group(2) or 1):
                problems.append(f"{i}: step {k + 1}: word {at!r} is not in its narration")
        vals = {}
        if len(ex["wrong"]) != 3:
            problems.append(f"{i}: needs exactly 3 wrong options")
        for w in ex["wrong"]:
            try:
                v = ev(w["e"], sub)
            except Exception as e:  # noqa: BLE001
                problems.append(f"{i}: wrong option {w['e']!r} cannot be evaluated: {e}")
                continue
            if v.denominator != 1:
                problems.append(f"{i}: wrong option {w['e']!r} = {v} is not an integer")
                continue
            w["_value"] = int(v)
            if v == ans:
                problems.append(f"{i}: wrong option {w['e']!r} equals the right answer")
            if int(v) in vals:
                problems.append(f"{i}: two wrong options give {int(v)}")
            vals[int(v)] = w["e"]
    return problems


# ---------------------------------------------------------------- markup
def markup(text, hl_at=None, hl_out=None, color="yellow"):
    s = text
    tag = f'<span class="hl c-{color}" data-at="{hl_at}" data-out="{hl_out}">' if hl_at else "<span>"
    s = s.replace("⟨", tag).replace("⟩", "</span>")
    s = re.sub(r"\[\[(.+?) \| (.+?)\]\]", r'<span class="frac"><span class="top">\1</span><span class="bot">\2</span></span>', s)
    return re.sub(r"\^(\d+)", r"<sup>\1</sup>", s)


def plain(text):
    return re.sub(r"\[\[(.+?) \| (.+?)\]\]", r"(\1) over (\2)", text.replace("⟨", "").replace("⟩", ""))


def width_chars(text):
    t = text.replace("⟨", "").replace("⟩", "")
    t = re.sub(r"\[\[(.+?) \| (.+?)\]\]", lambda m: max(m.group(1), m.group(2), key=len), t)
    return len(re.sub(r"\^", "", t))


def pick_size(lines, sizes, max_h, max_w=1600):
    frac = any("[[" in x for x in lines)
    wide = max(width_chars(x) for x in lines)
    for fs, name in sizes:
        rows = len(lines) * (fs * 1.1 * (2 if frac else 1) + 10)
        if rows <= max_h and wide * 0.66 * fs + 40 <= max_w:
            return name
    return sizes[-1][1]


# ---------------------------------------------------------------- videos
def video_files(data, ex, num, set_id):
    if ex["kind"] == "name":
        return name_video(data, ex, num, set_id)
    vid = f"{set_id}-{ex['id']}"
    n, lv = len(ex["chips"]), data["levels"][str(ex["level"])]
    wrong = ex["wrong"]
    if ex["kind"] == "num":
        ans = ex["_answer"]
        ans_say, ans_html, ans_plain = words(ans), money(ans), money(ans)
        trap_say = [words(w["_value"]) for w in wrong]
        trap_html = [money(w["_value"]) for w in wrong]
        trap_size = "sm"
    else:
        ans_say, ans_html, ans_plain = ex["a_read"], markup(ex["a"]), plain(ex["a"])
        trap_say = [w["read"] for w in wrong]
        trap_html = [markup(w["e"]) for w in wrong]
        trap_size = "xs"
    last_word = spoken_last(ans_say)
    trap_text = ("Watch out for these traps. "
                 + " ".join(f"If you {w['say']}, you get {ts}." for w, ts in zip(wrong[:2], trap_say)))

    blocks_s2 = []
    for k in range(n):
        blocks_s2.append({"id": f"b{k + 2:02d}", "text": ex["say"][k], "display": plain(ex["lines"][k + 1]),
                          "cue": f"step-{k + 1}"})
    b_ans, b_trap = f"b{n + 2:02d}", f"b{n + 3:02d}"
    script = {
        "format": "algebra-video-script", "version": 1, "video": vid,
        "title": f"Exercise {num}", "voice": "narrator",
        "scenes": [
            {"id": "s01", "title": "The problem", "blocks": [
                {"id": "b01", "text": "Let's solve this one step by step. " + ex["read"], "display": plain(ex["q"]),
                 "cue": "show-problem", "pause_after_s": 1.2}]},
            {"id": "s02", "title": "Step by step", "blocks": blocks_s2},
            {"id": "s03", "title": "The answer", "blocks": [
                {"id": b_ans, "text": f"So the answer is {ans_say}.", "display": f"= {ans_plain}", "cue": "answer"},
                {"id": b_trap, "text": trap_text, "cue": "traps"}]},
        ],
    }

    # --- page
    prob_size = pick_size([ex["q"]], [(132, ""), (96, "md"), (72, "sm"), (56, "xs")], 400, 1700)
    row_size = pick_size(ex["lines"], [(96, "md"), (72, "sm"), (56, "xs")], 730)
    rows = []
    for j, line in enumerate(ex["lines"]):
        if j < n:
            color = CHIP_COLOR[ex["chips"][j]]
            blk = f"b{j + 2:02d}"
            html = markup(line, hl_at=blk, hl_out=f"{blk}.end", color=color)
        else:
            html = markup(line)
        if j == 0:
            rows.append('      <span></span>')
            rows.append(f'      <div class="math {row_size} fade" data-at="b02-0.7">{html}</div>')
        else:
            blk = f"b{j + 1:02d}"
            at = f"{blk}@{ex['at'][j - 1]}"
            chip = ex["chips"][j - 1]
            rows.append(f'      <span class="chip c-{CHIP_COLOR[chip]} pop" data-at="{at}">{chip}</span>')
            cls = "pop green" if j == n else "fade"
            rows.append(f'      <div class="math {row_size} {cls}" data-at="{at}">{html}</div>')
    cards = []
    for k, w in enumerate(wrong):
        cards.append(
            f'        <div class="card trap fade c-red" data-at="{b_trap}+{0.15 + 0.25 * k:.2f}">'
            f'<div class="math {trap_size} red"><span class="strike" data-at="{b_trap}+{0.9 + 0.25 * k:.2f}" data-dur="0.5">{trap_html[k]}</span></div>'
            f'<div class="why">{w["why"]}</div></div>')
    prompt = f'\n    <div class="say fade muted" data-at="b01+0.4" style="font-size: 40px">{ex["prompt"]}</div>' if ex.get("prompt") else ""
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exercise {num} — step by step</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap">
<link rel="stylesheet" href="../_engine/player.css">
<style>
  .c-ink {{ --c: var(--ink); }}
  .frac {{ display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; margin: 0 0.12em; }}
  .frac .top {{ padding: 0.04em 0.25em 0.2em; border-bottom: 0.07em solid currentColor; }}
  .frac .bot {{ padding: 0.2em 0.25em 0.04em; }}
  /* highlight boxes reach past the text but take no room, so lines never shift when they appear */
  .hl {{ padding: 0 10px; margin: 0 -10px; }}
  sup {{ font-size: 0.6em; vertical-align: 0.55em; line-height: 0; }}
  .deriv {{ display: grid; grid-template-columns: auto auto; align-items: center; justify-content: center; gap: {"30px" if any("[[" in x for x in ex["lines"]) else "10px"} 28px; }}
  .deriv .chip {{ justify-self: end; }}
  .deriv:has(.md) .chip {{ min-width: 84px; height: 72px; font-size: 38px; }}
  .deriv:has(.sm) .chip {{ min-width: 70px; height: 60px; font-size: 32px; border-radius: 18px; }}
  .deriv:has(.xs) .chip {{ min-width: 58px; height: 48px; font-size: 26px; border-radius: 14px; }}
  .trap {{ width: 520px; padding: 28px 34px; gap: 14px; }}
  .trap .why {{ font: 500 30px/1.3 Inter, sans-serif; color: var(--muted); text-align: center; }}
</style>
</head>
<body>
<div id="stage">
  <div class="header"><span class="unit">Unit 0 · Practice {data["unit"]}</span><span class="title">Exercise {num}</span></div>

  <!-- s01: the problem -->
  <section class="scene" data-scene="s01">
    <div class="label yellow fade" data-at="b01">Exercise {num} · {lv}</div>
    <div class="math {prob_size} pop" data-at="b01">{markup(ex["q"])}</div>{prompt}
  </section>

  <!-- s02: step by step -->
  <section class="scene" data-scene="s02">
    <div class="deriv">
{chr(10).join(rows)}
    </div>
  </section>

  <!-- s03: the answer and the traps -->
  <section class="scene" data-scene="s03">
    <div class="math sm fade" data-at="{b_ans}-0.5">{markup(ex["q"])} <span class="green pop" data-at="{b_ans}@{last_word}">= {ans_html}</span></div>
    <div class="label red fade" data-at="{b_trap}">Common traps</div>
    <div class="row" style="align-items: stretch; gap: 36px">
{chr(10).join(cards)}
    </div>
    <div class="label muted fade" data-at="{b_trap}+1.5" style="font-size: 22px; font-weight: 500">This video uses an AI-generated voice.</div>
  </section>

  <div class="caption"></div>
  <div class="progress"></div>
  <div id="seek" title="Jump to a moment"></div>
  <button id="play" type="button" aria-label="Play"><span class="play-btn">▶</span><span class="play-label">Watch the solution</span></button>
</div>
<script src="../_engine/player.js"></script>
</body>
</html>
"""
    return vid, script, html

def page(title, header_unit, num, style, scenes, play_label="Watch the solution"):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap">
<link rel="stylesheet" href="../_engine/player.css">
<style>{style}</style>
</head>
<body>
<div id="stage">
  <div class="header"><span class="unit">{header_unit}</span><span class="title">Exercise {num}</span></div>
{scenes}
  <div class="caption"></div>
  <div class="progress"></div>
  <div id="seek" title="Jump to a moment"></div>
  <button id="play" type="button" aria-label="Play"><span class="play-btn">▶</span><span class="play-label">{play_label}</span></button>
</div>
<script src="../_engine/player.js"></script>
</body>
</html>
"""


def name_video(data, ex, num, set_id):
    """Video for "which property is this?": the identity, what changed (highlighted), the name, the traps."""
    vid = f"{set_id}-{ex['id']}"
    lv = data["levels"][str(ex["level"])]
    color = PROPERTIES[ex["a"]]
    nb = len(ex["say"])
    b_ans, b_trap = f"b{nb + 2:02d}", f"b{nb + 3:02d}"
    wrong = ex["wrong"]
    trap_text = ("Watch out for these traps. "
                 + " ".join(f"It isn't the {w['a'].lower()} property, because {w['say']}." for w in wrong))
    script = {
        "format": "algebra-video-script", "version": 1, "video": vid,
        "title": f"Exercise {num}", "voice": "narrator",
        "scenes": [
            {"id": "s01", "title": "The problem", "blocks": [
                {"id": "b01", "text": "Let's look at this one. " + ex["read"] + " Which property does it show?",
                 "display": plain(ex["q"]), "cue": "show-problem", "pause_after_s": 1.5}]},
            {"id": "s02", "title": "What changed", "blocks": [
                {"id": f"b{k + 2:02d}", "text": ex["say"][k], "display": plain(ex["show"][k]), "cue": f"step-{k + 1}"}
                for k in range(nb)]},
            {"id": "s03", "title": "The answer", "blocks": [
                {"id": b_ans, "text": f"So the answer is the {ex['a'].lower()} property.", "display": ex["a"],
                 "cue": "answer"},
                {"id": b_trap, "text": trap_text, "cue": "traps"}]},
        ],
    }
    size = pick_size(ex["show"] + [ex["q"]], [(132, ""), (96, "md"), (72, "sm"), (56, "xs")], 400, 1700)
    shows, notes = [], []
    for k in range(nb):
        blk = f"b{k + 2:02d}"
        out = f' data-out="b{k + 3:02d}"' if k < nb - 1 else ""
        shows.append(f'      <div class="math {size} fade" data-at="{blk}-0.3"{out}>{markup(ex["show"][k], hl_at=blk, hl_out="", color=color).replace(' data-out=""', "")}</div>')
        notes.append(f'      <div class="say fade muted" data-at="{blk}+0.2"{out} style="font-size: 40px">{ex["notes"][k]}</div>')
    last = f"b{nb + 1:02d}"
    cards = []
    for k, w in enumerate(wrong):
        cards.append(
            f'        <div class="card trap fade c-red" data-at="{b_trap}+{0.15 + 0.25 * k:.2f}">'
            f'<div class="name red"><span class="strike" data-at="{b_trap}+{0.9 + 0.25 * k:.2f}" data-dur="0.5">{w["a"]}</span></div>'
            f'<div class="why">{w["why"]}</div></div>')
    style = """
  .hl { padding: 0 10px; margin: 0 -10px; }
  sup { font-size: 0.6em; vertical-align: 0.55em; line-height: 0; }
  .prop { font: 700 52px Poppins, sans-serif; padding: 0 36px; height: 96px; border-radius: 26px; }
  .trap { width: 640px; padding: 28px 34px; gap: 14px; }
  .trap .name { font: 700 44px Poppins, sans-serif; }
  .trap .why { font: 500 30px/1.3 Inter, sans-serif; color: var(--muted); text-align: center; }
"""
    scenes = f"""
  <!-- s01: the problem -->
  <section class="scene" data-scene="s01">
    <div class="label yellow fade" data-at="b01">Exercise {num} · {lv}</div>
    <div class="math {size} pop" data-at="b01">{markup(ex["q"])}</div>
    <div class="say fade muted" data-at="b01@which" style="font-size: 40px">Which property is shown?</div>
  </section>

  <!-- s02: what changed -->
  <section class="scene" data-scene="s02">
    <div class="stack">
{chr(10).join(shows)}
    </div>
    <div class="stack">
{chr(10).join(notes)}
    </div>
    <span class="chip prop c-{color} pop" data-at="{last}@{ex["a"].lower()}">{ex["a"]}</span>
  </section>

  <!-- s03: the answer and the traps -->
  <section class="scene" data-scene="s03">
    <div class="math sm fade" data-at="{b_ans}-0.5">{markup(ex["q"])}</div>
    <span class="chip prop c-{color} pop" data-at="{b_ans}@{ex["a"].lower()}">✓ {ex["a"]}</span>
    <div class="label red fade" data-at="{b_trap}">Common traps</div>
    <div class="row" style="align-items: stretch; gap: 36px">
{chr(10).join(cards)}
    </div>
    <div class="label muted fade" data-at="{b_trap}+1.5" style="font-size: 22px; font-weight: 500">This video uses an AI-generated voice.</div>
  </section>
"""
    unit_label = f"Unit {data['unit'].split('.')[0]} · Practice {data['unit']}"
    return vid, script, page(f"Exercise {num} — step by step", unit_label, num, style, scenes)


# ---------------------------------------------------------------- quiz page
def plain_math(expr):
    """An expression in the plain form components/answer-check reads: * / - ( ) ^, implied products."""
    s = expr.replace("⟨", "").replace("⟩", "")
    s = re.sub(r"\[\[(.+?) \| (.+?)\]\]", r"((\1)/(\2))", s)
    s = s.replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-")
    return s.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")


def quiz_data(data):
    out = []
    for k, ex in enumerate(data["exercises"], 1):
        base = {"id": ex["id"], "n": k, "level": ex["level"], "prompt": ex.get("prompt", ""),
                "q": markup(ex["q"]), "aria": plain(ex["q"]).replace("^", " to the power of ")}
        # "find the value" and "expand": the student types the answer (docs/course-design.md)
        if ex["kind"] == "num":
            out.append({**base, "input": "num", "answer": str(ex["_answer"]), "aHtml": money(ex["_answer"]),
                        "mistakes": [{"v": str(w["_value"]), "why": w["why"]} for w in ex["wrong"]]})
            continue
        if ex["kind"] == "expr":
            out.append({**base, "input": "expr", "answer": plain_math(ex["a"]), "aHtml": markup(ex["a"]),
                        "mistakes": [{"e": plain_math(w["e"]), "why": w["why"]} for w in ex["wrong"]]})
            continue
        if ex["kind"] == "num":
            opts = [{"v": money(ex["_answer"]), "ok": True, "why": ""}]
            opts += [{"v": money(w["_value"]), "ok": False, "why": w["why"]} for w in ex["wrong"]]
        elif ex["kind"] == "expr":
            opts = [{"v": markup(ex["a"]), "ok": True, "why": ""}]
            opts += [{"v": markup(w["e"]), "ok": False, "why": w["why"]} for w in ex["wrong"]]
        else:
            opts = [{"v": ex["a"], "ok": True, "why": ""}]
            opts += [{"v": w["a"], "ok": False, "why": w["why"]} for w in ex["wrong"]]
        out.append({**base, "options": opts})
    return out


def build(set_dir, check_only):
    data = json.loads((set_dir / "exercises.json").read_text(encoding="utf-8"))
    problems = validate(data)
    if problems:
        print("\n".join("✗ " + p for p in problems))
        sys.exit(f"{len(problems)} problem(s) found")
    print(f"✓ {len(data['exercises'])} exercises: every answer, every step line and every wrong option checked")
    for ex in data["exercises"]:
        if ex["kind"] == "num":
            ans, wr = ex["_answer"], [w["_value"] for w in ex["wrong"]]
        elif ex["kind"] == "expr":
            ans, wr = ex["a"], [w["e"] for w in ex["wrong"]]
        else:
            ans, wr = ex["a"], [w["a"] for w in ex["wrong"]]
        print(f"  {ex['id']}  {ex['q']:<34} → {str(ans):<16} wrong: " + ", ".join(str(w) for w in wr))
    if check_only:
        return
    set_id = set_dir.name                                    # e.g. u00-l01
    for num, ex in enumerate(data["exercises"], 1):
        vid, script, html = video_files(data, ex, num, set_id)
        vdir = ROOT / "videos" / vid
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (vdir / "video.html").write_text(html, encoding="utf-8")
    tpl = (ROOT / "tools" / "quiz_template.html").read_text(encoding="utf-8")
    payload = {"unit": data["unit"], "title": data["title"], "setId": set_id, "levels": data["levels"],
               "exercises": quiz_data(data)}
    out = tpl.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    out = out.replace("__TITLE__", f"Practice {data['unit']} · {data['title']}")
    out = out.replace("__H1__", data.get("h1", 'Order of operations, <span class="y">with signs</span>'))
    (set_dir / "index.html").write_text(out, encoding="utf-8")
    print(f"✓ wrote {len(data['exercises'])} videos under videos/{set_id}-ex*/ and {set_dir / 'index.html'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("set_dir", type=pathlib.Path)
    ap.add_argument("--check", action="store_true", help="validate only")
    a = ap.parse_args()
    build(a.set_dir.resolve(), a.check)
