"""Command-line interface: inspect, extract/batch, replay, and verify."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import z3

from . import __version__
from . import verify as verification
from .pono import ENGINES, features, pono_identity, read_model
from .implied import BUDGET_NAMES, GenerationOptions
from .pipeline import analyze
from .reporting import write_report
from .replay import replay


def _positive(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract BTOR2 word-level constraints with independent SMT validation.")
    parser.add_argument("--version", action="version", version=f"Btor2Sieve {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="have Pono read a model and list its features")
    inspect.add_argument("model", type=Path)
    inspect.add_argument("--json", action="store_true")
    inspect.add_argument("--pono", default="pono", help="Pono executable (default: pono on PATH)")
    for command in ("extract", "batch"):
        run = commands.add_parser(command, help="extract and validate " + ("one model" if command == "extract" else "a set of models"))
        run.add_argument("models", type=Path, nargs=1 if command == "extract" else "+")
        run.add_argument("--out", type=Path, required=True, help="new output directory (never overwritten)")
        run.add_argument("--method", choices=("implied",), default="implied",
                         help="property-implied extraction (the default and only method)")
        run.add_argument("--scopes", help="property only (default); no model or reachability assumptions")
        run.add_argument("--property", dest="property_id", type=_positive, help="select one bad directive ID")
        profile = run.add_mutually_exclusive_group()
        profile.add_argument("--matched-budgets", action="store_true",
                             help="enable candidate, source-term, width, and discovery-query budgets")
        profile.add_argument("--unlimited", action="store_true",
                             help="property-only extraction without candidate, source-term, width, or query caps")
        run.add_argument("--max-candidates", type=_positive,
                         help="per-scope proposal budget (default: 200; implied requires --matched-budgets)")
        run.add_argument("--max-terms", type=_positive,
                         help="per-scope source-node budget (default: 16; implied requires --matched-budgets)")
        run.add_argument("--max-width", type=_positive,
                         help="source selection width limit (default: 64; implied requires --matched-budgets)")
        run.add_argument("--max-queries", type=_positive,
                         help="discovery query budget (default: 256; implied requires --matched-budgets)")
        run.add_argument("--timeout-ms", type=_positive, default=1000, help="timeout per SMT query, in milliseconds")
        run.add_argument("--reuse", action="store_true", help="revalidate accepted property facts against other properties")
        run.add_argument("--max-reuse", type=_positive, default=100, help="reuse query limit per target property")
        run.add_argument("--pono", default="pono", help="Pono executable (default: pono on PATH)")
        run.add_argument("--pono-timeout", type=_positive, default=300,
                         help="seconds Pono may take to print one property (default: 300)")
    replay = commands.add_parser("replay", help="recheck exported obligations with Z3 or independent cvc5")
    replay.add_argument("input", type=Path, help="report directory, results.json, or one .smt2 file")
    replay.add_argument("--backend", choices=("z3", "cvc5"), default="z3")
    replay.add_argument("--timeout-ms", type=_positive, default=5000)
    replay.add_argument("--accepted-only", action="store_true")
    verify = commands.add_parser(
        "verify", help="model-check each property with Pono, with and without the accepted constraints")
    verify.add_argument("input", type=Path, help="report directory or results.json from extract/batch")
    verify.add_argument("--out", type=Path, required=True, help="new output directory (never overwritten)")
    verify.add_argument("--pono", default="pono", help="Pono executable (default: pono on PATH)")
    verify.add_argument("--engine", dest="engines", action="append", choices=ENGINES,
                        help="Pono engine; repeat for several (default: ic3ia)")
    verify.add_argument("--bound", type=_positive, default=1000, help="Pono -k bound (default: 1000)")
    verify.add_argument("--timeout", type=_positive, default=60,
                        help="wall-clock limit per Pono run, in seconds (default: 60)")
    verify.add_argument("--keep-files", action="store_true", help="keep the generated BTOR2 files")
    return parser


def _inspect(args) -> int:
    model = read_model(pono_identity(args.pono)["path"], args.model)  # Pono must read every property.
    result = {"model": str(args.model), **features(model.lines), "bad_ids": model.bad_ids}
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"{args.model}: {result['nodes']} nodes, {result['states']} states, "
          f"{result['inputs']} inputs, {result['properties']} safety properties, "
          f"{result['array_sorts']} array sorts")
    if result["liveness_nodes"]:
        print("Fair/justice declarations present; extraction analyzes safety only.")
    return 0


def _options(parser: argparse.ArgumentParser, args) -> GenerationOptions:
    """Turn the budget flags into options: unlimited, matched, or unenforced defaults."""
    budgets = {name: getattr(args, name) for name in BUDGET_NAMES}
    if args.unlimited:
        if any(value is not None for value in budgets.values()):
            parser.error("--unlimited cannot be combined with --max-candidates, --max-terms, "
                         "--max-width, or --max-queries")
    else:
        defaults = GenerationOptions()
        budgets = {name: getattr(defaults, name) if value is None else value
                   for name, value in budgets.items()}
    return GenerationOptions(**budgets, timeout_ms=args.timeout_ms,
                             matched_budgets=args.matched_budgets)


def _print_summary(report: dict, output: Path, matched: bool) -> bool:
    """Print totals and return True if every property's search and validation completed."""
    base = [record for record in report["records"] if not record["reuse_from"]]
    accepted = sum(summary["accepted"] for summary in report["summaries"])
    print(f"{len(report['models'])} models · {len(base)} candidates · {accepted} accepted · "
          f"{len(report['errors'])} errors\nReport: {output.resolve() / 'report.html'}")
    searches = [summary.get("search", {}) for summary in report["summaries"]]
    counts = {key: sum(search.get(key, 0) for search in searches) for key in
              ("term_count", "total_candidates", "discovery_queries", "discovery_unknown")}
    complete = bool(searches) and all(search.get("complete", False) and
                                      search.get("validation_complete", False) for search in searches)
    if matched:
        coverage = f"budgeted search {'completed' if complete else 'partial'}"
    else:
        coverage = f"{'complete' if complete else 'partial'} finite template coverage"
    print(f"Implied search: {counts['term_count']} native terms · "
          f"{counts['total_candidates']} proposals · "
          f"{counts['discovery_queries']} discovery queries · "
          f"{counts['discovery_unknown']} discovery unknown · {coverage}")
    return complete


def _extract(parser: argparse.ArgumentParser, args) -> int:
    options = _options(parser, args)
    if args.scopes is not None and set(args.scopes.split(",")) != {"property"}:
        raise ValueError("the implied method supports only property scopes (P = not bad)")
    report = analyze(args.models, args.out, options, args.reuse, args.property_id, args.max_reuse,
                     pono=args.pono, pono_timeout=args.pono_timeout)
    write_report(report, args.out)
    complete = _print_summary(report, args.out, args.matched_budgets)
    for error in report["errors"]:
        print(f"error: {error['model']}: {error['error']}", file=sys.stderr)
    return 1 if report["errors"] or not complete else 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            return _inspect(args)
        if args.command == "replay":
            result, code = replay(args.input, backend=args.backend, timeout_ms=args.timeout_ms,
                                  accepted_only=args.accepted_only)
            print(json.dumps(result, indent=2))
            return code
        if args.command == "verify":
            result, code = verification.run(
                args.input, args.out, pono=args.pono, engines=args.engines, bound=args.bound,
                timeout=args.timeout, keep_files=args.keep_files,
                log=lambda message: print(message, file=sys.stderr))
            print(verification.format_summary(result, args.out))
            for error in result["errors"]:
                print(f"error: {error['model']}: {error['error']}", file=sys.stderr)
            return code
        return _extract(parser, args)
    except (OSError, ValueError, KeyError, TypeError, z3.Z3Exception) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
