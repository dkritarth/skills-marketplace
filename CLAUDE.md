# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this is

A personal Claude Code plugin marketplace of fine-tuned skills (LATEX,
WRITING, MATH, more TBD). See `PLAN.md` for the finalized concept —
problem statement, distribution-model decision, per-skill overlap
decisions, the WRITING journal mechanism, phased milestones, and success
criteria. See `AGENTS.md` for `SKILL.md` conventions, structure, and
testing workflow; follow it when adding or editing a skill.

## Structure

```
skills-marketplace/
├── .claude-plugin/marketplace.json   # marketplace manifest, one plugin per skill
├── skills/<name>/SKILL.md            # one folder per skill
├── PLAN.md                           # concept, decisions, specs, milestones
├── AGENTS.md                         # conventions for editing/adding skills
└── README.md                         # short pointer + status
```

## Workflow

- Building a new skill or changing an existing one: read `PLAN.md`'s spec
  sketch for that skill first, then follow `AGENTS.md`'s `SKILL.md`
  conventions and testing steps.
- Registering the marketplace locally: add an entry to
  `extraKnownMarketplaces` and `enabledPlugins` in
  `~/.claude/settings.local.json` while iterating (not the synced
  `settings.json`) — see AGENTS.md "How to test a skill".
- Follow the phase order in PLAN.md (WRITING first — it's the
  differentiator — then LATEX, then MATH conditionally, then candidate
  additions). Don't jump ahead to LATEX/MATH polish before WRITING's
  forward-looking brief actually works on a real draft.
- Keep prior-art awareness current: if `research/prior-art-research.md`
  gets updated with new competing repos, revisit each skill's "why this
  exists" note in its `SKILL.md`.

## Commands

Most of each skill is markdown + prompts, validated by running them against
real artifacts per `AGENTS.md`. Two skills now also carry real scripts:

- `writing`: `skills/writing/scripts/{init_journal,gather_context,append_entry}.sh`
  — dependency-free bash (needs `git`). No install step.
- `latex`: `skills/latex/scripts/{parse_log,bib_lint}.py` — Python stdlib
  only, no install step.
- `math`: `skills/math/scripts/sympy_verify.py` — requires `sympy`
  (`pip install sympy`; a venv is recommended). This is the script behind
  MATH's ship condition (see PLAN.md and `skills/math/SKILL.md`); it exits
  with a clear error if `sympy` isn't installed rather than silently
  no-op'ing.

No shared build system across skills yet — each script is invoked directly
via `Bash` from within the skill's instructions.
