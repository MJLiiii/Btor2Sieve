"""Measure the accepted constraints' effect on Pono's verification (C14 outcome 4).

For each property in an extraction report and each selected engine, Pono
model-checks the property twice:

* baseline: the original model with only that property's `bad` line;
* constrained: the same, plus `constraint (bad or C)` for every accepted C,
  that is, "P implies C".

Each accepted C was proved to follow from P, so "P implies C" holds in every
state. The added constraints therefore remove no state, and both runs must
give the same verdict; a different definite verdict is reported as
inconsistent. Only the time and the number of solved properties may change.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from time import perf_counter
from typing import Callable

import z3

from .pono import (ENGINES, Btor2Writer, EmitError, free_constants, pono_identity, read_model,
                   run_pono, sha256_file, without)


# Other properties and liveness lines are removed; init, next and the model's
# own environment constraints stay, so the model keeps its meaning.
VERIFY_DROPPED = frozenset({"bad", "fair", "justice"})
DEFINITE = {"sat", "unsat"}


class _Model:
    """One model file, read by Pono, and the text the verification files are built from."""

    def __init__(self, path: Path, pono: str, timeout: float):
        self.path = path
        text = path.read_text()
        model = read_model(pono, path, timeout=timeout)
        self.lines = model.lines
        # Variables and their sorts, as Pono reads them, for parsing recorded constraints.
        self.decls = {str(v): v for p in model.properties for v in free_constants(p.hypothesis)}
        self.base = without(text, self.lines, VERIFY_DROPPED)
        self.first_id = max((line.id for line in self.lines), default=0) + 1

    def formula(self, expression: str) -> z3.BoolRef:
        (parsed,) = z3.parse_smt2_string(f"(assert {expression})", decls=self.decls)
        return parsed

    def file(self, property_id: int, formulas: list[z3.BoolRef]) -> list[str]:
        """Model text, one `constraint (bad or C)` per formula, and the selected `bad`."""
        line = next((l for l in self.lines if l.op == "bad" and l.id == property_id), None)
        if line is None or not line.words:
            raise ValueError(f"bad directive {property_id} not found in {self.path}")
        bad = int(line.words[0])  # The bad term's ID, possibly negated; Pono interprets it.
        writer = Btor2Writer(self.first_id)
        bit = writer.sort(("bv", 1))
        for formula in formulas:
            writer.line("constraint", writer.line("or", bit, bad, writer.bit(formula)))
        writer.line("bad", bad)
        return [*self.base, *writer.lines]


def _resolve(entry: dict, report_root: Path) -> Path:
    path = Path(entry["path"])
    for candidate in ([path] if path.is_absolute() else [Path.cwd() / path, report_root / path]):
        if candidate.is_file():
            if sha256_file(candidate) != entry["sha256"]:
                raise ValueError(f"{candidate} changed since extraction (SHA-256 mismatch)")
            return candidate
    raise ValueError(f"model file not found: {entry['path']}")


def _property(model: _Model, model_id: str, property_id: int, accepted: list[dict],
              engines: list[str], bound: int, timeout: float, pono: str, output: Path,
              keep_files: bool, log: Callable[[str], None]) -> list[dict]:
    formulas, unsupported = [], 0
    for record in accepted:
        try:
            formula = model.formula(record["expression"])
            model.file(property_id, [formula])  # Fail early on an operator BTOR2 lacks.
            formulas.append(formula)
        except (EmitError, z3.Z3Exception):
            unsupported += 1
    files = {"baseline": model.file(property_id, []), "constrained": model.file(property_id, formulas)}
    rows = []
    for engine in engines:
        results, kept = {}, {}
        for kind, lines in files.items():
            path = output / "btor2" / f"{model_id}-p{property_id}-{engine}-{kind}.btor2"
            path.write_text("\n".join(lines) + "\n")
            results[kind] = run_pono(pono, path, engine, bound, timeout)
            kept[kind] = path
        baseline, constrained = results["baseline"], results["constrained"]
        consistent = not (baseline.verdict in DEFINITE and constrained.verdict in DEFINITE
                          and baseline.verdict != constrained.verdict)
        # Keep the files on request, or as evidence of a disagreement or a Pono error.
        keep = keep_files or not consistent or "error" in (baseline.verdict, constrained.verdict)
        for path in kept.values():
            if not keep:
                path.unlink()
        log(f"  property {property_id}, {engine}: baseline {baseline.verdict} ({baseline.seconds:.2f}s), "
            f"constrained {constrained.verdict} ({constrained.seconds:.2f}s)")
        rows.append({
            "model_id": model_id, "model": str(model.path), "property_id": property_id,
            "engine": engine, "bound": bound, "constraints": len(formulas),
            "constraints_unsupported": unsupported,
            "baseline": baseline.verdict, "baseline_seconds": baseline.seconds,
            "constrained": constrained.verdict, "constrained_seconds": constrained.seconds,
            "consistent": consistent,
            "baseline_file": str(kept["baseline"].relative_to(output)) if keep else None,
            "constrained_file": str(kept["constrained"].relative_to(output)) if keep else None,
            "baseline_detail": baseline.detail, "constrained_detail": constrained.detail,
        })
    return rows


def run(input_path: Path, output: Path, *, pono: str = "pono", engines: list[str] | None = None,
        bound: int = 1000, timeout: float = 60.0, keep_files: bool = False,
        log: Callable[[str], None] = lambda message: None) -> tuple[dict, int]:
    """Run the baseline and constrained Pono checks for every property of a report."""
    engines = list(engines or ["ic3ia"])
    unknown = [engine for engine in engines if engine not in ENGINES]
    if unknown:
        raise ValueError(f"unknown Pono engine: {', '.join(unknown)}")
    if bound <= 0 or timeout <= 0:
        raise ValueError("bound and timeout must be positive")
    report_path = input_path / "results.json" if input_path.is_dir() else input_path
    data = json.loads(report_path.read_text())
    identity = pono_identity(pono)
    output.mkdir(parents=True, exist_ok=False)
    (output / "btor2").mkdir()

    rows: list[dict] = []
    errors: list[dict] = []
    start = perf_counter()
    for entry in data["models"]:
        try:
            path = _resolve(entry, report_path.parent)
            log(f"{entry['id']}: {path}")
            model = _Model(path, identity["path"], timeout)
        except (OSError, ValueError, z3.Z3Exception) as exc:
            errors.append({"model": entry["path"], "error": str(exc)})
            continue
        for scope in entry["scopes"]:
            property_id = scope["property_id"]
            accepted = [r for r in data["records"] if r["model_id"] == entry["id"]
                        and r["property_id"] == property_id and r["status"] == "accepted"
                        and not r.get("syntactically_same_as_hypothesis")]
            try:
                rows += _property(model, entry["id"], property_id, accepted, engines, bound, timeout,
                                  identity["path"], output, keep_files, log)
            except (OSError, ValueError, z3.Z3Exception) as exc:
                errors.append({"model": entry["path"], "property_id": property_id, "error": str(exc)})

    result = {
        "schema_version": 1,
        "source_report": str(report_path),
        "pono": identity,
        "configuration": {"engines": engines, "bound": bound, "timeout_seconds": timeout},
        "method": "baseline: original model with one bad; constrained: plus constraint (bad or C) "
                  "per accepted C, which removes no state, so verdicts must agree",
        "summary": summarize(rows, errors),
        "runs": rows,
        "errors": errors,
        "duration_seconds": perf_counter() - start,
    }
    write_outputs(result, output)
    failed = result["summary"]["inconsistent"] or errors
    return result, 1 if failed else 0


def summarize(rows: list[dict], errors: list[dict]) -> dict:
    both = [r for r in rows if r["baseline"] in DEFINITE and r["constrained"] in DEFINITE]
    return {
        "runs": len(rows),
        "baseline_solved": sum(r["baseline"] in DEFINITE for r in rows),
        "constrained_solved": sum(r["constrained"] in DEFINITE for r in rows),
        "inconsistent": sum(not r["consistent"] for r in rows),
        "both_solved": len(both),
        "baseline_seconds_both_solved": sum(r["baseline_seconds"] for r in both),
        "constrained_seconds_both_solved": sum(r["constrained_seconds"] for r in both),
        "errors": len(errors),
    }


_COLUMNS = ["model_id", "model", "property_id", "engine", "bound", "constraints",
            "constraints_unsupported", "baseline", "baseline_seconds", "constrained",
            "constrained_seconds", "consistent", "baseline_file", "constrained_file"]


def write_outputs(result: dict, output: Path) -> None:
    (output / "verify.json").write_text(json.dumps(result, indent=2) + "\n")
    with (output / "verify.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, _COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["runs"])


def format_summary(result: dict, output: Path) -> str:
    summary = result["summary"]
    lines = [
        f"Pono {result['pono']['path']} (sha256 {result['pono']['sha256'][:12]}…)",
        f"{summary['runs']} runs · solved {summary['baseline_solved']} baseline vs "
        f"{summary['constrained_solved']} with constraints · {summary['inconsistent']} inconsistent verdicts",
    ]
    if summary["both_solved"]:
        lines.append(f"Solved by both ({summary['both_solved']}): "
                     f"{summary['baseline_seconds_both_solved']:.2f}s baseline vs "
                     f"{summary['constrained_seconds_both_solved']:.2f}s with constraints")
    lines.append(f"Results: {output.resolve() / 'verify.json'}")
    return "\n".join(lines)
