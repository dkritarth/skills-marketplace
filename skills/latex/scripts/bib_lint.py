#!/usr/bin/env python3
"""bib_lint.py <file.bib>

Citation/bib hygiene checks, no third-party dependencies:

- duplicate entry keys (same @key{...} defined more than once)
- missing required fields for the entry's type (author, title, year, plus
  the venue field for article/inproceedings/incollection)
- entries with no fields at all (likely a paste error)

This is a hygiene linter, not a full BibTeX-grammar parser: it uses a
regex-based entry scanner that assumes reasonably well-formed .bib syntax
(one `@type{key,` per entry, `field = {value}` or `field = "value"` pairs).
Deliberately narrow in scope per PLAN.md — it is not a general "explain
BibTeX" tool.
"""
import re
import sys

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL)
FIELD_RE = re.compile(r"(\w+)\s*=\s*[{\"]")

REQUIRED_FIELDS = {
    "article": {"author", "title", "journal", "year"},
    "inproceedings": {"author", "title", "booktitle", "year"},
    "incollection": {"author", "title", "booktitle", "year"},
    "book": {"author", "title", "publisher", "year"},
    "phdthesis": {"author", "title", "school", "year"},
    "mastersthesis": {"author", "title", "school", "year"},
    "techreport": {"author", "title", "institution", "year"},
    "misc": {"title"},
    "online": {"title"},
}


def parse_entries(text: str):
    entries = []
    for m in ENTRY_RE.finditer(text):
        entry_type = m.group(1).lower()
        key = m.group(2).strip()
        body = m.group(3)
        fields = {f.lower() for f in FIELD_RE.findall(body)}
        entries.append({"type": entry_type, "key": key, "fields": fields})
    return entries


def lint(entries):
    problems = []

    seen: dict[str, int] = {}
    for e in entries:
        seen[e["key"]] = seen.get(e["key"], 0) + 1
    for key, count in seen.items():
        if count > 1:
            problems.append(f"duplicate key '{key}' ({count} entries)")

    for e in entries:
        if not e["fields"]:
            problems.append(f"'{e['key']}' ({e['type']}): no fields parsed — check syntax")
            continue
        required = REQUIRED_FIELDS.get(e["type"])
        if required is None:
            continue  # unknown/uncommon entry type — don't guess requirements
        missing = required - e["fields"]
        if missing:
            problems.append(
                f"'{e['key']}' ({e['type']}): missing {', '.join(sorted(missing))}"
            )

    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <file.bib>", file=sys.stderr)
        return 1

    try:
        with open(argv[1], "r", errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read {argv[1]}: {e}", file=sys.stderr)
        return 1

    entries = parse_entries(text)
    if not entries:
        print("no entries parsed — check the file is a .bib and entries end with a line containing only '}'")
        return 1

    problems = lint(entries)
    print(f"parsed {len(entries)} entries")
    if not problems:
        print("no hygiene issues found")
        return 0

    for p in problems:
        print(f"- {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
