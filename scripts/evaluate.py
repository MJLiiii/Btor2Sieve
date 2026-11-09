#!/usr/bin/env python3
"""Compare syntax/semantic extraction on all local BTOR2 benchmark collections."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new evaluation directory")
    parser.add_argument("--benchmarks", type=Path, default=ROOT / "benchmarks",
                        help="recursively scan this directory for .btor2 files (default: benchmarks)")
    parser.add_argument("--timeout-ms", type=int, default=200)
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--max-terms", type=int, default=12)
    parser.add_argument("--max-queries", type=int, default=96)
    parser.add_argument("--skip-cvc5", action="store_true", help="only replay with Z3")
    args = parser.parse_args()
    if min(args.timeout_ms, args.max_candidates, args.max_terms, args.max_queries) <= 0:
        parser.error("all budgets must be positive")
    args.benchmarks = args.benchmarks.resolve()
    files = [str(p) for p in sorted(args.benchmarks.rglob("*.btor2")) if p.is_file()]
    if not files:
        parser.error(f"No .btor2 files found under {args.benchmarks}; extract your benchmarks there first")
    destination = args.out.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    evaluation = {"configuration": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                  "benchmarks": len(files), "input_files": files, "runs": {}}
    (destination / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
    print(f"Evaluating all {len(files)} BTOR2 files under {args.benchmarks}", flush=True)
    for mode in ("syntax", "semantic"):
        out = destination / mode
        command = [sys.executable, "-m", "btor2sieve", "batch", *files, "--out", str(out),
                   "--max-candidates", str(args.max_candidates), "--max-terms", str(args.max_terms),
                   "--max-queries", str(args.max_queries), "--timeout-ms", str(args.timeout_ms),
                   "--reuse", "--max-reuse", "30"]
        if mode == "syntax":
            command.append("--syntax-only")
        subprocess.run(command, cwd=ROOT, check=True)
        report = json.loads((out / "results.json").read_text())
        records = [r for r in report["records"] if not r["reuse_from"]]
        families = {}
        for row in records:
            families.setdefault(row["family"], Counter())[row["status"]] += 1
        run = {"command": command, "models": len(report["models"]), "scopes": len(report["summaries"]),
               "candidates": len(records), "counts": dict(Counter(r["status"] for r in records)),
               "families": {k: dict(v) for k, v in sorted(families.items())},
               "reuse": dict(Counter(r["status"] for r in report["records"] if r["reuse_from"])),
               "duration_seconds": report["duration_seconds"],
               "extraction_seconds": sum(s["extraction_seconds"] for s in report["summaries"]),
               "validation_seconds": sum(s["validation_seconds"] for s in report["summaries"]),
               "replay": {}}
        for backend in (("z3",) if args.skip_cvc5 else ("z3", "cvc5")):
            cmd = [sys.executable, "-m", "btor2sieve", "replay", str(out), "--accepted-only",
                   "--backend", backend, "--timeout-ms", "5000"]
            completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            (out / f"replay-{backend}.json").write_text(completed.stdout)
            if completed.stderr:
                (out / f"replay-{backend}.stderr.txt").write_text(completed.stderr)
            replay = json.loads(completed.stdout)
            run["replay"][backend] = {k: v for k, v in replay.items() if k != "checks"}
            if completed.returncode:
                evaluation["runs"][mode] = run
                (destination / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
                raise RuntimeError(f"{backend} replay failed; inspect {out}")
        evaluation["runs"][mode] = run
        (destination / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
        print(f"{mode}: {run['candidates']} candidates, {run['counts']}, independent replay passed", flush=True)
    print(f"Evaluation: {destination / 'evaluation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
