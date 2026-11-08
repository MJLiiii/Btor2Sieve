# Independent core review

Reviewed 2026-11-08: `validation.py`, `pipeline.py`, `reporting.py`, and `cli.py`, with the frontend/encoder inspected for scope construction. Compared with the design and research semantic contract. Candidate generation was deliberately excluded because it was still under implementation. No production files were edited.

## Findings

### P2: Report replay omits the evidence establishing non-vacuity

Locations: `src/btor2sieve/cli.py:67-89`; `src/btor2sieve/pipeline.py:157-164`.

A result is accepted only when its hypothesis is SAT and its implication obligation is UNSAT, but report replay checks only the implication files in `data["records"]`. Hypothesis files in `models[].scopes[]` are not replayed or hashed. Consequently, a report whose hypothesis file was changed from a SAT hypothesis to `(assert false)` or whose hypothesis file was deleted still replays with zero mismatches and exit status 0. This does not invalidate the original implication, but it leaves the promised non-vacuous acceptance and complete artifact-integrity claim unverified on replay.

Reproduction: analyze the small model below with property scope and a fixed candidate `x != 0`; overwrite or delete the scope's `obligation` file, then run accepted-only report replay. Both cases return `checked: 1, mismatched: 0`, exit 0.

Suggested repair: save a SHA-256 for each hypothesis artifact, replay each relevant scope once, and require SAT for scopes containing accepted records. Report hypothesis checks distinctly from candidate checks. Add corruption/deletion tests for these artifacts, including an empty candidate scope if full-report replay is intended to cover it.

### P2: A mid-scope failure leaves accepted records outside summary accounting

Locations: `src/btor2sieve/pipeline.py:151`, `173-192`; `src/btor2sieve/cli.py:119-122`.

Candidate records are appended incrementally, while a scope summary is appended only after every candidate finishes. If checking a later candidate raises a handled error, `analyze()` retains earlier records but never writes their summary. This makes the CLI's accepted count and `summary.csv` disagree with `results.json`, `constraints.csv`, and the HTML cards. The malformed-candidate boundary is relevant because generation is explicitly untrusted and validation accepts arbitrary Boolean candidates.

Reproduction: replace `pipeline.generate_candidates` in a probe with `[Candidate(x != 0, ...), Candidate(x, ...)]`, where `x` is a BV2. On property scope, the first candidate is accepted and the second raises `ValueError("candidate must be Boolean")`. The returned report has one accepted record, zero summaries, and one explicit error. The CLI computes zero accepted from summaries; HTML computes one from records. The batch failure itself is correctly surfaced.

Suggested repair: either make scope publication transactional, or preserve a partial-scope summary/status when a later candidate fails. Counts must be derived consistently, and the report should identify partial results. Add a focused mid-scope failure regression, beyond the existing parse-failure batch test.

## Evidence and checks

Direct probes were run with the project virtual environment and `PYTHONPATH=src`; temporary probe source is `/tmp/review_btor2_core.py`. Candidate generation was replaced with explicit fixed candidates so the review does not depend on unfinished discovery behavior. No unchanged full test suite was rerun.

Probe model:

```text
1 sort bitvec 1
2 sort bitvec 2
3 zero 2
4 state 2 x
5 init 2 4 3
6 one 2
7 add 2 4 6
8 next 2 4 7
9 eq 1 4 3
10 bad 9
11 constraint 9
```

For `C = (x = 0)`, exact property scope rejected the candidate while model, initial, and transition scopes accepted it. The transition scope accepted `x_next = 1`. This confirms that property checks do not inherit the contradictory environment condition and that transition assertions use primed state variables. Inspection also confirms fresh solver creation per candidate, separate hypothesis satisfiability checks, exclusion of vacuous/unknown implications from accepted status, and independent target-property revalidation for reuse.

Replay paths are resolved and constrained beneath the report directory, candidate obligation bytes are hashed before parsing, and HTML content is escaped. Output directory creation refuses overwrite. Parse errors are explicitly recorded and batch processing continues. These mechanisms are sound for their stated purpose; the missing hypothesis-integrity coverage above is the outstanding replay gap.

## Verdict

The central implication contract is sound on inspection and targeted probes: `P_j`, `A`, `I ∧ A`, and `T ∧ A` remain distinct; candidate facts never justify one another; no reachability or hardware-safety claim is inferred from acceptance. The report explicitly states the source-only environment for transition scope and the solver/frontend trust boundary. No P0/P1 proof-soundness defect was found in the reviewed core.

The implementation is compact and understandable. Fix the two P2 evidence/accounting gaps before calling the complete replay/report workflow reliable. Counts currently include direct property atoms and other syntactic facts; the HTML appropriately says they do not measure novelty, so evaluation must retain that qualification and avoid interpreting raw accepted totals as nontrivial mining yield. This review does not certify candidate generation, public benchmark evaluation, or full frontend semantics.

## Scoped repair review

Re-reviewed the fixes on 2026-11-08. Both original P2 findings are resolved.

- Hypothesis artifacts now carry SHA-256 hashes and join the replay selection, including accepted-only replay. Re-running the original probe after overwriting a hypothesis reports `checked=2, mismatched=1`, an explicit SHA-256 error, and exit status 1. Deleting the hypothesis likewise reports a missing-file error and exit status 1. Normal hypothesis and implication replay now independently confirms SAT and UNSAT respectively.
- Per-model report publication is transactional: failed models discard partial models, summaries, and records, and the error records how many partial records were discarded. The original malformed-second-candidate probe now reports zero retained accepted records and `discarded_partial_records=1`, with no summary inconsistency. Artifact cleanup targets only the failed model's generated filename prefix; completed models are committed separately.
- Replay now reports original run errors and returns failure for an empty or failed run. The added regression tests cover the central failure paths. This review inspected those tests and reran the original direct repro instead of repeating the full suite.
- SMT exports now declare `ALL`. A focused two-bit example replays its SAT hypothesis and UNSAT implication successfully through both installed Z3 and cvc5 backends.

No new actionable defect was found in this scoped repair review. The earlier verdict about the core implication semantics remains unchanged. Candidate generation and overall project completion remain outside this review's scope.
