"""Run extraction end to end: read with Pono, propose, validate, and record evidence.

For every model and every bad directive (property scope):

0. Pono parses the model and supplies P = not bad (``pono.read_model``).
1. ``discover_implied_candidates`` proposes candidate formulas from P (untrusted).
2. A fresh ``Validator`` checks each one under exactly that P.
3. Every query is saved as a standalone SMT-LIB obligation with its SHA-256.

A model that fails part-way is rolled back completely (records and files),
and the next model is still analyzed.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import platform
from time import perf_counter

import z3

from . import __version__
from .pono import PonoModel, features, pono_identity, read_model, symbols
from .implied import (BUDGET_NAMES, FAMILIES, Candidate, GenerationOptions, check_options,
                      discover_implied_candidates)
from .reporting import STATUSES
from .validation import Scope, Validator, property_scopes


SCOPE_DESCRIPTIONS = {
    "property": "P = not selected bad; no environment or reachability assumptions",
}


def budget_policy(options: GenerationOptions) -> str:
    if options.matched_budgets:
        return "matched"
    if all(getattr(options, name) is None for name in BUDGET_NAMES):
        return "unlimited"
    return "method-defaults"  # Budgets were given but are not enforced.


def _configuration(options: GenerationOptions, reuse: bool, property_id: int | None,
                   max_reuse: int) -> dict:
    matched = options.matched_budgets
    return {
        # Unenforced budgets are recorded as null.
        **{name: getattr(options, name) if matched else None for name in BUDGET_NAMES},
        "timeout_ms": options.timeout_ms, "method": "implied", "matched_budgets": matched,
        "scopes": ["property"], "reuse": reuse, "property_id": property_id, "max_reuse": max_reuse,
        "budget_policy": budget_policy(options),
        "constraint_families": list(FAMILIES),
        "implied_workflow": "property-word-level-budgeted-v1" if matched else "property-word-level-v1",
        "implied_families": list(FAMILIES),
        "implied_vocabulary": (
            "bit-vector and array subterms of Pono's property formula, budgeted selection" if matched else
            "every bit-vector and array subterm of Pono's property formula"),
    }


def analyze(paths: list[Path], output: Path, options: GenerationOptions, reuse: bool = False,
            property_id: int | None = None, max_reuse: int = 100, pono: str = "pono",
            pono_timeout: float = 300.0) -> dict:
    """Analyze each model, continuing after input errors. Never overwrite a run."""
    if not paths:
        raise ValueError("provide at least one BTOR2 file")
    if max_reuse <= 0:
        raise ValueError("max_reuse must be positive")
    if pono_timeout <= 0:
        raise ValueError("pono_timeout must be positive")
    check_options(options)
    # Resolve Pono before creating output, so a missing binary leaves nothing behind.
    identity = pono_identity(pono)
    output.mkdir(parents=True, exist_ok=False)
    (output / "obligations").mkdir()
    report = {
        "schema_version": 1,
        "tool": {"name": "Btor2Sieve", "version": __version__, "python": platform.python_version(),
                 "z3": z3.get_version_string(), "platform": platform.platform()},
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": _configuration(options, reuse, property_id, max_reuse),
        "frontend": {"name": "pono", "pono": identity,
                     "role": "Pono parses every model and supplies each property P"},
        "models": [], "summaries": [], "records": [], "errors": [],
        "scope_definitions": SCOPE_DESCRIPTIONS,
        "trust_boundary": "Pono's BTOR2 frontend and the SMT solver; replayable obligations are not proof certificates",
    }
    start = perf_counter()
    for index, path in enumerate(paths):
        model_id = f"m{index:04d}"
        partial = {"models": [], "summaries": [], "records": []}
        try:
            _analyze_model(path, model_id, output, options, reuse, property_id, max_reuse, partial,
                           identity["path"], pono_timeout)
        except (OSError, ValueError, z3.Z3Exception) as exc:
            # Roll back the whole model so counts never mix complete and partial work.
            report["errors"].append({"model": str(path), "error": str(exc),
                                     "discarded_partial_records": len(partial["records"])})
            for artifact in (output / "obligations").glob(f"{model_id}-*"):
                artifact.unlink()
        else:
            for key in partial:
                report[key].extend(partial[key])
    report["duration_seconds"] = perf_counter() - start
    return report


class _Evidence:
    """Writes one model's SMT obligations and appends its validation records."""

    def __init__(self, output: Path, model_id: str, path: Path, records: list[dict]):
        self.output, self.model_id, self.path, self.records = output, model_id, path, records
        self.count = 0

    def write(self, filename: str, smt2: str) -> dict:
        data = smt2.encode()
        (self.output / filename).write_bytes(data)
        return {"obligation": filename, "sha256": hashlib.sha256(data).hexdigest()}

    def check(self, validator: Validator, scope: Scope, candidate: Candidate,
              reuse_from: str | None = None) -> dict:
        """Validate one candidate, save its obligation, and record the result."""
        result = validator.check(candidate.expr)
        self.count += 1
        record_id = f"{self.model_id}-{self.count:05d}"
        row = {
            "id": record_id, "model_id": self.model_id, "model": str(self.path),
            "scope": scope.name, "property_id": scope.property_id,
            "family": candidate.family, "origin": candidate.origin,
            "source_nodes": list(candidate.source_nodes), "expression": candidate.expr.sexpr(),
            "status": result.status, "solver_result": result.solver_result,
            "hypothesis_result": result.hypothesis_result,
            "validation_seconds": result.duration_seconds, "counterexample": result.counterexample,
            "reason": result.reason,
            **self.write(f"obligations/{record_id}.smt2", result.smt2),
            "reuse_from": reuse_from,
            "syntactically_same_as_hypothesis": z3.eq(z3.simplify(candidate.expr),
                                                      z3.simplify(scope.hypothesis)),
        }
        self.records.append(row)
        return row


def _model_entry(path: Path, model_id: str, model: PonoModel, options: GenerationOptions) -> dict:
    entry = {"id": model_id, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "features": features(model.lines), "pono_seconds": model.seconds,
             "symbols": symbols(model.lines),
             "warnings": [], "scopes": []}
    if not model.bad_ids:
        entry["warnings"].append("No bad-state properties: no property scopes were analyzed.")
    if entry["features"]["liveness_nodes"]:
        entry["warnings"].append("Safety analysis only: fair/justice nodes are recorded, not assumed.")
    if options.matched_budgets:
        coverage = ("Candidate, source-term, width, and discovery-query budgets apply. Completion "
                    "means the configured bounded search finished; it does not claim full cone coverage.")
    else:
        coverage = ("Candidate, term, width, and discovery-query caps are unused; each solver query "
                    "has a timeout. Completion describes the implemented finite templates and "
                    "discovery procedure, not all possible word-level consequences.")
    entry["warnings"].append("Property-implied extraction preserves native bit-vector and array "
                             "expressions. Only the selected property is assumed. " + coverage)
    return entry


def _scope_summary(model_id: str, path: Path, scope: Scope, entry: dict, rows: list[dict],
                   validator: Validator, extraction_seconds: float, search: dict) -> dict:
    counts = Counter(row["status"] for row in rows)
    families: dict[str, Counter] = {}
    for row in rows:
        families.setdefault(row["family"], Counter())[row["status"]] += 1
    family_counts = {family: dict(families[family]) for family in sorted(families)}
    for family in FAMILIES:
        family_counts.setdefault(family, {})
    search = dict(search)
    search["validation_complete"] = (validator.hypothesis_result != "unknown" and
                                     all(row["status"] != "unknown" for row in rows))
    search["complete"] = search["complete"] and search["validation_complete"]
    return {
        "model_id": model_id, "model": str(path), "scope": scope.name,
        "property_id": scope.property_id, "array_sorts": entry["features"]["array_sorts"],
        "nodes": entry["features"]["nodes"], "candidates": len(rows),
        **{status: counts[status] for status in STATUSES},
        "extraction_seconds": extraction_seconds,
        "validation_seconds": sum(row["validation_seconds"] for row in rows),
        "hypothesis_result": validator.hypothesis_result,
        "hypothesis_seconds": validator.hypothesis_seconds,
        "families": family_counts,
        "search": search,
    }


def _analyze_model(path: Path, model_id: str, output: Path, options: GenerationOptions,
                   reuse: bool, property_id: int | None, max_reuse: int, report: dict,
                   pono: str, pono_timeout: float = 300.0) -> None:
    model = read_model(pono, path, property_ids=None if property_id is None else [property_id],
                       timeout=pono_timeout)
    scopes = property_scopes(model)
    entry = _model_entry(path, model_id, model, options)
    report["models"].append(entry)
    evidence = _Evidence(output, model_id, path, report["records"])
    validators: dict[str, Validator] = {}
    accepted: dict[str, list[Candidate]] = {}
    summaries: dict[str, dict] = {}

    for scope in scopes:
        validator = validators[scope.name] = Validator(scope.hypothesis, options.timeout_ms)
        hypothesis_file = f"obligations/{model_id}-{scope.name.replace(':', '-')}-hypothesis.smt2"
        entry["scopes"].append({"name": scope.name, "property_id": scope.property_id,
                                "hypothesis": scope.hypothesis.sexpr(),
                                "hypothesis_result": validator.hypothesis_result,
                                "hypothesis_seconds": validator.hypothesis_seconds,
                                "hypothesis_reason": validator.hypothesis_reason,
                                **evidence.write(hypothesis_file, validator.hypothesis_smt2)})
        start = perf_counter()
        discovery = discover_implied_candidates(scope.hypothesis, options)
        extraction_seconds = perf_counter() - start
        rows = []
        accepted[scope.name] = []
        for candidate in discovery.candidates:
            if candidate.family not in FAMILIES:
                raise ValueError(f"unsupported constraint family: {candidate.family}")
            row = evidence.check(validator, scope, candidate)
            rows.append(row)
            if row["status"] == "accepted":
                accepted[scope.name].append(candidate)
        summary = _scope_summary(model_id, path, scope, entry, rows, validator,
                                 extraction_seconds, discovery.statistics)
        summaries[scope.name] = summary
        report["summaries"].append(summary)

    if not reuse:
        return
    # Cross-property reuse: re-check facts accepted for one property against
    # each other property, from scratch, under that property's own hypothesis.
    for target in scopes:
        attempts, seen = 0, set()
        for source in scopes:
            if source.name == target.name:
                continue
            for candidate in accepted[source.name]:
                key = z3.simplify(candidate.expr).sexpr()
                if key in seen or attempts >= max_reuse:
                    continue
                seen.add(key)
                attempts += 1
                row = evidence.check(validators[target.name], target, candidate, source.name)
                if row["status"] == "unknown":
                    search = summaries[target.name]["search"]
                    search["validation_complete"] = search["complete"] = False
                    if not search["reason"]:
                        search["reason"] = "cross-property revalidation returned unknown"
