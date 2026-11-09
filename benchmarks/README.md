# Benchmark datasets

Organize local datasets as `benchmarks/<source>/<year>/<track>/`. For [HWMCC’25](https://zenodo.org/records/17428464), download and extract the word-level archives yourself, then place their contents as follows:

| Archive | Dataset directory |
| --- | --- |
| `hwmcc25-benchmarks-wordlevel-bv.tar.gz` | `benchmarks/hwmcc/2025/bv/` |
| `hwmcc25-benchmarks-wordlevel-array.tar.gz` | `benchmarks/hwmcc/2025/arrays/` |

Keep the upstream family folders and model filenames inside each track. If extraction creates a track wrapper directory, move its contents into the corresponding directory above. Use lowercase source and track names; future sources and years get sibling directories under the same convention. These names organize the data and do not filter evaluation. The project does not download or extract archives and has no fixed corpus manifest.

## Compare extraction methods

From the repository root, after installing the project:

```sh
python scripts/evaluate.py --out results/hwmcc25-local
```

This compares the existing semantic word-level method with the paper's implied-constraint method on the same property scopes (`P = not bad`). It recursively discovers **all regular `.btor2` files** under `benchmarks/`, sorted by path. New files are included on the next run without updating a list. Archives and other file types are not model inputs; extract the archives before running. An empty or missing input directory produces an error before creating output.

To use another extracted directory, or select one track:

```sh
python scripts/evaluate.py --benchmarks /path/to/extracted/models --out results/all-models
python scripts/evaluate.py --benchmarks benchmarks/hwmcc/2025/arrays --out results/arrays
```

Relative `--benchmarks` paths are resolved from your current directory. The default always points to this repository’s `benchmarks/`, regardless of where you invoke the script. Output directories must be new.

For a small comparison, filter paths relative to the benchmark directory and take the first models in sorted order:

```sh
python scripts/evaluate.py --filter 'hwmcc/2025/bv/*' --limit 3 --out results/bv-trial
python scripts/evaluate.py --filter 'hwmcc/2025/arrays/*' --limit 3 --out results/array-trial
```

Quote `--filter` so your shell does not expand it. It uses case-sensitive shell-style matching against the entire relative path; `*` also matches directory separators. Filtering happens before `--limit`. A filter matching no models fails before creating output.

Select modes explicitly with `--methods`:

| Mode | Extraction | Output directory |
| --- | --- | --- |
| `semantic` | Existing word-level method, with syntax templates and solver-guided discovery | `word-level/semantic/` |
| `syntax` | Existing word-level method with solver-guided discovery disabled | `word-level/syntax/` |
| `implied` | Paper method: implications between selected Boolean state literals | `implied-constraints/` |

The default is `--methods semantic implied --scopes property`. To reproduce the previous syntax/semantic comparison and its scopes, or run only the paper method:

```sh
python scripts/evaluate.py --methods syntax semantic --scopes property,model --out results/word-level-ablation
python scripts/evaluate.py --methods implied --limit 3 --out results/implied-trial
```

All selected methods use the same scopes. When `implied` is selected, only `property` is allowed; incompatible scopes are rejected before output is created. This keeps the comparison under the paper's property hypothesis without adding initialization, transitions, or environment assumptions.

## Supported archives

The [official competition format](https://hwmcc.github.io/2025/#format) specifies:

| Archive category | Suitability |
| --- | --- |
| Word-level BV | BTOR2 safety without arrays; supported input format |
| Word-level array | BTOR2 safety with arrays; supported input format |
| Bit-level safety | AIGER 1.9; not directly supported |
| Bit-level liveness | AIGER 1.9 and liveness semantics; not supported |
| Results CSVs, certificates, logs | Reference data, not model inputs |

The 225 local files inspected on 2026-11-09 (120 array-track and 105 BV-track files) all passed parsing and SMT encoding. Each had one `bad` property and no `fair` or `justice` declarations. This included 20 files in `liveness-l2s-*` folders: their transformed safety properties are usable. These counts describe that inspection, not a selection limit or a claim that the complete archives are present. Files added later require their own validation.

## Results and limits

Evaluation replays accepted implications and all hypotheses with Z3 and cvc5. Install the `crosscheck` extra, or use `--skip-cvc5` for Z3-only replay. It does not invoke Pono or establish model safety.

`evaluation.json` records the input directory, selected paths, budgets, mode summaries, extraction errors, and process/replay exit codes. `comparison.csv` gives one row per mode, model, and scope, with status counts and extraction/validation times. Both include `output_directory`, a path relative to the evaluation directory, to locate each run's reports.

Results are grouped by extraction method. For a run selecting all three modes, the layout is:

```text
results/my-evaluation/
├── evaluation.json
├── comparison.csv
├── word-level/
│   ├── semantic/
│   │   ├── report.html
│   │   ├── results.json
│   │   └── obligations/
│   └── syntax/
│       ├── report.html
│       ├── results.json
│       └── obligations/
└── implied-constraints/
    ├── report.html
    ├── results.json
    └── obligations/
```

Only selected modes get directories; the default run creates `word-level/semantic/` and `implied-constraints/`. Each run also contains CSV reports, input SHA-256 hashes in `results.json`, and extraction/replay logs. No pre-existing hash list is required. For example, replay the two default runs independently with:

```sh
python -m btor2sieve replay results/hwmcc25-local/word-level/semantic --accepted-only
python -m btor2sieve replay results/hwmcc25-local/implied-constraints --accepted-only
```

A failed extraction or replay is retained in `evaluation.json`, and evaluation continues with the other methods. Successfully analyzed models in a failed batch still contribute comparison rows and replay evidence. Any failed mode makes the final exit status nonzero; compare the errors and model coverage before interpreting aggregate counts.

Shared defaults are `--timeout-ms 200 --max-candidates 80 --max-terms 12 --max-width 64 --max-queries 96`. For word-level extraction, `max_terms` bounds discovery terms and `max_queries` bounds discovery solver calls. For implied extraction, `max_terms` bounds selected state bits; `max_queries` is unused because each proposed implication goes directly to independent validation. Array states and words wider than `max_width` are excluded from its literal vocabulary. Candidate counts describe different vocabularies, not equivalent coverage or model-checking speedups.

Solver budgets are per query, not total runtime limits; replay uses 5000 ms per query. Large collections can take substantial time and disk space. For a smaller extraction-only run, pass selected files to `btor2sieve batch`. The local test suite checks the evaluator using tiny temporary models, so it does not depend on external benchmark datasets.
