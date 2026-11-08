"""Validation must never accept a guess solely because generation suggests it."""

import z3
import pytest

from btor2sieve.validation import Validator, replay_smt2


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
