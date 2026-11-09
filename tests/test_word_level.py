import pytest
import z3

from btor2sieve.btor2 import parse
from btor2sieve.methods.common import GenerationOptions
from btor2sieve.methods.word_level import generate_candidates
from btor2sieve.encoding import Encoder


def check(hypothesis, candidate):
    solver = z3.Solver()
    solver.add(hypothesis, z3.Not(candidate))
    return solver.check()


def test_syntax_generates_bounds_and_keeps_rejected_guesses():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 input 1 word
4 constd 1 3
5 ugt 2 3 4
6 bad 5
"""))
    hypothesis = encoder.property(6)
    candidates = generate_candidates(encoder, hypothesis, [5], GenerationOptions(semantic=False))
    word = encoder.expr(3)
    assert any(c.family == "unsigned_bound" and c.expr.eq(z3.ULE(word, 4)) for c in candidates)
    assert any(c.family == "signed_bound" for c in candidates)
    assert any(c.family == "equality" and check(hypothesis, c.expr) == z3.sat for c in candidates)
    assert any(c.family == "disequality" and check(hypothesis, c.expr) == z3.unsat for c in candidates)
    assert all(not z3.simplify(c.expr).eq(z3.simplify(hypothesis)) for c in candidates)


def test_syntax_keeps_local_implications_and_mask_consequences():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 input 1 word
4 constd 1 12
5 and 1 3 4
6 constd 1 4
7 eq 2 5 6
8 zero 1
9 neq 2 3 8
10 and 2 7 9
11 bad -10
"""))
    hypothesis = encoder.property(11)
    candidates = generate_candidates(encoder, hypothesis, [-10], GenerationOptions(semantic=False))
    assert any(c.family == "implication" and check(hypothesis, c.expr) == z3.unsat
               and check(z3.BoolVal(True), c.expr) == z3.sat for c in candidates)
    assert any(c.family == "masked_bits" and 3 in c.source_nodes
               and check(hypothesis, c.expr) == z3.unsat for c in candidates)


def test_syntax_preserves_read_over_write_identity_and_array_guesses():
    encoder = Encoder(parse("""1 sort bitvec 2
2 sort bitvec 4
3 sort array 1 2
4 input 3 mem
5 input 1 index
6 input 2 data
7 write 3 4 5 6
8 read 2 7 5
"""))
    candidates = generate_candidates(encoder, z3.BoolVal(True), [8], GenerationOptions(semantic=False))
    expected = encoder.expr(8) == encoder.expr(6)
    assert any(c.family == "array" and 7 in c.source_nodes
               and c.expr.eq(expected) and check(z3.BoolVal(True), c.expr) == z3.unsat
               for c in candidates)
    assert any(c.family == "array" and check(z3.BoolVal(True), c.expr) == z3.sat for c in candidates)


def test_semantic_discovers_exact_interval_and_known_bits_independently():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 state 1 word
4 constd 1 2
5 mul 1 3 4
6 constd 1 10
7 eq 2 5 6
8 bad -7
"""))
    hypothesis = encoder.property(8)
    candidates = generate_candidates(encoder, hypothesis, [-7])
    discovered = [c for c in candidates if c.origin.startswith("semantic:")]
    word = encoder.expr(3)
    # The only solutions to 2*x = 10 modulo 16 are 5 and 13.
    assert any(c.expr.eq(z3.UGE(word, 5)) for c in discovered)
    assert any(c.expr.eq(z3.ULE(word, 13)) for c in discovered)
    assert any(c.expr.eq((word & 7) == 5) for c in discovered)
    assert all(check(hypothesis, c.expr) == z3.unsat for c in discovered)
    limited = generate_candidates(encoder, hypothesis, [-7], GenerationOptions(max_candidates=1))
    assert len(limited) == 1
    assert limited[0].origin.startswith("semantic:")


def test_empty_roots_fall_back_to_declarations_and_honor_width_and_term_limits():
    encoder = Encoder(parse("""1 sort bitvec 128
2 sort bitvec 4
3 input 1 wide
4 state 2 first
5 input 2 second
"""))
    options = GenerationOptions(max_terms=1, max_candidates=4, semantic=False)
    first = generate_candidates(encoder, z3.BoolVal(True), [], options)
    second = generate_candidates(encoder, z3.BoolVal(True), [], options)
    assert 0 < len(first) <= 4
    assert all(c.source_nodes == (4,) for c in first)
    assert [(c.expr.sexpr(), c.family, c.origin) for c in first] == [
        (c.expr.sexpr(), c.family, c.origin) for c in second
    ]
    assert len({z3.simplify(c.expr).sexpr() for c in first}) == len(first)


@pytest.mark.parametrize("result", [z3.sat, z3.unknown])
def test_discovery_obeys_query_budget_and_stops_on_unknown(monkeypatch, result):
    encoder = Encoder(parse("""1 sort bitvec 4
2 state 1 word
"""))
    hypothesis = encoder.expr(2) == 5
    calls = []
    real_solver = z3.Solver

    class TrackingSolver:
        def __init__(self, *args, **kwargs):
            self.solver = real_solver(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.solver, name)

        def check(self, *args):
            calls.append(args)
            if len(calls) == 2 and result == z3.unknown:
                return z3.unknown
            return self.solver.check(*args)

    monkeypatch.setattr(z3, "Solver", TrackingSolver)
    budget = 2 if result == z3.sat else 256
    candidates = generate_candidates(encoder, hypothesis, [], GenerationOptions(max_queries=budget))
    assert len(calls) == 2
    if result == z3.unknown:
        assert all(not c.origin.startswith("semantic:") for c in candidates)


def test_syntax_keeps_word_bounds_when_same_sort_pairs_fill_budget():
    declarations = "\n".join(f"{node_id} input 1" for node_id in range(2, 18))
    encoder = Encoder(parse(f"1 sort bitvec 4\n{declarations}\n"))
    candidates = generate_candidates(encoder, z3.BoolVal(True), [], GenerationOptions(semantic=False))
    assert len(candidates) == 200
    assert {"equality", "disequality", "unsigned_bound", "signed_bound"} <= {c.family for c in candidates}


def test_syntax_uses_values_of_complemented_literal_references():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 input 1 word
4 constd 1 5
5 ugt 2 3 -4
6 bad 5
"""))
    hypothesis = encoder.property(6)
    candidates = generate_candidates(encoder, hypothesis, [5], GenerationOptions(semantic=False))
    assert any(c.family == "unsigned_bound" and c.expr.eq(z3.ULE(encoder.expr(3), 11))
               for c in candidates)


def test_syntax_generates_a_nontrivial_array_read_consequence():
    encoder = Encoder(parse("""1 sort bitvec 2
2 sort bitvec 4
3 sort bitvec 1
4 sort array 1 2
5 input 4 mem
6 input 1 address
7 read 2 5 6
8 constd 2 3
9 neq 3 7 8
10 bad 9
"""))
    hypothesis = encoder.property(10)
    candidates = generate_candidates(encoder, hypothesis, [9], GenerationOptions(semantic=False))
    expected = encoder.expr(7) != 4
    assert any(c.family == "array" and c.expr.eq(expected)
               and check(hypothesis, c.expr) == z3.unsat
               and check(z3.BoolVal(True), c.expr) == z3.sat for c in candidates)


def test_reversed_equality_is_deduplicated_against_the_hypothesis():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 input 1 left
4 input 1 right
5 neq 2 3 4
6 bad 5
"""))
    hypothesis = encoder.property(6)
    candidates = generate_candidates(encoder, hypothesis, [4, 3, 5], GenerationOptions(semantic=False))
    reversed_equality = encoder.expr(4) == encoder.expr(3)
    assert all(not c.expr.eq(reversed_equality) for c in candidates)


def test_deep_boolean_cone_reserves_slots_for_word_facts():
    depth = 64
    wrappers = "\n".join(f"{node_id} not 2 {node_id - 1}" for node_id in range(8, 8 + depth))
    root = 7 + depth
    encoder = Encoder(parse(f"""1 sort bitvec 4
2 sort bitvec 1
3 state 1 word
4 constd 1 2
5 mul 1 3 4
6 constd 1 10
7 eq 2 5 6
{wrappers}
{root + 1} bad -{root}
"""))
    hypothesis = encoder.property(root + 1)
    candidates = generate_candidates(encoder, hypothesis, [-root], GenerationOptions(max_terms=4))
    word = encoder.expr(3)
    discovered = [c for c in candidates if c.origin.startswith("semantic:")]
    assert any(c.expr.eq(z3.ULE(word, 13)) for c in discovered)
    assert any(c.expr.eq((word & 7) == 5) for c in discovered)
    assert all(check(hypothesis, c.expr) == z3.unsat for c in discovered)


def test_selection_keeps_nearby_guards_and_word_terms_under_budget():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 input 2 enable
4 state 1 word
5 constd 1 5
6 eq 2 4 5
7 zero 2
8 ite 2 3 6 7
9 bad -8
"""))
    hypothesis = encoder.property(9)
    candidates = generate_candidates(encoder, hypothesis, [-8], GenerationOptions(max_terms=5, semantic=False))
    guard_implies_equality = z3.Implies(encoder.bool_expr(3), encoder.expr(4) == 5)
    assert any(c.family == "implication"
               and z3.simplify(c.expr).eq(z3.simplify(guard_implies_equality))
               for c in candidates)
    assert any(c.family == "unsigned_bound" and 4 in c.source_nodes for c in candidates)


@pytest.mark.parametrize("zero_budget", ["max_candidates", "max_terms", "max_width", "max_queries"])
def test_zero_budgets_disable_only_the_relevant_work(zero_budget):
    encoder = Encoder(parse("1 sort bitvec 4\n2 input 1 word\n"))
    options = GenerationOptions(**{zero_budget: 0})
    candidates = generate_candidates(encoder, encoder.expr(2) == 5, [], options)
    if zero_budget == "max_queries":
        assert candidates
        assert all(c.origin.startswith("syntax:") for c in candidates)
    else:
        assert candidates == []


@pytest.mark.parametrize("stop_call, expected", [(4, "minimum"), (8, "maximum")])
@pytest.mark.parametrize("interruption", ["budget", "unknown"])
def test_partial_bounds_after_unsat_refinement_remain_sound(monkeypatch, stop_call, expected, interruption):
    encoder = Encoder(parse("1 sort bitvec 4\n2 state 1 word\n"))
    word = encoder.expr(2)
    hypothesis = z3.And(z3.UGE(word, 5), z3.ULE(word, 10))
    real_solver = z3.Solver
    results = []

    class InterruptingSolver:
        def __init__(self, *args, **kwargs):
            self.solver = real_solver(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.solver, name)

        def check(self, *args):
            if interruption == "unknown" and len(results) + 1 == stop_call:
                result = z3.unknown
            else:
                result = self.solver.check(*args)
            results.append(result)
            return result

    with monkeypatch.context() as patch:
        patch.setattr(z3, "Solver", InterruptingSolver)
        budget = stop_call - 1 if interruption == "budget" else 256
        candidates = generate_candidates(encoder, hypothesis, [], GenerationOptions(max_queries=budget))
    assert results[-2 if interruption == "unknown" else -1] == z3.unsat
    partial = [c for c in candidates if c.origin == "semantic:interval-partial"]
    bound = z3.UGE(word, 4) if expected == "minimum" else z3.ULE(word, 11)
    assert any(c.expr.eq(bound) for c in partial)
    for candidate in partial:
        assert candidate.family == "unsigned_bound"
        assert candidate.source_nodes == (2,)
        # Check each partial guarantee with a fresh, uninterrupted solver.
        assert check(hypothesis, candidate.expr) == z3.unsat
