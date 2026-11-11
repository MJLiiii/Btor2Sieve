"""Validation must never accept a guess solely because generation suggests it."""

import z3
import pytest

from btor2sieve.pono import read_model
from btor2sieve.validation import Validator, property_scopes, replay_smt2


def test_invalid_candidate_has_counterexample_and_valid_one_replays():
    x = z3.BitVec("x", 8)
    validator = Validator(z3.ULT(x, 10))
    accepted = validator.check(z3.ULE(x, 9))
    rejected = validator.check(x == 0)
    assert accepted.status == "accepted"
    assert accepted.solver_result == "unsat"
    assert replay_smt2(accepted.smt2).status == "unsat"
    assert rejected.status == "rejected"
    assert rejected.solver_result == "sat"
    assert 0 < int(rejected.counterexample["x"]) < 10


def test_contradictory_hypothesis_is_vacuous_not_accepted():
    x = z3.BitVec("x", 4)
    result = Validator(z3.And(x == 0, x == 1)).check(x == 7)
    assert result.status == "vacuous"
    assert result.hypothesis_result == "unsat"
    assert result.solver_result == "unsat"


def test_validation_queries_do_not_leak_between_candidates():
    x = z3.BitVec("x", 4)
    validator = Validator(x == 3)
    assert validator.check(x == 3).status == "accepted"
    assert validator.check(x == 4).status == "rejected"
    assert validator.check(x == 3).status == "accepted"


def test_bv_sort_candidate_is_rejected_with_clear_error():
    with pytest.raises(ValueError, match="Boolean"):
        Validator(z3.BoolVal(True)).check(z3.BitVec("x", 4))


def test_resource_exhaustion_is_unknown_not_proof():
    # Tiny deterministic resource limit, rather than a wall-clock race.
    xs = [z3.BitVec(f"x{i}", 64) for i in range(10)]
    h = z3.And(*[xs[i] * xs[i + 1] == 163 for i in range(9)])
    result = Validator(h, rlimit=1).check(xs[0] == 0)
    assert result.status == "unknown"
    assert result.reason


def test_replay_does_not_treat_bad_smt_or_multiple_checks_as_success():
    assert replay_smt2("not SMT-LIB").status == "error"
    # Replay consumes assertions, not a forged expected-result comment.
    assert replay_smt2("; expected unsat\n(assert true)\n(check-sat)").status == "sat"


def test_independent_cvc5_replay_for_arrays_and_bitvectors():
    pytest.importorskip("cvc5")
    a = z3.Array("a", z3.BitVecSort(4), z3.BitVecSort(8))
    i = z3.BitVec("i", 4)
    v = z3.BitVec("v", 8)
    result = Validator(v == 42).check(z3.Select(z3.Store(a, i, v), i) == 42)
    assert result.status == "accepted"
    replay = replay_smt2(result.smt2, backend="cvc5")
    assert replay.status == "unsat", replay.reason


def test_cvc5_replays_constant_array_initialization_satisfiability():
    pytest.importorskip("cvc5")
    array = z3.Array("memory", z3.BitVecSort(4), z3.BitVecSort(8))
    validator = Validator(array == z3.K(z3.BitVecSort(4), z3.BitVecVal(42, 8)))
    replay = replay_smt2(validator.hypothesis_smt2, backend="cvc5")
    assert replay.status == "sat", replay.reason


def test_validator_accepts_formulas_from_an_explicit_z3_context():
    context = z3.Context()
    x = z3.BitVec("local_x", 8, ctx=context)
    validator = Validator(x == 10)
    assert validator.check(z3.ULE(x, 20)).status == "accepted"
    assert validator.check(x == 9).status == "rejected"


def test_unsat_implication_with_unknown_hypothesis_is_not_accepted(monkeypatch):
    # Force only the antecedent check to be UNKNOWN; solve the implication
    # normally so this tests classification without a wall-clock timeout race.
    original_check = z3.Solver.check
    first_check = True

    def interrupted_hypothesis(solver, *assumptions):
        nonlocal first_check
        if first_check:
            first_check = False
            return z3.unknown
        return original_check(solver, *assumptions)

    monkeypatch.setattr(z3.Solver, "check", interrupted_hypothesis)
    word = z3.BitVec("word", 4)
    result = Validator(word == 3).check(z3.ULE(word, 3))
    assert result.solver_result == "unsat"
    assert result.hypothesis_result == "unknown"
    assert result.status == "unknown"
    assert "hypothesis satisfiability unknown" in result.reason


def test_property_scope_does_not_silently_assume_environment(tmp_path):
    path = tmp_path / "model.btor2"
    path.write_text("""1 sort bitvec 1
2 sort bitvec 8
3 state 2 counter
4 constd 2 10
5 eq 1 3 4
6 bad 5
7 ult 1 3 4
8 constraint 7
""")
    [scope] = property_scopes(read_model("pono", path))
    counter = z3.BitVec("s_3", 8)
    # Pono read P = counter != 10, without the environment constraint counter < 10.
    solver = z3.Solver()
    solver.add(scope.hypothesis != (counter != 10))
    assert solver.check() == z3.unsat
    assert Validator(scope.hypothesis).check(z3.ULT(counter, 10)).status == "rejected"
