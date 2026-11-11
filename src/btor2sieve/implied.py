"""Propose property-implied bit-vector and array constraints.

Everything here is *untrusted*: it only proposes candidate formulas C. The
separate ``Validator`` decides whether the property P really implies C.

Two kinds of proposals are made from the vocabulary of P, the formula Pono
read for the property (its subterms; see ``vocabulary.py``):

* Templates (syntax): both polarities of each predicate, implications between
  predicate pairs, word comparisons with constants and landmarks (0, 1, max,
  sign bit), equalities between same-sort operands of a subterm, and typed
  array read/write relations.
* Semantic facts (SMT-guided, assuming exactly P): for every word, its known
  bits (a mask) and its exact signed and unsigned minimum and maximum.

The default profile is uncapped; every solver query still has a timeout.
``matched_budgets`` bounds the source selection, widths, proposals, and
discovery queries. A completed search means the procedure finished without
solver UNKNOWN; it never means all logical consequences were found.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from itertools import chain, combinations, islice

import z3

from .vocabulary import Vocabulary, build_vocabulary, variable_ids


FAMILIES = (
    "unsigned_bound", "signed_bound", "equality", "disequality",
    "implication", "masked_bits", "array",
)
BUDGET_NAMES = ("max_candidates", "max_terms", "max_width", "max_queries")


@dataclass(frozen=True)
class Candidate:
    expr: z3.BoolRef
    family: str
    origin: str
    source_nodes: tuple[int, ...] = ()  # line IDs of the states and inputs C reads


@dataclass(frozen=True)
class GenerationOptions:
    # The max_* budgets apply only when matched_budgets is set.
    max_candidates: int | None = 200
    max_terms: int | None = 16
    max_width: int | None = 64
    timeout_ms: int = 1000
    max_queries: int | None = 256
    matched_budgets: bool = False


@dataclass
class ImpliedDiscovery:
    candidates: list[Candidate]
    statistics: dict


def check_options(options: GenerationOptions) -> None:
    """Reject settings that would make a search meaningless."""
    if options.timeout_ms <= 0:
        raise ValueError("timeout_ms must be positive")
    if options.matched_budgets and any(
            getattr(options, name) is None or getattr(options, name) <= 0 for name in BUDGET_NAMES):
        raise ValueError("matched discovery budgets must be positive")


def _bv(value: int, sort: z3.BitVecSortRef) -> z3.BitVecRef:
    # Decimal avoids Python's integer-to-string digit limit for wide words.
    literal = z3.BitVecVal(str(Decimal(value)), sort)
    # Wrap as a plain BitVecRef so `literal <op> word` keeps its written order.
    return z3.BitVecRef(literal.as_ast(), sort.ctx)


def _unsigned(value: z3.BitVecNumRef) -> int:
    return int(value.as_binary_string(), 2)  # Base 2 has no digit limit.


def _vocabulary(hypothesis: z3.BoolRef, options: GenerationOptions) -> Vocabulary:
    if options.matched_budgets:
        return build_vocabulary(hypothesis, options.max_terms, options.max_width)
    return build_vocabulary(hypothesis)


# --- Templates --------------------------------------------------------------

def _contains(expr: z3.ExprRef, kinds: set[int]) -> bool:
    pending, seen = [expr], set()
    while pending:
        item = pending.pop()
        if item.get_id() in seen:
            continue
        seen.add(item.get_id())
        if item.decl().kind() in kinds:
            return True
        pending.extend(item.children())
    return False


def _family(expr: z3.BoolRef) -> str | None:
    """Classify a formula; None means it is not one of the reported families."""
    if _contains(expr, {z3.Z3_OP_SELECT, z3.Z3_OP_STORE}) or any(z3.is_array(c) for c in expr.children()):
        return "array"
    if z3.is_not(expr):
        child = expr.arg(0)
        if z3.is_eq(child):
            return "array" if any(z3.is_array(c) for c in child.children()) else "disequality"
        return _family(child)
    if _contains(expr, {z3.Z3_OP_BAND}) and z3.is_eq(expr):
        return "masked_bits"
    kind = expr.decl().kind()
    if kind in {z3.Z3_OP_ULEQ, z3.Z3_OP_UGEQ, z3.Z3_OP_ULT, z3.Z3_OP_UGT}:
        return "unsigned_bound"
    if kind in {z3.Z3_OP_SLEQ, z3.Z3_OP_SGEQ, z3.Z3_OP_SLT, z3.Z3_OP_SGT}:
        return "signed_bound"
    if z3.is_implies(expr):
        return "implication"
    if z3.is_distinct(expr):
        return "disequality"
    return "equality" if z3.is_eq(expr) else None


def _proposal(expr: z3.BoolRef, family: str | None = None) -> Candidate:
    return Candidate(expr, family or _family(expr), "implied:syntax", variable_ids(expr))


def _templates(vocabulary: Vocabulary) -> Iterator[Candidate]:
    """Yield syntactic proposals; each is still checked independently later."""
    # 1. Each predicate in both polarities. Predicates without a family are
    #    still used in step 2.
    for predicate in vocabulary.predicates:
        if _family(predicate) is not None:
            yield _proposal(predicate)
            yield _proposal(z3.Not(predicate))

    # 2. Implications between predicate pairs. Four clauses suffice: the
    #    reverse directions are their contrapositives.
    for left, right in combinations(vocabulary.predicates, 2):
        for antecedent, consequent in (
            (left, right), (right, left), (left, z3.Not(right)), (z3.Not(left), right),
        ):
            yield _proposal(z3.Implies(antecedent, consequent), family="implication")

    # 3. Each word compared with same-sort constants from P and with the
    #    landmarks 0, 1, all ones, signed minimum, and signed maximum.
    constants: dict[str, set[int]] = {}
    for term in vocabulary.terms:
        value = z3.simplify(term)
        if z3.is_bv_value(value):
            constants.setdefault(value.sort().sexpr(), set()).add(_unsigned(value))
    for word in vocabulary.words:
        width = word.size()
        values = set(constants.get(word.sort().sexpr(), ()))
        values.update((0, 1, (1 << width) - 1, 1 << (width - 1), (1 << (width - 1)) - 1))
        for value in sorted(values):
            literal = _bv(value, word.sort())
            for expression in (word == literal, word != literal):
                yield _proposal(expression)
            for expression, family in (
                (z3.UGE(word, literal), "unsigned_bound"), (z3.ULE(word, literal), "unsigned_bound"),
                (word >= literal, "signed_bound"), (word <= literal, "signed_bound"),
            ):
                yield _proposal(expression, family=family)

    # 4. Relations local to one subterm: its same-sort word or array operands
    #    (no all-pairs product over every word), read-over-write, and array
    #    (dis)equality.
    for term in vocabulary.subterms:
        operands = [child for child in term.children() if not z3.is_bool(child)]
        for left, right in combinations(operands, 2):
            if left.sort().eq(right.sort()):
                for expression in (left == right, left != right):
                    yield _proposal(expression)
        if z3.is_select(term) and z3.is_store(term.arg(0)):
            base, address, value = term.arg(0).children()
            index = term.arg(1)
            yield _proposal(z3.Implies(index == address, term == value), family="array")
            yield _proposal(z3.Implies(index != address, term == z3.Select(base, index)), family="array")
        if (z3.is_eq(term) or z3.is_distinct(term)) and z3.is_array(term.arg(0)):
            left, right = term.arg(0), term.arg(1)
            for index in vocabulary.terms:
                if left.domain().eq(index.sort()):
                    yield _proposal(z3.Select(left, index) == z3.Select(right, index), family="array")


def _unique(candidates: Iterable[Candidate]) -> Iterator[Candidate]:
    """Drop trivial and duplicate formulas (compared after simplification)."""
    seen = set()
    for candidate in candidates:
        expression = z3.simplify(candidate.expr)
        if z3.is_true(expression) or z3.is_false(expression):
            continue
        key = expression.sexpr()
        if key not in seen:
            seen.add(key)
            # Keep the original formula: simplification can erase masks,
            # reads/writes, and other useful native structure.
            yield candidate


def generate_implied_candidates(
    hypothesis: z3.BoolRef, options: GenerationOptions | None = None,
) -> Iterator[Candidate]:
    """Yield template proposals for P only (no solver calls)."""
    options = options or GenerationOptions()
    check_options(options)
    candidates = _unique(_templates(_vocabulary(hypothesis, options)))
    yield from islice(candidates, options.max_candidates) if options.matched_budgets else candidates


# --- SMT-guided discovery ---------------------------------------------------

class _Search:
    """A solver that holds P, counts queries, and enforces the query budget."""

    def __init__(self, hypothesis: z3.BoolRef, options: GenerationOptions, stats: dict):
        self.solver = z3.Solver(ctx=hypothesis.ctx)
        self.solver.set(timeout=options.timeout_ms, random_seed=0)
        self.solver.add(hypothesis)
        self.max_queries = options.max_queries if options.matched_budgets else None
        self.stats = stats

    def check(self, *conditions) -> z3.CheckSatResult | None:
        """Return sat/unsat/unknown, or None once the query budget is used up."""
        if self.max_queries is not None and self.stats["discovery_queries"] >= self.max_queries:
            if "max_queries" not in self.stats["budget_exhausted"]:
                self.stats["budget_exhausted"].append("max_queries")
            return None
        self.stats["discovery_queries"] += 1
        status = self.solver.check(*conditions)
        if status == z3.unknown:
            self.stats["discovery_unknown"] += 1
            self.stats["reason"] = self.solver.reason_unknown()
        return status

    def stopped(self) -> bool:
        return bool(self.stats["discovery_unknown"]) or "max_queries" in self.stats["budget_exhausted"]

    def value(self, expr: z3.ExprRef) -> int:
        return _unsigned(self.solver.model().eval(expr, model_completion=True))


def _extremum(search: _Search, rank: z3.BitVecRef, seed_model: z3.ModelRef,
              minimum: bool) -> int | None:
    """Binary-search the unsigned minimum or maximum of rank under P (None if stopped)."""
    seed = _unsigned(seed_model.eval(rank, model_completion=True))
    low, high = (0, seed) if minimum else (seed, (1 << rank.size()) - 1)
    while low < high:
        middle = (low + high + (not minimum)) // 2
        if minimum:
            condition = z3.ULE(rank, _bv(middle, rank.sort()))
        else:
            condition = z3.UGE(rank, _bv(middle, rank.sort()))
        status = search.check(condition)
        if status == z3.sat:
            # Jump straight to the witness value, which is at least as good.
            if minimum:
                high = search.value(rank)
            else:
                low = search.value(rank)
        elif status == z3.unsat:
            if minimum:
                low = middle + 1
            else:
                high = middle - 1
        else:
            return None
    return low


def _semantic_facts(search: _Search, vocabulary: Vocabulary) -> list[Candidate]:
    """Known bits and exact signed/unsigned bounds of every word under P.

    Stops at the first solver UNKNOWN or when the query budget runs out.
    """
    seed_model = search.solver.model()  # Any model of P; queries refine it.
    facts: list[Candidate] = []

    def fact(expression, family):
        facts.append(Candidate(expression, family, "implied:semantic", variable_ids(expression)))

    for word in vocabulary.words:
        sort, width = word.sort(), word.size()
        full, sign = (1 << width) - 1, 1 << (width - 1)
        seed = _unsigned(seed_model.eval(word, model_completion=True))

        # Known bits: start from "all bits fixed" and clear every bit on which a
        # counterexample differs from the seed. No per-bit queries are needed.
        mask = full
        while mask:
            expression = (word & _bv(mask, sort)) == _bv(seed & mask, sort)
            status = search.check(z3.Not(expression))
            if status != z3.sat and status != z3.unsat:
                break  # Unknown or out of budget.
            if status == z3.unsat:
                if mask == full:
                    family = "array" if _contains(word, {z3.Z3_OP_SELECT}) else "equality"
                    fact(word == _bv(seed, sort), family)
                else:
                    fact(expression, "masked_bits")
                break
            mask &= ~(seed ^ search.value(word))
        if search.stopped():
            break
        if mask == full:
            continue  # A constant word needs no bounds.

        # Signed order is unsigned order after flipping the sign bit.
        for signed in (False, True):
            rank = word ^ _bv(sign, sort) if signed else word
            for minimum in (True, False):
                value = _extremum(search, rank, seed_model, minimum)
                if value is None:
                    break
                if value == (0 if minimum else full):
                    continue  # Trivial bound.
                literal = _bv(value ^ sign if signed else value, sort)
                if signed:
                    expression = word >= literal if minimum else word <= literal
                else:
                    expression = z3.UGE(word, literal) if minimum else z3.ULE(word, literal)
                fact(expression, "signed_bound" if signed else "unsigned_bound")
            if search.stopped():
                break
        if search.stopped():
            break
    # Prefer an exact bound over a mask that simplifies to the same formula.
    facts.sort(key=lambda candidate: candidate.family == "masked_bits")
    return facts


def discover_implied_candidates(
    hypothesis: z3.BoolRef, options: GenerationOptions | None = None,
) -> ImpliedDiscovery:
    """Propose semantic facts and templates for the property ``hypothesis``.

    A budget limit is an ordinary cutoff, never an UNSAT answer. Solver
    UNKNOWN stops the semantic search and leaves it incomplete.
    """
    options = options or GenerationOptions()
    check_options(options)
    vocabulary = _vocabulary(hypothesis, options)
    stats = dict(kind="property-word-level", term_count=len(vocabulary.terms),
                 predicate_count=len(vocabulary.predicates), total_candidates=0,
                 discovery_queries=0, discovery_unknown=0, hypothesis_result=None,
                 complete=False, reason=None,
                 coverage="budgeted" if options.matched_budgets else "finite-cone",
                 budget_exhausted=[], selected_terms=len(vocabulary.subterms))
    discovery = ImpliedDiscovery([], stats)
    search = _Search(hypothesis, options, stats)

    initial = search.check()
    stats["hypothesis_result"] = str(initial)
    if initial == z3.unknown:
        return discovery
    if initial == z3.unsat:
        stats.update(complete=True, reason="property is unsatisfiable; no nonvacuous proposals")
        return discovery
    if z3.is_true(z3.simplify(hypothesis)):
        stats.update(complete=True, reason="tautological property; no property-derived constraints")
        return discovery

    candidates = _unique(chain(_semantic_facts(search, vocabulary), _templates(vocabulary)))
    if options.matched_budgets:
        discovery.candidates = list(islice(candidates, options.max_candidates))
        if len(discovery.candidates) == options.max_candidates:
            stats["budget_exhausted"].append("max_candidates")
    else:
        discovery.candidates = list(candidates)
    stats["total_candidates"] = len(discovery.candidates)
    stats["complete"] = stats["discovery_unknown"] == 0
    return discovery
