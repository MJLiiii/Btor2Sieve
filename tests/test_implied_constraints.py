from itertools import product

import pytest
import z3

from btor2sieve.btor2 import parse
from btor2sieve.methods.common import Candidate, GenerationOptions
from btor2sieve.encoding import Encoder
from btor2sieve.methods.implied_constraints import find_equivalences, generate_implied_candidates
from btor2sieve.validation import Validator


def bit_model(count=2):
    declarations = "\n".join(f"{index + 2} state 1" for index in range(count))
    return Encoder(parse(f"1 sort bitvec 1\n{declarations}\n"))


def truth_table(expr, words):
    return tuple(
        z3.is_true(z3.simplify(z3.substitute(
            expr, *((word, z3.BitVecVal(value, word.size()))
                    for word, value in zip(words, values))
        )))
        for values in product((0, 1), repeat=len(words))
    )


def test_literal_vocabulary_matches_all_nontrivial_implications_exhaustively():
    encoder = bit_model(3)
    words = list(encoder.states.values())
    candidates = generate_implied_candidates(encoder, [], GenerationOptions())
    actual = [truth_table(candidate.expr, words) for candidate in candidates]
    # Independent Boolean semantics over every ordered signed literal pair.
    valuations = list(product((False, True), repeat=3))
    expected = {
        tuple(not (values[left] == left_sign) or (values[right] == right_sign)
              for values in valuations)
        for left, right in product(range(3), repeat=2)
        for left_sign, right_sign in product((False, True), repeat=2)
    } - {(True,) * 8}
    assert len(candidates) == 18
    assert len(actual) == len(set(actual))
    assert set(actual) == expected
    assert all(z3.is_implies(candidate.expr) for candidate in candidates)
    assert all(candidate.family == "implication" for candidate in candidates)


def test_validator_acceptance_matches_every_nonempty_two_bit_property():
    encoder = bit_model()
    words = list(encoder.states.values())
    candidates = generate_implied_candidates(encoder, [], GenerationOptions())
    valuations = list(product((0, 1), repeat=2))
    for mask in range(1, 16):
        allowed = [values for index, values in enumerate(valuations) if mask & (1 << index)]
        hypothesis = z3.Or([z3.And([word == value for word, value in zip(words, values)])
                            for values in allowed])
        validator = Validator(hypothesis)
        for candidate in candidates:
            table = truth_table(candidate.expr, words)
            expected = all(table[index] for index in range(4) if mask & (1 << index))
            assert (validator.check(candidate.expr).status == "accepted") == expected


@pytest.mark.parametrize("complemented", [False, True])
def test_equivalences_link_two_accepted_implications(complemented):
    encoder = bit_model()
    left, right = (encoder.bool_expr(node) for node in encoder.states)
    hypothesis = left != right if complemented else left == right
    validator = Validator(hypothesis)
    accepted = [(candidate, f"proof-{index}") for index, candidate in enumerate(
        generate_implied_candidates(encoder, [], GenerationOptions()))
        if validator.check(candidate.expr).status == "accepted"]
    equivalences = find_equivalences(accepted)
    assert len(equivalences) == 1
    record = equivalences[0]
    assert tuple(record["source_nodes"]) == (2, 3)
    assert len(set(record["implication_ids"])) == 2
    proofs = {proof_id: candidate for candidate, proof_id in accepted}
    expression = z3.parse_smt2_string(
        "(declare-fun s_2 () (_ BitVec 1))\n"
        "(declare-fun s_3 () (_ BitVec 1))\n"
        f"(assert {record['expression']})"
    )[0]
    assert z3.is_eq(expression)
    assert truth_table(expression, list(encoder.states.values())) == (
        (False, True, True, False) if complemented else (True, False, False, True)
    )
    solver = z3.Solver()
    solver.add(*(proofs[proof_id].expr for proof_id in record["implication_ids"]))
    solver.add(z3.Not(expression))
    assert solver.check() == z3.unsat


def test_equivalence_normalizes_contrapositives_and_deduplicates_proofs():
    a, b = z3.Bools("a b")
    accepted = [
        (Candidate(z3.Implies(a, b), "implication", "test", (2, 3)), "forward"),
        (Candidate(z3.Implies(z3.Not(a), z3.Not(b)), "implication", "test", (2, 3)), "reverse"),
        (Candidate(z3.Implies(b, a), "implication", "test", (3, 2)), "duplicate"),
        (Candidate(z3.Implies(a, z3.Not(a)), "implication", "test", (2,)), "unit"),
    ]
    records = find_equivalences(accepted)
    assert len(records) == 1
    assert records[0]["expression"] == (a == b).sexpr()
    assert records[0]["implication_ids"] == ["forward", "reverse"]
    assert find_equivalences(accepted[:1]) == []
    assert find_equivalences(accepted[-1:]) == []


def test_word_bits_are_round_robin_with_cone_priority_and_fallback():
    encoder = Encoder(parse("""1 sort bitvec 3
2 sort bitvec 1
3 state 1 outside
4 state 1 left
5 state 1 right
6 eq 2 4 5
7 bad -6
"""))
    options = GenerationOptions(max_terms=2, max_candidates=100)
    candidates = generate_implied_candidates(encoder, [-6], options)
    assert {node for candidate in candidates for node in candidate.source_nodes} == {4, 5}
    selected_words = [z3.Extract(0, 0, encoder.expr(node)) for node in (4, 5)]
    tables = {truth_table(candidate.expr, selected_words) for candidate in candidates}
    assert (True, True, False, False) in tables  # left bit zero
    assert (False, True, False, True) in tables  # right bit one
    fallback = generate_implied_candidates(
        encoder, [-6], GenerationOptions(max_terms=7, max_candidates=100)
    )
    assert {node for candidate in fallback for node in candidate.source_nodes} == {3, 4, 5}
    assert len(fallback) == 98


def test_arrays_inputs_and_overwide_states_are_not_literal_candidates():
    encoder = Encoder(parse("""1 sort bitvec 1
2 sort bitvec 4
3 sort bitvec 128
4 sort array 1 2
5 state 4 memory
6 input 1 input_bit
7 state 3 wide
8 state 2 eligible
"""))
    candidates = generate_implied_candidates(
        encoder, [], GenerationOptions(max_width=4, max_terms=3)
    )
    assert len(candidates) == 18
    assert all(candidate.source_nodes == (8,) for candidate in candidates)
    assert any("extract 2 2" in candidate.expr.sexpr() for candidate in candidates)
    assert all("extract 3 3" not in candidate.expr.sexpr() for candidate in candidates)
    arrays_only = Encoder(parse("1 sort bitvec 1\n2 sort array 1 1\n3 state 2\n"))
    assert generate_implied_candidates(arrays_only, [], GenerationOptions()) == []


@pytest.mark.parametrize("limit", [0, 1, 3, 7, 8, 100])
def test_candidate_budget_is_a_deterministic_prefix(limit):
    encoder = bit_model()
    complete = generate_implied_candidates(encoder, [], GenerationOptions())
    limited = generate_implied_candidates(encoder, [], GenerationOptions(max_candidates=limit))
    assert [candidate.expr.sexpr() for candidate in limited] == [
        candidate.expr.sexpr() for candidate in complete[:limit]
    ]


@pytest.mark.parametrize("budget", ["max_terms", "max_width"])
def test_zero_vocabulary_budgets_produce_no_candidates(budget):
    assert generate_implied_candidates(bit_model(), [], GenerationOptions(**{budget: 0})) == []


def test_discovery_query_budget_and_semantic_flag_do_not_disable_literal_enumeration():
    candidates = generate_implied_candidates(
        bit_model(), [], GenerationOptions(max_queries=0, semantic=False)
    )
    assert len(candidates) == 8


@pytest.mark.parametrize("budget", ["max_candidates", "max_terms", "max_width"])
def test_negative_budgets_are_rejected(budget):
    with pytest.raises(ValueError, match="nonnegative"):
        generate_implied_candidates(bit_model(), [], GenerationOptions(**{budget: -1}))
