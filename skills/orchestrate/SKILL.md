---
name: orchestrate
version: 0.1.0
description: >
  Model-routing orchestration skill: classifies each unit of work into one of
  five provider-neutral difficulty tiers and spawns a subagent on the cheapest
  model that can do that tier reliably. Ships mappings for both Anthropic
  (Fable orchestrates only; Opus deep reasoning; Sonnet implementation; Haiku
  mechanical/bulk) and OpenAI Codex (gpt-5.1-codex-max / gpt-5.1-codex /
  gpt-5.1-codex-mini with matching reasoning-effort settings), and can route
  tiers cross-provider via the codex CLI. Use when a task decomposes into
  multiple delegable units, or when the user asks to "orchestrate", "route
  models", or "use the right model per task". Do NOT use for a single small
  task that one inline pass finishes faster than spawning any subagent, and do
  NOT use to bypass an explicit model or provider choice the user already
  made.
allowed-tools: Agent, Read, Grep, Glob, Bash
---

# Orchestrate — model-tier task routing

## Why this exists / not X

The stock `Agent` tool inherits the session model for every subagent, and the
`caveman:cavecrew` skill routes by *output compression*, not by *model
capability*. Nothing local decides "this subtask is mechanical, send it to
Haiku" versus "this subtask is a gnarly concurrency bug, send it to Opus".
This skill is that decision procedure: an explicit, auditable tier table so
delegation cost tracks task difficulty instead of defaulting everything to the
most expensive model. If a future harness ships native difficulty-based
routing, retire this skill.

## The five tiers

Tiers are **provider-neutral**: classify first, then map the tier to a model
via the provider table below. Classify every delegable unit of work into
exactly one tier before spawning anything. When a unit straddles two tiers,
split it until each piece sits in one.

| Tier | Name | What belongs here |
|------|------|-------------------|
| 0 | Orchestration | Decomposing the task, writing subagent prompts, sequencing/parallelizing, synthesizing results, final judgment on conflicting subagent outputs. Never spawned as a subagent — whatever model runs the main loop *is* the orchestrator. |
| 1 | Deep reasoning | Architecture and API design, hard debugging (race conditions, memory issues, heisenbugs), security analysis, algorithm design, adversarial verification of another agent's claim, anything where a wrong-but-plausible answer is expensive. |
| 2 | Standard implementation | Multi-file features against a clear spec, refactors with defined boundaries, writing tests for known behavior, ordinary code review, documentation of existing behavior. |
| 3 | Mechanical execution | Renames, formatting, boilerplate, applying a worked example to N more sites, single-file edits where the diff is fully specified in the prompt. |
| 4 | Bulk retrieval & classification | Fan-out file reads, "find every caller of X", summarizing many documents, labeling/classifying items against fixed criteria, extracting structured data. |

## Provider mapping

| Tier | Anthropic (Claude Code) | OpenAI (Codex) |
|------|------------------------|----------------|
| 0 | **fable** — the main loop; never a subagent | **gpt-5.1-codex-max**, reasoning effort `xhigh` — the main Codex session; never a spawned sub-task |
| 1 | **opus** | **gpt-5.1-codex-max**, reasoning effort `high` |
| 2 | **sonnet** | **gpt-5.1-codex**, reasoning effort `medium` |
| 3 | **haiku** | **gpt-5.1-codex-mini**, reasoning effort `low` |
| 4 | **haiku** | **gpt-5.1-codex-mini**, reasoning effort `low` (drop to `minimal` for pure retrieval/labeling) |

Two rules keep this table honest:

- **Model IDs drift.** Providers ship new families faster than this file
  updates. Before a session's first spawn on a provider, verify the IDs
  (`codex --help` / provider docs, or the `claude-api` skill for Anthropic);
  if a newer generation exists, substitute it at the same relative tier
  (max/full-size reasoning ↔ Tier 0–1, standard ↔ Tier 2, mini/small ↔
  Tier 3–4) and keep the tier semantics unchanged.
- **Same-tier equivalence, not mixing for taste.** Within one task, pick one
  provider per tier and stick to it, so escalation comparisons stay
  meaningful. Cross-provider escalation (e.g. Sonnet failed → try
  gpt-5.1-codex-max instead of Opus) is allowed only when the failure looks
  model-family-specific (refusal, format quirk), not merely difficulty.

## Spawn mechanics per harness

- **Claude Code (this harness):** `Agent(model: "haiku" | "sonnet" | "opus",
  ...)`. The `model` parameter only accepts Anthropic tiers here — Codex
  models cannot be passed to `Agent`.
- **Codex CLI as the harness:** run sub-tasks as
  `codex exec -m <model> -c model_reasoning_effort=<effort> "<prompt>"`,
  using the OpenAI column above.
- **Cross-provider from Claude Code:** route a tier to OpenAI by shelling
  out via Bash: `codex exec -m gpt-5.1-codex-mini "<prompt>"` (requires the
  `codex` CLI installed and authenticated; check `command -v codex` before
  planning any cross-provider routing, and fall back to the Anthropic column
  if absent). Useful for second-opinion verification (Tier 1 adversarial
  check by a different model family) and for cost routing when one
  provider's quota is exhausted.
- **Cross-provider from Codex:** symmetric — shell out to
  `claude -p --model <model> "<prompt>"` when a Claude-family opinion or
  capability is wanted.

## Classification procedure

For each unit, answer three questions in order; first hit wins:

1. **Is the answer fully specified in the prompt I can write?** (The subagent
   executes, it doesn't decide.) → Tier 3 if it edits, Tier 4 if it reads.
2. **Could a competent mid-level engineer do it from the spec without asking
   questions?** → Tier 2.
3. **Does correctness depend on reasoning the spec can't pin down —
   trade-offs, hidden interactions, adversarial cases?** → Tier 1.

If none hit, the unit is under-specified: that's Tier 0 work — decompose
further before delegating.

## Spawning rules

- Pass the tier's model explicitly using the mechanics for the current
  harness (see "Spawn mechanics per harness"). Never spawn the Tier 0 model
  as a subagent — orchestration stays in the main loop on every provider.
- Each subagent prompt must contain: the concrete deliverable, the file paths
  or inputs it needs (subagents start cold), and the return format. Tier 3/4
  prompts should be executable without judgment calls; if you can't write such
  a prompt, the unit isn't Tier 3/4.
- Parallelize units with no data dependency; sequence the rest.

## Escalation and demotion

- **Escalate one tier** when a subagent returns "unsure", contradicts itself,
  or its output fails your verification. Re-run the same unit one tier up
  (Tier 4/3 → 2 → 1, i.e. Haiku → Sonnet → Opus, or gpt-5.1-codex-mini →
  gpt-5.1-codex → gpt-5.1-codex-max), including the failed attempt in the new
  prompt as context. Never silently retry at the same tier more than once.
- **Verify asymmetrically:** Tier 1 outputs get an independent Tier 1
  adversarial check when stakes justify it; Tier 2 outputs get a Tier 0
  (inline) review; Tier 3/4 outputs get spot-checked mechanically (grep,
  tests, counts) — not with another LLM.
- **Demote next time:** if a tier-2 unit came back trivially correct and the
  next unit is of the same shape, route the next one Tier 3.

## When to use

- A task splits into 3+ delegable units of visibly different difficulty.
- Long sessions where context is precious and subagents keep the main loop
  clean.
- The user asks for model routing or cost-aware delegation explicitly.

## When not to use

- Single-unit tasks — inline work beats orchestration overhead.
- The user already pinned a model or provider ("do this with Opus", "use
  Codex for this") — respect it.
- Work where every unit is the same tier — just spawn them all at that tier;
  no classification pass needed.

## State

None. This skill is a pure decision procedure; it writes no files.
