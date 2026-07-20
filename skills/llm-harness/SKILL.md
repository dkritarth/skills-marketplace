---
name: llm-harness
version: 0.1.0
description: >
  Builds an evaluation harness around any LLM-dependent system (a prompt, a
  pipeline, an agent, an API integration): infers what the system is trying
  to do from its prompts and code, derives measurable success criteria,
  generates a golden + adversarial case set, wires a grader, and reports a
  baseline accuracy number you can iterate against. Use when changing a
  prompt or LLM pipeline and "it seems better" is the only measure, or when
  the user says "build a harness", "eval this prompt", or "measure accuracy".
  Do NOT use when the system already has an eval framework (extend that
  instead), or when success is genuinely unmeasurable prose taste with no
  reference answers — a harness needs a gradeable criterion.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# LLM-harness — build eval harnesses for LLM-dependent systems

## Why this exists / not X

`agent-skills:test-driven-development` and `mattpocock-skills:tdd` test
*deterministic code*; they have no answer for a component whose output varies
run to run. `deep-research`-style adversarial-verify patterns check *one
answer*, not a system's accuracy over a distribution of inputs. Nothing local
turns "here is my prompt/pipeline" into "here is a number that goes up when
you improve it". This skill is that missing piece: prompt changes stop being
vibes and start being measured. If the project already carries promptfoo,
Braintrust, LangSmith evals, or a bespoke eval suite, extend that — don't
build a parallel harness.

## Core loop

### 1. Infer intent

Read the system's prompts, tool definitions, and calling code. Write down,
and confirm with the user before building anything:

- **Task statement** — what the LLM step is supposed to produce, one
  sentence.
- **Input space** — what actually varies across calls (user text, retrieved
  docs, tool results).
- **Failure modes that matter** — what "wrong" looks like here
  (hallucinated fields, missed extraction, wrong label, unsafe action,
  format break). These drive the adversarial cases.

This step is the skill's namesake: the harness is derived from what the
system is *trying to do*, not from a generic eval template.

### 2. Pick the grading mode

Choose the cheapest mode that captures correctness; mixed suites are normal
(per-case `grader` field):

| Mode | When | Grader |
|------|------|--------|
| Exact / normalized match | Classification, extraction with one right answer | String/JSON compare after normalization |
| Programmatic assertion | Structured output, code, tool calls | Schema validation, unit-test-style checks, does-it-execute |
| Reference similarity | Free text with a gold answer | Embedding or rubric distance to reference |
| LLM-as-judge | Open-ended quality with a rubric | Judge prompt with a written rubric and 2–3 anchored score examples; judge model ≥ the tier of the system under test. Prefer a judge from a *different* provider family than the system under test (Claude judges a GPT/Codex pipeline and vice versa) — same-family judges share failure modes and inflate scores |

LLM-as-judge is the last resort, not the default — every judge is itself an
unvalidated LLM component. If used, spot-check ≥10 judge verdicts by hand
before trusting the aggregate number.

### 3. Build the case set

Target 30–50 cases minimum before the aggregate number means anything; say
so explicitly if shipping fewer.

- **Golden cases** — representative inputs with known-correct outputs.
  Mine them from real logs/fixtures first; synthesize only to fill gaps.
- **Adversarial cases** — one cluster per failure mode from step 1: edge
  inputs, ambiguous inputs, inputs engineered to trigger hallucination or
  format breaks, injection attempts if the system consumes untrusted text.
- **Held-out slice** — mark ~20% `"split": "holdout"`; iterate prompts
  against the rest, report both numbers to catch overfitting to the suite.

### 4. Wire and run

Scaffold under `harness/` in the target project (layout below), run the
full suite against the current system, and report:

- overall accuracy, dev vs. holdout;
- per-failure-mode breakdown (the actionable part — "misses negations"
  beats "87%");
- the 5 worst cases verbatim, for the next prompt iteration.

Run N=3 repetitions per case when the system is nondeterministic and report
variance; a 2-point "improvement" inside run-to-run noise is not an
improvement.

### 5. Iterate

Change the prompt/pipeline → rerun → compare against the stored baseline.
Refuse to declare a change an improvement without a harness delta.

## Harness layout (state)

Everything lives in the target project, versioned with it — nothing hidden:

```
harness/
├── README.md          # task statement, grading modes, how to run, baseline log
├── cases.jsonl        # one case per line: {id, input, expected, grader, split, failure_mode}
├── run.py             # loads cases, calls the system, grades, prints report
├── graders/           # one module per non-trivial grader (incl. judge prompts)
└── results/           # timestamped run outputs (gitignore if noisy)
```

Staleness: `run.py` records the git SHA of the system-under-test in each
result; a baseline whose SHA no longer matches the current prompt files is
flagged stale in the report, never silently compared.

## When to use

- Any prompt/pipeline change currently evaluated by eyeballing outputs.
- Before a model swap within a provider (does Haiku hold accuracy where
  Sonnet was used? gpt-5.1-codex-mini where gpt-5.1-codex was?) or across
  providers (Claude ↔ GPT/Codex) — the harness is provider-agnostic: it
  calls the system under test through whatever SDK/CLI that system already
  uses, so the same case set benchmarks any provider's model in the slot.
- Regression protection on an LLM feature that already works.

## When not to use

- An eval framework already exists in the project — extend it.
- No gradeable criterion exists even in principle — fix that first; a
  harness cannot grade what the owner cannot.
- One-off throwaway prompts not worth a suite.
