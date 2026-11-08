"""Implication checking independent of the candidate generator.

The trusted boundary is BTOR2 translation plus the SMT solver. SMT-LIB files
are replayable obligations, not independently kernel-checked proof certificates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

import z3

if TYPE_CHECKING:
    from .encoding import Encoder


@dataclass
class Scope:
    name: str
    hypothesis: z3.BoolRef
    roots: tuple[int, ...]
    property_id: int | None = None


def make_scopes(encoder: Encoder, kinds: tuple[str, ...] = ("property", "model")) -> list[Scope]:
    """Build exact proof contexts without strengthening property hypotheses."""
    model = encoder.model
    scopes: list[Scope] = []
    for kind in kinds:
        if kind == "property":
            scopes.extend(Scope(f"property:{n.id}", encoder.property(n.id), n.args, n.id)
                          for n in model.bads)
        elif kind == "model":
            scopes.append(Scope("model", encoder.assumptions,
                                tuple(a for n in model.constraints for a in n.args)))
        elif kind == "initial":
            scopes.append(Scope("initial", z3.And(encoder.initial, encoder.assumptions),
                                tuple(a for n in model.inits + model.constraints for a in n.args)))
        elif kind == "transition":
            scopes.append(Scope("transition", z3.And(encoder.transition, encoder.assumptions),
                                tuple(a for n in model.nexts + model.constraints for a in n.args)))
        else:
            raise ValueError(f"unknown scope: {kind}")
    return scopes


@dataclass
class ValidationResult:
    status: str
    solver_result: str
    hypothesis_result: str
    duration_seconds: float
    smt2: str
    counterexample: dict[str, str] = field(default_factory=dict)
    reason: str | None = None


def _solver(timeout_ms: int, rlimit: int = 0, ctx: z3.Context | None = None) -> z3.Solver:
    solver = z3.Solver(ctx=ctx)
    solver.set(timeout=timeout_ms, random_seed=0)
    if rlimit:
        solver.set(rlimit=rlimit)
    return solver


def _smt2(solver: z3.Solver) -> str:
    # ALL supports nested array sorts too, and avoids backend default-logic drift.
    return "(set-logic ALL)\n" + solver.to_smt2()


class Validator:
    """Check H once for vacuity; discharge every H / not-C query afresh."""

    def __init__(self, hypothesis: z3.BoolRef, timeout_ms: int = 1000, rlimit: int = 0):
        if not z3.is_bool(hypothesis):
            raise ValueError("hypothesis must be Boolean")
        if timeout_ms <= 0 or rlimit < 0:
            raise ValueError("timeout_ms must be positive and rlimit nonnegative")
        self.hypothesis = hypothesis
        self.timeout_ms = timeout_ms
        self.rlimit = rlimit
        solver = _solver(timeout_ms, rlimit, hypothesis.ctx)
        solver.add(hypothesis)
        start = perf_counter()
        self.hypothesis_result = str(solver.check())
        self.hypothesis_seconds = perf_counter() - start
        self.hypothesis_reason = solver.reason_unknown() if self.hypothesis_result == "unknown" else None
        self.hypothesis_smt2 = _smt2(solver)

    def check(self, candidate: z3.BoolRef) -> ValidationResult:
        if not z3.is_bool(candidate):
            raise ValueError("candidate must be Boolean")
        solver = _solver(self.timeout_ms, self.rlimit, self.hypothesis.ctx)
        solver.add(self.hypothesis, z3.Not(candidate))
        start = perf_counter()
        result = solver.check()
        elapsed = perf_counter() - start
        status = {"sat": "rejected", "unsat": "accepted", "unknown": "unknown"}[str(result)]
        reason = solver.reason_unknown() if result == z3.unknown else None
        if result == z3.unsat:
            if self.hypothesis_result == "unsat":
                status = "vacuous"
            elif self.hypothesis_result == "unknown":
                # Implication is proved, but non-vacuity remains unestablished.
                status = "unknown"
                reason = "implication unsat; hypothesis satisfiability unknown: " + str(self.hypothesis_reason)
        witness: dict[str, str] = {}
        if result == z3.sat:
            model = solver.model()
            witness = {str(d): str(model[d]) for d in sorted(model.decls(), key=str)}
        return ValidationResult(status, str(result), self.hypothesis_result, elapsed,
                                _smt2(solver), witness, reason)


@dataclass
class ReplayResult:
    status: str
    duration_seconds: float
    reason: str | None = None


def replay_smt2(text: str, timeout_ms: int = 1000, backend: str = "z3") -> ReplayResult:
    """Replay one assertion set in a fresh solver; never trust file comments."""
    start = perf_counter()
    try:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        if backend == "z3":
            solver = _solver(timeout_ms)
            solver.from_string(text)
            result = solver.check()
            return ReplayResult(str(result), perf_counter() - start,
                                solver.reason_unknown() if result == z3.unknown else None)
        if backend == "cvc5":
            return _replay_cvc5(text, timeout_ms, start)
        raise ValueError(f"unknown solver backend: {backend}")
    except (z3.Z3Exception, ValueError, RuntimeError, ImportError) as exc:
        return ReplayResult("error", perf_counter() - start, str(exc))


def _replay_cvc5(text: str, timeout_ms: int, start: float) -> ReplayResult:
    import cvc5  # Optional independent solver; not needed to extract.

    solver = cvc5.Solver()
    solver.setOption("tlimit-per", str(timeout_ms))
    solver.setOption("produce-models", "true")
    # Constant-array initialization uses SMT-LIB's `(as const ...)` operator.
    solver.setOption("arrays-exp", "true")
    parser = cvc5.InputParser(solver)
    parser.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6, text, "obligation.smt2")
    manager = parser.getSymbolManager()
    # Generated artifacts contain declarations/assertions and one check-sat.
    # Consume only formula-building commands, then perform our own single check.
    while True:
        command = parser.nextCommand()
        if command.isNull():
            break
        name = command.getCommandName()
        if name in {"check-sat", "get-model", "exit"}:
            continue
        if name not in {"set-logic", "declare-fun", "declare-sort", "define-fun", "assert", "set-info"}:
            raise ValueError(f"unsupported replay command: {name}")
        command.invoke(solver, manager)
    result = solver.checkSat()
    return ReplayResult(str(result), perf_counter() - start,
                        str(result.getUnknownExplanation()) if result.isUnknown() else None)
