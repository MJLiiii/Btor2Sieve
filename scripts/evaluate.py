#!/usr/bin/env python3
"""Evaluate implied-constraint extraction on local BTOR2 models."""

from __future__ import annotations

import argparse
import csv
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODE = "implied"
OUTPUT_DIRECTORY = "implied-constraints"
MAX_AUTO_JOBS = 16
MATCHED_DEFAULTS = {"max_candidates": 80, "max_terms": 12, "max_width": 64, "max_queries": 96}
SEARCH_FIELDS = ["kind", "term_count", "predicate_count", "total_candidates", "discovery_queries",
                 "discovery_unknown", "complete", "validation_complete", "coverage",
                 "budget_exhausted", "hypothesis_result", "reason"]
COMPARISON_FIELDS = [
    "mode", "method", "workflow", "output_directory", "model", "outcome", "cpu_seconds", "wall_seconds",
    "peak_memory_mib", "scope", "property_id", "candidates", "accepted",
    "rejected", "unknown", "vacuous", "extraction_seconds", "validation_seconds",
    "hypothesis_result", "hypothesis_seconds", *(f"search_{key}" for key in SEARCH_FIELDS),
]


def _jobs(text: str) -> int | str:
    if text == "auto":
        return text
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer or 'auto'")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new evaluation directory")
    parser.add_argument("--benchmarks", type=Path, default=ROOT / "benchmarks",
                        help="recursively scan this directory for .btor2 files (default: benchmarks)")
    parser.add_argument("--methods", nargs="+", choices=(MODE,), default=[MODE],
                        help="extraction method (default and only choice: implied)")
    parser.add_argument("--scopes", default="property", help="property scope (the only supported scope)")
    parser.add_argument("--filter", default="*", help="shell-style glob on paths relative to --benchmarks; * matches / too")
    parser.add_argument("--limit", type=int, help="maximum number of models after filtering and sorting")
    parser.add_argument("--timeout-ms", type=int, default=1000)
    parser.add_argument("--max-candidates", type=int, help="proposal budget with a bounded policy (default: 80)")
    parser.add_argument("--max-terms", type=int, help="source-node budget with a bounded policy (default: 12)")
    parser.add_argument("--max-width", type=int, help="discovery width with a bounded policy (default: 64)")
    parser.add_argument("--max-queries", type=int, help="discovery query budget with a bounded policy (default: 96)")
    parser.add_argument("--budget-policy", choices=("unlimited", "matched", "method-defaults"), default="unlimited",
                        help="unlimited discovery (default), finite matched budgets, or uncapped method defaults")
    parser.add_argument("--memory-limit-mib", type=int, default=4096,
                        help="resident plus swapped memory per benchmark (default: 4096 = 4 GiB)")
    parser.add_argument("--cpu-limit-s", type=int, default=300,
                        help="CPU seconds per benchmark (default: 300)")
    parser.add_argument("--wall-limit-s", type=int, default=600,
                        help="wall-clock seconds per benchmark (default: 600)")
    parser.add_argument("--jobs", type=_jobs, default="auto",
                        help="concurrent benchmark processes; auto (default) uses as many as can each be "
                             f"guaranteed the memory limit, at most {MAX_AUTO_JOBS} and the usable CPUs")
    parser.add_argument("--skip-cvc5", action="store_true", help="only replay with Z3")
    return parser


def _check_arguments(parser: argparse.ArgumentParser, args) -> None:
    """Validate budgets and limits, filling matched-policy defaults. Exits on error."""
    if args.budget_policy == "unlimited":
        if any(getattr(args, key) is not None for key in MATCHED_DEFAULTS):
            parser.error("--max-* limits cannot be combined with unlimited discovery; "
                         "select --budget-policy matched or method-defaults")
    else:
        for key, default in MATCHED_DEFAULTS.items():
            if getattr(args, key) is None:
                setattr(args, key, default)
    if args.timeout_ms <= 0 or any(getattr(args, key) is not None and getattr(args, key) <= 0
                                   for key in MATCHED_DEFAULTS):
        parser.error("all budgets must be positive")
    for flag in ("memory_limit_mib", "cpu_limit_s", "wall_limit_s"):
        if getattr(args, flag) <= 0:
            parser.error(f"--{flag.replace('_', '-')} must be positive")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    if set(args.scopes.split(",")) != {"property"}:
        parser.error("implied extraction requires --scopes property")
    args.methods = list(dict.fromkeys(args.methods))


def _select_files(parser: argparse.ArgumentParser, args) -> list[str]:
    """Every .btor2 file under --benchmarks matching --filter, sorted, up to --limit."""
    args.benchmarks = args.benchmarks.resolve()
    files = [str(path) for path in sorted(args.benchmarks.rglob("*.btor2"))
             if path.is_file() and fnmatchcase(path.relative_to(args.benchmarks).as_posix(), args.filter)]
    files = files[:args.limit]
    if not files:
        parser.error(f"No .btor2 files found under {args.benchmarks} matching {args.filter!r}")
    return files


def _available_memory() -> int:
    with open("/proc/meminfo") as stream:
        for line in stream:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) << 10
    raise OSError("/proc/meminfo has no MemAvailable entry")


def _usable_cpus() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def _choose_jobs(parser: argparse.ArgumentParser, args) -> None:
    """Run only as many workers as can each hold the full memory limit at once.

    Overcommitted workers can trigger the kernel's OOM killer, and CPU
    oversubscription would turn contention into wall-time limit hits.
    """
    try:
        available = _available_memory()
    except OSError as exc:
        parser.error(f"per-benchmark memory limits require Linux /proc/meminfo: {exc}")
    cpus = _usable_cpus()
    per_job = args.memory_limit_mib << 20
    capacity = min(cpus, available // per_job)
    args.requested_jobs, args.memory_available_bytes = args.jobs, available
    if capacity < 1:
        parser.error(f"only {available >> 20} MiB of memory is available, less than "
                     f"--memory-limit-mib {args.memory_limit_mib} for one benchmark")
    if args.jobs == "auto":
        args.jobs = min(MAX_AUTO_JOBS, capacity)
    elif args.jobs > capacity:
        reasons = []
        if args.jobs > cpus:
            reasons.append(f"the {cpus} usable CPUs")
        if args.jobs * per_job > available:
            reasons.append(f"{available >> 20} MiB available memory at {args.memory_limit_mib} MiB per benchmark")
        parser.error(f"--jobs {args.jobs} exceeds {' and '.join(reasons)}; use --jobs {capacity} or fewer")


def _effective_settings(args, configuration: dict) -> dict:
    """Record the extraction limits actually reported by the extractor."""
    return {
        **{key: configuration.get(key) for key in
           ("scopes", "max_candidates", "max_terms", "max_width", "max_queries", "timeout_ms",
            "reuse", "max_reuse", "constraint_families", "budget_policy")},
        "jobs": args.jobs,
        "memory_limit_mib": args.memory_limit_mib,
        "cpu_limit_s": args.cpu_limit_s,
        "wall_limit_s": args.wall_limit_s,
        "replay_timeout_ms": 5000,
        "replay_backends": ["z3"] if args.skip_cvc5 else ["z3", "cvc5"],
    }


def _save(destination: Path, evaluation: dict, comparison: list[dict]) -> None:
    (destination / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
    with (destination / "comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, COMPARISON_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(comparison)


def _save_status(destination: Path, status: str, jobs: int) -> None:
    """Top-level run-status.json; the extraction directory has its own detailed one."""
    (destination / "run-status.json").write_text(json.dumps({
        "status": status, "mode": MODE, "jobs": jobs,
        "method_status": f"{OUTPUT_DIRECTORY}/run-status.json",
    }, indent=2) + "\n")


def _print_run(run: dict) -> None:
    outcomes = ", ".join(f"{count} {name}" for name, count in sorted(run["outcomes"].items()))
    print(f"{MODE}: {run['candidates']} candidates, {dict(run['counts'])}, {run['status']} "
          f"({outcomes})", flush=True)
    search = run["search"]
    completion = "complete" if search["complete"] and search["validation_complete"] else "partial"
    coverage = (f"{completion} budgeted search" if search["coverage"] == "budgeted"
                else f"{completion} finite template coverage")
    print(f"implied search: {search['term_count']} native terms, "
          f"{search['total_candidates']} proposals, "
          f"{search['discovery_queries']} discovery queries, "
          f"{search['discovery_unknown']} discovery unknown, "
          f"{coverage}", flush=True)


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    _check_arguments(parser, args)
    files = _select_files(parser, args)
    _choose_jobs(parser, args)

    destination = args.out.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    evaluation = {"configuration": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                  "benchmarks": len(files), "input_files": files, "runs": {}}
    comparison: list[dict] = []
    _save(destination, evaluation, comparison)
    # Imported here so that this file can be loaded on its own (e.g. by tests).
    from parallel_evaluate import run_parallel

    print(f"Evaluating {len(files)} selected BTOR2 files under {args.benchmarks} with {args.jobs} "
          f"worker{'s' if args.jobs > 1 else ''}; limits per benchmark: "
          f"{args.memory_limit_mib} MiB memory, {args.cpu_limit_s} s CPU, {args.wall_limit_s} s wall", flush=True)
    out = destination / OUTPUT_DIRECTORY
    _save_status(destination, "running", args.jobs)
    try:
        run, rows, failed = run_parallel(args, files, out)
    except (KeyboardInterrupt, Exception) as exc:
        interrupted = isinstance(exc, KeyboardInterrupt)
        state = "interrupted" if interrupted else "failed"
        evaluation["runs"][MODE] = {
            "status": state, "method": MODE, "output_directory": OUTPUT_DIRECTORY,
            "jobs": args.jobs, "errors": [{"error": str(exc) or "Evaluation interrupted"}],
        }
        _save(destination, evaluation, comparison)
        _save_status(destination, state, args.jobs)
        print(f"{MODE}: {state}; per-model reports preserved in {out / 'models'}", flush=True)
        if interrupted:
            return 130
        raise

    run["effective_settings"] = _effective_settings(args, run.pop("extraction_configuration", {}))
    evaluation["runs"][MODE] = run
    comparison.extend(rows)
    _save(destination, evaluation, comparison)
    _print_run(run)
    (destination / "run-status.json").write_text(json.dumps({
        "status": "failed" if failed else "completed", "jobs": args.jobs,
        "methods": {MODE: run["status"]},
    }, indent=2) + "\n")
    print(f"Evaluation: {destination / 'evaluation.json'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
