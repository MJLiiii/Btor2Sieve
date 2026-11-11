# Btor2Sieve

Btor2Sieve extracts **property-implied** bit-vector and array constraints from
BTOR2 hardware models and checks every one of them independently with an SMT
solver. You get a CLI, a searchable HTML report, CSV/JSON results, standalone
SMT-LIB obligations that anyone can replay, cross-property revalidation, and a
script for evaluating whole benchmark collections.

The [method](docs/METHODS.md) explains exactly what a result establishes. The
[research notes](docs/research/constraint-literature.md) and
[historical measurements](docs/RESULTS.md) give background. The supplied
assignment and proposal are preserved unchanged in `docs/`. Retired methods are
kept in a movable [archive](archive/README.md).

## Install

Python 3.11 or newer is required. From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,crosscheck]'
```

On NixOS, run `nix-shell` first: the z3-solver and cvc5 wheels need
`libstdc++.so.6`, which `shell.nix` puts on the library path, and the shell
activates `.venv` (creating it if missing).

The only runtime dependency is `z3-solver`. The `dev` extra adds pytest;
`crosscheck` adds cvc5 as an independent replay solver. For the exact versions
used in the recorded experiment:

```sh
python -m pip install -r requirements-reproduce.txt
python -m pip install -e .
```

Extraction needs the [Pono](https://github.com/stanford-centaur/pono) model
checker on `PATH`, because Pono reads each property (see
[How Pono is used](#how-pono-is-used)). `shell.nix` provides a pinned prebuilt
binary (x86-64 Linux); elsewhere, install Pono yourself. Btor2Sieve has no
BTOR2 parser of its own. No native compiler, account, API key, or network
connection is needed.

## Quick start

```sh
btor2sieve inspect examples/counter.btor2
btor2sieve extract examples/counter.btor2 --out results/my-counter --reuse
btor2sieve replay results/my-counter --accepted-only --backend cvc5
```

Open `results/my-counter/report.html` in a browser. Output directories must be
new: existing directories are never overwritten. Run any command with `--help`
for all options. More examples:

```sh
btor2sieve extract examples/array.btor2 --out results/my-array
# Modular arithmetic, word equality, a guarded bound, and an array read:
btor2sieve extract examples/property_implied.btor2 --out results/native-implied
# Several models with a reproducible (bounded) budget:
btor2sieve batch benchmarks/hwmcc/2025/bv/hkust/*.btor2 --out results/my-suite \
  --matched-budgets --max-candidates 80 --max-terms 12 --max-queries 96 --timeout-ms 200 --reuse
```

* `--property ID` selects one **bad directive ID**, not the ID of its Boolean
  expression. For example, the counter's properties are bad directives 11 and 14.
* `--reuse` revalidates facts accepted for one property against the others;
  `--max-reuse` limits those queries per target property.
* `--timeout-ms` is per solver query, not a total deadline.

## What gets extracted

For each bad node `b`, the property is `P = not b`. Btor2Sieve proposes candidate
formulas `C` over the words and arrays that make up P as Pono reads it (P's
subterms, down to the states and inputs it reads), in these families:

| Family | Example |
| --- | --- |
| `unsigned_bound`, `signed_bound` | `x <= 9` (separate unsigned and signed tags) |
| `equality`, `disequality` | `x == y`, `x != 0` |
| `implication` | `enable => x <= 3` |
| `masked_bits` | `x & 7 == 5` |
| `array` | read/write and array (dis)equality relations |

Proposals come from finite typed templates plus SMT-guided discovery of exact
signed/unsigned bounds and known-bit masks. Proposals are untrusted: a candidate
is **accepted** only when `P and not C` is UNSAT and `P` itself is SAT, checked
by a fresh solver. The validator never assumes initialization, transitions,
environment constraints, other properties, or previously accepted facts.
The obligation for candidates derived directly from the model (an inductive
invariant check) is [defined in the methods](docs/METHODS.md#model-derived-candidates-defined-not-implemented)
but not yet implemented.

This follows the property-implied word-level direction in [C14](docs/C14.pdf),
page 1, adapting the motivation of *Speeding up Model Checking by Exploiting
Explicit and Hidden Verification Constraints*. It is not a literal reproduction
of that paper's Boolean algorithm, and it does not perform the paper's circuit
rewriting or claim model-checking speedups.

### Read the results correctly

* **A property consequence is not an invariant.** Do not append it as a BTOR2
  `constraint`: doing so can erase the first bad state. The tool emits facts and
  evidence; it does not modify your model or prove its safety.
* Rejected candidates come with counterexamples; unknown results with reasons.
  An inconsistent hypothesis is reported as **vacuous** and never counted as accepted.
* Cross-property reuse checks are counted separately from ordinary candidates.
* A count measures validated formulas, not how much information they contain.
* Fair/justice declarations are reported as liveness features; only finite safety
  formulas are analyzed.

### Budgets

| Profile | How to select | Meaning |
| --- | --- | --- |
| Uncapped (default) | nothing, or `--unlimited` | No candidate, term, width, or query caps. Workflow `property-word-level-v1`. |
| Matched | `--matched-budgets` with `--max-candidates/-terms/-width/-queries` | Bounded search (defaults 200/16/64/256). Workflow `property-word-level-budgeted-v1`. |

`--unlimited` cannot be combined with `--max-*` flags. Without
`--matched-budgets`, `--max-*` values are not enforced and are reported as null. Every solver
query still has a timeout. Solver UNKNOWN stops semantic discovery and leaves the
search **partial**. "Uncapped" means no truncation of the implemented finite
procedure; it does not enumerate all possible logical consequences. A completed
budgeted search means the run finished within its limits, not full coverage.
Reports include the effective settings, family counts, discovery queries, and
whether search and validation completed. See
[method details](docs/METHODS.md#property-word-level-implied-constraints).

### Report files

* `report.html`: searchable, filterable report with expandable formulas and counterexamples.
* `summary.csv`: one row per model and property, including counts and timings.
* `families.csv`: counts by model, property, and constraint family.
* `constraints.csv`: every validation result, including reuse.
* `results.json`: full provenance, symbols, hypotheses, configuration, timings, and hashes.
* `obligations/*.smt2`: standalone implication and hypothesis queries.

`replay` checks the hashes and re-solves both the implications and the
hypotheses; `--accepted-only` still checks hypothesis satisfiability. Use
`--backend cvc5` for solver diversity. These are replayable SMT obligations, not
proof certificates checked by a proof kernel; Pono's BTOR2 frontend remains part
of the trusted boundary.

**Exit codes:** 0 means the command completed; 1 means an input failed, implied
search was incomplete (e.g. solver UNKNOWN), or replay was incomplete or
mismatched; 2 means an invalid command, input, or output path. `batch` continues
after a failed model, and partial runs keep their reports and available evidence.

## How Pono is used

**Pono is the only BTOR2 frontend.** For each property, Btor2Sieve runs Pono on
the model file and takes the SMT-LIB formula Pono prints for that property;
that formula is P. Candidates C are built from P's subterms, and Z3 proves
"P implies C". Btor2Sieve itself only splits lines into words, to find the
`bad` lines, the lines to leave out before Pono reads the file, and the counts
in reports; it never interprets an expression. Each report records the Pono
binary's path and SHA-256.

**Known Pono limitation:** this Pono build misreads `rol` and `ror` (it rotates
by the second operand's line ID instead of its value), so models that use them
are refused with an error rather than analyzed under the wrong meaning. None of
the bundled or HWMCC'25 sample models use them.

`btor2sieve verify` measures what the accepted constraints do for Pono's
model checking (C14 outcome 4):

```sh
btor2sieve extract examples/counter.btor2 --out results/my-counter
btor2sieve verify results/my-counter --out results/my-counter-verify
btor2sieve verify results/my-counter --out results/my-counter-verify-2 \
  --engine ic3ia --engine ind --timeout 120
```

Each property is checked by each `--engine` (default `ic3ia`) twice: on the
original model, and with every accepted C added as `constraint (bad or C)`,
which says "P implies C". That is already proved true in every state, so the
two runs must give the same verdict (a difference is reported as
*inconsistent*); only the time and the number of solved properties can change.
Results go to `verify.json` and `verify.csv`. Generated BTOR2 files are kept
only with `--keep-files`, after an inconsistency, or after a Pono error. The
model files must be unchanged since extraction (SHA-256 is checked). Pono's
exit code is not a verdict (it is 0 for `sat`), so its printed verdict is read.

## Evaluate a benchmark collection

```sh
python scripts/evaluate.py --limit 5 --out results/implied-5
python scripts/evaluate.py --benchmarks benchmarks/hwmcc/2025/bv \
  --filter '*example_156*' --out results/implied-selected
python scripts/evaluate.py --benchmarks /path/to/extracted/models --out results/my-evaluation
```

The script recursively selects **every `.btor2` file** under `--benchmarks`
(default `benchmarks/`), sorted, optionally narrowed by `--filter` and `--limit`.
There is no fixed corpus list or automatic download; see
[benchmark setup](benchmarks/README.md). Organize collections as
`benchmarks/<source>/<year>/<track>/`, keeping upstream family folders and
filenames (for example `benchmarks/hwmcc/2025/bv/` and `.../arrays/`).

Each benchmark is extracted in its own Python process, then replayed with Z3
and cvc5 (install the `crosscheck` extra or pass `--skip-cvc5`). Defaults:

| Setting | Value |
| --- | --- |
| Scope | Property only: `P = not bad` |
| Budgets (`--budget-policy`) | `unlimited`; `matched` uses 80 proposals, 12 source nodes, 64-bit width, 96 queries; `method-defaults` uses the extractor's uncapped default |
| Discovery/validation timeout per query | 1,000 ms |
| Memory per benchmark (`--memory-limit-mib`) | 4 GiB, resident plus swapped |
| CPU time per benchmark (`--cpu-limit-s`) | 300 s |
| Wall time per benchmark (`--wall-limit-s`) | 600 s |
| Cross-property reuse limit per target | 30 |
| Independent replay | Z3 and cvc5, 5,000 ms per query |

**Workers.** `--jobs auto` (the default) runs as many benchmarks at once as can
each hold the full memory limit, given the memory available at launch, capped at
16 and at the usable CPUs (with 4 GiB per benchmark and about 10.5 GiB available,
that is 2). An explicit `--jobs` that does not fit is rejected before any output
is created, because overcommitted workers can trigger the kernel's out-of-memory
killer, which may also kill unrelated programs.

**Resource limits** (Linux only) apply to extraction, not replay. Memory is
sampled every 0.1 s together with the kernel's peak-resident record, and CPU time
is backed by a kernel limit. The first limit exceeded stops that benchmark, which
is recorded as `memory-limit`, `cpu-limit`, or `wall-limit`: its unreported
obligations are deleted, it is not replayed, and `comparison.csv` lists it with
that `outcome`. That is a benchmark outcome, not a tool failure; but if no
benchmark completes its search, the evaluation is incomplete and exits with 1. A
process killed by anything else (such as the system OOM killer) is a failure.
Every benchmark records its CPU time, wall time, and peak memory in
`run-status.json` and as `cpu_seconds`, `wall_seconds`, and `peak_memory_mib` in
`comparison.csv`. Direct `btor2sieve extract`/`batch` runs have no process-wide
limits.

**Outputs:**

```text
results/my-evaluation/
  evaluation.json         input list, effective_settings, family counts, search outcome
  comparison.csv          per-property results with resource columns
  run-status.json         overall progress
  implied-constraints/    combined report, replay results, run-status.json
    models/mNNNN/         each model's own report, obligations, and logs
```

Progress is printed as models complete. `duration_seconds` measures parallel wall
time; `worker_seconds` and `analysis_seconds` record summed worker and extraction
time. Ctrl+C stops the active workers and keeps completed model reports; the run
is marked incomplete, so rerun into a fresh directory. Inconclusive discovery or
validation makes the evaluation exit nonzero even if replay passes. The full
HWMCC collection can take hours; for a quick extraction-only run, pass selected
files to `btor2sieve batch`.

## Code tour

Follow one model through the package:

```text
BTOR2 file → Pono reads each property P (pono.py) → property scopes (validation.py)
                                                         ↓
   P's subterms (vocabulary.py) → candidate proposals (implied.py)
                                                         ↓
reports (reporting.py) ← evidence + obligations (pipeline.py) ← independent Validator (Z3)
```

| Module | Responsibility |
| --- | --- |
| [pono.py](src/btor2sieve/pono.py) | Have Pono read each property P; split lines into words; run Pono; write Z3 constraints back into BTOR2. |
| [vocabulary.py](src/btor2sieve/vocabulary.py) | Pick the terms and predicates among P's subterms (all of them, or a bounded selection). |
| [implied.py](src/btor2sieve/implied.py) | `Candidate`, `GenerationOptions`, template proposals, and SMT-guided bounds/masks. Untrusted. |
| [validation.py](src/btor2sieve/validation.py) | Build property scopes, check each candidate independently, replay single SMT queries. |
| [pipeline.py](src/btor2sieve/pipeline.py) | Run the steps above per model, revalidate reuse, save obligations; isolate failed models. |
| [reporting.py](src/btor2sieve/reporting.py) | Write JSON, CSV, and a self-contained HTML report. |
| [replay.py](src/btor2sieve/replay.py) | Load a report or SMT file, verify paths and hashes, and replay the queries. |
| [verify.py](src/btor2sieve/verify.py) | Model-check each property with Pono with and without the accepted constraints. |
| [cli.py](src/btor2sieve/cli.py) | Parse command-line options and print results. |

Other directories:

```text
tests/        automated tests, one file per area
scripts/      evaluate.py (command line) and parallel_evaluate.py (workers, limits, merging)
examples/     small runnable BTOR2 models
benchmarks/   input datasets, grouped by source/year/track
docs/         method, research, and historical results
archive/      snapshots of retired methods
results/      generated reports (not tracked)
```

## Extend the extractor

To try a new candidate, build a Boolean Z3 expression and give it to the
validator. Run this from the project root:

```python
import z3
from pathlib import Path
from btor2sieve.implied import Candidate
from btor2sieve.pono import read_model
from btor2sieve.validation import Validator

model = read_model("pono", Path("examples/counter.btor2"), property_ids=[11])
hypothesis = model.properties[0].hypothesis  # P for bad directive 11, as Pono reads it.
candidate = Candidate(
    z3.ULE(z3.BitVec("s_5", 8), 9),  # s_5 is the state on line 5.
    family="unsigned_bound",
    origin="example:counter-bound",
    source_nodes=(5,),
)
result = Validator(hypothesis).check(candidate.expr)
print(result.status)  # accepted: P implies counter <= 9.
```

To add a new proposal rule, extend `_templates` or `_semantic_facts` in
`implied.py`, with focused tests in `tests/test_implied.py`. The validator must never assume a
proposed or previously accepted formula. See [METHODS.md](docs/METHODS.md) for
the soundness boundaries. Inductive/Houdini inference, passing constraints into
Pono's engines directly (rather than as BTOR2 constraints), proof-certificate
production, and large-suite speedup evaluation remain research extensions.

## Test

```sh
nix-shell --run 'python -m pytest -q'
```

Pono reads every model in the tests, so run them where `pono` is on `PATH`
(inside `nix-shell`). The suite needs no downloaded benchmarks. It covers
reading properties through Pono, bit-vector wraparound and signed operations,
arrays, writing constraints back into BTOR2 (checked by Pono reading them back), candidate budgets, invalid guesses, vacuity, solver
UNKNOWN, exact property scopes, cross-property reuse, report counts, failed-model
isolation, per-benchmark memory/CPU/wall-time limits, and tamper detection.
