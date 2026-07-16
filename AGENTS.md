# AGENTS.md

Instructions for AI coding agents working in this repo.

## Purpose

This repo is a personal Claude Code plugin marketplace: a small, curated
set of fine-tuned skills (LATEX, WRITING, MATH, and future additions) that
I install the same way I install `caveman` and other plugin marketplaces in
`~/.claude`. See `PLAN.md` for the finalized concept, rationale, and
skill-by-skill specs — read it before making structural changes.

## Structure

```
skills-marketplace/
├── .claude-plugin/
│   └── marketplace.json      # lists each skill as a plugin, source: "./skills/<name>"
├── skills/
│   ├── latex/SKILL.md
│   ├── writing/SKILL.md
│   ├── math/SKILL.md
│   └── <future-skill>/SKILL.md
├── PLAN.md
├── AGENTS.md                 # this file
├── CLAUDE.md
└── README.md
```

Mirror `~/.claude/plugins/marketplaces/caveman`'s layout, not a flat
submodule layout — each skill lives directly in this repo, not as a git
submodule.

## SKILL.md conventions

Every `SKILL.md` needs:
- YAML frontmatter: `name`, `version` (semver), `description` (states when
  to use it and, crucially, when *not* to — see `academic-humanizer` in
  `~/.claude/skills/` for the reference style), `allowed-tools`.
- A short "why this exists / not X" note pointing at the specific
  overlapping skill or competing repo named in
  `research/prior-art-research.md` §7, and stating the differentiator. If a
  skill can't state one, it shouldn't exist yet — fold it into another
  skill instead (see PLAN.md's ship conditions).
- A `## When to use` / `## When not to use` pair, not just a feature list.
- Any persistent state a skill introduces (e.g. WRITING's
  `.writing-journal.md`) must be documented: where the file lives, its
  format, and how staleness/drift is detected. Never invent silent state.

## How to test a skill

1. Enable the marketplace locally (`extraKnownMarketplaces` +
   `enabledPlugins` in `~/.claude/settings.local.json`, not the synced
   `settings.json`, while iterating) and restart Claude Code.
2. Run the skill against a **real** artifact of mine (an actual paper
   draft, `.tex` file, or proof) — not a synthetic fixture. Success
   criteria in PLAN.md are anchored to real usage; synthetic tests won't
   surface the failure modes that matter (journal drift, wrong template
   choice, false-positive rigor flags).
3. For WRITING specifically: verify the journal entry it appends is
   accurate against what actually changed (diff the manuscript against
   git), and verify it flags a contradiction if you deliberately go against
   a previously stated direction.
4. Only promote a skill from `settings.local.json` to the committed
   `settings.json`/this repo's default-enabled state once it has passed
   a real-usage test, not just a smoke test.

## What not to do

- Do not extend `academic-humanizer` or `research-paper-writing` in
  `~/.claude/skills/` to add journal/intent-tracking — WRITING is
  deliberately a separate, stateful skill that composes with them (see
  PLAN.md). Don't merge the two.
- Do not ship MATH as a standalone plugin without the SymPy/Lean
  verification round-trip — a template-only rigor checker duplicates
  existing prior art with no wedge (see PLAN.md ship condition).
- Do not build a broad, generic LaTeX helper — that ground is already
  covered by shipped tools (Overleaf AI, several GitHub repos). Keep LATEX
  scoped to real recurring pain points.
- Do not touch files outside `skills-marketplace/` from this repo's
  context.
- Do not commit changes to the user's global `~/.claude/settings.json`
  from within this repo — marketplace registration there is a manual,
  separate step the user does themselves.
