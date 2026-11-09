"""Command-line interface for reproducible extraction and solver replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import z3

from . import __version__
from .btor2 import parse_file
from .methods.common import GenerationOptions
from .pipeline import analyze, features
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
    inspect = commands.add_parser("inspect", help="check BTOR2 syntax and list theory features")
    inspect.add_argument("model", type=Path)
    inspect.add_argument("--json", action="store_true")
    for command in ("extract", "batch"):
        run = commands.add_parser(command, help="extract and validate " + ("one model" if command == "extract" else "a set of models"))
        run.add_argument("models", type=Path, nargs=1 if command == "extract" else "+")
        run.add_argument("--out", type=Path, required=True, help="new output directory (never overwritten)")
        run.add_argument("--method", choices=("word-level", "implied"), default="word-level",
                         help="word-level (existing method) or paper state-literal implications")
        run.add_argument("--scopes", help="comma-separated property,model,initial,transition; "
                         "default: property,model for word-level; property for implied")
        run.add_argument("--property", dest="property_id", type=_positive, help="select one bad directive ID")
        run.add_argument("--syntax-only", action="store_true", help="disable solver-guided discovery")
        run.add_argument("--max-candidates", type=_positive, default=200, help="per-scope candidate budget")
        run.add_argument("--max-terms", type=_positive, default=16,
                         help="per-scope term budget; selected state bits for implied")
        run.add_argument("--max-width", type=_positive, default=64, help="maximum bit width for scalar discovery")
        run.add_argument("--max-queries", type=_positive, default=256,
                         help="word-level discovery query budget (unused by implied)")
        run.add_argument("--timeout-ms", type=_positive, default=1000, help="timeout per SMT query, in milliseconds")
        run.add_argument("--reuse", action="store_true", help="revalidate accepted property facts against other properties")
        run.add_argument("--max-reuse", type=_positive, default=100, help="reuse query limit per target property")
    replay = commands.add_parser("replay", help="recheck exported obligations with Z3 or independent cvc5")
    replay.add_argument("input", type=Path, help="report directory, results.json, or one .smt2 file")
    replay.add_argument("--backend", choices=("z3", "cvc5"), default="z3")
    replay.add_argument("--timeout-ms", type=_positive, default=5000)
    replay.add_argument("--accepted-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            model = parse_file(args.model)
            result = {"model": str(args.model), **features(model),
                      "bad_ids": [n.id for n in model.bads]}
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"{args.model}: {result['nodes']} nodes, {result['states']} states, "
                      f"{result['inputs']} inputs, {result['properties']} safety properties, "
                      f"{result['array_sorts']} array sorts")
                if result["liveness_nodes"]:
                    print("Fair/justice declarations present; extraction analyzes safety only.")
            return 0
        if args.command == "replay":
            result, code = replay(args.input, backend=args.backend, timeout_ms=args.timeout_ms,
                                  accepted_only=args.accepted_only)
            print(json.dumps(result, indent=2))
            return code
        if args.method == "implied" and args.syntax_only:
            parser.error("--syntax-only is only available for word-level, not implied")
        options = GenerationOptions(max_candidates=args.max_candidates, max_terms=args.max_terms,
                                    max_width=args.max_width, semantic=not args.syntax_only,
                                    timeout_ms=args.timeout_ms, max_queries=args.max_queries,
                                    method=args.method)
        scopes = tuple(args.scopes.split(",")) if args.scopes is not None else None
        report = analyze(args.models, args.out, options, scopes,
                         args.reuse, args.property_id, args.max_reuse)
        write_report(report, args.out)
        total = len([r for r in report["records"] if not r["reuse_from"]])
        accepted = sum(s["accepted"] for s in report["summaries"])
        print(f"{len(report['models'])} models · {total} candidates · {accepted} accepted · "
              f"{len(report['errors'])} errors\nReport: {args.out.resolve() / 'report.html'}")
        for error in report["errors"]:
            print(f"error: {error['model']}: {error['error']}", file=sys.stderr)
        return 1 if report["errors"] else 0
    except (OSError, ValueError, KeyError, TypeError, z3.Z3Exception) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
