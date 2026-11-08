"""Connect parsing, untrusted discovery, validation, and durable evidence."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import platform
from time import perf_counter

import z3

from . import __version__
from .btor2 import Model, parse_file
from .candidates import Candidate, GenerationOptions, generate_candidates
from .encoding import Encoder
from .validation import Scope, Validator, make_scopes


SCOPE_DESCRIPTIONS = {
    "property": "P = not selected bad; no environment or reachability assumptions",
    "model": "A: assumption/combinational consequence; no reachability claim",
    "initial": "I and A: initial-frame fact only",
    "transition": "T and A: one-step fact with source environment; no next-frame A",
}


def features(model: Model) -> dict:
    return {
        "nodes": len(model.nodes), "states": len(model.states), "inputs": len(model.inputs),
        "properties": len(model.bads), "constraints": len(model.constraints),
        "array_sorts": sum(s.kind == "array" for s in model.sorts.values()),
        "max_bit_width": max((s.width for s in model.sorts.values() if s.kind == "bitvec"), default=0),
        "operations": dict(sorted(Counter(n.op for n in model.nodes.values()).items())),
        "liveness_nodes": sum(n.op in {"fair", "justice"} for n in model.nodes.values()),
    }


def _transition_candidates(encoder: Encoder, options: GenerationOptions) -> list[Candidate]:
    """Include primed terms: total functional T alone cannot constrain current s."""
    pool = []
    for node in encoder.model.nexts[:options.max_terms]:
        state, update = node.args
        nxt, current, rhs = encoder.next_states[state], encoder.expr(state), encoder.expr(update)
        pool.append(Candidate(nxt == rhs, "transition", "next-equation", (node.id,)))
        pool.append(Candidate(nxt == current, "equality", "transition-stability-guess", (node.id,)))
        if z3.is_bv(nxt) and nxt.size() <= options.max_width:
            pool.extend([
                Candidate(nxt == 0, "equality", "next-value-guess", (node.id,)),
                Candidate(z3.ULE(nxt, rhs), "unsigned_bound", "next-bound", (node.id,)),
            ])
        elif z3.is_array(nxt) and z3.is_store(rhs):
            index, value = rhs.arg(1), rhs.arg(2)
            pool.append(Candidate(z3.Select(nxt, index) == value, "array", "next-read-over-write", (node.id,)))
    return pool


def _deduplicate(candidates: list[Candidate], limit: int) -> list[Candidate]:
    if limit <= 0:
        return []
    result, seen = [], set()
    for candidate in candidates:
        key = z3.simplify(candidate.expr).sexpr()
        if key in seen or key == "true":
            continue
        seen.add(key)
        result.append(candidate)
        if len(result) >= limit:
            break
    return result


def analyze(paths: list[Path], output: Path, options: GenerationOptions,
            scope_kinds: tuple[str, ...] = ("property", "model"), reuse: bool = False,
            property_id: int | None = None, max_reuse: int = 100) -> dict:
    """Analyze each model, continuing after input errors. Never overwrite a run."""
    if not paths:
        raise ValueError("provide at least one BTOR2 file")
    if max_reuse <= 0:
        raise ValueError("max_reuse must be positive")
    if not scope_kinds or any(k not in SCOPE_DESCRIPTIONS for k in scope_kinds):
        raise ValueError("scopes must be chosen from property,model,initial,transition")
    output.mkdir(parents=True, exist_ok=False)
    (output / "obligations").mkdir()
    report = {
        "schema_version": 1,
        "tool": {"name": "Btor2Sieve", "version": __version__, "python": platform.python_version(),
                 "z3": z3.get_version_string(), "platform": platform.platform()},
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {**asdict(options), "scopes": scope_kinds, "reuse": reuse,
                          "property_id": property_id, "max_reuse": max_reuse},
        "models": [], "summaries": [], "records": [], "errors": [],
        "scope_definitions": SCOPE_DESCRIPTIONS,
        "trust_boundary": "BTOR2 frontend and SMT solver; replayable obligations are not proof certificates",
    }
    start_run = perf_counter()
    for model_index, path in enumerate(paths):
        partial = {"models": [], "summaries": [], "records": []}
        try:
            _analyze_model(path, model_index, output, options, scope_kinds, reuse,
                           property_id, max_reuse, partial)
        except (OSError, ValueError, z3.Z3Exception) as exc:
            report["errors"].append({"model": str(path), "error": str(exc),
                                     "discarded_partial_records": len(partial["records"])})
            for artifact in (output / "obligations").glob(f"m{model_index:04d}-*.smt2"):
                artifact.unlink()
        else:
            for key in partial:
                report[key].extend(partial[key])
    report["duration_seconds"] = perf_counter() - start_run
    return report


def _analyze_model(path: Path, model_index: int, output: Path, options: GenerationOptions,
                   scope_kinds: tuple[str, ...], reuse: bool, property_id: int | None,
                   max_reuse: int, report: dict) -> None:
    start = perf_counter()
    model = parse_file(path)
    encoder = Encoder(model)
    scopes = make_scopes(encoder, tuple(dict.fromkeys(scope_kinds)))
    if property_id is not None:
        if property_id not in {n.id for n in model.bads}:
            raise ValueError(f"bad directive {property_id} not found in {path}")
        scopes = [s for s in scopes if s.property_id is None or s.property_id == property_id]
    model_id = f"m{model_index:04d}"
    entry = {"id": model_id, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "features": features(model), "parse_encode_seconds": perf_counter() - start,
             "symbols": {str(n.id): n.symbol for n in model.states + model.inputs},
             "warnings": [], "scopes": []}
    if not model.bads:
        entry["warnings"].append("No bad-state properties: no property scopes were analyzed.")
    if entry["features"]["liveness_nodes"]:
        entry["warnings"].append("Safety analysis only: fair/justice nodes are recorded, not assumed.")
    report["models"].append(entry)
    accepted_by_scope: dict[str, list[Candidate]] = {}
    validators: dict[str, Validator] = {}
    counter = 0

    def record(scope: Scope, candidate: Candidate, reuse_from: str | None = None) -> dict:
        nonlocal counter
        validator = validators[scope.name]
        result = validator.check(candidate.expr)
        counter += 1
        filename = f"obligations/{model_id}-{counter:05d}.smt2"
        data = result.smt2.encode()
        (output / filename).write_bytes(data)
        row = {
            "id": f"{model_id}-{counter:05d}", "model_id": model_id, "model": str(path),
            "scope": scope.name, "property_id": scope.property_id, "family": candidate.family,
            "origin": candidate.origin, "source_nodes": list(candidate.source_nodes),
            "expression": candidate.expr.sexpr(), "status": result.status,
            "solver_result": result.solver_result, "hypothesis_result": result.hypothesis_result,
            "validation_seconds": result.duration_seconds, "counterexample": result.counterexample,
            "reason": result.reason, "obligation": filename,
            "sha256": hashlib.sha256(data).hexdigest(), "reuse_from": reuse_from,
            "syntactically_same_as_hypothesis": z3.eq(z3.simplify(candidate.expr), z3.simplify(scope.hypothesis)),
        }
        report["records"].append(row)
        return row

    for scope in scopes:
        validator = Validator(scope.hypothesis, options.timeout_ms)
        validators[scope.name] = validator
        hyp_file = f"obligations/{model_id}-{scope.name.replace(':', '-')}-hypothesis.smt2"
        (output / hyp_file).write_text(validator.hypothesis_smt2)
        entry["scopes"].append({"name": scope.name, "property_id": scope.property_id,
                                "hypothesis": scope.hypothesis.sexpr(),
                                "hypothesis_result": validator.hypothesis_result,
                                "hypothesis_seconds": validator.hypothesis_seconds,
                                "hypothesis_reason": validator.hypothesis_reason,
                                "obligation": hyp_file,
                                "sha256": hashlib.sha256(validator.hypothesis_smt2.encode()).hexdigest()})
        start = perf_counter()
        candidates = generate_candidates(encoder, scope.hypothesis, scope.roots, options)
        if scope.name == "transition":
            candidates = _transition_candidates(encoder, options) + candidates
        candidates = _deduplicate(candidates, options.max_candidates)
        extraction_seconds = perf_counter() - start
        rows = []
        accepted_by_scope[scope.name] = []
        for candidate in candidates:
            row = record(scope, candidate)
            rows.append(row)
            if row["status"] == "accepted":
                accepted_by_scope[scope.name].append(candidate)
        counts = Counter(r["status"] for r in rows)
        families = {}
        for row in rows:
            families.setdefault(row["family"], Counter())[row["status"]] += 1
        report["summaries"].append({
            "model_id": model_id, "model": str(path), "scope": scope.name,
            "property_id": scope.property_id, "array_sorts": entry["features"]["array_sorts"],
            "nodes": entry["features"]["nodes"], "candidates": len(rows),
            **{k: counts[k] for k in ("accepted", "rejected", "unknown", "vacuous")},
            "extraction_seconds": extraction_seconds,
            "validation_seconds": sum(r["validation_seconds"] for r in rows),
            "hypothesis_result": validator.hypothesis_result,
            "hypothesis_seconds": validator.hypothesis_seconds,
            "families": {k: dict(v) for k, v in sorted(families.items())},
        })
    if reuse:
        property_scopes = [s for s in scopes if s.property_id is not None]
        for target in property_scopes:
            attempts, seen = 0, set()
            for source in property_scopes:
                if source.name == target.name:
                    continue
                for candidate in accepted_by_scope[source.name]:
                    key = z3.simplify(candidate.expr).sexpr()
                    if key in seen or attempts >= max_reuse:
                        continue
                    seen.add(key)
                    record(target, candidate, source.name)
                    attempts += 1
