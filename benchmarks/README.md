# Benchmark datasets

Organize local datasets as `benchmarks/<source>/<year>/<track>/`. For [HWMCC’25](https://zenodo.org/records/17428464), download and extract the word-level archives yourself, then place their contents as follows:

| Archive | Dataset directory |
| --- | --- |
| `hwmcc25-benchmarks-wordlevel-bv.tar.gz` | `benchmarks/hwmcc/2025/bv/` |
| `hwmcc25-benchmarks-wordlevel-array.tar.gz` | `benchmarks/hwmcc/2025/arrays/` |

Keep the upstream family folders and model filenames inside each track. If extraction creates a track wrapper directory, move its contents into the corresponding directory above. Use lowercase source and track names; future sources and years get sibling directories under the same convention. These names organize the data and do not filter evaluation. The project does not download or extract archives and has no fixed corpus manifest.

### Multi- and single-property models: CAV'18 Btor2 benchmarks

HWMCC word-level models have exactly one `bad` property each. The competition has split multi-property designs into single-property files since its first word-level track (HWMCC'19). For multi-property word-level models, `benchmarks/cav18/2018/` holds the ten benchmarks from Niemetz, Preiner, Wolf and Biere, [Btor2, BtorMC and Boolector 3.0](https://fmv.jku.at/papers/NiemetzPreinerWolfBiere-CAV18.pdf) (CAV 2018). These Yosys-synthesized designs (PicoRV32, PonyLink, VexRiscv, ZipCPU) were the seed material for the HWMCC'19 word-level track.

The collection is grouped by property count, then by track:

```text
benchmarks/cav18/2018/
├── multi/                          8 multi-property models, as published
│   ├── arrays/<model>.btor2
│   └── bv/zipcpu-busdelay.btor2
└── single/                         180 single-property models
    ├── arrays/ponylink-slaveTXlen-{sat,unsat}.btor2   published with one property
    ├── arrays/<model>/<model>-bNN.btor2               split from multi/arrays/<model>
    └── bv/zipcpu-busdelay/zipcpu-busdelay-bNN.btor2   split from multi/bv
```

| Model | Track | `bad` (= single-property splits) | `constraint` |
| --- | --- | --- | --- |
| `picorv32-check` | arrays | 23 | 2 |
| `picorv32-pcregs` | arrays | 3 | 0 |
| `VexRiscv-regch0-15`, `-20`, `-30` | arrays | 2 each | 3 |
| `zipcpu-pfcache` | arrays | 39 | 35 |
| `zipcpu-zipmmu` | arrays | 57 | 42 |
| `zipcpu-busdelay` | bv | 50 | 32 |
| `ponylink-slaveTXlen-sat`, `-unsat` | arrays | 1 each (single only) | 0 |

**Conversion.** The originals in the [artifact](https://fmv.jku.at/cav18-btor2/) (`cav18-materials.tar.xz`, directory `benchmarks/btor/`) use the pre-release BTOR2 dialect of Yosys 0.7. They have `output <sort> <node>` lines, the operator `ne`, and `init` values defined after their state, so they do not parse directly. As with HWMCC, download and extract the artifact yourself. [scripts/convert_legacy_btor2.py](../scripts/convert_legacy_btor2.py) rewrites outputs, renames `ne` to `neq`, and renumbers lines so each initial value precedes its state. It refuses to write a model unless the result parses and is node-for-node identical to the source under the renumbering, with inputs, states, outputs and properties in their original order (so `b0`, `b1`, … are unchanged).

**Splitting.** [scripts/split_properties.py](../scripts/split_properties.py) writes one file per `bad` directive, `<model>-bNN.btor2` for property `bNN`. Each split keeps every other line of the model unchanged, including all `constraint` lines, and drops only the other `bad` lines. Nothing is renumbered and no cone-of-influence reduction is applied, so a property has the same `property_id` in the multi and single reports. It refuses to write a split that does not parse or that changes any other line.

The archive has no top-level folder, so extract it into its own, then convert and split:

```sh
mkdir cav18 && tar -xJf cav18-materials.tar.xz -C cav18
B=benchmarks/cav18/2018
python scripts/convert_legacy_btor2.py cav18/benchmarks/btor/zipcpu-busdelay.btor --out $B/multi/bv
python scripts/convert_legacy_btor2.py $(ls cav18/benchmarks/btor/*.btor | grep -v -e busdelay -e ponylink) \
  --out $B/multi/arrays
python scripts/convert_legacy_btor2.py cav18/benchmarks/btor/ponylink-*.btor --out $B/single/arrays
python scripts/split_properties.py $B/multi/arrays/*.btor2 --out $B/single/arrays
python scripts/split_properties.py $B/multi/bv/*.btor2 --out $B/single/bv
```

**Comparing multi and single.** The default evaluation directory includes all of these. Select one side with `--filter`:

```sh
python scripts/evaluate.py --filter 'cav18/2018/multi/*' --out results/cav18-multi
python scripts/evaluate.py --filter 'cav18/2018/single/*/*/*' --out results/cav18-single
```

The second filter selects only the split files, leaving out the two PonyLink models, so both sides cover the same 178 properties. Join the two `comparison.csv` files on the model's family and `property_id`. Without `--reuse`, every property should get the same candidate and status counts on both sides: each property is analyzed under its own scope, which ignores other `bad` lines. On `zipcpu-busdelay` with `--budget-policy matched`, all 50 properties matched. Use `--reuse` with `btor2sieve extract` on the multi models to revalidate accepted facts across a model's properties, which the single side cannot do.

When comparing time, note that `cpu_seconds`, `wall_seconds` and `peak_memory_mib` in `comparison.csv` describe the whole benchmark process. A multi-property model repeats them on each of its property rows, so count them once per model rather than summing rows. `extraction_seconds` and `validation_seconds` are per property. In the run above, the multi model took 2.6 s in one process and its 50 splits took 14.9 s in total. Extraction plus validation took 0.4 s on both sides, so the difference is per-process setup.

## Evaluate implied extraction

From the repository root, after installing the project:

```sh
python scripts/evaluate.py --out results/hwmcc25-local
```

This evaluates native implied-constraint extraction under property scopes (`P = not bad`). It recursively discovers **all regular `.btor2` files** under `benchmarks/`, sorted by path. New files are included on the next run without updating a list. Archives and other file types are not model inputs; extract the archives before running. An empty or missing input directory produces an error before creating output.

To use another extracted directory, or select one track:

```sh
python scripts/evaluate.py --benchmarks /path/to/extracted/models --out results/all-models
python scripts/evaluate.py --benchmarks benchmarks/hwmcc/2025/arrays --out results/arrays
```

Relative `--benchmarks` paths are resolved from your current directory. The default always points to this repository’s `benchmarks/`, regardless of where you invoke the script. Output directories must be new.

For an evaluation across all local HWMCC models:

```sh
python scripts/evaluate.py --benchmarks benchmarks/hwmcc \
  --methods implied --budget-policy unlimited --out results/hwmcc-unlimited-limits
```

Every benchmark runs in its own extraction process with its own limits: 4 GiB memory (resident plus swapped), 300 s CPU time and 600 s wall
time. Change them with `--memory-limit-mib`, `--cpu-limit-s` and
`--wall-limit-s`. Limits require Linux. They apply to extraction, not to the
replays that follow it. Memory is sampled every 0.1 s together with the kernel's
peak-memory record, and a kernel CPU limit backs up the CPU check. Core dumps
are disabled for extraction processes.

`--jobs N` runs up to N benchmark processes at once; solver contexts are never
shared between threads. The default `--jobs auto`
starts as many workers as can each hold the full memory limit at the same time,
given the memory available at launch, capped at 16 and at the usable CPUs. An
explicit `--jobs` beyond that capacity is rejected before output is created.
Overcommitted workers could otherwise trigger the kernel's out-of-memory
killer, and more workers than CPUs would turn contention into wall-time limit
hits. `--jobs 1` runs one benchmark at a time with the same per-benchmark layout.

A benchmark that exceeds a limit is stopped and recorded as `memory-limit`,
`cpu-limit` or `wall-limit`, with its CPU time, wall time and peak memory. It
has no result: its unreported obligations are deleted, its logs are kept, and it
is not replayed. These limit outcomes are not tool failures. They do not make
an evaluation fail solely for reaching a limit when other benchmarks complete
their searches. If no search completes—for example, every benchmark hits a
resource limit—the evaluation remains incomplete and exits with code 1. A
process killed for any other reason is a failure.

Outputs contain `models/mNNNN/` with a complete report,
SMT obligations, and logs for each benchmark, plus a run-level `run-status.json`
updated as workers finish, including each benchmark's outcome and measured
resources. The aggregate JSON/CSVs aggregate models in input order with unique
IDs and artifact paths; its HTML report links to model reports. Its `results.json`
lists limit outcomes among `errors` with a `resource_limit` field, so replaying the
aggregate still reports that some benchmarks have no evidence.
`duration_seconds` is wall time, while `worker_seconds` and
`analysis_seconds` are summed worker and extraction-run times. Do not compare
those summed times directly with single-worker wall time as a speedup measurement.
Ctrl+C stops active workers and preserves completed model outputs; it does not
mark an interrupted experiment as complete or automatically resume it.

For a small evaluation, filter paths relative to the benchmark directory and take the first models in sorted order:

```sh
python scripts/evaluate.py --filter 'hwmcc/2025/bv/*' --limit 3 --out results/bv-trial
python scripts/evaluate.py --filter 'hwmcc/2025/arrays/*' --limit 3 --out results/array-trial
```

Quote `--filter` so your shell does not expand it. It uses case-sensitive shell-style matching against the entire relative path; `*` also matches directory separators. Filtering happens before `--limit`. A filter matching no models fails before creating output.

The only extraction mode is `implied`, selected by default. `--methods implied`
is accepted explicitly. Reports are written under `implied-constraints/`.

```sh
python scripts/evaluate.py --methods implied --limit 3 --out results/implied-trial
```

Only `property` scopes are supported. Other scopes are rejected before output is
created, keeping extraction under the safety property without adding initialization,
transition relations, or environment assumptions. The retired original `word-level`
method and its syntax/semantic evaluation modes are preserved in the movable
[archive](../archive/README.md).

## Supported archives

The [official competition format](https://hwmcc.github.io/2025/#format) specifies:

| Archive category | Suitability |
| --- | --- |
| Word-level BV | BTOR2 safety without arrays; supported input format |
| Word-level array | BTOR2 safety with arrays; supported input format |
| Bit-level safety | AIGER 1.9; not directly supported |
| Bit-level liveness | AIGER 1.9 and liveness semantics; not supported |
| Results CSVs, certificates, logs | Reference data, not model inputs |

The 225 local files inspected on 2026-11-09 (120 array-track and 105 BV-track files) all passed parsing and SMT encoding. Each had one `bad` property and no `fair` or `justice` declarations. This included 20 files in `liveness-l2s-*` folders: their transformed safety properties are usable. These counts describe that inspection, not a selection limit or a claim that the complete archives are present. Files added later require their own validation. The 8 multi-property and 180 single-property CAV'18 files (2026-11-10) parse with the property counts listed above. When they are present locally, `tests/test_convert_legacy.py` and `tests/test_split_properties.py` check this, including that each model's splits cover its properties in order.

## Results and limits

Evaluation replays accepted implications and all hypotheses with Z3 and cvc5. Install the `crosscheck` extra, or use `--skip-cvc5` for Z3-only replay. Replay does not establish model safety; run `btor2sieve verify` on an extraction report to model-check the properties with Pono.

`evaluation.json` records the input directory, selected paths, budgets, the requested and actual worker count with the memory available at launch, extraction summaries, extraction errors, and process/replay exit codes. Each run records `effective_settings` from its extraction report, including limits, scopes, constraint families, worker count, per-benchmark memory/CPU/wall limits, and replay settings, plus `outcomes` (benchmarks per outcome) and `resource_limits` (each benchmark stopped at a limit, with its measurements). The default unlimited policy records null candidate, term, width, and discovery-query limits for extraction. The run identifies `workflow = "property-word-level-v1"` and aggregates native term counts, proposal counts, and discovery queries/unknowns. The bounded `--budget-policy matched` selects workflow `property-word-level-budgeted-v1` and additionally records budget cutoffs. `comparison.csv` gives one row per model and scope, with `workflow`, the benchmark's `outcome`, `cpu_seconds`, `wall_seconds` and `peak_memory_mib`, status counts, extraction/validation times, and implied `search_*` fields for the same coverage metadata plus hypothesis result and reason. A benchmark stopped at a limit has one row with its outcome and measurements and no counts. Both include `output_directory`, a path relative to the evaluation directory, to locate each run's reports. Validation and family status counts describe actual independent checks, including rejected proposals.

Results use this layout:

```text
results/my-evaluation/
├── evaluation.json
├── comparison.csv
├── run-status.json
└── implied-constraints/
    ├── report.html
    ├── results.json
    ├── run-status.json
    └── models/mNNNN/   (report, obligations/, logs)
```

The extraction run also contains CSV reports, input SHA-256 hashes in
`results.json`, and extraction/replay logs. No pre-existing hash list is required.
Replay an aggregate run with:

```sh
python -m btor2sieve replay results/hwmcc25-local/implied-constraints --accepted-only
```

A failed extraction or replay is retained in `evaluation.json`. Successfully
analyzed models in a failed batch still contribute rows and replay evidence.
Extraction/replay failures and incomplete discovery or validation make evaluation
exit nonzero, even when accepted proofs replay successfully. Rejected proposals
do not fail a run on their own. Resource-limit outcomes alone do not fail a run
with completed searches, but a run with no completed search is incomplete and
exits with code 1. Check errors, limit outcomes, model coverage, and search completeness before
interpreting aggregate counts.

The default evaluation uses these settings:

| Setting | Value |
| --- | --- |
| Concurrent benchmark workers | `auto`: as many as can each hold the memory limit, at most 16 and the usable CPUs |
| Memory per benchmark | 4 GiB, resident plus swapped |
| CPU time per benchmark | 300 s |
| Wall time per benchmark | 600 s |
| Hypothesis | Selected property `P = not bad` |
| Constraint families | Signed/unsigned bit-vector bounds, equality, disequality, implication, masked-bit relations, arrays |
| Solver timeout | 1,000 ms per discovery/validation query |
| Candidate limit | Unlimited |
| Source-node selection limit | Unlimited |
| Discovery width limit | Unlimited; original widths retained |
| Discovery solver queries | Unlimited; each query still has a timeout |
| Cross-property reuse | Up to 30 queries per target property |
| Independent replay | Z3 and cvc5, 5,000 ms per query |

The default `--budget-policy unlimited` removes all four discovery limits. It
passes `--unlimited` to extraction and records the effective limits as null.
Solver UNKNOWN still stops semantic discovery; removing a query-count cap does
not disable that stopping rule or the per-query timeout.

For bounded extraction, select `--budget-policy matched`; omitted limits then
use 80 proposals, 12 source nodes, 64-bit selection width, and 96 discovery queries
per property. `--max-candidates`, `--max-terms`, `--max-width`, and `--max-queries`
can override those values. Explicit max-limit flags with the unlimited policy are
rejected rather than silently ignored. `--budget-policy method-defaults` uses
the extractor's uncapped default behavior.

Implied discovery combines finite typed templates with solver-guided bounds and known-bit masks. Every proposal receives its own `P and not C` validation. `search.complete` means the configured search and validation finished without an inconclusive solver result; `search.validation_complete` exposes the validation part separately. In matched mode, `search.coverage = "budgeted"` and `search.budget_exhausted` records candidate/query cutoffs. Reaching a budget is normal completion of a bounded run, not exhaustive extraction or a solver UNKNOWN. In uncapped mode, `search.coverage = "finite-cone"` describes the documented finite procedure, not all possible word-level constraints. Query timeouts remain visible as incomplete searches, and both direct implied extraction and evaluation return exit code 1 for those cases. Accepted counts measure independently proved formulas found by the configured search, not model-checking speedups.

The earlier Boolean state/combinational literal algorithm is archived in `archive/boolean-implications-method-2026-11-10.tar.gz`. Its historical run in `results/hwmcc-expanded-implied/evaluation.json` recorded 624,400 accepted Boolean basis formulas across 225 models. That run and its atom/witness/unit-redundancy metrics are historical; they do not describe the native workflow. Use fresh outputs and the workflow identifier when collecting or comparing new measurements.

Solver budgets are per query; the per-benchmark CPU and wall-time limits bound each extraction as a whole. Replay uses 5000 ms per query and has no process limit. Large collections can take substantial time and disk space; at 300 s CPU per benchmark, expect several hours for the full HWMCC set with 2 workers. For a smaller extraction-only run, pass selected files to `btor2sieve batch`, which has no process-wide limits. The local test suite checks the evaluator using tiny temporary models, so it does not depend on external benchmark datasets.
