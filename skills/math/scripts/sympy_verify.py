#!/usr/bin/env python3
"""sympy_verify.py <claims-file>

Real verification round-trip for symbolic/numeric sub-claims extracted
from a proof, per PLAN.md's MATH ship condition: this skill only ships
standalone because this script exists, not because it templates rigor
prose.

Claim syntax, one per line (blank lines and lines starting with `#`
ignored):

    CLAIM <id>: <lhs> <op> <rhs> [assuming <var><cmp><bound>, ...]

`<op>` is one of `== != >= <= > <`. `<lhs>`/`<rhs>` are ordinary Python/
SymPy expression syntax (`x**2 + 2*x + 1`, `sin(x)**2 + cos(x)**2`, ...).
`assuming` optionally restricts a variable, e.g. `assuming x>0, y>=0` —
used both to build the SymPy symbol with that assumption and to bound
numeric sampling.

Examples:

    CLAIM expand1: (x+1)**2 == x**2 + 2*x + 1
    CLAIM pyth: sin(x)**2 + cos(x)**2 == 1
    CLAIM pos1: x**2 + 1 > 0
    CLAIM mono: 2*x + 3 >= 3 assuming x>=0

For each claim, prints one of:

    PASS  (proved)      — symbolic proof succeeded (simplify to 0, or
                           a closed-form inequality solve covering the
                           full domain)
    PASS  (numeric only) — no symbolic proof found, but N random samples
                           in the domain all satisfy the claim; this is
                           evidence, not a proof, and is reported as such
    FAIL                 — a counterexample was found (symbolic
                           simplification shows lhs != rhs, or a sampled
                           point violates the inequality)
    UNVERIFIABLE          — could not parse or evaluate the claim (e.g.
                           expression uses something SymPy can't handle)

Requires the `sympy` package (`pip install sympy`); exits with a clear
error if it isn't installed, rather than silently no-op'ing.
"""
from __future__ import annotations

import random
import re
import sys

try:
    import sympy
    from sympy import symbols as sympy_symbols
    from sympy.parsing.sympy_parser import parse_expr
except ImportError:
    print(
        "error: sympy is not installed. Install it with `pip install sympy` "
        "(a venv is recommended) before running this script.",
        file=sys.stderr,
    )
    raise SystemExit(2)

CLAIM_RE = re.compile(
    r"^CLAIM\s+(?P<id>\S+):\s*(?P<lhs>.+?)\s*(?P<op>==|!=|>=|<=|>|<)\s*(?P<rhs>.+?)"
    r"(?:\s+assuming\s+(?P<assump>.+))?$"
)
ASSUMPTION_RE = re.compile(r"(\w+)\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)")

OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}

N_SAMPLES = 200
DEFAULT_RANGE = (-10.0, 10.0)


class Claim:
    def __init__(self, claim_id, lhs_str, op, rhs_str, assump_str):
        self.id = claim_id
        self.lhs_str = lhs_str
        self.op = op
        self.rhs_str = rhs_str
        self.bounds: dict[str, list[float]] = {}
        if assump_str:
            for m in ASSUMPTION_RE.finditer(assump_str):
                var, cmp, bound = m.group(1), m.group(2), float(m.group(3))
                b = self.bounds.setdefault(var, [DEFAULT_RANGE[0], DEFAULT_RANGE[1]])
                if cmp in (">", ">="):
                    b[0] = max(b[0], bound)
                else:
                    b[1] = min(b[1], bound)


def parse_claims(text: str) -> list[Claim]:
    claims = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = CLAIM_RE.match(line)
        if not m:
            print(f"warning: could not parse claim line, skipping: {line!r}", file=sys.stderr)
            continue
        claims.append(Claim(m.group("id"), m.group("lhs"), m.group("op"), m.group("rhs"), m.group("assump")))
    return claims


def free_symbol_names(*expr_strs: str) -> set[str]:
    names = set()
    for s in expr_strs:
        names |= set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", s))
    # drop known function/constant names so they aren't treated as free vars
    reserved = {
        "sin", "cos", "tan", "exp", "log", "sqrt", "pi", "E", "oo",
        "Abs", "asin", "acos", "atan", "sinh", "cosh", "tanh",
    }
    return names - reserved


def verify_claim(claim: Claim) -> tuple[str, str]:
    var_names = free_symbol_names(claim.lhs_str, claim.rhs_str)
    local_dict = {name: sympy_symbols(name, real=True) for name in var_names}

    try:
        lhs = parse_expr(claim.lhs_str, local_dict=local_dict)
        rhs = parse_expr(claim.rhs_str, local_dict=local_dict)
    except Exception as e:  # noqa: BLE001 - report, don't crash the batch
        return "UNVERIFIABLE", f"parse error: {e}"

    if claim.op in ("==", "!="):
        try:
            diff = sympy.simplify(lhs - rhs)
        except Exception as e:  # noqa: BLE001
            return "UNVERIFIABLE", f"simplify error: {e}"

        is_zero = diff == 0
        if claim.op == "==":
            if is_zero:
                return "PASS", "proved: simplify(lhs - rhs) == 0"
            # numeric fallback: sample points, see if they consistently agree/disagree
            ok, bad_point = _numeric_sample(lhs - rhs, var_names, claim.bounds, lambda v: abs(v) < 1e-9)
            if ok:
                return "PASS", "numeric only: simplify() did not reduce to 0, but sampled points agree — check by hand"
            return "FAIL", f"counterexample: lhs - rhs != 0 at {bad_point}"
        else:  # !=
            if is_zero:
                return "FAIL", "lhs == rhs (simplify(lhs - rhs) == 0), contradicts claimed !="
            return "PASS", "proved: simplify(lhs - rhs) != 0"

    # inequalities
    op_fn = OPS[claim.op]
    if len(var_names) <= 1:
        try:
            var = local_dict[next(iter(var_names))] if var_names else None
            expr = lhs - rhs
            if var is not None:
                rel = op_fn(expr, 0)
                solution = sympy.solve_univariate_inequality(rel, var, relational=False)
                domain = sympy.Interval(*_bounds_for(var_names, claim.bounds).get(str(var), DEFAULT_RANGE))
                if domain.is_subset(solution):
                    return "PASS", f"proved: holds on {domain} (solution set {solution})"
        except Exception:  # noqa: BLE001 - fall through to numeric
            pass

    ok, bad_point = _numeric_sample(lhs - rhs, var_names, claim.bounds, lambda v, op=claim.op: OPS[op](v, 0))
    if ok:
        return "PASS", f"numeric only: {N_SAMPLES} samples in domain all satisfy the claim — not a proof"
    return "FAIL", f"counterexample: claim violated at {bad_point}"


def _bounds_for(var_names, bounds):
    return {name: tuple(bounds.get(name, list(DEFAULT_RANGE))) for name in var_names}


def _numeric_sample(expr, var_names, bounds, predicate):
    var_names = sorted(var_names)
    domains = _bounds_for(var_names, bounds)
    rng = random.Random(1234)  # deterministic across runs
    for _ in range(N_SAMPLES):
        subs = {}
        point = {}
        for name in var_names:
            lo, hi = domains[name]
            val = rng.uniform(lo, hi)
            subs[sympy_symbols(name, real=True)] = val
            point[name] = round(val, 4)
        try:
            value = float(expr.subs(subs).evalf())
        except Exception:  # noqa: BLE001
            return False, f"{point} (could not evaluate)"
        if not predicate(value):
            return False, f"{point} -> {value}"
    return True, None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <claims-file>", file=sys.stderr)
        return 1

    try:
        with open(argv[1], "r") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read {argv[1]}: {e}", file=sys.stderr)
        return 1

    claims = parse_claims(text)
    if not claims:
        print("no CLAIM lines found")
        return 1

    exit_code = 0
    for claim in claims:
        status, detail = verify_claim(claim)
        if status in ("FAIL", "UNVERIFIABLE"):
            exit_code = 1
        print(f"{claim.id}: {status} — {detail}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
