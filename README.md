# Btor2Sieve

Extract word-level bit-vector and array constraints from BTOR2 hardware models. Every candidate is independently checked with SMT. The product includes a CLI, searchable HTML reports, CSV/JSON results, standalone SMT-LIB obligations, cross-property revalidation, and evaluation of local BTOR2 benchmark collections.

Start with the installation and counter example below. The [method](docs/METHODS.md) explains what the results establish; the [research notes](docs/research/constraint-literature.md) and [historical measurements](docs/RESULTS.md) provide background. The supplied assignment and proposal are preserved unchanged in `docs/`. Original design decisions and the implementation plan are in [docs/superpowers](docs/superpowers).

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
btor2sieve batch benchmarks/hwmcc/2025/bv/hkust/*.btor2 --out results/my-suite \
  --max-candidates 80 --max-terms 12 --max-queries 96 --timeout-ms 200 --reuse
```

`--syntax-only` disables solver-guided range and known-bit discovery. `--property ID` selects a **bad directive ID**, not the ID of its Boolean expression. For example, the counter's properties are bad directives 11 and 14. `--max-reuse` limits reuse queries per target property. Timeouts are per solver call, not a total run deadline.

## Project layout

```text
src/btor2sieve/          Python package
tests/                  Automated tests
scripts/                Evaluation entry point
examples/               Small runnable BTOR2 examples
benchmarks/             Input datasets, grouped by source/year/track
  hwmcc/2025/
    bv/                 Bit-vector benchmarks
    arrays/             Array benchmarks
docs/                   Methods, research, and historical results
results/                Generated evaluation reports
```

Use lowercase names for collection directories and descriptive track names. Keep upstream family directories and model filenames unchanged so inputs remain traceable to their source. Store generated reports in `results/`.

## Find your way around the code

Follow one model through the package:

```text
BTOR2 text → typed Model → Encoder → exact scopes → candidate proposals
                                                        ↓
reports and SMT files ← pipeline ← independent Validator
```

| Module | Responsibility |
| --- | --- |
| [btor2.py](src/btor2sieve/btor2.py) | Parse lines into sorts and nodes, checking references and types. |
| [encoding.py](src/btor2sieve/encoding.py) | Translate nodes into Z3 expressions and build assumptions, initialization, and transition equations. |
| [candidates.py](src/btor2sieve/candidates.py) | Propose formulas within budgets and select candidates for each scope. Proposals are untrusted. |
| [validation.py](src/btor2sieve/validation.py) | Define exact scope hypotheses, check each candidate independently, and replay individual SMT queries. |
| [pipeline.py](src/btor2sieve/pipeline.py) | Run those steps, revalidate reuse, and record evidence; isolate failures by model. |
| [reporting.py](src/btor2sieve/reporting.py) | Write JSON, CSV, and a self-contained HTML report from the result dictionaries. |
| [replay.py](src/btor2sieve/replay.py) | Read a report or SMT file, verify artifact paths/hashes, and replay its queries. |
| [cli.py](src/btor2sieve/cli.py) | Parse command-line options, call the operation, and print its result. |

Tests follow these boundaries in `tests/`. `scripts/evaluate.py` runs the evaluation on local benchmark collections.

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
python scripts/evaluate.py --out results/my-evaluation
```

Organize downloaded BTOR2 collections under `benchmarks/<source>/<year>/<track>/`, preserving the upstream family folders and filenames. The HWMCC’25 collection uses `benchmarks/hwmcc/2025/bv/` and `benchmarks/hwmcc/2025/arrays/`. The evaluation script recursively selects **every `.btor2` file** under `benchmarks/`, including files added later. There is no fixed corpus list, fetch step, or automatic download. See [benchmark setup](benchmarks/README.md) for the source and supported categories.

To evaluate a different directory:

```sh
python scripts/evaluate.py --benchmarks /path/to/extracted/models --out results/my-evaluation
```

Evaluation runs syntax and semantic modes with the same budgets, then replays accepted implications and all hypotheses with Z3 and cvc5. It requires the `crosscheck` extra (or `--skip-cvc5`). `evaluation.json` records the selected input paths; each mode’s `results.json` records model hashes. Budgets limit individual queries, not total runtime. Run the automated test suite locally with `python -m pytest -q`; it does not require a downloaded benchmark corpus.

The suite covers strict parsing, bit-vector wraparound and signed operations, arrays, missing initialization/next, deep DAGs, finite safety/liveness separation, candidate budgets, invalid guesses, vacuity, solver UNKNOWN, exact property scopes, cross-property reuse, report counts, failed-model isolation, and tamper detection.

## Extend the extractor

To try a new candidate, build a Boolean Z3 expression, attach its source node IDs, and pass it to the existing validator. For example, run this from the project root:

```python
import z3
from btor2sieve.btor2 import parse_file
from btor2sieve.candidates import Candidate
from btor2sieve.encoding import Encoder
from btor2sieve.validation import Validator

encoder = Encoder(parse_file("examples/counter.btor2"))
hypothesis = encoder.property(11)  # Safety predicate for bad directive 11.
candidate = Candidate(
    z3.ULE(encoder.states[5], 9),
    family="unsigned_bound",
    origin="example:counter-bound",
    source_nodes=(5,),
)
result = Validator(hypothesis).check(candidate.expr)
print(result.status)  # accepted: the predicate implies counter <= 9.
```

To include a template in normal extraction, yield its `Candidate` from the appropriate generator in `candidates.py` and add a focused test. `generate_candidates` produces bounded proposals; `select_scope_candidates` combines those proposals with transition templates when needed and applies the final validation budget/filter. The pipeline calls these two stages explicitly. Keep the validator unchanged: it must never assume a proposed or previously accepted formula.

See [METHODS.md](docs/METHODS.md) for the soundness boundaries. Inductive/Houdini inference, Pono integration, proof-certificate production, and large-suite speedup evaluation remain research extensions.
