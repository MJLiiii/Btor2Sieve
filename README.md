# Btor2Sieve

Extract word-level bit-vector and array constraints from BTOR2 hardware models. Every candidate is independently checked with SMT. The product includes a CLI, searchable HTML reports, CSV/JSON results, standalone SMT-LIB obligations, cross-property revalidation, and a pinned public benchmark corpus.

**Start with the [method](docs/METHODS.md), [research notes](docs/research/constraint-literature.md), and [measured results](docs/RESULTS.md).** The supplied assignment and proposal are preserved unchanged. Design decisions and the implementation plan are in [docs/superpowers](docs/superpowers).

## Install

Python 3.11 or newer is required. From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,crosscheck]'
```

The only runtime dependency for extraction is `z3-solver`. The `dev` extra adds pytest; `crosscheck` adds the independent cvc5 replay backend. For the exact versions used in the recorded experiment:

```sh
python -m pip install -r requirements-reproduce.txt
python -m pip install -e .
```

The development environment in this workspace is already installed: use `.venv/bin/btor2sieve` or activate `.venv`. No Pono, native compiler, account, API key, or network connection is needed to run the vendored examples.

## Run a complete example

```sh
btor2sieve inspect examples/counter.btor2
btor2sieve extract examples/counter.btor2 --out results/my-counter --reuse
btor2sieve replay results/my-counter --accepted-only --backend cvc5
```

Open `results/my-counter/report.html` in a browser. Output paths must be new: existing directories are never overwritten. Run with `--help` for all options.

For arrays and initial/transition facts:

```sh
btor2sieve extract examples/array.btor2 --out results/my-array \
  --scopes property,model,initial,transition
```

Process multiple models with a reproducible budget:

```sh
btor2sieve batch benchmarks/public/*.btor2 --out results/my-suite \
  --max-candidates 80 --max-terms 12 --max-queries 96 --timeout-ms 200 --reuse
```

`--syntax-only` disables solver-guided range and known-bit discovery. `--property ID` selects a **bad directive ID**, not the ID of its Boolean expression. For example, the counter's properties are bad directives 11 and 14. `--max-reuse` limits reuse queries per target property. Timeouts are per solver call, not a total run deadline.

## Read the results correctly

For each bad node `b`, the property is `P = not b`. A property candidate is accepted only when `P and not C` is UNSAT and P itself is SAT. The validator does not silently assume initialization, transition equations, environment constraints, or other properties.

| Scope | Exact hypothesis | What it establishes |
| --- | --- | --- |
| `property:ID` | `not bad_ID` | Consequence of one safety predicate |
| `model` | Original BTOR2 constraints A | Assumption/combinational consequence |
| `initial` | I and A | Initial-frame fact |
| `transition` | T and A | One-step relation, with primed states |

The default scopes are `property,model`. Rejected candidates have counterexamples; unknown queries have reasons. An inconsistent hypothesis is reported as vacuous and excluded from accepted counts. Cross-property reuse repeats the target implication and is counted separately.

**A property consequence is not an invariant.** Do not append it as a BTOR2 `constraint`: doing so can erase the first bad state. This tool emits facts and evidence; it does not modify your model, prove its safety, or claim verification speedups. Fair/justice declarations are disclosed as liveness features; extraction analyzes finite safety formulas only.

Each report directory contains:

* `report.html`: searchable, filterable local report with expandable formulas and counterexamples.
* `summary.csv`: one row per model and scope, including counts and timings.
* `families.csv`: counts by model, scope and candidate family.
* `constraints.csv`: every validation result, including reuse.
* `results.json`: full provenance, symbols, hypotheses, configuration, timings and hashes.
* `obligations/*.smt2`: standalone implication and hypothesis queries.

Replay checks hashes and re-solves both the implications and the hypotheses. `--accepted-only` still checks hypothesis satisfiability. Use a new CLI process and `--backend cvc5` for solver diversity. These are replayable SMT obligations, not proof certificates checked by a proof kernel; parser/encoder correctness remains part of the trusted boundary.

CLI exit codes: 0 means the command completed, 1 means a batch input failed or replay was incomplete/mismatched, and 2 means an invalid command/input/output path. A successful extract command can contain unknown or vacuous results; inspect the status counts. Batch continues after a failed model and retains complete results for successful models.

## Reproduce and test

```sh
python -m pytest -q
python scripts/fetch_benchmarks.py --check
python scripts/evaluate.py --out results/my-evaluation
```

The evaluation script runs syntax and semantic modes with the same configured budgets, then replays accepted implications and all hypotheses with both Z3 and cvc5. It requires the `crosscheck` extra (or `--skip-cvc5`). [The corpus manifest](benchmarks/manifest.json) pins original URLs, commits, licenses, hashes, model features, and verified HWMCC provenance. The 13 small public files are included, with their licenses; four are confirmed HWMCC19 entries, and the other files are explicitly identified as family or upstream regression examples.

The suite covers strict parsing, bit-vector wraparound and signed operations, arrays, missing initialization/next, deep DAGs, finite safety/liveness separation, candidate budgets, invalid guesses, vacuity, solver UNKNOWN, exact property scopes, cross-property reuse, report counts, failed-model isolation, and tamper detection.

## Extend the extractor

The modules are intentionally small:

* `btor2.py` and `encoding.py`: strict typed reader and word-level semantics.
* `candidates.py`: bounded, untrusted templates and semantic discovery.
* `validation.py`: independent exact-hypothesis checks and SMT replay.
* `pipeline.py`, `reporting.py`, `cli.py`: orchestration and user-facing artifacts.

To evaluate a new candidate generator, emit `Candidate(expr, family, origin, source_nodes)` and keep the validator unchanged. See [METHODS.md](docs/METHODS.md) for a Python/API-level explanation of the boundaries. Inductive/Houdini inference, Pono integration, proof-certificate production, and large-suite speedup evaluation are documented research extensions, not implemented capabilities.
