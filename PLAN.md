# PLAN — Personal Skills Marketplace

## Problem statement

I write papers, proofs, and LaTeX documents with Claude Code regularly, and
the generic help it gives is shallow: it doesn't enforce LaTeX structure
beyond what any general-purpose assistant would, it has no memory of where a
paper draft is *headed* across revisions (only what the latest diff says),
and it doesn't hold proofs to a consistent rigor standard. I already
maintain two writing-adjacent skills (`academic-humanizer`,
`research-paper-writing`) in `~/.claude/skills/`, but neither tracks
draft-to-draft intent, and neither is LaTeX- or proof-specific. This project
packages a small, personally-curated set of fine-tuned skills — distributed
the same way I already distribute `caveman` and the other plugin
marketplaces — instead of scattering one-off skill folders.

Prior-art research (`research/prior-art-research.md`, section 7) found real,
functionally-overlapping competition for LaTeX-fine-tuning and prose-level
proof-rigor skills (e.g. `hameefy/claude-latex-skill`,
`foogtil/claude-code-math-skills`, `morankor/theorist-toolbox`), but found
**no existing implementation** of forward-looking revision-intent tracking
for paper drafts — every comparable tool (Narrative Version Control,
git-ai, academic-research-skills) is retrospective, summarizing past diffs
rather than inferring where a draft is going next. That gap is the reason
this project is worth building, and it changes how the three skills should
be prioritized.

## Decisions

### Distribution model — decision: personal marketplace repo

Follow the existing `~/.claude/plugins/marketplaces/<name>/` pattern
(`caveman`, `addy-agent-skills`, `anthropic-agent-skills`) rather than
standalone per-skill repos. Reasons:

- **Consistency with existing tooling.** `settings.json` already has
  `extraKnownMarketplaces` and `enabledPlugins` wired up; adding one more
  marketplace entry is a one-line change, versus registering N standalone
  skill repos individually (`skills/anthropics-skills`-style submodules
  require manual `SKILL.md` discovery per repo, marketplaces don't).
- **Single install surface.** One `marketplace.json` at the root lists all
  three (soon four+) skills as plugins with `source: "./skills/<name>"`.
  A future machine setup clones one repo and enables one marketplace,
  instead of tracking a growing list of git remotes.
- **Shared versioning and changelog.** Skills that reuse the same journal
  mechanism (see WRITING below) benefit from being versioned together —
  a fix to the journal format should land in LATEX/WRITING/MATH at once,
  which a shared repo makes trivial and separate repos make painful.
- **Standalone repos would only win** if a skill needed independent
  external contributors, its own issue tracker, or public visibility
  distinct from the rest — none of that applies here; this is a personal,
  curated set.

Concretely: this repo becomes
`skills-marketplace/` with `.claude-plugin/marketplace.json` at the root,
one plugin per skill, each in `skills/<name>/SKILL.md` — mirroring
`caveman`'s layout, not `anthropics-skills`' flat submodule layout (no need
for the submodule indirection since I author these directly).

### Overlap with existing skills — decision per skill

- **WRITING vs. `academic-humanizer` / `research-paper-writing`: build
  fresh, do not extend.** Both existing skills are single-pass style/clarity
  editors — they take a manuscript as it is *now* and improve its prose.
  WRITING's job (tracking modification history and inferring future intent
  across drafts) is a different axis entirely: it needs persistent state
  across sessions (a journal), not just a one-shot edit pass. Bolting that
  onto `academic-humanizer` would turn a stateless, single-responsibility
  skill into a stateful one and break its "never changes voice without a
  full pass" contract. Instead, WRITING should **invoke**
  `academic-humanizer` as a downstream step (once intent is captured, hand
  the prose polish to the existing skill) rather than reimplement clarity
  editing. Net: WRITING is new; it composes with, but does not replace,
  the two existing skills.
- **LATEX: build fresh, scoped narrow.** No existing local skill covers
  LaTeX. Given prior art already covers generic "fine-tuned LaTeX assistant"
  ground closely (hameefy, foogtil), this skill should not try to be a
  general LaTeX helper — scope it to the concrete recurring pain points I
  actually hit (journal/venue-specific templates, compile-error triage,
  citation/bib hygiene) rather than reproducing a broad assistant.
- **MATH: build fresh, but only if it adds the formal-verification angle.**
  Prose-level "enforce a Proposition/Proof template" is already shipped
  elsewhere (`foogtil/claude-code-math-skills`, `theorist-toolbox`). Per the
  research verdict, MATH is only worth shipping as a distinct skill if it
  round-trips through an actual checker (SymPy for symbolic/numeric claims,
  optionally Lean for formalizable statements) rather than templating prose
  rigor. If that verification step isn't built, fold MATH's remaining value
  (proof structure, exposition ordering) into LATEX as a template rather
  than maintaining a third skill nobody differentiates on.

### What WRITING's modification/intent tracking concretely requires

Mechanism: **one journal file per draft, append-only, read by the skill on
every invocation, backed by git for the raw diffs.**

- `<draft-root>/.writing-journal.md` — a single append-only markdown file
  living next to the manuscript (not in `~/.claude`, so it travels with the
  paper's own repo/folder). Each entry, written by the skill at the end of
  a session, has a fixed shape:
  - date/session marker
  - **what changed** (one-line summary of the substantive edit, not a diff
    dump — the diff itself lives in git)
  - **why** (the user's stated or inferred reason: reviewer comment,
    new result, restructuring for clarity, etc.)
  - **stated direction** (what the user said or implied comes next — new
    section, tightened claim, a result still pending)
- On invocation, the skill reads the *entire* journal (it's small, append-
  only prose, not a full diff corpus) plus `git log -p` for the manuscript
  path to reconcile stated intent against actual changes, and produces a
  short "where this draft is heading" brief before doing any edit. This
  brief is what distinguishes WRITING from a stateless editor: it is the
  artifact that lets the skill say "you said in session 3 you'd tighten the
  related-work section before adding the ablation — do you still want to
  do that first?"
  - Rationale for journal + git rather than git history alone: git commit
    messages capture *what* changed but rarely *why* or *toward what*, and
    manuscripts are frequently not committed atomically (drafts get pasted
    around, edited outside git, saved as new files) — a dedicated journal
    is a forcing function to capture intent that commit metadata won't
    reliably contain.
  - The journal is plain markdown so it's diffable, human-readable without
    the skill, and portable if the manuscript later moves to a different
    tool.
- Failure mode to design against: journal drift (journal says one thing,
  manuscript went somewhere else). The skill's brief-generation step must
  explicitly flag contradictions rather than silently trusting the journal.

## Skill-by-skill spec sketch

### WRITING (flagship, build first)
- **Input:** manuscript path/repo, `.writing-journal.md` (created on first
  run if absent), git history for that path.
- **Core loop:** read journal + git log → produce "current state vs. stated
  direction" brief → surface contradictions/staleness → let user confirm or
  redirect → make edits (delegating prose polish to `academic-humanizer`
  where applicable) → append a new journal entry summarizing the session's
  change and updated direction.
- **Explicitly out of scope:** clarity/voice editing itself (delegate),
  citation formatting (delegate to LATEX), proof correctness (delegate to
  MATH).
- **Differentiator to protect:** the forward-looking brief. If this skill
  ships without it, it's just another retrospective diff-summarizer and the
  whole rationale for building it (per prior-art verdict) disappears.

### LATEX (build second, scoped narrow)
- **Input:** `.tex` source tree, target venue/journal (if known).
- **Core loop:** venue-specific template application, compile-error triage
  (parse the log, point at the actual offending line/package, not a generic
  "check your syntax"), citation/bib hygiene (duplicate keys, missing
  fields, consistent style).
- **Explicitly out of scope:** general "explain LaTeX to me" help
  (Overleaf's shipped AI features and multiple existing repos already cover
  that baseline); don't reproduce it.

### MATH (build third, conditional)
- **Input:** a proof or proof sketch in prose or LaTeX.
- **Core loop:** structure enforcement (claim → assumptions → proof →
  where it's used) *plus* a verification pass — SymPy for symbolic/
  numeric sub-claims, flag (don't force) candidates for Lean
  formalization.
- **Ship condition:** do not ship MATH as a standalone skill unless the
  verification round-trip is actually implemented — a template-only version
  duplicates existing prior art with no wedge. If verification isn't ready
  by the phase-2 milestone, fold structure-only guidance into LATEX as a
  proof-environment template instead.

### Candidate additions (not yet scoped, TBD)
- **REVIEW** — apply the WRITING journal's "stated direction" concept in
  reverse: given a reviewer's comments on a submitted draft, map each
  comment to the journal history to check whether it was already
  considered and rejected for a stated reason (avoids re-litigating a
  decision already made deliberately).
- **BIB** — a citation-hygiene-only slice split out of LATEX if that scope
  grows too large to stay "narrow" (dedup keys, verify DOIs resolve, flag
  retracted papers). Candidate only; fold into LATEX unless it proves it
  needs to be separate.

## Phased milestones

1. **Phase 0 — scaffolding.** Marketplace repo structure
   (`.claude-plugin/marketplace.json`, `skills/<name>/SKILL.md` stubs),
   register the marketplace in `~/.claude/settings.json`
   `extraKnownMarketplaces`/`enabledPlugins`. No behavior yet.
2. **Phase 1 — WRITING v0.** Journal file format finalized, read/write
   loop working, forward-looking brief generation working on at least one
   real in-progress draft of mine. This is the differentiator; it ships
   before LATEX or MATH get real effort.
3. **Phase 2 — LATEX v0.** Compile-error triage + one real venue template
   (whichever I'm submitting to next), tested against a real document.
4. **Phase 3 — MATH v0, conditional.** Only if SymPy verification
   round-trip is feasible in scope; otherwise fold into LATEX per the
   ship condition above and revisit later.
5. **Phase 4 — candidates.** Evaluate REVIEW/BIB against real usage of
   phases 1–3 before building either.

## Success criteria

- WRITING's forward-looking brief catches at least one real case where I
  drifted from a previously stated direction without noticing, on an
  actual draft (not a synthetic test).
- Each shipped skill has a documented reason it isn't redundant with an
  existing local skill or a specific competing repo named in the prior-art
  research (see AGENTS.md conventions for where this lives in each
  `SKILL.md`).
- Marketplace installs cleanly via the same mechanism as `caveman` (add to
  `extraKnownMarketplaces`, enable plugin, restart) with no manual
  `SKILL.md` copying.
- MATH does not ship as a standalone plugin unless it clears the
  verification-round-trip bar above.

## Risks

- **Scope creep on LATEX/MATH** re-building things that already exist
  (explicitly the risk the prior-art research flagged) — mitigated by the
  narrow-scope and ship-condition rules above.
- **Journal becomes another thing to maintain and abandon**, like many
  personal-productivity meta-tools — mitigated by keeping it append-only
  and auto-written by the skill itself, not a manual chore.
- **Journal/git drift** (journal claims a direction the actual diffs
  contradict) silently misleading future sessions — mitigated by the
  explicit contradiction-flagging requirement in the WRITING spec above.
- **Single-user validation only.** All three skills are tuned to my own
  writing/proof habits; success criteria are deliberately anchored to real
  personal usage rather than general-purpose benchmarks, so "it works" is
  necessarily subjective. Acceptable for a personal marketplace, but means
  this isn't a project to over-invest in generalizing prematurely.
