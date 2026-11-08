# Small public BTOR2 corpus

This corpus contains 13 unmodified upstream BTOR2 files (49,024 bytes) for frontend validation and reproducible extraction experiments. It is deliberately small and does not support competition-scale performance claims. Original `.btor` files have `.btor2` filenames here; their contents are unchanged.

The manifest records pinned raw URLs, SHA-256 hashes, byte and structural counts, license paths, and provenance. Four Mann files are byte-identical to the corresponding entries in the HWMCC19 mirror: safe analog estimation, unsafe intersymbol analog estimation, and both arbitrated FIFOs. Two further Mann files are clearly labeled family examples; exact selected competition membership was not established. The seven Btor2Tools/Pono files are upstream regression examples, not claimed competition entries.

| Group | Files | Coverage |
| --- | ---: | --- |
| Makai Mann hardware family | 6 | Four BV circuits, two array FIFOs, state/input constraints, missing next assignments |
| Btor2Tools examples | 3 | Two bad properties, negative references, constraints, uninitialized states |
| Pono regressions | 4 | Constant arrays, array-valued ite, missing next, ten rotation properties |

All 13 files were accepted by the official Btor2Tools `catbtor`, built from commit `e6941e37e056084ab6e51c5c1eee6233089a330d`, on 2026-11-08. The manifest's `safe`/`unsafe` values are upstream source-directory labels, not new model-checking conclusions. Multiple bad conditions may have different truth values; labels must not be inferred for each from a file name.

Verify the vendored files without network access:

```sh
python3 scripts/fetch_benchmarks.py --check
```

Restore missing files from their pinned original sources:

```sh
python3 scripts/fetch_benchmarks.py
```

The fetcher verifies exact size and SHA-256 before installing each file and refuses to overwrite existing differing data. For a fresh independent download, use `--destination /tmp/btor2sieve-corpus`; the same layout is written under that directory. License notices are included in `public/licenses/`: Mann and Pono are BSD-3-Clause; Btor2Tools is MIT.

See [the research note](../docs/research/btor2-frontend.md) and [manifest.json](manifest.json) for source links, distinctions between selected HWMCC files and family membership, and exact versions.
