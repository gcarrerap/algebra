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
              "COMM": "blue", "ASSOC": "purple", "DIST": "yellow", "CALC": "green", "REWRITE": "ink",
              # lesson 0.3: the parts of an expression
              "TERM": "blue", "FACTOR": "purple", "COEF": "yellow", "CONST": "green",
              # lesson 0.4: collecting like terms (DIST stays yellow, as in 0.2)
              "COMBINE": "green",
              # lesson 0.5: words into algebra
              "VAR": "blue", "WORDS": "yellow", "ORDER": "purple", "GROUP": "green", "TEST": "ink",
              # lesson 1.3: the properties of equality (DIST yellow and COMBINE green as before) and the
              # verdict on each step of a student's work
              "ADD": "blue", "SUBTRACT": "purple", "MULTIPLY": "yellow", "DIVIDE": "green",
              "OK": "green", "ERROR": "red", "CARRY": "ink"}
CHIP_NAME = {"P": "parentheses and groups", "E": "exponents", "MD": "multiply and divide",
             "AS": "add and subtract", "SUB": "substitute", "COMM": "commutative property",
             "ASSOC": "associative property", "DIST": "distributive property", "CALC": "calculate",
             "REWRITE": "rewrite", "TERM": "terms", "FACTOR": "factors", "COEF": "coefficient",
             "CONST": "constant", "COMBINE": "combine like terms", "VAR": "define the variable",
             "WORDS": "match the words", "ORDER": "order", "GROUP": "grouping", "TEST": "test it",
             "ADD": "addition property", "SUBTRACT": "subtraction property", "MULTIPLY": "multiplication property",
             "DIVIDE": "division property", "OK": "step is allowed", "ERROR": "first wrong step",
             "CARRY": "carries the error"}
# lesson 0.5: the words each operation goes by (check "operation" on multi / match)
OPERATION_WORDS = {"addition": ["sum", "more than", "increased by", "plus", "total of", "added to"],
                   "subtraction": ["difference", "less than", "decreased by", "minus", "subtract", "fewer than", "take away"],
                   "multiplication": ["product", "times", "twice", "triple", "double"],
                   "division": ["quotient", "per", "divided by", "split", "shared equally"]}
# lesson 1.1: a chip that is an operation written with its number ("−7", "÷3", "×6") takes the
# color of the operation: + blue, − purple, × yellow, ÷ green. It means "do this to both sides".
OP_COLOR = {"+": "blue", "−": "purple", "×": "yellow", "÷": "green"}


def chip_color(c):
    return CHIP_COLOR.get(c) or OP_COLOR.get(c[:1])


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


def equation_var(eq):
    """The one letter of an equation like "3x − 4 = 11"."""
    letters = sorted(set(re.findall(r"[a-z]", eq.replace("⟨", "").replace("⟩", ""))))
    if len(letters) != 1:
        raise ValueError(f"{eq!r} must have exactly one variable, found {letters}")
    return letters[0]


def solve_one_var(eq):
    """Solve a linear equation "L = R" exactly: returns (variable, value). The difference L − R is
    evaluated at three values of the variable, so an equation that is not linear (or is true for
    every value, or never) is refused."""
    var = equation_var(eq)
    left, right = eq.split("=")
    f = lambda v: ev(left, {var: f"({v})"}) - ev(right, {var: f"({v})"})
    a, b = f(1) - f(0), f(0)
    if f(2) != 2 * a + b or f(5) != 5 * a + b:
        raise ValueError(f"{eq!r} is not linear")
    if a == 0:
        raise ValueError(f"{eq!r} has no single solution")
    return var, -b / a


def substitute_text(eq, var, value):
    """The equation with the variable replaced by value, for the check line of a solution video:
    2x + 3 = 11 with 4 → 2(4) + 3 = 11. Negatives and numbers next to a number or ")" get parentheses."""
    text = eq.replace("⟨", "").replace("⟩", "")
    v = str(value).replace("-", "−")

    def one(m):
        before = text[:m.start()].rstrip(" ")[-1:]
        return f"({v})" if (value < 0 or before.isdigit() or before == ")") else v
    return re.sub(rf"(?<![A-Za-z]){var}(?![A-Za-z])", one, text)


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
        if chip_color(c) is None:
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


def validate_solve(ex, problems):
    """kind "solve" (lesson 1.1): the learner types the value of the variable. The question is an
    equation with one integer solution, computed here. Every line of the work must be an equation with
    that same solution, the last one must read "<var> = <solution>", and every wrong value must be a
    number that does NOT solve the equation (substituting it is how the page names the mistake)."""
    i = ex["id"]
    try:
        var, sol = solve_one_var(ex["q"])
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: cannot solve: {e}")
        return
    if sol.denominator != 1:
        problems.append(f"{i}: the solution {sol} is not an integer")
        return
    ex["_answer"], ex["_var"] = int(sol), var
    if not check_steps(ex, problems):
        return
    for k, line in enumerate(ex["lines"]):
        try:
            v2, s2 = solve_one_var(line)
            if v2 != var or s2 != sol:
                problems.append(f"{i}: line {k} {line!r} has solution {s2}, not {sol}")
        except Exception as e:  # noqa: BLE001
            problems.append(f"{i}: line {k} cannot be solved: {e}")
    want = f"{var} = {ex['_answer']}".replace("-", "−")
    if ex["lines"][-1] != want:
        problems.append(f"{i}: the last line must be {want!r}")
    for f in ("prompt", "read"):
        if not ex.get(f):
            problems.append(f"{i}: needs {f!r}")
    if len(ex["wrong"]) != 3:
        problems.append(f"{i}: needs exactly 3 wrong options")
    seen = {ex["_answer"]}
    for w in ex["wrong"]:
        try:
            v = ev(w["e"])
        except Exception as e:  # noqa: BLE001
            problems.append(f"{i}: wrong option {w['e']!r} cannot be evaluated: {e}")
            continue
        if v.denominator != 1:
            problems.append(f"{i}: wrong option {w['e']!r} = {v} is not an integer")
            continue
        w["_value"] = int(v)
        if int(v) in seen:
            problems.append(f"{i}: wrong option {w['e']!r} = {int(v)} equals the answer or another option")
        seen.add(int(v))
        left, right = ex["q"].split("=")
        if ev(left, {var: f"({v})"}) == ev(right, {var: f"({v})"}):
            problems.append(f"{i}: wrong option {w['e']!r} actually solves the equation")
        for f in ("why", "say"):
            if not w.get(f):
                problems.append(f"{i}: wrong option {w['e']!r} has no {f!r}")


def validate_words(ex, problems):
    """kind "words" (lesson 0.5): the learner types an expression for a sentence. The sentence's meaning is
    pinned by a test: with "var" = "value", the words say the result is "means" (an arithmetic
    expression written from the sentence). The answer must give that result, every wrong option a
    different one, and every on-screen line is only text, so lines are not compared."""
    i = ex["id"]
    for f in ("prompt", "read", "a", "a_read", "test"):
        if not ex.get(f):
            problems.append(f"{i}: needs {f!r}")
    if not ex.get("test"):
        return
    t = ex["test"]
    try:
        ex["_test_value"] = ev(t["means"])
        got = ev(ex["a"], {t["var"]: f"({t['value']})"})
        if got != ex["_test_value"]:
            problems.append(f"{i}: at {t['var']} = {t['value']} the answer gives {got}, but the words give {ex['_test_value']}")
        if ex["_test_value"].denominator != 1:
            problems.append(f"{i}: the test result {ex['_test_value']} is not an integer")
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: cannot evaluate: {e}")
        return
    if not check_steps(ex, problems):
        return
    if ex["lines"][-1] != ex["a"]:
        problems.append(f"{i}: the last line must be the answer {ex['a']!r}")
    if len(ex["wrong"]) != 3:
        problems.append(f"{i}: needs exactly 3 wrong options")
    seen = [ex["a"]]
    for w in ex["wrong"]:
        if any(same(w["e"], o) for o in seen):
            problems.append(f"{i}: wrong option {w['e']!r} equals the answer or another option")
        seen.append(w["e"])
        try:
            if ev(w["e"], {t["var"]: f"({t['value']})"}) == ex["_test_value"]:
                problems.append(f"{i}: wrong option {w['e']!r} passes the test at {t['var']} = {t['value']}")
        except Exception as e:  # noqa: BLE001
            problems.append(f"{i}: wrong option {w['e']!r} cannot be evaluated: {e}")
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


# ---------------------------------------------------------------- parts of an expression (topic 0.3)
def _norm(s):
    """An expression as plain text without spaces: - * ^ ( ), no ⟨⟩, no unicode minus or powers."""
    s = s.replace("⟨", "").replace("⟩", "").replace("−", "-").replace("·", "*").replace("×", "*")
    s = s.replace("²", "^2").replace("³", "^3")
    return re.sub(r"\s+", "", s)


def split_terms(expr):
    """The terms of an expression: pieces separated by + and − outside parentheses; the sign stays with
    the term that follows it (a leading minus belongs to the first term)."""
    s, terms, depth, cur = _norm(expr), [], 0, ""
    for k, ch in enumerate(s):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch in "+-" and depth == 0 and k > 0 and s[k - 1] not in "*^(+-":
            terms.append(cur)
            cur = ch
        else:
            cur += ch
    terms.append(cur)
    return terms


GROUP = r"\([^()]*\)|\[[^\[\]]*\]"


def term_parts(t):
    sign = -1 if t.startswith("-") else 1
    body = t.lstrip("+-")
    m = re.match(r"\d+", body)
    num = int(m.group(0)) if m else None
    return {"text": t.lstrip("+"), "sign": sign, "body": body, "num": num,
            "var": bool(re.search(r"[a-z]", body)), "group": bool(re.search(GROUP, body)),
            "coef": sign * (num if num is not None else 1)}


def all_parts(expr):
    return [term_parts(t) for t in split_terms(expr)]


def find_term(parts, target, what):
    want = _norm(target).lstrip("+")
    for p in parts:
        if p["text"] == want:
            return p
    raise ValueError(f"{what}: {target!r} is not a term of the expression")


def factor_count(body):
    """Things multiplied inside one term: the number, every letter (x² is two factors), each group."""
    rest = re.sub(GROUP, "", body)
    n = len(re.findall(GROUP, body)) + (1 if re.match(r"\d+", rest) else 0)
    return n + sum(int(e or 1) for _, e in re.findall(r"([a-z])(?:\^(\d+))?", rest))


def var_part(t):
    """The variable part of one term as sorted (letter, power) pairs: 5xy and 2yx give the same one,
    x and x^2 do not, a constant gives (). A term containing a group has no single variable part."""
    body = _norm(t).lstrip("+-")
    if re.search(GROUP, body):
        raise ValueError(f"{t!r} contains a group")
    powers = {}
    for v, e in re.findall(r"([a-z])(?:\^(\d+))?", body):
        powers[v] = powers.get(v, 0) + int(e or 1)
    return tuple(sorted(powers.items()))


# ---------------------------------------------------------------- equations and their steps (topic 1.3)
XS = [F(0), F(1), F(2), F(-3), F(5, 7), F(11)]           # values of x an equation step is tested at
EQ_DERIVE = ("operand", "solve", "first-error")           # derive kinds that read an equation or a step
STEP_OF_CHIP = {"ADD": "Addition", "SUBTRACT": "Subtraction", "MULTIPLY": "Multiplication",
                "DIVIDE": "Division", "DIST": "Distributive", "COMBINE": "Combine"}


def fx(expr, v):
    """An expression in x at x = v, with exact fractions."""
    return ev(expr, {"x": f"({v})"})


def split_eq(eq):
    if eq.count("=") != 1:
        raise ValueError(f"{eq!r} is not one equation")
    left, right = eq.split("=")
    return left.strip(), right.strip()


def lin(expr):
    """(m, k) with expr = m·x + k; fails if the expression is not linear in x."""
    k, m = fx(expr, XS[0]), fx(expr, XS[1]) - fx(expr, XS[0])
    if any(fx(expr, v) != m * v + k for v in XS):
        raise ValueError(f"{expr!r} is not linear in x")
    return m, k


def solve_linear(eq):
    """The solution of a linear equation in x: a Fraction, "all" (every x) or "none" (no x)."""
    left, right = split_eq(eq)
    (m1, k1), (m2, k2) = lin(left), lin(right)
    m, k = m1 - m2, k2 - k1
    if m == 0:
        return "all" if k == 0 else "none"
    return k / m


def step_kind(a, b):
    """Which property takes equation a to equation b, read from the two equations themselves:
    Distributive / Combine (each side keeps its value, only its form changes: a group is opened, or
    like terms are collected), Addition / Subtraction (the same expression is added to or taken from
    both sides) or Multiplication / Division (both sides times a number, or over one). None when
    the step is none of these (so a wrong step is never given a name)."""
    la, ra = split_eq(a)
    lb, rb = split_eq(b)
    if all(fx(la, v) == fx(lb, v) and fx(ra, v) == fx(rb, v) for v in XS):
        changed = [(p, q) for p, q in ((la, lb), (ra, rb)) if _norm(p) != _norm(q)]
        if not changed:
            return None
        return "Distributive" if any("(" in p and "(" not in q for p, q in changed) else "Combine"
    add = [fx(lb, v) - fx(la, v) for v in XS]
    if add == [fx(rb, v) - fx(ra, v) for v in XS]:           # c(x) added to both sides
        c0, c1 = add[0], add[1] - add[0]
        if all(add[k] == c1 * XS[k] + c0 for k in range(len(XS))):
            lead = c1 if c1 != 0 else c0
            if lead != 0:
                return "Addition" if lead > 0 else "Subtraction"
        return None
    for v in XS:                                             # both sides times c
        if fx(ra, v) != 0:
            c = fx(rb, v) / fx(ra, v)
            break
    else:
        return None
    if c != 0 and all(fx(lb, v) == fx(la, v) * c and fx(rb, v) == fx(ra, v) * c for v in XS):
        if c.denominator == 1 and abs(c) > 1:
            return "Multiplication"
        if abs(c.numerator) == 1 and abs(c.denominator) > 1:
            return "Division"
    return None


def step_number(a, b):
    """(property, n): the number a step adds, subtracts, multiplies by or divides by (n keeps its
    sign for multiplication and division, so ÷ −5 gives −5). Only for a step by a plain number."""
    prop = step_kind(a, b)
    la, ra = split_eq(a)
    lb, rb = split_eq(b)
    if prop in ("Addition", "Subtraction"):
        cs = {fx(lb, v) - fx(la, v) for v in XS}
        if len(cs) != 1:
            raise ValueError("the step does not add or subtract a plain number")
        return prop, abs(cs.pop())
    if prop in ("Multiplication", "Division"):
        v = next(v for v in XS if fx(ra, v) != 0)
        c = fx(rb, v) / fx(ra, v)
        return prop, c if prop == "Multiplication" else 1 / c
    raise ValueError(f"{a!r} → {b!r} is not a step by a plain number")


def side_without_x(eq):
    """The number on the side of an equation that has no x (the other side holds x)."""
    for side in split_eq(eq):
        m, k = lin(side)
        if m == 0:
            return k
    raise ValueError(f"{eq!r} has x on both sides")


def eq_derive(q, spec):
    """derive kinds for equations (1.3): operand[:<Property>] — the number a step "A → B" adds, subtracts,
    multiplies by or divides by; solve — the solution of an equation (an integer); first-error — the
    number of the first line of a student's work (lines separated by newlines) that stops being
    equivalent to the first one."""
    kind, _, arg = spec.partition(":")
    if kind == "operand":
        a, b = (s.strip() for s in q.split("→"))
        prop, n = step_number(a, b)
        if arg and prop != arg:
            raise ValueError(f"the step is the {prop} property, not {arg}")
        value = n
    elif kind == "solve":
        value = solve_linear(q)
        if not isinstance(value, F):
            raise ValueError(f"{q!r} has {value!r} solutions")
    else:
        lines = q.split("\n")
        base = solve_linear(lines[0])
        bad = [k + 1 for k, line in enumerate(lines) if k and solve_linear(line) != base]
        if not bad:
            raise ValueError("every line is equivalent to the first one")
        value = F(bad[0])
    if value.denominator != 1:
        raise ValueError(f"the answer {value} is not an integer")
    return int(value)


def eq_mistake(code, q, spec, ans):
    """The number a named mistake gives on an equation exercise (1.3)."""
    kind = spec.partition(":")[0]
    if kind == "operand":
        a, b = (s.strip() for s in q.split("→"))
        if code == "sign":                               # the number given with the property's sign
            return -ans
        if code == "result":                             # the number on the right of the new equation
            return int(side_without_x(b))
        if code == "start":                              # the number on the right of the old equation
            return int(side_without_x(a))
        if code == "coef":                               # the coefficient of x in the old equation
            return int(next(lin(s)[0] for s in split_eq(a) if lin(s)[0] != 0))
    elif kind == "solve":
        (m1, k1), (m2, k2) = (lin(s) for s in split_eq(q))
        got = {"sign-k": (k2 + k1) / (m1 - m2),          # moved the constant with the wrong sign
               "sign-x": (k2 - k1) / (m1 + m2) if m1 + m2 else None,   # moved the x term with the wrong sign
               "no-divide": k2 - k1,                     # stopped before dividing
               "ignore-k": k2 / (m1 - m2),               # forgot the constant on the x side
               "order": (k1 - k2) / (m1 - m2)}.get(code)  # subtracted in the wrong order
        if got is not None:
            if got.denominator != 1:
                raise ValueError(f"mistake {code!r} gives {got}, not an integer")
            return int(got)
    elif kind == "first-error":
        n = len(q.split("\n"))
        got = {"last": n, "before": ans - 1, "after": ans + 1, "first": 1}.get(code)
        if got is not None:
            return got
    raise ValueError(f"unknown mistake {code!r} for derive {spec!r}")


def validate_equation_lines(ex, problems):
    """The lines of a 1.3 solution video must be true: every step of an operand/solve exercise is the
    property its chip says, every line of a solve has the solution, and a student's work gets the
    verdict it really deserves (OK before the first wrong line, ERROR at it, CARRY after it)."""
    i, kind, ans = ex["id"], ex["derive"].partition(":")[0], ex["_answer"]
    lines = [re.sub("[⟨⟩]", "", ln) for ln in ex["lines"]]
    try:
        if kind == "first-error":
            if "\n".join(lines) != ex["q"]:
                problems.append(f"{i}: the lines must be the student's work, exactly as in q")
            for j, chip in enumerate(ex["chips"]):
                want = "OK" if j + 2 < ans else "ERROR" if j + 2 == ans else "CARRY"
                if chip != want:
                    problems.append(f"{i}: step {j + 1} ({lines[j]!r} → {lines[j + 1]!r}) should be {want}, not {chip}")
                if want == "CARRY" and solve_linear(lines[j + 1]) != solve_linear(lines[j]):
                    problems.append(f"{i}: step {j + 1} is a second mistake; a CARRY step must be fine on its own")
            return
        for j, chip in enumerate(ex["chips"]):
            if chip not in STEP_OF_CHIP:
                problems.append(f"{i}: chip {chip!r} is not a property of equality or a rewrite")
            elif (got := step_kind(lines[j], lines[j + 1])) != STEP_OF_CHIP[chip]:
                problems.append(f"{i}: step {j + 1} ({lines[j]!r} → {lines[j + 1]!r}) is {got}, not {STEP_OF_CHIP[chip]}")
        if kind == "solve":
            if _norm(lines[0]) != _norm(ex["q"]):
                problems.append(f"{i}: the first line must be the question")
            for ln in lines:
                if solve_linear(ln) != ans:
                    problems.append(f"{i}: line {ln!r} does not have the solution {ans}")
        else:
            if ex["q"] != f"{lines[0]} → {lines[1]}":
                problems.append(f"{i}: q must be the two lines of the step, joined by ' → '")
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: cannot check the lines: {e}")


def check_equation_tools():
    """Tests of the equation tools themselves; they run before every build."""
    cases = [("x + 5 = 9", "x = 4", "Subtraction"), ("x − 3 = 7", "x = 10", "Addition"),
             ("[[x | 2]] = 6", "x = 12", "Multiplication"), ("3x = 12", "x = 4", "Division"),
             ("−5x = 30", "x = −6", "Division"), ("2(x + 3) = 14", "2x + 6 = 14", "Distributive"),
             ("3x + 2x = 20", "5x = 20", "Combine"), ("5x = 3x + 8", "2x = 8", "Subtraction"),
             ("2x + 5 = 3x − 1", "5 = x − 1", "Subtraction"), ("x − 1 = 5", "x = 6", "Addition"),
             ("2x + 3 = 11", "2x = 14", None),            # 3 was added, not subtracted: a wrong step has no name
             ("3x + 2 = 11", "x + 2 = [[11 | 3]]", None),  # only one term divided
             ("x + 5 = 9", "x + 5 = 9", None)]
    for a, b, want in cases:
        got = step_kind(a, b)
        assert got == want, f"step_kind({a!r}, {b!r}) = {got}, expected {want}"
    assert solve_linear("3(x − 2) = 12") == 6 and solve_linear("x + 1 = x + 1") == "all"
    assert solve_linear("x + 1 = x + 2") == "none" and solve_linear("2x = 3") == F(3, 2)
    assert step_number("−5x = 30", "x = −6") == ("Division", -5)
    assert step_number("x + 8 = 15", "x = 7") == ("Subtraction", 8)


def derive(q, spec):
    """The answer of a structural question, computed from the expression: terms · constant ·
    coef:<term> · factors:<term>; for equations (1.3) operand · solve · first-error."""
    kind, _, arg = spec.partition(":")
    if kind in EQ_DERIVE:
        return eq_derive(q, spec)
    parts = all_parts(q)
    if kind == "terms":
        return len(parts)
    if kind == "constant":
        cs = [p for p in parts if not p["var"]]
        if len(cs) != 1:
            raise ValueError("needs exactly one constant term")
        return cs[0]["coef"]
    if kind == "coef":
        return find_term(parts, arg, "coef")["coef"]
    if kind == "factors":
        return factor_count(find_term(parts, arg, "factors")["body"])
    raise ValueError(f"unknown derive {spec!r}")


def mistake_value(code, q, spec, ans):
    """The number a named mistake gives, so a wrong option can be checked against its description."""
    if spec.partition(":")[0] in EQ_DERIVE:
        return eq_mistake(code, q, spec, ans)
    parts = all_parts(q)
    kind, _, arg = code.partition(":")
    flat = re.sub(r"\^\d+", "", _norm(q))
    pieces = len(re.findall(r"\d+|[a-z]", flat))
    if kind == "one":                                   # the whole thing taken as one piece
        return 1
    if kind == "pieces":                                # every number and letter counted
        return pieces
    if kind == "tokens":                                # every number, letter and sign counted
        return pieces + len(re.findall(r"[+-]", flat))
    if kind == "flat":                                  # terms inside groups counted as well
        return sum(len(split_terms(re.search(GROUP, p["body"]).group(0)[1:-1])) if p["group"] else 1 for p in parts)
    if kind == "variable-terms":                        # only terms with a variable
        return sum(1 for p in parts if p["var"])
    if kind == "distinct-vars":
        return len(set(re.findall(r"[a-z]", flat)))
    if kind == "drop-sign":
        return abs(ans)
    if kind == "hidden-zero":                           # "no number written" read as zero
        t = find_term(parts, spec.partition(":")[2], "hidden-zero")
        if t["num"] is not None:
            raise ValueError("hidden-zero needs a term with no written number")
        return 0
    if kind == "constant":
        return derive(q, "constant")
    if kind == "coef-of":                               # the coefficient of another term
        return find_term(parts, arg, "coef-of")["coef"]
    if kind == "sum-numbers":                           # every coefficient and constant added
        return sum(p["coef"] for p in parts)
    raise ValueError(f"unknown mistake {code!r}")


def validate_derive(ex, problems):
    """kind "num" with "derive": the answer is read from the expression's structure (terms, coefficient,
    constant, factors), never typed; every wrong value is checked against the named mistake "m"."""
    i, q = ex["id"], ex["q"]
    try:
        ans = derive(q, ex["derive"])
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: cannot derive {ex['derive']!r}: {e}")
        return
    ex["_answer"] = ans
    if check_steps(ex, problems) and ex["derive"].partition(":")[0] in EQ_DERIVE:
        validate_equation_lines(ex, problems)
    for f in ("prompt", "read"):
        if not ex.get(f):
            problems.append(f"{i}: needs {f!r}")
    if len(ex["wrong"]) != 3:
        problems.append(f"{i}: needs exactly 3 wrong options")
    seen = {}
    for w in ex["wrong"]:
        for f in ("v", "why", "say", "m"):
            if w.get(f) is None:
                problems.append(f"{i}: wrong option {w.get('v')!r} has no {f!r}")
        if w.get("v") is None or not w.get("m"):
            continue
        w["_value"] = int(w["v"])
        try:
            got = mistake_value(w["m"], q, ex["derive"], ans)
        except Exception as e:  # noqa: BLE001
            problems.append(f"{i}: mistake {w['m']!r} cannot be computed: {e}")
            continue
        if got != w["_value"]:
            problems.append(f"{i}: mistake {w['m']!r} gives {got}, but the option says {w['v']}")
        if w["_value"] == ans:
            problems.append(f"{i}: wrong option {w['v']} equals the right answer")
        if w["_value"] in seen:
            problems.append(f"{i}: two wrong options give {w['_value']}")
        seen[w["_value"]] = w["m"]


def check_claim(ex, item_text, claim, problems, what):
    """kind multi/match with "check": verify one statement with code.
    claim "true"            → item is an identity "L = R" that holds for every value of the letters
                              (so "x − 8 = 8 − x" is false and "x + 8 = 8 + x" is true);
    claim "property:<Name>" → item is a true identity showing that property;
    claim "equals:<expr>"   → item equals <expr> for every value of the variables;
    claim "term-of:<expr>"  → item is one of the terms of <expr> (sign included);
    claim "terms:<n>"       → item has exactly <n> terms;
    claim "coefficient:<n>" → item is one term whose coefficient is <n>;
    claim "like:<term>"     → item is one term with the same variable part as <term> (a like term);
    claim "solution:<eq>"   → item ("x = 5" or "5") is a solution of the equation <eq> (1.1: checked by substituting);
    claim "operation:<name>"→ the phrase contains a key word of exactly that operation (OPERATION_WORDS);
    claim "step:<Property>" → item is a step "A → B" between two equations that is justified by that
                              property (Addition, Subtraction, Multiplication, Division, Distributive,
                              Combine; only the first word counts), read from the equations (1.3);
    claim "valid-from:<equation>" → item is an equation with the same solution as <equation>, so it could
                              be the next line of its solution (1.3)."""
    i = ex["id"]
    kind, _, arg = claim.partition(":")
    try:
        if kind == "step":
            a, b = (s.strip() for s in item_text.split("→"))
            got = step_kind(a, b)
            if got is None:
                problems.append(f"{i}: {what} {item_text!r} is not a step by any property of equality")
                return None
            return got == arg.split()[0]
        if kind == "valid-from":
            return solve_linear(item_text) == solve_linear(arg)
        if kind == "property":
            left, right = item_text.split("=")
            if not same(left, right):
                problems.append(f"{i}: {what} {item_text!r} is not a true identity")
                return None
            return classify(item_text) == arg
        if kind == "equals":
            return same(item_text, arg)
        if kind == "true":
            left, right = item_text.split("=")
            return same(left, right)
        if kind == "solution":
            var = equation_var(arg)
            m = re.fullmatch(rf"\s*{var}\s*=\s*(.+)", item_text)
            v = ev(m.group(1) if m else item_text)
            left, right = arg.split("=")
            return ev(left, {var: f"({v})"}) == ev(right, {var: f"({v})"})
        if kind == "term-of":
            return _norm(item_text).lstrip("+") in [t.lstrip("+") for t in split_terms(arg)]
        if kind == "terms":
            return len(split_terms(item_text)) == int(arg)
        if kind == "coefficient":
            ts = split_terms(item_text)
            if len(ts) != 1:
                problems.append(f"{i}: {what} {item_text!r} is not a single term")
                return None
            return term_parts(ts[0])["coef"] == int(_norm(arg))
        if kind == "like":
            ts = split_terms(item_text)
            if len(ts) != 1:
                problems.append(f"{i}: {what} {item_text!r} is not a single term")
                return None
            return var_part(ts[0]) == var_part(arg)
        if kind == "operation":
            low = item_text.lower() + " "
            hits = {op for op, ws in OPERATION_WORDS.items() if any(re.search(rf"(?<![a-z]){re.escape(w)}", low) for w in ws)}
            if arg not in OPERATION_WORDS:
                problems.append(f"{i}: unknown operation {arg!r}")
                return None
            if len(hits) != 1:
                problems.append(f"{i}: {what} {item_text!r} matches operations {sorted(hits)}; it must match exactly one")
                return None
            return arg in hits
    except Exception as e:  # noqa: BLE001
        problems.append(f"{i}: {what} {item_text!r} cannot be evaluated: {e}")
        return None
    problems.append(f"{i}: unknown check {claim!r}")
    return None


def validate_multi(ex, problems):
    """kind "multi": select ALL that apply. 4–6 options, at least one right and one wrong. With
    "check" ("property:<Name>" or "equals:<expr>") every option's ok flag is verified by code."""
    i, opts = ex["id"], ex.get("options", [])
    if not 4 <= len(opts) <= 6:
        problems.append(f"{i}: a multi exercise needs 4–6 options")
    if not any(o.get("ok") for o in opts) or all(o.get("ok") for o in opts):
        problems.append(f"{i}: needs at least one right and one wrong option")
    if len({o.get("t") for o in opts}) != len(opts):
        problems.append(f"{i}: two options are the same")
    for o in opts:
        for f in ("t", "why", "say"):
            if not o.get(f):
                problems.append(f"{i}: option {o.get('t')!r} has no {f!r}")
        if ex.get("check") and o.get("t"):
            truth = check_claim(ex, o["t"], ex["check"], problems, "option")
            if truth is not None and truth != bool(o.get("ok")):
                problems.append(f"{i}: option {o['t']!r} is marked ok={bool(o.get('ok'))}, but the check says {truth}")
    for f in ("prompt", "read", "say_answer"):
        if not ex.get(f):
            problems.append(f"{i}: needs {f!r}")


def validate_match(ex, problems):
    """kind "match": match every left item with a right item. 3–6 pairs; right items may repeat
    (sorting into categories). With "check": "property" (left = identity, right = its property) or
    "equal" (left and right are equal expressions) every pair is verified by code."""
    i, pairs = ex["id"], ex.get("pairs", [])
    if not 3 <= len(pairs) <= 6:
        problems.append(f"{i}: a match exercise needs 3–6 pairs")
    if len({p.get("l") for p in pairs}) != len(pairs):
        problems.append(f"{i}: two left items are the same")
    if len({p.get("r") for p in pairs}) < 2:
        problems.append(f"{i}: needs at least two different right items")
    for p in pairs:
        for f in ("l", "r", "why", "say"):
            if not p.get(f):
                problems.append(f"{i}: pair {p.get('l')!r} has no {f!r}")
        chk = ex.get("check")
        if chk and p.get("l") and p.get("r"):
            claim = f"property:{p['r']}" if chk == "property" else f"equals:{p['r']}" if chk == "equal" \
                else f"coefficient:{p['r']}" if chk == "coefficient" \
                else f"operation:{p['r']}" if chk == "operation" \
                else f"step:{p['r']}" if chk == "step" \
                else f"terms:{p['r']}" if chk == "terms" \
                else f"solution:{p['l']}" if chk == "solves" else chk
            item = p["r"] if chk == "solves" else p["l"]      # "solves": left = equation, right = its solution
            if check_claim(ex, item, claim, problems, "pair") is False:
                problems.append(f"{i}: pair {p['l']!r} → {p['r']!r} is not right")
    if chk := ex.get("check"):
        if chk == "solves":   # no right value may also solve another pair's equation
            for p in pairs:
                for q in pairs:
                    if q is not p and q["r"] != p["r"] and check_claim(ex, q["r"], f"solution:{p['l']}", problems, "pair") is True:
                        problems.append(f"{i}: {q['r']!r} also solves {p['l']!r}")
        if chk == "equal":   # no left item may also equal another pair's right item
            for p in pairs:
                for q in pairs:
                    if q is not p and q["r"] != p["r"] and same(p["l"], q["r"]):
                        problems.append(f"{i}: {p['l']!r} also equals {q['r']!r}")
    for f in ("prompt", "read", "say_answer"):
        if not ex.get(f):
            problems.append(f"{i}: needs {f!r}")


def validate(data):
    problems = []
    check_equation_tools()
    for ex in data["exercises"]:
        kind = ex.setdefault("kind", "num")
        if kind == "multi":
            validate_multi(ex, problems)
            continue
        if kind == "match":
            validate_match(ex, problems)
            continue
        if kind == "expr":
            validate_expr(ex, problems)
            continue
        if kind == "name":
            validate_name(ex, problems)
            continue
        if kind == "words":
            validate_words(ex, problems)
            continue
        if kind == "solve":
            validate_solve(ex, problems)
            continue
        if ex.get("derive"):
            validate_derive(ex, problems)
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
            if chip_color(c) is None:
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
    return re.sub(r"\^(\d+)", r"<sup>\1</sup>", s).replace("\n", "<br>")   # a student's work is several lines


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
def item_title(data, ex, num):
    """What a solution video calls itself: "Exercise 5" in a practice set. A unit exam sets
    data["video_title"] (placeholders {num} and {block}) so its Boss solution videos say so."""
    return data.get("video_title", "Exercise {num}").format(num=num, block=ex.get("block_name", ""))


def unit_label(data):
    """The small label at the top left of a solution video."""
    return data.get("video_unit") or f"Unit {data['unit'].split('.')[0]} · Practice {data['unit']}"


def video_files(data, ex, num, set_id):
    if ex["kind"] == "name":
        return name_video(data, ex, num, set_id)
    if ex["kind"] == "multi":
        return multi_video(data, ex, num, set_id)
    if ex["kind"] == "match":
        return match_video(data, ex, num, set_id)
    vid = f"{set_id}-{ex['id']}"
    item = item_title(data, ex, num)
    n, lv = len(ex["chips"]), data["levels"][str(ex["level"])]
    wrong = ex["wrong"]
    isw = ex["kind"] == "words"
    iss = ex["kind"] == "solve"
    q_plain = plain(ex["prompt"]) if isw else plain(ex["q"])
    if iss:      # lesson 1.1: the answer reads "x = 5"; each trap is a wrong value of x
        ans, var = ex["_answer"], ex["_var"]
        ans_say, ans_html, ans_plain = f"{var} equals {words(ans)}", markup(ex["lines"][-1]), ex["lines"][-1]
        trap_say = [words(w["_value"]) for w in wrong]
        trap_html = [markup(f"{var} = {w['_value']}".replace("-", "−")) for w in wrong]
        trap_size = "sm"
    elif ex["kind"] == "num":
        ans = ex["_answer"]
        # "a_read" / "a_show": how the answer is spoken and shown when it is not just the number
        # (1.3: "line three", "x = 6")
        ans_say, ans_html, ans_plain = ex.get("a_read") or words(ans), ex.get("a_show") or money(ans), money(ans)
        trap_say = [words(w["_value"]) for w in wrong]
        trap_html = [money(w["_value"]) for w in wrong]
        trap_size = "sm"
    else:
        ans_say, ans_html, ans_plain = ex["a_read"], markup(ex["a"]), plain(ex["a"])
        trap_say = [w["read"] for w in wrong]
        trap_html = [markup(w["e"]) for w in wrong]
        trap_size = "xs"
    last_word = spoken_last(ans_say)
    if isw:      # the answer block also tests the expression with a real number, computed here
        t = ex["test"]
        val = int(ex["_test_value"])
        test_say = f" Test it. If {t['var']} is {words(t['value'])}, the expression gives {words(val)}."
        test_html = f"{t['var']} = {t['value']}: {markup(ex['a'])} → <span class=\"green\">{money(val)}</span>"
    elif iss:    # the check the lesson teaches: put the answer back in the equation, computed here
        left, right = ex["q"].split("=")
        lv, rv = ev(left, {var: f"({ans})"}), ev(right, {var: f"({ans})"})
        if lv != rv:
            raise ValueError(f"{ex['id']}: the check does not balance")
        test_say = f" Check it. Put {words(ans)} in for {var}, and both sides equal {words(int(lv))}."
        test_html = f"{markup(substitute_text(ex['q'], var, ans))} <span class=\"green\">✓</span>"
    else:
        test_say = test_html = ""
    test_word = "check" if iss else "test"
    trap_text = ("Watch out for these traps. "
                 + " ".join(f"If you {w['say']}, you get {ts}." for w, ts in zip(wrong[:2], trap_say)))

    blocks_s2 = []
    for k in range(n):
        blocks_s2.append({"id": f"b{k + 2:02d}", "text": ex["say"][k], "display": plain(ex["lines"][k + 1]),
                          "cue": f"step-{k + 1}"})
    b_ans, b_trap = f"b{n + 2:02d}", f"b{n + 3:02d}"
    script = {
        "format": "algebra-video-script", "version": 1, "video": vid,
        "title": item, "voice": "narrator",
        "scenes": [
            {"id": "s01", "title": "The problem", "blocks": [
                {"id": "b01", "text": "Let's solve this one step by step. " + ex["read"], "display": q_plain,
                 "cue": "show-problem", "pause_after_s": 1.2}]},
            {"id": "s02", "title": "Step by step", "blocks": blocks_s2},
            {"id": "s03", "title": "The answer", "blocks": [
                {"id": b_ans, "text": f"So the answer is {ans_say}.{test_say}", "display": ans_plain if ex.get("derive") or iss else f"= {ans_plain}", "cue": "answer"},
                {"id": b_trap, "text": trap_text, "cue": "traps"}]},
        ],
    }

    # --- page
    prob_size = "" if isw else pick_size(ex["q"].split("\n"), [(132, ""), (96, "md"), (72, "sm"), (56, "xs")], 400, 1700)
    problem_div = (f'<div class="say pop" style="font-size: 60px; max-width: 1500px" data-at="b01">{ex["prompt"]}</div>' if isw
                   else f'<div class="math {prob_size} pop" data-at="b01">{markup(ex["q"])}</div>')
    row_size = pick_size(ex["lines"], [(96, "md"), (72, "sm"), (56, "xs")], 730)
    rows = []
    for j, line in enumerate(ex["lines"]):
        if j < n:
            color = chip_color(ex["chips"][j])
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
            rows.append(f'      <span class="chip c-{chip_color(chip)} pop" data-at="{at}">{chip}</span>')
            cls = "pop green" if j == n else "fade"
            rows.append(f'      <div class="math {row_size} {cls}" data-at="{at}">{html}</div>')
    cards = []
    for k, w in enumerate(wrong):
        cards.append(
            f'        <div class="card trap fade c-red" data-at="{b_trap}+{0.15 + 0.25 * k:.2f}">'
            f'<div class="math {trap_size} red"><span class="strike" data-at="{b_trap}+{0.9 + 0.25 * k:.2f}" data-dur="0.5">{trap_html[k]}</span></div>'
            f'<div class="why">{w["why"]}</div></div>')
    if isw or iss:
        answer_line = (f'<div class="math sm green pop" data-at="{b_ans}@{last_word}">{ans_html}</div>'
                       f'<div class="math xs fade" data-at="{b_ans}@{test_word}">{test_html}</div>')
    elif ex.get("derive"):    # a question about the parts, not an equation: show the question, then the answer
        # a student's work (several lines) is not repeated here: it would not leave room for the traps
        q_again = "" if "\n" in ex["q"] else f'<div class="math sm fade" data-at="{b_ans}-0.5">{markup(ex["q"])}</div>'
        answer_line = (f'<div class="col" style="gap: 14px">{q_again}'
                       f'<div class="say fade muted" style="font-size: 40px" data-at="{b_ans}-0.5">{ex["prompt"]}</div>'
                       f'<div class="math sm green pop" data-at="{b_ans}@{last_word}">{ans_html}</div></div>')
    else:
        answer_line = (f'<div class="math sm fade" data-at="{b_ans}-0.5">{markup(ex["q"])} '
                       f'<span class="green pop" data-at="{b_ans}@{last_word}">= {ans_html}</span></div>')
    prompt = f'\n    <div class="say fade muted" data-at="b01+0.4" style="font-size: 40px">{ex["prompt"]}</div>' if ex.get("prompt") and not isw else ""
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{item} — step by step</title>
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
  .deriv {{ display: grid; grid-template-columns: auto auto; align-items: center; justify-content: center; gap: {"30px" if any("[[" in x for x in ex["lines"]) or ex.get("derive") else "10px"} 28px; }}
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
  <div class="header"><span class="unit">{unit_label(data)}</span><span class="title">{item}</span></div>

  <!-- s01: the problem -->
  <section class="scene" data-scene="s01">
    <div class="label yellow fade" data-at="b01">{item} · {lv}</div>
    {problem_div}{prompt}
  </section>

  <!-- s02: step by step -->
  <section class="scene" data-scene="s02">
    <div class="deriv">
{chr(10).join(rows)}
    </div>
  </section>

  <!-- s03: the answer and the traps -->
  <section class="scene" data-scene="s03">
    {answer_line}
    <div class="label red fade" data-at="{b_trap}">Common traps</div>
    <div class="row" style="align-items: stretch; gap: 36px">
{chr(10).join(cards)}
    </div>
    <div class="label muted fade" data-at="{b_trap}+1.5" style="font-size: 22px; font-weight: 500; position: absolute; right: 0; top: -72px">This video uses an AI-generated voice.</div>
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

def page(title, header_unit, item, style, scenes, play_label="Watch the solution"):
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
  <div class="header"><span class="unit">{header_unit}</span><span class="title">{item}</span></div>
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
    item = item_title(data, ex, num)
    lv = data["levels"][str(ex["level"])]
    color = PROPERTIES[ex["a"]]
    nb = len(ex["say"])
    b_ans, b_trap = f"b{nb + 2:02d}", f"b{nb + 3:02d}"
    wrong = ex["wrong"]
    trap_text = ("Watch out for these traps. "
                 + " ".join(f"It isn't the {w['a'].lower()} property, because {w['say']}." for w in wrong))
    script = {
        "format": "algebra-video-script", "version": 1, "video": vid,
        "title": item, "voice": "narrator",
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
    <div class="label yellow fade" data-at="b01">{item} · {lv}</div>
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
    return vid, script, page(f"{item} — step by step", unit_label(data), item, style, scenes)


CHOICE_STYLE = """
  .hl { padding: 0 10px; margin: 0 -10px; }
  sup { font-size: 0.6em; vertical-align: 0.55em; line-height: 0; }
  .frac { display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; margin: 0 0.12em; }
  .frac .top { padding: 0.04em 0.25em 0.2em; border-bottom: 0.07em solid currentColor; }
  .frac .bot { padding: 0.2em 0.25em 0.04em; }
  .prompt-l { font: 600 40px/1.3 Inter, sans-serif; color: var(--muted); text-align: center; max-width: 1500px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 26px 40px; width: 1500px; }
  .opt { position: relative; display: flex; align-items: center; justify-content: center; min-height: 130px; padding: 18px 30px;
    border-radius: 26px; border: 3px solid #2a3a5c; background: #18243d; font: 600 52px Poppins, sans-serif; }
  .opt .mark { position: absolute; top: -22px; right: -18px; width: 64px; height: 64px; border-radius: 50%; display: grid; place-items: center;
    font: 700 40px Poppins, sans-serif; color: #101a2e; }
  .opt .mark.ok { background: var(--green); } .opt .mark.no { background: var(--red); }
  .pairs { display: grid; grid-template-columns: auto 120px auto; gap: 26px 10px; align-items: center; justify-content: center; }
  .pairs .l { justify-self: end; } .pairs .r { justify-self: start; }
  .pairs .arrow { font: 700 56px Poppins, sans-serif; color: var(--yellow); text-align: center; }
  .side { padding: 14px 30px; border-radius: 22px; border: 3px solid #2a3a5c; background: #18243d; font: 600 46px Poppins, sans-serif; }
  .why-l { font: 500 32px/1.3 Inter, sans-serif; color: var(--muted); text-align: center; max-width: 1400px; }
"""


def choice_text(t):
    """Option or matching item: math gets the usual markup, words stay as they are."""
    return markup(t)


def multi_video(data, ex, num, set_id):
    """Select all that apply: the options, then one block per option that says why it is in or out."""
    vid = f"{set_id}-{ex['id']}"
    item = item_title(data, ex, num)
    lv = data["levels"][str(ex["level"])]
    opts = ex["options"]
    nb = len(opts)
    b_ans = f"b{nb + 2:02d}"
    script = {
        "format": "algebra-video-script", "version": 1, "video": vid, "title": item, "voice": "narrator",
        "scenes": [
            {"id": "s01", "title": "The problem", "blocks": [
                {"id": "b01", "text": "Let's look at this one. " + ex["read"], "display": ex["prompt"],
                 "cue": "show-problem", "pause_after_s": 1.5}]},
            {"id": "s02", "title": "One by one", "blocks": [
                {"id": f"b{k + 2:02d}", "text": o["say"], "display": plain(o["t"]), "cue": f"option-{k + 1}"}
                for k, o in enumerate(opts)]},
            {"id": "s03", "title": "The answer", "blocks": [
                {"id": b_ans, "text": ex["say_answer"], "cue": "answer"}]},
        ],
    }
    cells = []
    for k, o in enumerate(opts):
        blk = f"b{k + 2:02d}"
        color = "green" if o["ok"] else "red"
        mark = (f'<span class="mark ok pop" data-at="{blk}.end-0.6">✓</span>' if o["ok"]
                else f'<span class="mark no pop" data-at="{blk}.end-0.6">✗</span>')
        inner = choice_text(o["t"])
        if not o["ok"]:
            inner = f'<span class="strike" data-at="{blk}.end-0.6" data-dur="0.4">{inner}</span>'
        cells.append(f'      <div class="opt glow c-{color}" data-at="{blk}">{mark}'
                     f'<span>{inner}</span></div>')
    plain_cells = "\n".join(f'      <div class="opt">{choice_text(o["t"])}</div>' for o in opts)
    whys = "\n".join(
        f'      <div class="why-l fade" data-at="b{k + 2:02d}+0.2"{f" data-out=\"b{k + 3:02d}\"" if k < nb - 1 else ""}>{o["why"]}</div>'
        for k, o in enumerate(opts))
    right = "\n".join(f'      <div class="opt glow c-green pop" data-at="{b_ans}+{0.2 + 0.2 * k:.1f}">{choice_text(o["t"])}</div>'
                      for k, o in enumerate(x for x in opts if x["ok"]))
    scenes = f"""
  <section class="scene" data-scene="s01">
    <div class="label yellow fade" data-at="b01">{item} · {lv}</div>
    <div class="prompt-l fade" data-at="b01">{ex["prompt"]}</div>
    <div class="grid fade" data-at="b01+0.6">
{plain_cells}
    </div>
  </section>

  <section class="scene" data-scene="s02">
    <div class="grid">
{chr(10).join(cells)}
    </div>
    <div class="stack">
{whys}
    </div>
  </section>

  <section class="scene" data-scene="s03">
    <div class="label green fade" data-at="{b_ans}">All that apply</div>
    <div class="row" style="flex-wrap: wrap; gap: 26px; max-width: 1600px; justify-content: center">
{right}
    </div>
    <div class="label muted fade" data-at="{b_ans}+1.5" style="font-size: 22px; font-weight: 500">This video uses an AI-generated voice.</div>
  </section>
"""
    return vid, script, page(f"{item} — step by step", unit_label(data), item, CHOICE_STYLE, scenes)


def match_video(data, ex, num, set_id):
    """Matching: the items, then one block per pair that joins it and says why."""
    vid = f"{set_id}-{ex['id']}"
    item = item_title(data, ex, num)
    lv = data["levels"][str(ex["level"])]
    pairs = ex["pairs"]
    nb = len(pairs)
    b_ans = f"b{nb + 2:02d}"
    script = {
        "format": "algebra-video-script", "version": 1, "video": vid, "title": item, "voice": "narrator",
        "scenes": [
            {"id": "s01", "title": "The problem", "blocks": [
                {"id": "b01", "text": "Let's look at this one. " + ex["read"], "display": ex["prompt"],
                 "cue": "show-problem", "pause_after_s": 1.5}]},
            {"id": "s02", "title": "Pair by pair", "blocks": [
                {"id": f"b{k + 2:02d}", "text": p["say"], "display": f"{plain(p['l'])} → {plain(p['r'])}", "cue": f"pair-{k + 1}"}
                for k, p in enumerate(pairs)]},
            {"id": "s03", "title": "The answer", "blocks": [
                {"id": b_ans, "text": ex["say_answer"], "cue": "answer"}]},
        ],
    }
    rights = list(dict.fromkeys(p["r"] for p in pairs))
    lefts = "\n".join(f'      <div class="side">{choice_text(p["l"])}</div>' for p in pairs)
    rlist = "\n".join(f'      <div class="side">{choice_text(r)}</div>' for r in rights)
    rows = []
    for k, p in enumerate(pairs):
        blk = f"b{k + 2:02d}"
        rows.append(f'      <div class="side l fade" data-at="{blk}">{choice_text(p["l"])}</div>'
                    f'<div class="arrow pop" data-at="{blk}.end-0.8">→</div>'
                    f'<div class="side r glow c-green pop" data-at="{blk}.end-0.8">{choice_text(p["r"])}</div>')
    whys = "\n".join(
        f'      <div class="why-l fade" data-at="b{k + 2:02d}+0.2"{f" data-out=\"b{k + 3:02d}\"" if k < nb - 1 else ""}>{p["why"]}</div>'
        for k, p in enumerate(pairs))
    scenes = f"""
  <section class="scene" data-scene="s01">
    <div class="label yellow fade" data-at="b01">{item} · {lv}</div>
    <div class="prompt-l fade" data-at="b01">{ex["prompt"]}</div>
    <div class="row fade" data-at="b01+0.6" style="gap: 120px; align-items: center">
      <div class="col" style="gap: 20px">
{lefts}
      </div>
      <div class="col" style="gap: 20px">
{rlist}
      </div>
    </div>
  </section>

  <section class="scene" data-scene="s02">
    <div class="pairs">
{chr(10).join(rows)}
    </div>
    <div class="stack">
{whys}
    </div>
  </section>

  <section class="scene" data-scene="s03">
    <div class="label green fade" data-at="{b_ans}">Every pair</div>
    <div class="pairs fade" data-at="{b_ans}+0.2">
{chr(10).join(f'      <div class="side l">{choice_text(p["l"])}</div><div class="arrow">→</div><div class="side r glow c-green">{choice_text(p["r"])}</div>' for p in pairs)}
    </div>
    <div class="label muted fade" data-at="{b_ans}+1.5" style="font-size: 22px; font-weight: 500">This video uses an AI-generated voice.</div>
  </section>
"""
    return vid, script, page(f"{item} — step by step", unit_label(data), item, CHOICE_STYLE, scenes)


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
                "q": markup(ex.get("q", "")), "aria": plain(ex.get("q", "")).replace("^", " to the power of ")}
        # "find the value" and "expand": the student types the answer (docs/course-design.md)
        if ex["kind"] == "num":
            out.append({**base, "input": "num", "answer": str(ex["_answer"]), "aHtml": money(ex["_answer"]),
                        "mistakes": [{"v": str(w["_value"]), "why": w["why"]} for w in ex["wrong"]]})
            continue
        if ex["kind"] == "solve":
            out.append({**base, "input": "num", "answer": str(ex["_answer"]), "aHtml": markup(ex["lines"][-1]),
                        "mistakes": [{"v": str(w["_value"]), "why": w["why"]} for w in ex["wrong"]]})
            continue
        if ex["kind"] == "words":
            out.append({**base, "q": "", "input": "expr", "anyForm": True, "answer": plain_math(ex["a"]), "aHtml": markup(ex["a"]),
                        "mistakes": [{"e": plain_math(w["e"]), "why": w["why"]} for w in ex["wrong"]]})
            continue
        if ex["kind"] == "expr":
            out.append({**base, "input": "expr", "answer": plain_math(ex["a"]), "aHtml": markup(ex["a"]),
                        "mistakes": [{"e": plain_math(w["e"]), "why": w["why"]} for w in ex["wrong"]]})
            continue
        if ex["kind"] == "multi":
            out.append({**base, "q": "", "pick": "multi",
                        "options": [{"v": choice_text(o["t"]), "ok": bool(o["ok"]), "why": o["why"]} for o in ex["options"]]})
            continue
        if ex["kind"] == "match":
            rights = list(dict.fromkeys(p["r"] for p in ex["pairs"]))
            out.append({**base, "q": "", "pick": "match", "rights": [choice_text(r) for r in rights],
                        "pairs": [{"l": choice_text(p["l"]), "r": rights.index(p["r"]), "why": p["why"]} for p in ex["pairs"]]})
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
        if ex["kind"] in ("multi", "match"):
            if ex["kind"] == "multi":
                desc = "select all: " + ", ".join(o["t"] for o in ex["options"] if o["ok"])
            else:
                desc = "match: " + "; ".join(f"{p['l']} → {p['r']}" for p in ex["pairs"])
            print(f"  {ex['id']}  {ex['prompt'][:34]:<34} → {desc}")
            continue
        if ex["kind"] in ("num", "solve"):
            ans, wr = ex["_answer"], [w["_value"] for w in ex["wrong"]]
        elif ex["kind"] in ("expr", "words"):
            ans, wr = ex["a"], [w["e"] for w in ex["wrong"]]
        else:
            ans, wr = ex["a"], [w["a"] for w in ex["wrong"]]
        print(f"  {ex['id']}  {ex.get('q') or ex['prompt'][:34]:<34} → {str(ans):<16} wrong: " + ", ".join(str(w) for w in wr))
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
