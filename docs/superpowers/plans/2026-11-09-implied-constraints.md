# Implied Constraints Implementation Plan

> **For agentic workers:** Use Superpowers TDD and verification-before-completion;
> implement the independent benchmark task in parallel with core integration.

**Goal:** Add the paper's literal implication extraction without replacing the
existing method, and make both methods easy to benchmark.

**Architecture:** A separate implied generator produces ordinary Candidate
objects for the existing independent Validator. Pipeline dispatch preserves
the word-level branch. Benchmark selection compares identically scoped runs.

**Tech Stack:** Python 3.11+, existing Z3 dependency, pytest, optional cvc5.

**Spec:** `docs/superpowers/specs/2026-11-09-implied-constraints-design.md`.

## Global constraints

Keep the existing method, local paper and user files. No new runtime dependency.
No model transformation or model-safety claim. Keep edits uncommitted for review.

## Review focus

- Unsatisfiable properties and UNKNOWN must not yield accepted equivalences.
- Property checks must exclude environment, initialization and transition facts.
- Positive/negative literals and duplicate clauses must behave consistently.
- Array-only and wide-state models must report their restricted vocabulary.
- One failed benchmark method must leave the other method's evidence available.

## Task 1: Literal candidate generator

Files: `src/btor2sieve/implied.py`, `tests/test_implied.py`.
Interface: `generate_implied_candidates(encoder, roots, options) -> list[Candidate]`;
`find_equivalences(accepted: list[tuple[Candidate, str]]) -> list[dict]` records
expression, source_nodes, and implication_ids.

- [x] Write failing tests for both polarities, unit facts, direct/complemented
  equivalence and budgets, then run `pytest tests/test_implied.py -q`.
- [x] Implement state-bit selection, implication enumeration/deduplication and
  equivalence recognition, then rerun the focused tests.

## Task 2: CLI, pipeline and documentation

Files: `candidates.py`, `pipeline.py`, `cli.py`, `reporting.py`, related tests,
`README.md`, `docs/METHODS.md`.

- [x] Add failing tests for method selection, scope errors, non-vacuity,
  assumption exclusion and independent replay.
- [x] Append GenerationOptions.method, dispatch to the new generator, record
  equivalence proof references and method-specific warnings; preserve default
  generation branch. Show method/equivalences in HTML without CSV schema churn.
- [x] Run focused tests and document paper fidelity, budgets and examples.

## Task 3: Benchmark comparison

Files: `scripts/evaluate.py`, `tests/test_evaluate.py`, `benchmarks/README.md`.

- [x] Add and run failing tests for default semantic/implied selection,
  explicit syntax/semantic selection, filtering/limits and failure retention.
- [x] Add --methods (syntax, semantic, implied), --scopes (default property),
  --max-width, --filter and --limit; emit comparison.csv and retain failed runs.
- [x] Run evaluator tests and document copyable benchmark commands.

## Task 4: Integration and review

- [x] Run full pytest and git diff --check.
- [x] Run both methods on examples and representative local BV/array inputs;
  replay accepted obligations and hypotheses with Z3/cvc5.
- [x] Independent review; address actionable findings with regression tests.
- [x] Report commands, verification and limits, leaving changes uncommitted.

## Verification record

- Baseline: 143 tests passed before edits. Integrated suite: 185 tests passed.
- Generator: 19 focused tests include exhaustive truth tables for all signed
  literal pairs and all nonempty two-bit properties. Integration covers
  non-vacuity, UNKNOWN, proof separation, reuse and replay.
- Compared committed original against the updated default word-level path in
  fresh processes, on all three examples with all four scopes and reuse:
  all 493 records match excluding validation timing; all 508 SMT obligations
  are byte-identical. Same-process comparisons were replaced with fresh
  processes because Z3's internal let names depend on allocation history.
- Two-method smoke evaluation: three examples, one local BV benchmark and two
  local array benchmarks. Z3 and cvc5 replay both report zero mismatches for
  every run. These are smoke tests, not a full-corpus performance claim.
- Evidence directory: `/tmp/btor2sieve-implied-epeMJm/`.
- Edits remain uncommitted in the supplied checkout; the user-added PDF is
  retained unchanged. No new runtime dependencies were added.
- Final independent review found no actionable issues. It independently ran
  46 focused tests and checked equivalence soundness for all 255 nonempty
  three-bit properties (90 derived equivalences and their proof pairs).
