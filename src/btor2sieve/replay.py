"""Replay exported SMT obligations and verify report evidence integrity."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path

from .validation import replay_smt2


def replay(path: Path, *, backend: str = "z3", timeout_ms: int = 5000,
           accepted_only: bool = False) -> tuple[dict, int]:
    """Replay a standalone SMT file or a report, returning output and exit code."""
    if path.suffix == ".smt2":
        result = replay_smt2(path.read_text(), timeout_ms, backend)
        return asdict(result), 0 if result.status in {"sat", "unsat"} else 1
    report_path = path / "results.json" if path.is_dir() else path
    data = json.loads(report_path.read_text())
    root = report_path.parent.resolve()
    checks = []
    selected = [dict(r, kind="implication") for r in data["records"]
                if not accepted_only or r["status"] == "accepted"]
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
            result = replay_smt2(content.decode(), timeout_ms, backend)
            expected = row["solver_result"]
            checks.append({"id": row["id"], "kind": row["kind"], "expected": expected, **asdict(result),
                           "matches": result.status == expected and result.status in {"sat", "unsat"}})
        except (OSError, UnicodeError) as exc:
            checks.append({"id": row["id"], "status": "error", "matches": False, "reason": str(exc)})
    mismatch = sum(not row["matches"] for row in checks)
    try:
        backend_version = version("z3-solver" if backend == "z3" else "cvc5")
    except PackageNotFoundError:
        backend_version = None
    result = {"backend": backend, "solver_version": backend_version,
              "solver_options": ({"tlimit-per": timeout_ms, "arrays-exp": True, "produce-models": True}
                                 if backend == "cvc5" else {"timeout": timeout_ms, "random_seed": 0}),
              "checked": len(checks), "mismatched": mismatch,
              "incomplete_run_errors": len(data.get("errors", [])), "checks": checks}
    return result, 1 if mismatch or not checks or data.get("errors") else 0

