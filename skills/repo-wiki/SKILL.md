---
name: repo-wiki
version: 0.1.0
description: >
  Builds and maintains a GitHub wiki for a repository by distilling CLAUDE.md,
  README, AGENTS.md, docs/, and the code layout into structured wiki pages,
  then makes the wiki the first-read entry point for any agent exploring the
  codebase. Use when a repo has accumulated docs an agent must re-derive every
  session, when onboarding a new agent/person to an unfamiliar codebase, or
  when the user says "create a wiki", "update the wiki", or "document this
  repo as a wiki". Installs the first-read pointer in both CLAUDE.md (Claude
  Code) and AGENTS.md (Codex and other agents). Do NOT use for repos without
  a GitHub remote (no wiki backend exists), for single-file scripts, or as a
  replacement for CLAUDE.md/AGENTS.md — the wiki extends them, the pointer
  stays in-repo.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Repo-wiki — generate and maintain a GitHub wiki from repo docs

## Why this exists / not X

`/init` generates a single CLAUDE.md and stops; every later agent still
re-explores the tree to answer "how is this repo shaped, where do things
live, what are the conventions". GitHub wikis are a free, versioned,
browsable home for that knowledge, but nothing keeps them generated from —
and consistent with — the in-repo docs. This skill closes both gaps: it
*derives* the wiki from the repo's own documentation plus structure scan, and
it installs a first-read rule so exploration starts from the distilled wiki
instead of a cold tree walk. If a repo's docs are a single short README, this
skill adds nothing — skip it.

## How GitHub wikis work (mechanics)

A GitHub wiki is a separate git repo at `<repo-url>.wiki.git`. Pages are
markdown files at the wiki repo root; `Home.md` is the landing page;
filenames become page titles (`Architecture.md` → "Architecture"). The wiki
must be enabled once in the repo's GitHub settings (`gh repo edit
--enable-wiki` or the web UI), and the first page must exist before the
`.wiki.git` remote accepts clones — create `Home.md` via the web UI or
`gh api` if the clone 404s.

## Core loop

1. **Gather sources.** Read, in priority order: `CLAUDE.md`, `AGENTS.md`,
   `README.md`, everything under `docs/`, `PLAN.md`/`ARCHITECTURE.md` if
   present, plus a structure scan (top-two-level tree, package manifests,
   entry points). Sources are authoritative; the wiki never invents facts
   the repo doesn't state or show.
2. **Clone the wiki repo** into a temp dir: `git clone <repo-url>.wiki.git`.
   If it 404s, enable the wiki and seed `Home.md` first (see mechanics).
3. **Generate pages.** Standard set, omitting any page with nothing real to
   say:
   - `Home.md` — one-paragraph purpose, page index, and the freshness line
     (see State below).
   - `Architecture.md` — directory map, major components, how they connect.
   - `Setup.md` — install, build, test, run commands, verbatim from sources.
   - `Conventions.md` — coding/commit/testing conventions from
     CLAUDE.md/AGENTS.md.
   - `Subsystems/<name>.md` — one page per major subsystem when the repo is
     big enough to warrant it.
   Distill; don't mirror. A wiki page that copies README wholesale is noise —
   each page answers the questions an exploring agent actually asks.
4. **Stamp and push.** Add the source-SHA footer to every generated page
   (see State), commit to the wiki repo with a message naming the source
   commit, push.
5. **Install the first-read rule.** Add (or update) a short section in the
   repo's agent instruction files — `CLAUDE.md` for Claude Code AND
   `AGENTS.md` for Codex/other agents (create `AGENTS.md` with just this
   section if the repo lacks one; if both exist, keep the section identical
   in both):

   > ## Codebase wiki
   > Before exploring this codebase, read the wiki at `<repo-url>/wiki`
   > (clone: `<repo-url>.wiki.git`) — start at Home. It is generated from
   > this repo's docs at a stamped commit; if the stamp is older than files
   > you're touching, trust the repo and run `/repo-wiki` to refresh.

   This is what makes the wiki load-bearing: exploring agents read the
   distilled map first and fall back to tree-walking only for what the wiki
   doesn't cover.

## Staleness / refresh

On every invocation after the first, diff instead of regenerating blindly:
read each page's source-SHA footer, `git diff --stat <stamped-sha>..HEAD`
on the source repo, and regenerate only pages whose source files changed.
If the stamped SHA is unreachable (history rewritten), regenerate everything.

## When to use

- Repo has real accumulated documentation (CLAUDE.md + README + docs/) and
  agents or people keep re-deriving the same orientation.
- After a structural change big enough that the wiki's Architecture page is
  wrong.
- User asks for a wiki, onboarding docs, or "make agents stop re-exploring".

## When not to use

- No GitHub remote, or wiki deliberately disabled — there is nowhere to push.
- Tiny repos where README alone orients anyone in one read.
- As a CLAUDE.md replacement: CLAUDE.md stays the in-context instruction
  file; the wiki is the *extended* reference it points to.

## State

Two pieces, both visible and documented:

- **The wiki repo itself** (`<repo-url>.wiki.git`) — all generated pages.
  Every generated page ends with a footer line:
  `<!-- repo-wiki: generated from <source-repo> @ <commit-sha> on <date> -->`
  That stamp is the staleness detector: stamp older than the touched files ⇒
  page is suspect, repo wins, refresh via this skill.
- **The `## Codebase wiki` section in the source repo's CLAUDE.md and
  AGENTS.md** — the first-read pointer, duplicated so both Claude Code
  (reads CLAUDE.md) and Codex/other agents (read AGENTS.md) hit it. It is
  idempotently updated (replaced, not appended) in both files on each run.

No hidden state anywhere else.
