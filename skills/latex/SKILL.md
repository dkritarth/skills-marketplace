---
name: latex
version: 0.1.0
description: |
  Narrow-scoped LaTeX skill for three recurring pain points: compile-error
  log triage (points at the actual offending file and line, not a generic
  "check your syntax"), bib/citation hygiene (duplicate keys, missing
  required fields), and applying a venue-specific template. Use when a
  LaTeX document fails to compile and you have a log, when auditing a
  .bib file before submission, or when starting a new draft against a
  known venue. Not a general "explain LaTeX to me" helper — that ground is
  already covered by Overleaf's own AI features and other existing repos;
  don't ask this skill to teach LaTeX from scratch.
license: MIT
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob]
---

# LATEX

## Why this exists / not X

- No existing local skill covers LaTeX at all, so there's no in-repo
  overlap to avoid.
- **vs. `hameefy/claude-latex-skill`, `foogtil/claude-code-math-skills`**
  and similar (`research/prior-art-research.md` §7): those aim to be
  general-purpose LaTeX assistants. Per PLAN.md's decision, this skill
  deliberately does **not** try to be one — it's scoped to the concrete
  recurring pain points below, not a broad "ask me anything about LaTeX"
  tool. If a request falls outside compile-error triage, bib hygiene, or
  venue templating, treat it as out of scope rather than improvising a
  general answer.

## When to use

- A LaTeX compile failed and you have the `.log` (or can generate one) —
  triage it to a specific file/line instead of guessing.
- Auditing a `.bib` file for duplicate keys or missing required fields
  before submission.
- Starting a draft that needs to follow a specific venue's format.

## When not to use

- General "how does LaTeX work" / "explain this package" questions —
  answer those directly or point at existing docs; don't invoke this
  skill's machinery for them.
- Proof structure or mathematical rigor — that's the `math` skill.
- Prose clarity/voice — that's `academic-humanizer`, invoked by the
  `writing` skill.

## Core loop

1. **Compile-error triage.** Given a compile log, run:
   `scripts/parse_log.py <compile.log>`
   It walks the log tracking which source file is currently open (via the
   `(path.tex` / closing-paren bookkeeping LaTeX logs use — a heuristic,
   not a full TeX-engine parser) and pairs each `!`-prefixed error with its
   `l.<N>` line number, printing `<file>:<line>: <message>` plus a short
   hint for common error classes (undefined control sequence, missing `$`,
   undefined citation, file not found, unbalanced braces). Point the user
   at the actual file/line before speculating about causes.
2. **Bib hygiene.** Given a `.bib` file, run:
   `scripts/bib_lint.py <file.bib>`
   Reports duplicate keys and, per entry type, missing required fields
   (e.g. `article` needs `author`, `title`, `journal`, `year`). It's a
   hygiene linter, not a BibTeX-grammar validator — assumes reasonably
   well-formed syntax (one `@type{key,` per entry).
3. **Venue templates.** `templates/generic-article/main.tex` is a
   placeholder skeleton — **not yet a real venue template**. Per PLAN.md
   Phase 2, this skill isn't considered validated until it's been used
   against a real submission's actual venue template (NeurIPS, ACL, a
   specific journal, whichever is next). When that happens, add
   `templates/<venue>-<year>/` alongside the generic one and note in this
   file which venues have been tested for real, rather than just claimed.

## Explicitly out of scope

General LaTeX Q&A, proof rigor (→ `math`), prose editing (→
`academic-humanizer` via `writing`). Keep additions here scoped to compile
triage, bib hygiene, and templates — see AGENTS.md "What not to do" and
PLAN.md's `BIB` candidate note (split bib hygiene into its own skill only
if this one's scope grows past "narrow").

## Scripts

- `scripts/parse_log.py <compile.log>` — no dependencies beyond the Python
  standard library.
- `scripts/bib_lint.py <file.bib>` — no dependencies beyond the Python
  standard library.
