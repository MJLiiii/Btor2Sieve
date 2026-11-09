# Evaluation results — 2026-11-08

The delivered product completes the core C14 workflow: typed BTOR2 extraction, separate implication validation, per-model/per-property tables, and replayable bit-vector and array evidence. It does not integrate into a model checker, prove the input safety properties, or claim a verification speedup.

## Reproducible artifacts

This page records the original 2026-11-08 experiment. Its generated reports and receipts are no longer present in this checkout; the measurements below remain historical results. The original files were under `results/final-evaluation/` and `results/demo/`.

The [pinned source manifest](../benchmarks/manifest.json), [methods](METHODS.md), and [literature review](research/constraint-literature.md) remain available. Regenerate reports in a new output directory:

```sh
python scripts/fetch_benchmarks.py --check
python scripts/evaluate.py --out results/my-evaluation
python -m btor2sieve batch examples/*.btor2 --out results/my-demo \
  --scopes property,model,initial,transition --reuse
```

The evaluation writes `evaluation.json` and `syntax/` and `semantic/` directories containing `report.html`, `summary.csv`, `families.csv`, `constraints.csv`, and replay receipts. The demo writes its all-scope report to `results/my-demo/report.html`. New timings and environment details will differ from this historical run.

## Corpus and configuration

The public corpus has 13 unmodified upstream models, 23 bad-state properties and four models with arrays. Two models have multiple bad nodes: the factorial example has two and the rotation regression has ten. Four files are verified byte-for-byte against HWMCC19 mirror entries, two are from the same published hardware benchmark family, and seven are upstream BTOR2Tools/Pono regression examples. They are not 13 independently selected competition tasks. Original labels such as “safe” and “unsafe” come from upstream directories, not from this extractor.

Both modes used 80 candidates per scope, 12 selected terms, maximum scalar width 64, at most 96 discovery queries per scope, and a 200 ms timeout per SMT call. Scopes were each individual property plus model assumptions: 36 total. Reuse allowed 30 attempts per target property. The semantic mode shares the same candidate limit with syntax templates, so its candidate set need not contain every baseline candidate.

Recorded environment: Python 3.12.13, Z3 5.3.3.0, cvc5 1.4.2, macOS ARM64. Exact runtime/platform strings are in each report. Replay used 5,000 ms per check. cvc5's `arrays-exp` option is enabled for constant-array initializations. The measurements below are single local runs, not statistically robust performance estimates.

## Final comparison

| Mode | Candidates | Accepted | Rejected | Unknown | Vacuous | Discovery (s) | Validation (s) | Total analysis (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Syntax only | 1,912 | 90 | 1,822 | 0 | 0 | 0.414 | 1.543 | 3.914 |
| Syntax + semantic | 1,914 | 92 | 1,822 | 0 | 0 | 0.642 | 1.554 | 4.199 |

Discovery and validation columns exclude separate hypothesis-satisfiability checks. Total analysis also includes parsing, encoding, bookkeeping and SMT artifact writes, but excludes final HTML/CSV/JSON rendering and external replay. All figures are taken from `evaluation.json`.

Semantic mode has 46 accepted property consequences and 46 accepted assumption/combinational consequences. It accepted only two more formulas overall than syntax mode. The useful change is the vocabulary: eleven additional accepted unsigned bounds and one known-bit mask replace ten accepted equality formulas under the shared budget. This small corpus does not establish that semantic extraction generally outperforms the syntax baseline.

| Family | Syntax candidates | Syntax accepted | Semantic candidates | Semantic accepted |
| --- | ---: | ---: | ---: | ---: |
| Array relations | 57 | 8 | 57 | 8 |
| Disequality | 491 | 25 | 491 | 25 |
| Equality | 484 | 22 | 474 | 12 |
| Implication | 56 | 8 | 56 | 8 |
| Masked bits | 16 | 0 | 17 | 1 |
| Signed bounds | 410 | 17 | 410 | 17 |
| Unsigned bounds | 398 | 10 | 409 | 21 |

Counts are validated formulas, not independent facts or a measure of novelty. Normalization removes obvious tautologies and the normalized hypothesis, but does not test full logical independence or minimality. Some predicates describe combinational structure rather than restricting externally visible state.

## Independent replay and representative evidence

The final syntax run has 90 accepted implications and 36 hypotheses: all **126** checks agree in Z3 and cvc5. The final semantic run has 92 accepted implications and 36 hypotheses: all **128** checks agree in both solvers, with zero hash failures or mismatches. Replay receipts are in each report directory as `replay-z3.json` and `replay-cvc5.json`.

One semantic example is `pono-array_lt200`, property 20. Under its original safety predicate, the tool validates:

```smt2
(= (bvand (select s_11 i_6) #x7fffff00) #x00000000)
```

This is a relation over a native array read, not a bit-blasted representation. The mask is partial because of the discovery query budget; the tool does not claim the strongest possible mask. The original standalone obligation was `semantic/obligations/m0010-00002.smt2`, corresponding to record `m0010-00002` in the JSON report. Regenerate the evaluation to inspect its evidence. The candidate is only a consequence of this property's predicate, not a proven reachable invariant.

The constant-array benchmark also yields native read disequalities, such as `select(memory,index) != 1` under the property requiring the read to be zero. The counter demo yields unsigned bounds and known-bit facts; transition scope gives facts about `s_ID_next`, and initial scope stays distinct from invariance.

The three hand-written demo files produce **458 ordinary candidates: 89 accepted, 363 rejected, and 6 vacuous**. Cross-property attempts are separate: **23 accepted and 93 rejected**. The accepted-only demo replay includes 112 accepted ordinary/reuse implications plus 15 scope hypotheses, for **127 matching checks in each solver**. The public corpus itself had only one eligible reuse attempt under these budgets, and it was rejected. Successful reuse is therefore demonstrated by the explicit counter example, not claimed as a public-corpus result.

## Term selection experiment

An earlier implementation stopped dependency traversal after the first 12 nearby eligible nodes. Six Mann property cones spent ten of those slots on non-word terms and missed deeper word declarations. The updated implementation walks the full cone, then shares the bounded vocabulary among word declarations/reads, local predicates/guards, word operations, and literals.

At the same budgets, the earlier semantic run accepted 116 of 1,821 candidates; the revised run accepts 92 of 1,914. The decrease is intentional and not presented as a success based on count. Compared with the earlier run, accepted signed bounds increase from 6 to 17, implications from 0 to 8, and a nontrivial mask over an array read appears. Boolean equalities/disequalities decrease. Earlier artifacts were stored under `results/public-evaluation/`; they are also absent from this checkout and reflected a different selection policy. This was a development experiment, not a held-out evaluation.

## Verification and limitations

The test suite covers parser diagnostics, modular and signed arithmetic, division by zero, overflow, rotations, array initialization, native array operations, negative references, unconstrained missing initialization/next, deep DAGs, candidate/query limits, partial semantic search, exact scope separation, SAT counterexamples, UNKNOWN, vacuity, explicit Z3 contexts, independent constant-array replay, cross-property revalidation, output escaping, transactional failures, and altered evidence files. The original test receipt was `results/pytest.txt`; run `python -m pytest -q` for current verification.

All 13 corpus files were accepted by the official pinned BTOR2Tools `catbtor` as well as Btor2Sieve. Independent reviews are recorded in [review-core.md](review-core.md) and [review-final.md](review-final.md). Agreement with a reference parser checks syntax compatibility, not full semantic equivalence; frontend and solver correctness remain trusted.

This is a small functional evaluation with short timeouts. No large-model scalability, repeated timing statistics, downstream solved-property increase, proof-kernel certificate, or model-checking speedup is established. Optional follow-on work is ranked in the literature review: broader benchmarks and candidate quality metrics first; initialized inductive/Houdini inference and certified Pono integration next; richer quantified templates or LLM-proposed typed hints only with a measured need.
