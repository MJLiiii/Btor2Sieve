"""Candidate proposal: vocabulary from P, templates, and SMT-guided discovery.

Most tests state P directly as a Z3 formula over `s_<ID>` / `i_<ID>`, the
names Pono's variables get. Tests that need real BTOR2 structure have Pono
read the model (Pono must be on PATH, inside nix-shell).

The first half covers the default (uncapped) profile; the second half covers
the bounded profile selected with matched budgets.
"""

from dataclasses import replace
from decimal import Decimal

import pytest
import z3

from btor2sieve import implied
from btor2sieve.implied import Candidate, GenerationOptions
from btor2sieve.pono import read_model
from btor2sieve.vocabulary import (build_vocabulary, expression_width_allowed, select_subterms,
                                   variable_ids)


def prove(hypothesis, expression):
    solver = z3.Solver()
    solver.add(hypothesis, z3.Not(expression))
    return solver.check() == z3.unsat


def pono_p(tmp_path, text, bad):
    """P for one bad line, as Pono reads the model."""
    path = tmp_path / "model.btor2"
    path.write_text(text)
    (prop,) = read_model("pono", path, property_ids=[bad]).properties
    return prop.hypothesis


def discover(hypothesis, options=None):
    result = implied.discover_implied_candidates(hypothesis, options)
    keys = [z3.simplify(c.expr).sexpr() for c in result.candidates]
    assert len(keys) == len(set(keys))
    return result


def has(result, family, expr):
    return any(c.family == family and prove(z3.BoolVal(True), c.expr == expr)
               for c in result.candidates)


def test_equality_from_pono_keeps_inputs_and_ignores_unrelated_states(tmp_path):
    result = discover(pono_p(tmp_path, '''1 sort bitvec 1
2 sort bitvec 8
3 state 2 x
4 input 2 y
5 state 2 unrelated
6 eq 1 3 4
7 bad -6
''', 7))
    x, y = z3.BitVec('s_3', 8), z3.BitVec('i_4', 8)
    assert has(result, 'equality', x == y)
    assert all(5 not in c.source_nodes and 's_5' not in c.expr.sexpr() for c in result.candidates)
    assert all(set(c.source_nodes) <= {3, 4} for c in result.candidates)
    assert result.statistics['kind'] == 'property-word-level'
    assert result.statistics['complete']


def test_modular_arithmetic_discovers_bounds_and_known_mask():
    word = z3.BitVec('s_3', 4)
    result = discover(word * 2 == 10, GenerationOptions(max_terms=0, max_candidates=0, max_width=0,
                                                        max_queries=0))
    assert has(result, 'unsigned_bound', z3.UGE(word, 5))
    assert has(result, 'unsigned_bound', z3.ULE(word, 13))
    assert has(result, 'signed_bound', word >= -3)
    assert has(result, 'signed_bound', word <= 5)
    assert any(c.family == 'masked_bits' and c.expr.eq((word & 7) == 5) for c in result.candidates)
    assert has(result, 'disequality', word != 0)
    assert result.statistics['complete']


def test_predicate_implication_survives_discovery():
    enable, x = z3.BitVec('i_3', 1), z3.BitVec('s_4', 8)
    result = discover(z3.Implies(enable == 1, z3.ULE(x, 3)))
    assert has(result, 'implication', z3.Implies(enable == 1, z3.ULE(x, 3)))


@pytest.mark.parametrize('width, lower, upper', [(1, -1, -1), (4, -8, -1), (4, 0, 7), (129, -2, 2)])
def test_signed_and_unsigned_extrema(width, lower, upper):
    word = z3.BitVec('i_2', width)
    hypothesis = z3.And(word >= lower, word <= upper)
    result = discover(hypothesis)
    minimum, maximum = -(1 << (width - 1)), (1 << (width - 1)) - 1
    if lower != minimum and lower != upper:
        assert has(result, 'signed_bound', word >= lower)
    if upper != maximum and lower != upper:
        assert has(result, 'signed_bound', word <= upper)
    if lower == upper:
        assert has(result, 'equality', word == lower)
    assert result.statistics['complete']
    assert all(prove(hypothesis, c.expr) for c in result.candidates if c.origin.startswith('implied:semantic'))


def test_array_reads_and_nested_array_values_remain_typed(tmp_path):
    result = discover(pono_p(tmp_path, '''1 sort bitvec 1
2 sort bitvec 2
3 sort bitvec 8
4 sort array 2 3
5 sort array 2 4
6 input 5 outer
7 input 2 index
8 input 4 row
9 write 5 6 7 8
10 read 4 9 7
11 input 2 column
12 read 3 10 11
13 constd 3 7
14 eq 1 12 13
15 bad -14
''', 15))
    row, column = z3.Array('i_8', z3.BitVecSort(2), z3.BitVecSort(8)), z3.BitVec('i_11', 2)
    assert any(c.family == 'array' and 'select' in c.expr.sexpr() for c in result.candidates)
    assert any(c.family == 'array' and prove(z3.BoolVal(True), c.expr == (z3.Select(row, column) == 7))
               for c in result.candidates)
    assert result.statistics['complete']


def test_true_property_has_no_candidates():
    result = discover(z3.BoolVal(True))
    assert result.candidates == []
    assert result.statistics['complete']
    assert build_vocabulary(z3.BoolVal(True)).terms == []


def test_false_property_is_vacuous_without_candidates():
    result = discover(z3.BoolVal(False))
    assert result.candidates == []
    assert result.statistics['hypothesis_result'] == 'unsat'
    assert result.statistics['complete']
    assert 'unsatisfiable' in result.statistics['reason']


@pytest.mark.parametrize('initial', [True, False])
def test_unknown_never_becomes_a_proof_or_complete_search(monkeypatch, initial):
    word = z3.BitVec('s_2', 8)
    actual = z3.Solver.check
    monkeypatch.setattr(z3.Solver, 'check', lambda self, *conditions:
                        z3.unknown if initial or conditions else actual(self))
    monkeypatch.setattr(z3.Solver, 'reason_unknown', lambda self: 'deterministic timeout')
    result = discover(word == 3)
    assert not result.statistics['complete']
    assert result.statistics['discovery_unknown'] > 0
    assert all(not c.origin.startswith('implied:semantic') for c in result.candidates)
    assert 'timeout' in result.statistics['reason']


def test_uncapped_word_values_exceed_python_decimal_digit_limit():
    word = z3.BitVec('i_2', 15000)
    value = z3.BitVecVal(str(Decimal(1 << 14999)), 15000)
    result = discover(word == value)
    assert result.statistics['complete']
    assert has(result, 'equality', word == value)


def test_pono_comparisons_do_not_create_slice_predicates(tmp_path):
    result = discover(pono_p(tmp_path, '''1 sort bitvec 1
2 sort bitvec 10
3 state 2 pc
4 constd 2 15
5 ulte 1 3 4
6 bad -5
''', 6))
    pc = z3.BitVec('s_3', 10)
    assert all('extract' not in candidate.expr.sexpr() for candidate in result.candidates)
    assert any(candidate.expr.eq(z3.ULE(pc, 15)) for candidate in result.candidates)


def test_vocabulary_comes_from_the_subterms_of_p():
    x, y, flag = z3.BitVec('s_3', 8), z3.BitVec('i_4', 8), z3.BitVec('s_5', 1)
    vocabulary = build_vocabulary(z3.Not(z3.And(z3.ULT(x + y, 9), flag == 1)))
    assert {t.sexpr() for t in vocabulary.words} == {'s_3', 'i_4', '(bvadd s_3 i_4)', 's_5'}
    assert {p.sexpr() for p in vocabulary.predicates} >= {'(bvult (bvadd s_3 i_4) #x09)', '(= s_5 #b1)'}
    assert variable_ids(x + y == 0) == (3, 4)


def test_pono_one_bit_circuits_become_plain_predicates():
    x, y, flag = z3.BitVec('s_3', 8), z3.BitVec('i_4', 8), z3.BitVec('s_5', 1)
    bit = lambda formula: z3.If(formula, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
    hypothesis = z3.Not(z3.And((~z3.Extract(0, 0, x) | flag) == 1,  # A gate: split into its parts.
                               bit(z3.ULT(x, 7)) == 1,
                               ~bit(x == y) == 1))
    predicates = {p.sexpr() for p in build_vocabulary(hypothesis).predicates}
    assert '(bvult s_3 #x07)' in predicates
    assert '(= s_3 i_4)' in predicates
    assert '(= s_5 #b1)' in predicates
    assert not any('bvnot' in p or 'ite' in p for p in predicates)


# --- Bounded (matched-budget) profile ---------------------------------------

def matched(**changes):
    """Options for the bounded (matched-budget) profile."""
    return replace(GenerationOptions(matched_budgets=True), **changes)


def test_selected_vocabulary_stays_within_the_selected_subterms():
    x, y = z3.BitVec('i_3', 8), z3.BitVec('i_4', 8)
    hypothesis = z3.UGE(x + y, 40)
    budget = matched(max_terms=2)
    selected = select_subterms(hypothesis, budget.max_terms, budget.max_width)
    vocabulary = implied._vocabulary(hypothesis, budget)
    assert list(vocabulary.subterms) == selected and len(selected) == 2
    permitted = {i for term in selected for i in variable_ids(term)}
    candidates = list(implied.generate_implied_candidates(hypothesis, budget))
    assert candidates
    assert all(set(candidate.source_nodes) <= permitted for candidate in candidates)


@pytest.mark.parametrize('queries', [1, 2, 3, 5, 10])
def test_discovery_query_cutoff_never_becomes_an_unsat_answer(monkeypatch, queries):
    word = z3.BitVec('i_2', 8)
    hypothesis = z3.And(z3.UGE(word, 40), z3.ULE(word, 200))
    actual_check = z3.Solver.check
    calls = []

    def counted_check(self, *assumptions):
        calls.append(assumptions)
        return actual_check(self, *assumptions)

    monkeypatch.setattr(z3.Solver, 'check', counted_check)
    result = implied.discover_implied_candidates(hypothesis, matched(max_queries=queries))
    assert len(calls) == result.statistics['discovery_queries'] <= queries
    assert result.statistics['complete']
    assert result.statistics['coverage'] == 'budgeted'
    assert result.statistics['discovery_unknown'] == 0
    assert 'max_queries' in result.statistics['budget_exhausted']
    monkeypatch.setattr(z3.Solver, 'check', actual_check)
    for candidate in result.candidates:
        if candidate.origin == 'implied:semantic':
            assert prove(hypothesis, candidate.expr)
    if queries == 1:
        assert all(candidate.origin != 'implied:semantic' for candidate in result.candidates)


def test_candidate_cap_stops_template_enumeration_lazily(monkeypatch):
    word = z3.BitVec('i_2', 8)
    visited = []

    def proposals(*_args):
        for value in range(200):
            visited.append(value)
            yield Candidate(word == value, 'equality', 'implied:syntax', (2,))

    monkeypatch.setattr(implied, '_templates', proposals)
    result = implied.discover_implied_candidates(z3.UGE(word, 40), matched(max_candidates=2, max_queries=1))
    assert len(result.candidates) == result.statistics['total_candidates'] == 2
    assert visited == [0, 1]
    assert 'max_candidates' in result.statistics['budget_exhausted']
    assert result.statistics['complete']
    visited.clear()
    assert len(list(implied.generate_implied_candidates(z3.UGE(word, 40), matched(max_candidates=2)))) == 2
    assert visited == [0, 1]


def test_width_cap_checks_comparison_operands_and_array_index_sorts():
    wide, other = z3.BitVec('i_5', 129), z3.BitVec('i_6', 129)
    memory = z3.Array('i_8', z3.BitVecSort(129), z3.BitVecSort(4))
    narrow = z3.BitVec('i_9', 4)
    hypothesis = z3.Not(z3.And(wide == other, z3.Select(memory, wide) == 0, z3.ULT(narrow, 3)))
    vocabulary = implied._vocabulary(hypothesis, matched(max_width=64, max_terms=20))
    assert vocabulary.subterms
    assert all(expression_width_allowed(term, 64) for term in vocabulary.subterms)
    used = {i for term in vocabulary.terms + vocabulary.predicates for i in variable_ids(term)}
    assert used == {9}


@pytest.mark.parametrize('name', ['max_candidates', 'max_terms', 'max_width', 'max_queries'])
def test_matched_profile_rejects_nonpositive_budgets(name):
    word = z3.BitVec('i_2', 8)
    budget = matched(**{name: 0})
    with pytest.raises(ValueError, match='positive'):
        implied.discover_implied_candidates(word == 3, budget)
    with pytest.raises(ValueError, match='positive'):
        list(implied.generate_implied_candidates(word == 3, budget))


def test_parity_predicate_is_not_mislabeled_as_an_equality(tmp_path):
    hypothesis = pono_p(tmp_path, '''1 sort bitvec 1
2 sort bitvec 4
3 input 2 x
4 redxor 1 3
5 bad -4
''', 5)
    candidates = list(implied.generate_implied_candidates(hypothesis, matched()))
    assert candidates
    for candidate in candidates:
        if candidate.family == 'equality':
            assert z3.is_eq(candidate.expr)
