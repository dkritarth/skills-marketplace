---
name: math
version: 0.1.0
description: |
  Proof structure enforcement (Claim -> Assumptions -> Proof -> Where used)
  plus a real SymPy verification round-trip for symbolic and numeric
  sub-claims extracted from a proof (equalities, inequalities), with
  candidates for Lean formalization flagged, not forced. Use when reviewing
  or drafting a proof or proof sketch and you want its algebraic sub-claims
  actually checked, not just its prose structure tidied. Not for informal
  arguments with no checkable symbolic content, and not a replacement for
  Lean/Coq when a claim genuinely needs full formal verification — it flags
  those cases rather than attempting them.
license: MIT
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob]
---

# MATH

## Why this exists / not X, and the ship condition

Per PLAN.md, MATH is only worth shipping as a distinct skill if it
round-trips through an actual checker rather than templating proof rigor
in prose — otherwise its remaining value (structure, exposition order)
should fold into `latex` as a template. This skill clears that bar because
`scripts/sympy_verify.py` performs a real verification pass: it parses
`CLAIM` lines out of a proof, evaluates them with SymPy (symbolic proof
where possible, numeric sampling with explicit counterexamples otherwise),
and reports PASS/FAIL/UNVERIFIABLE per claim — see the script's PASS
(proved) vs. PASS (numeric only) distinction, which is the honesty
mechanism that keeps this from overclaiming rigor it didn't actually check.

- **vs. `foogtil/claude-code-math-skills`, `morankor/theorist-toolbox`**
  (`research/prior-art-research.md` §7): both enforce a
  Proposition/Proof-style prose template with no checker behind it. MATH's
  differentiator is specifically the SymPy round-trip; the structure
  enforcement below is secondary value, not the reason this skill exists.
- **If `sympy_verify.py` is ever removed** or the skill starts accepting
  proofs with zero extractable `CLAIM` lines as "verified," this skill has
  regressed to exactly the prior art it was scoped to differ from — fold it
  back into `latex` per PLAN.md's ship condition rather than keep
  maintaining it as a separate, undifferentiated skill.

## When to use

- Reviewing or drafting a proof/proof sketch that contains algebraic,
  trigonometric, or other SymPy-expressible sub-claims worth checking
  mechanically (an expansion, an inequality bound, a trig identity used
  mid-proof).
- Auditing proof structure: does the writeup actually state its
  assumptions before using them, and does it say where each claim gets
  used downstream?

## When not to use

- Purely informal or philosophical arguments with no checkable symbolic
  content — there's nothing for `sympy_verify.py` to do, and forcing
  `CLAIM` extraction would be theater.
- Full formal verification needs (a claim that's genuinely only trustworthy
  after a Lean/Coq proof) — this skill flags such candidates (see below)
  but does not attempt Lean formalization itself.
- Prose clarity of the writeup — that's `academic-humanizer` via `writing`.

## Core loop

1. **Extract claims.** Read the proof/proof sketch and pull out any
   sub-claim expressible as a SymPy equality or inequality — an expansion,
   an identity, a bound — into the `CLAIM` syntax `scripts/sympy_verify.py`
   understands:

   ```
   CLAIM <id>: <lhs> <op> <rhs> [assuming <var><cmp><bound>, ...]
   ```

   `<op>` is one of `== != >= <= > <`. Write extracted claims to a
   scratch file (e.g. alongside the draft, not committed unless the user
   wants a record) and run:

   `scripts/sympy_verify.py <claims-file>`

2. **Read the verdicts precisely.** Four outcomes per claim:
   - `PASS (proved)` — SymPy proved it symbolically (simplified to zero, or
     an inequality solved exactly over the domain). Trust this.
   - `PASS (numeric only)` — no symbolic proof found, but sampled points in
     the domain all satisfied the claim. This is evidence, not proof —
     say so to the user; don't report it as "verified" without the
     qualifier.
   - `FAIL` — a concrete counterexample was found; report the point and
     value, not just "failed."
   - `UNVERIFIABLE` — parsing/evaluation failed (SymPy couldn't handle the
     expression). Don't silently drop the claim; tell the user it needs
     manual review.
3. **Enforce structure.** Independent of the verification pass, check the
   writeup states, in order: **Claim** (what's being proved) → 
   **Assumptions** (what's given/assumed, stated before use, not
   introduced mid-proof) → **Proof** (the argument) → **Where used** (what
   downstream result depends on this one, if any — omit only for
   standalone lemmas). Flag missing or out-of-order sections rather than
   silently reordering the user's writeup.
4. **Flag (don't force) Lean candidates.** If a claim is a fully formal
   statement over a standard decidable theory (arithmetic, real
   inequalities, elementary algebra) and carries real weight in the
   argument, note it as a Lean-formalization candidate — but do not attempt
   the formalization; that's a deliberate scope boundary, not a TODO to
   fill in silently.

## Scripts

- `scripts/sympy_verify.py <claims-file>` — requires `sympy`
  (`pip install sympy`, a venv is recommended); exits with a clear error
  rather than silently no-op'ing if it's missing. Deterministic numeric
  sampling (fixed RNG seed) so re-runs on the same claims are reproducible.
