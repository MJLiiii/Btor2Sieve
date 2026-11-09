# Method structure refactor

**Goal:** Make the two extraction methods identifiable directly from source,
test and benchmark directory names, preserving their algorithms and proofs.

## Design

Move implementations side by side into `src/btor2sieve/methods/`:

- `word_level.py`: existing syntax templates, semantic discovery and selection.
- `implied_constraints.py`: paper state-literal implications and equivalences.
- `common.py`: shared Candidate and GenerationOptions data classes.
- `__init__.py`: package description, without a registry or extra dispatch layer.

The shared pipeline imports these modules explicitly. Keep the existing
two-call word-level generation/selection sequence and all validation unchanged.
Tiny root `candidates.py` and `implied.py` compatibility modules preserve public
imports, while documentation and internal imports point to canonical modules.
Rename method tests to `test_word_level.py`, `test_implied_constraints.py`, and
`test_implied_constraints_pipeline.py`.

Group benchmark outputs into `word-level/semantic/`, `word-level/syntax/`, and
`implied-constraints/`. Keep CLI method selectors and evaluation run keys
unchanged. Record a relative `output_directory` in each run and comparison row.
Existing saved reports remain untouched and replayable.

This keeps the organization shallow: a method package with named files, no
per-method framework or duplicated validators. A filename-only rename would
leave shared types coupled to one method; a class/registry hierarchy would
add complexity without helping the requested navigation.

## Execution

- [x] Move method implementations and shared types, update imports, rename tests;
  verify public compatibility imports refer to the same canonical objects.
- [x] Update evaluator output paths, metadata, tests and benchmark guide.
- [x] Update source walkthrough and method documentation to match the layout.
- [x] Run full tests and compare both methods' pre/post records and SMT artifacts
  on existing examples in fresh processes. Replay both methods with Z3/cvc5.
- [x] Obtain independent review; leave changes uncommitted.

## Baseline

185 tests pass before refactoring. The prior uncommitted implementation and
user-added PDF are preserved. Snapshot for behavior comparison:
`/tmp/btor2sieve-structure-4CICIs/baseline-source/`.

## Verification

- Full suite: 185 tests pass. `git diff --check` passes.
- Word-level: 493 pre/post records and 508 SMT obligations match exactly
  (record timing excluded); summary content is unchanged.
- Implied constraints: 97 pre/post records and 103 SMT obligations match
  exactly (record timing excluded); summary content is unchanged.
- All six public compatibility exports refer to the same objects as their
  canonical method modules.
- Evaluator exercised syntax, semantic and implied modes on all three examples
  in the new directories. Z3 and cvc5 replay each report zero mismatches.
- Evidence: `/tmp/btor2sieve-structure-4CICIs/`.
- Independent review found no behavior or packaging issues. Its one stale
  current-command description in `docs/RESULTS.md` was corrected; the original
  experiment's historical measurements and artifact paths remain unchanged.
