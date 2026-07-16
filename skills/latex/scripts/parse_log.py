#!/usr/bin/env python3
"""parse_log.py <compile.log>

Triage a LaTeX compile log: walk it once, track which source file the
engine currently has open (via the `(path.tex` / closing `)` bookkeeping
LaTeX logs use), and pair every `!`-prefixed error with the `l.<N>` line
number that follows it, when present. Prints one line per error:

    <file>:<line>: <message>

File tracking is a heuristic (a simplified open/close-paren stack), not a
full TeX-engine-accurate parser — deeply nested \\input chains or engines
that don't balance parens exactly (rare, but happens with some packages)
can attribute an error to the wrong file. Good enough to point at "check
this file near this line" instead of "check your syntax somewhere."

No third-party dependencies.
"""
import re
import sys

FILE_OPEN_RE = re.compile(r"\(([^\s()]+\.(?:tex|sty|cls|cfg|def))")
LINE_RE = re.compile(r"^l\.(\d+)")

# Common LaTeX error message patterns worth calling out with a specific
# hint beyond "read the message" — kept small and honest rather than
# pretending to cover every package's custom errors.
HINTS = [
    (re.compile(r"Undefined control sequence"), "likely a missing \\usepackage or a typo'd command name"),
    (re.compile(r"Missing \$ inserted"), "math-mode characters (_, ^, or similar) used outside $...$"),
    (re.compile(r"Undefined citation"), "check the .bib key and that bibtex/biber ran after this compile"),
    (re.compile(r"Citation .* undefined"), "check the .bib key and that bibtex/biber ran after this compile"),
    (re.compile(r"File .* not found"), "check the file path/name and that the package or included file is present"),
    (re.compile(r"Package \S+ Error"), "package-specific error — read the package's own message above for detail"),
    (re.compile(r"Too many }"), "unbalanced braces — count { vs } around the reported line"),
    (re.compile(r"Emergency stop"), "fatal error upstream; fix the first reported error and recompile before chasing this one"),
]


def hint_for(message: str) -> str | None:
    for pattern, hint in HINTS:
        if pattern.search(message):
            return hint
    return None


def parse_log(text: str):
    lines = text.splitlines()
    file_stack: list[str] = []
    errors = []

    for i, line in enumerate(lines):
        # Track file-open events left to right (a real balanced-paren
        # scanner would also need to count plain ')' closes per character,
        # but TeX logs interleave enough noise that per-line char scanning
        # buys little extra accuracy for the added complexity here).
        for m in FILE_OPEN_RE.finditer(line):
            file_stack.append(m.group(1))
        closes = line.count(")")
        for _ in range(closes):
            if file_stack:
                file_stack.pop()

        if line.startswith("!"):
            message = line[1:].strip()
            lineno = None
            for j in range(i + 1, min(i + 6, len(lines))):
                m2 = LINE_RE.match(lines[j])
                if m2:
                    lineno = int(m2.group(1))
                    break
            errors.append(
                {
                    "file": file_stack[-1] if file_stack else "(unknown — check top-level .tex)",
                    "line": lineno,
                    "message": message,
                    "hint": hint_for(message),
                }
            )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <compile.log>", file=sys.stderr)
        return 1

    try:
        with open(argv[1], "r", errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read {argv[1]}: {e}", file=sys.stderr)
        return 1

    errors = parse_log(text)
    if not errors:
        print("no `!`-prefixed errors found in log")
        return 0

    for e in errors:
        loc = f"{e['file']}:{e['line'] if e['line'] is not None else '?'}"
        print(f"{loc}: {e['message']}")
        if e["hint"]:
            print(f"    hint: {e['hint']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
