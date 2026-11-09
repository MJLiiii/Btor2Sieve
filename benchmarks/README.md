# Benchmark datasets

Organize local datasets as `benchmarks/<source>/<year>/<track>/`. For [HWMCC’25](https://zenodo.org/records/17428464), download and extract the word-level archives yourself, then place their contents as follows:

| Archive | Dataset directory |
| --- | --- |
| `hwmcc25-benchmarks-wordlevel-bv.tar.gz` | `benchmarks/hwmcc/2025/bv/` |
| `hwmcc25-benchmarks-wordlevel-array.tar.gz` | `benchmarks/hwmcc/2025/arrays/` |

Keep the upstream family folders and model filenames inside each track. If extraction creates a track wrapper directory, move its contents into the corresponding directory above. Use lowercase source and track names; future sources and years get sibling directories under the same convention. These names organize the data and do not filter evaluation. The project does not download or extract archives and has no fixed corpus manifest.

## Evaluate every local model

From the repository root, after installing the project:

```sh
python scripts/evaluate.py --out results/hwmcc25-local
```

This recursively discovers **all regular `.btor2` files** under `benchmarks/`, sorted by path. New files are included on the next run without updating a list. Archives and other file types are not model inputs; extract the archives before running. An empty or missing input directory produces an error before creating output.

To use another extracted directory, or select one track:

```sh
python scripts/evaluate.py --benchmarks /path/to/extracted/models --out results/all-models
python scripts/evaluate.py --benchmarks benchmarks/hwmcc/2025/arrays --out results/arrays
```

Relative `--benchmarks` paths are resolved from your current directory. The default always points to this repository’s `benchmarks/`, regardless of where you invoke the script. Output directories must be new.

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

Evaluation compares syntax and semantic extraction and replays accepted implications and all hypotheses with Z3 and cvc5. Install the `crosscheck` extra, or use `--skip-cvc5` for Z3-only replay. It does not invoke Pono or establish model safety.

`evaluation.json` records the input directory, selected paths, budgets, and completed mode summaries. Each mode’s `results.json` records input SHA-256 hashes and analysis errors, alongside the HTML/CSV reports and SMT obligations. No pre-existing hash list is required. A failed batch or replay causes evaluation to exit unsuccessfully; inspect the output for details.

Solver budgets are per query, not total runtime limits. Large collections can take substantial time and disk space. For a smaller extraction-only run, pass selected files to `btor2sieve batch`. The local test suite checks the evaluator using tiny temporary models, so it does not depend on external benchmark datasets.
