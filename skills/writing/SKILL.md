---
name: writing
version: 0.1.0
description: |
  Paper-writing skill for resuming an in-progress manuscript or proof draft
  across sessions. Tracks modification history via a per-draft journal file
  (`.writing-journal.md`) backed by git, and infers the draft's forward
  trajectory — where it's headed next — rather than only summarizing past
  diffs. Use at the start of a session on a multi-session draft, before
  making edits, to get a "current state vs. stated direction" brief and to
  catch drift from a previously stated plan. Not for one-shot prose polish
  (delegate to academic-humanizer), not for generating a first draft from
  nothing, and not for single-session documents with no revision history to
  track.
license: MIT
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion]
---

# WRITING

The flagship skill in this marketplace. Its entire reason to exist is the
forward-looking brief described below — if that step is ever skipped, this
skill degrades into a plain diff summarizer and should be treated as
broken, not just incomplete.

## Why this exists / not X

- **vs. `academic-humanizer`, `research-paper-writing`** (`~/.claude/skills/`):
  both are stateless, single-pass prose editors — they take the manuscript
  as it is *now* and improve clarity/voice. Neither has memory across
  sessions. WRITING's job is a different axis: persistent intent-tracking
  across revisions via a journal. WRITING **composes with** `academic-humanizer`
  as a downstream step (once intent is captured and edits are made, hand the
  clarity pass to it) — it does not reimplement prose editing, and
  `academic-humanizer` is not extended to do journaling (see AGENTS.md "What
  not to do").
- **vs. Narrative Version Control, git-ai, academic-research-skills**
  (`research/prior-art-research.md` §7): every one of these is
  *retrospective* — they summarize diffs that already happened. None of them
  infer where a draft is going next. WRITING is forward-looking: it
  reconciles a journal's stated intent against actual git changes and
  produces a brief about the draft's trajectory, explicitly flagging
  contradictions between what was said and what happened.
- **Differentiator to protect:** step 3 of the core loop below ("produce the
  brief"). A version of this skill that only writes journal entries but
  never reads them back to challenge the user is not this skill.

## When to use

- Resuming work on a manuscript, proof, or grant draft that has at least one
  prior WRITING session (a `.writing-journal.md` already exists), or is
  starting its first tracked session and will accumulate history going
  forward.
- Any time you're about to make a substantive edit to a multi-session draft
  and want to know whether the edit matches what was previously planned.

## When not to use

- Pure prose/clarity editing with no interest in tracking direction — use
  `academic-humanizer` directly.
- Generating a first draft from an outline or from nothing — there's no
  history to track yet; write the draft, then start using WRITING from the
  next session on.
- Single-session, throwaway documents (a quick abstract, an email) — the
  journal overhead isn't worth it.

## Persistent state: `.writing-journal.md`

- **Location:** `<draft-root>/.writing-journal.md`, next to the manuscript
  itself (not under `~/.claude`), so it travels with the paper's own
  repo/folder and survives the manuscript moving between machines.
- **Format:** append-only markdown. A short header (written once, by
  `scripts/init_journal.sh`) followed by one entry per session. Entry shape
  is fixed — see `reference/journal-entry-template.md`:
  - an ISO-8601 UTC timestamp heading
  - **what changed** — one-line summary of the substantive edit, not a diff
    dump (the diff lives in git)
  - **why** — the user's stated or inferred reason
  - **stated direction** — what comes next, concrete enough to check against
    later
- **Never edit past entries** except to correct a factual error, and note
  the correction as a new entry rather than silently rewriting history — the
  journal's value depends on it being an honest record of what was actually
  said at the time.
- **Staleness / drift detection:** on every invocation, compare the most
  recent entry's "stated direction" against what `git log -p` shows actually
  happened since that entry's timestamp. Three outcomes:
  1. **Aligned** — the latest changes match the stated direction. Say so
     briefly and move on.
  2. **Drifted** — the changes went somewhere the last entry didn't mention.
     Surface this explicitly before doing any new edit: "Session on
     `<date>` said you'd tighten related work next; the diffs since then
     touch the experiments section instead — intentional pivot, or did this
     slip?" Let the user confirm or correct; don't silently accept either
     story.
  3. **No signal** — manuscript isn't in git, or no commits touch it since
     the last entry (edited outside git, pasted around, etc.). Say so
     explicitly rather than presenting a confident-sounding brief built on
     nothing; treat this as a drift risk, not a clean "aligned" result.

## Core loop

1. **Locate the draft root and journal.** The draft root is the directory
   containing the manuscript file. If `.writing-journal.md` doesn't exist
   yet, this is the first tracked session: run
   `scripts/init_journal.sh <draft-root>` to create it, and skip the brief
   (there's no history yet) — just note that tracking starts now.
2. **Gather context.** Run
   `scripts/gather_context.sh <manuscript-path> [n-commits]`. This prints
   the full journal plus `git log -p` for the manuscript, in one read-only
   pass. Default is the last 20 commits touching the file; widen it if the
   journal references sessions further back than that.
3. **Produce the "current state vs. stated direction" brief.** Read the
   journal's last 1-3 entries and the git log output together. State, in a
   few sentences: what the last session(s) said would happen next, what
   actually happened per the diffs, and whether they match (see drift
   outcomes above). This step happens *before* any edit — it's the whole
   point of the skill.
4. **Surface contradictions and let the user confirm or redirect.** If
   drifted, ask explicitly (use `AskUserQuestion` when a clear choice is
   available) whether to continue the new direction, return to the
   previously stated one, or something else. Don't proceed on an assumption.
5. **Make the edits.** Do the actual writing/restructuring work the user
   asked for. Delegate specific concerns rather than reimplementing them:
   - prose clarity/voice → `academic-humanizer`
   - citation/bib formatting, compile issues → the `latex` skill in this
     marketplace
   - proof correctness/rigor → the `math` skill in this marketplace
6. **Append a new journal entry.** At the end of the session, run
   `scripts/append_entry.sh <draft-root> "<what>" "<why>" "<direction>"`
   (or write the entry manually following
   `reference/journal-entry-template.md` via `Edit`) summarizing this
   session's actual change, its reason, and — critically — what comes next.
   A vague "stated direction" here degrades every future session's brief;
   push for something checkable.

## Scripts

All three live in `scripts/` and are plain, dependency-free bash — no
runtime beyond `git` and coreutils.

- `init_journal.sh <draft-root>` — idempotent; creates the journal with its
  header if absent, no-ops otherwise.
- `gather_context.sh <manuscript-path> [n-commits]` — read-only; prints the
  journal and `git log -p` for the manuscript in one pass. Explicitly flags
  when the manuscript isn't tracked in git or has no matching commits, since
  that's the drift-risk case the brief step must call out.
- `append_entry.sh <draft-root> <what> <why> <direction>` — appends one
  fixed-shape entry; fails loudly (rather than silently no-op) if the
  journal doesn't exist yet, so a session can't skip journaling by accident.
