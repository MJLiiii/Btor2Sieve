"""Command-line interface for reproducible extraction and solver replay."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sys

import z3

from . import __version__
from .btor2 import parse_file
from .candidates import GenerationOptions
from .pipeline import analyze, features
from .reporting import write_report
from .validation import replay_smt2


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
        run.add_argument("--scopes", default="property,model", help="comma-separated property,model,initial,transition")
        run.add_argument("--property", dest="property_id", type=_positive, help="select one bad directive ID")
        run.add_argument("--syntax-only", action="store_true", help="disable solver-guided discovery")
        run.add_argument("--max-candidates", type=_positive, default=200, help="per-scope candidate budget")
        run.add_argument("--max-terms", type=_positive, default=16, help="per-scope discovery term budget")
        run.add_argument("--max-width", type=_positive, default=64, help="maximum bit width for scalar discovery")
        run.add_argument("--max-queries", type=_positive, default=256, help="per-scope discovery query budget")
        run.add_argument("--timeout-ms", type=_positive, default=1000, help="timeout per SMT query, in milliseconds")
        run.add_argument("--reuse", action="store_true", help="revalidate accepted property facts against other properties")
        run.add_argument("--max-reuse", type=_positive, default=100, help="reuse query limit per target property")
    replay = commands.add_parser("replay", help="recheck exported obligations with Z3 or independent cvc5")
    replay.add_argument("input", type=Path, help="report directory, results.json, or one .smt2 file")
    replay.add_argument("--backend", choices=("z3", "cvc5"), default="z3")
    replay.add_argument("--timeout-ms", type=_positive, default=5000)
    replay.add_argument("--accepted-only", action="store_true")
    return parser


def _replay(args) -> tuple[dict, int]:
    path = args.input
    if path.suffix == ".smt2":
        result = replay_smt2(path.read_text(), args.timeout_ms, args.backend)
        return asdict(result), 0 if result.status in {"sat", "unsat"} else 1
    report_path = path / "results.json" if path.is_dir() else path
    data = json.loads(report_path.read_text())
    root = report_path.parent.resolve()
    checks = []
    selected = [dict(r, kind="implication") for r in data["records"]
                if not args.accepted_only or r["status"] == "accepted"]
    # Replay the antecedents as well: UNSAT implication alone does not establish
    # the non-vacuity required by an accepted result.
    for model in data["models"]:
        for scope in model["scopes"]:
            selected.append({"id": f"{model['id']}:{scope['name']}:hypothesis", "kind": "hypothesis",
                             "obligation": scope["obligation"], "sha256": scope["sha256"],
                             "solver_result": scope["hypothesis_result"]})
    for row in selected:
        obligation = (root / row["obligation"]).resolve()
        if not obligation.is_relative_to(root):
            checks.append({"id": row["id"], "status": "error", "matches": False,
                           "reason": "obligation path escapes report directory"})
            continue
        try:
            content = obligation.read_bytes()
            if hashlib.sha256(content).hexdigest() != row["sha256"]:
                checks.append({"id": row["id"], "status": "error", "matches": False,
                               "reason": "obligation SHA-256 mismatch"})
                continue
            result = replay_smt2(content.decode(), args.timeout_ms, args.backend)
            expected = row["solver_result"]
            checks.append({"id": row["id"], "kind": row["kind"], "expected": expected, **asdict(result),
                           "matches": result.status == expected and result.status in {"sat", "unsat"}})
        except (OSError, UnicodeError) as exc:
            checks.append({"id": row["id"], "status": "error", "matches": False, "reason": str(exc)})
    mismatch = sum(not row["matches"] for row in checks)
    try:
        backend_version = version("z3-solver" if args.backend == "z3" else "cvc5")
    except PackageNotFoundError:
        backend_version = None
    result = {"backend": args.backend, "solver_version": backend_version,
              "solver_options": ({"tlimit-per": args.timeout_ms, "arrays-exp": True, "produce-models": True}
                                 if args.backend == "cvc5" else {"timeout": args.timeout_ms, "random_seed": 0}),
              "checked": len(checks), "mismatched": mismatch,
              "incomplete_run_errors": len(data.get("errors", [])), "checks": checks}
    return result, 1 if mismatch or not checks or data.get("errors") else 0


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
            result, code = _replay(args)
            print(json.dumps(result, indent=2))
            return code
        options = GenerationOptions(max_candidates=args.max_candidates, max_terms=args.max_terms,
                                    max_width=args.max_width, semantic=not args.syntax_only,
                                    timeout_ms=args.timeout_ms, max_queries=args.max_queries)
        report = analyze(args.models, args.out, options, tuple(args.scopes.split(",")),
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
