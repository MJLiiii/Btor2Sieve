#!/usr/bin/env python3
"""Compare word-level and implied-constraint extraction on local BTOR2 models."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from fnmatch import fnmatchcase
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_FIELDS = [
    "mode", "method", "output_directory", "model", "scope", "property_id", "candidates", "accepted",
    "rejected", "unknown", "vacuous", "extraction_seconds", "validation_seconds",
    "hypothesis_result", "hypothesis_seconds",
]


def _save(destination: Path, evaluation: dict, comparison: list[dict]) -> None:
    (destination / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
    with (destination / "comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, COMPARISON_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(comparison)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new evaluation directory")
    parser.add_argument("--benchmarks", type=Path, default=ROOT / "benchmarks",
                        help="recursively scan this directory for .btor2 files (default: benchmarks)")
    parser.add_argument("--methods", nargs="+", choices=("syntax", "semantic", "implied"),
                        default=["semantic", "implied"], help="modes to compare (default: semantic implied)")
    parser.add_argument("--scopes", default="property", help="shared comma-separated scopes (default: property)")
    parser.add_argument("--filter", default="*", help="shell-style glob on paths relative to --benchmarks; * matches / too")
    parser.add_argument("--limit", type=int, help="maximum number of models after filtering and sorting")
    parser.add_argument("--timeout-ms", type=int, default=200)
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--max-terms", type=int, default=12)
    parser.add_argument("--max-width", type=int, default=64)
    parser.add_argument("--max-queries", type=int, default=96)
    parser.add_argument("--skip-cvc5", action="store_true", help="only replay with Z3")
    args = parser.parse_args()
    if min(args.timeout_ms, args.max_candidates, args.max_terms, args.max_width, args.max_queries) <= 0:
        parser.error("all budgets must be positive")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    scopes = args.scopes.split(",")
    if any(scope not in {"property", "model", "initial", "transition"} for scope in scopes):
        parser.error("scopes must be chosen from property,model,initial,transition")
    if "implied" in args.methods and set(scopes) != {"property"}:
        parser.error("implied extraction requires --scopes property")
    args.methods = list(dict.fromkeys(args.methods))
    args.benchmarks = args.benchmarks.resolve()
    files = [str(p) for p in sorted(args.benchmarks.rglob("*.btor2"))
             if p.is_file() and fnmatchcase(p.relative_to(args.benchmarks).as_posix(), args.filter)]
    files = files[:args.limit]
    if not files:
        parser.error(f"No .btor2 files found under {args.benchmarks} matching {args.filter!r}")
    destination = args.out.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    evaluation = {"configuration": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                  "benchmarks": len(files), "input_files": files, "runs": {}}
    comparison = []
    _save(destination, evaluation, comparison)
    failed = False
    print(f"Evaluating {len(files)} selected BTOR2 files under {args.benchmarks}", flush=True)
    for mode in args.methods:
        output_directory = "implied-constraints" if mode == "implied" else f"word-level/{mode}"
        out = destination / output_directory
        method = "implied" if mode == "implied" else "word-level"
        command = [sys.executable, "-m", "btor2sieve", "batch", *files, "--out", str(out),
                   "--method", method, "--scopes", args.scopes, "--max-width", str(args.max_width),
                   "--max-candidates", str(args.max_candidates), "--max-terms", str(args.max_terms),
                   "--max-queries", str(args.max_queries), "--timeout-ms", str(args.timeout_ms),
                   "--reuse", "--max-reuse", "30"]
        if mode == "syntax":
            command.append("--syntax-only")
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        out.mkdir(parents=True, exist_ok=True)
        (out / "extract.stdout.txt").write_text(completed.stdout)
        (out / "extract.stderr.txt").write_text(completed.stderr)
        run = {"command": command, "method": method, "output_directory": output_directory,
               "returncode": completed.returncode,
               "errors": [], "replay": {}}
        evaluation["runs"][mode] = run
        try:
            report = json.loads((out / "results.json").read_text())
        except (OSError, ValueError) as exc:
            run["errors"].append({"error": f"Cannot read extraction report: {exc}"})
            failed = True
            _save(destination, evaluation, comparison)
            print(f"{mode}: extraction failed; inspect {out}", flush=True)
            continue
        run["errors"] = report["errors"]
        run_failed = bool(completed.returncode or run["errors"])
        records = [r for r in report["records"] if not r["reuse_from"]]
        families = {}
        for row in records:
            families.setdefault(row["family"], Counter())[row["status"]] += 1
        run.update({"models": len(report["models"]), "scopes": len(report["summaries"]),
               "candidates": len(records), "counts": dict(Counter(r["status"] for r in records)),
               "families": {k: dict(v) for k, v in sorted(families.items())},
               "reuse": dict(Counter(r["status"] for r in report["records"] if r["reuse_from"])),
               "duration_seconds": report["duration_seconds"],
               "extraction_seconds": sum(s["extraction_seconds"] for s in report["summaries"]),
               "validation_seconds": sum(s["validation_seconds"] for s in report["summaries"])})
        comparison.extend({"mode": mode, "method": method, "output_directory": output_directory,
                           **summary} for summary in report["summaries"])
        _save(destination, evaluation, comparison)
        for backend in (("z3",) if args.skip_cvc5 else ("z3", "cvc5")):
            cmd = [sys.executable, "-m", "btor2sieve", "replay", str(out), "--accepted-only",
                   "--backend", backend, "--timeout-ms", "5000"]
            completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            (out / f"replay-{backend}.json").write_text(completed.stdout)
            if completed.stderr:
                (out / f"replay-{backend}.stderr.txt").write_text(completed.stderr)
            try:
                replay = json.loads(completed.stdout)
                if not isinstance(replay, dict):
                    raise ValueError("expected a replay result object")
                replay = {k: v for k, v in replay.items() if k != "checks"}
            except ValueError as exc:
                replay = {"error": f"Cannot read replay report: {exc}"}
            run["replay"][backend] = {**replay, "returncode": completed.returncode}
            if completed.returncode or "error" in replay:
                run_failed = True
        failed |= run_failed
        _save(destination, evaluation, comparison)
        outcome = "failed; inspect output" if run_failed else "independent replay passed"
        print(f"{mode}: {run['candidates']} candidates, {run['counts']}, {outcome}", flush=True)
    print(f"Evaluation: {destination / 'evaluation.json'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
