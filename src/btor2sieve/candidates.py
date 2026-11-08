"""Bounded syntax and SMT-guided candidate generation."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import combinations, islice, zip_longest
from typing import TYPE_CHECKING

import z3

if TYPE_CHECKING:
    from .encoding import Encoder


@dataclass(frozen=True)
class Candidate:
    expr: z3.BoolRef
    family: str
    origin: str
    source_nodes: tuple[int, ...] = ()


@dataclass(frozen=True)
class GenerationOptions:
    max_candidates: int = 200
    max_terms: int = 16
    max_width: int = 64
    semantic: bool = True
    timeout_ms: int = 1000
    max_queries: int = 256


_ATOM_FAMILIES = {
    "eq": "equality", "neq": "disequality", "iff": "equality",
    "ult": "unsigned_bound", "ulte": "unsigned_bound",
    "ugt": "unsigned_bound", "ugte": "unsigned_bound",
    "slt": "signed_bound", "slte": "signed_bound",
    "sgt": "signed_bound", "sgte": "signed_bound",
    "implies": "implication",
}
_WORD_ANCHORS = {"state", "input", "read"}


def _width_allowed(sort: z3.SortRef, max_width: int) -> bool:
    pending = [sort]
    seen = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        if isinstance(current, z3.ArraySortRef):
            pending.extend((current.domain(), current.range()))
        elif current.size() > max_width:
            return False
    return True


def _cone_terms(encoder: Encoder, roots: tuple[int, ...], options: GenerationOptions) -> list[int]:
    # Inspect the cone once, even when a property has a deep one-bit skeleton.
    # Keep only a bounded BFS prefix per category. Round-robin selection reserves
    # room for words, local atoms/guards, and constants at small term budgets.
    if not roots:
        roots = tuple(sorted(encoder.states.keys() | encoder.inputs.keys()))
    pending = deque(dict.fromkeys(abs(root) for root in roots))
    seen = set(pending)
    anchors, atoms, words, literals, fallback = [], [], [], [], []
    allowed_sorts = {}
    while pending:
        node_id = pending.popleft()
        node = encoder.model.nodes[node_id]
        term = encoder.terms.get(node_id)
        if term is not None:
            if node.sort_id not in allowed_sorts:
                allowed_sorts[node.sort_id] = _width_allowed(term.sort(), options.max_width)
            if allowed_sorts[node.sort_id]:
                if z3.is_bv_value(term):
                    bucket = literals
                elif encoder.model.sorts[node.sort_id].width != 1:
                    bucket = anchors if node.op in _WORD_ANCHORS else words
                elif node.op in _ATOM_FAMILIES or node.op == "ite":
                    bucket = atoms
                else:
                    bucket = fallback
                if len(bucket) < options.max_terms:
                    bucket.append(node_id)
        for arg in node.args:
            child = abs(arg)
            if child not in seen:
                seen.add(child)
                pending.append(child)
    ranked = (node_id for group in zip_longest(anchors, atoms, words, literals)
              for node_id in group if node_id is not None)
    selected = list(islice(ranked, options.max_terms))
    return selected + fallback[:options.max_terms - len(selected)]


def _syntax_candidates(
    encoder: Encoder, terms: list[int], max_width: int,
) -> Iterator[Candidate]:
    atoms: dict[int, z3.BoolRef] = {}
    literals: dict[int, dict[int, int]] = defaultdict(dict)
    words = []
    for node_id in terms:
        term = encoder.terms[node_id]
        node = encoder.model.nodes[node_id]
        if z3.is_bv_value(term):
            literals[term.size()].setdefault(term.as_long(), node_id)
            continue

        for arg in node.args:
            base = encoder.terms[abs(arg)]
            if z3.is_bv_value(base) and base.size() <= max_width:
                value = z3.simplify(encoder.expr(arg)).as_long() if arg < 0 else base.as_long()
                literals[base.size()].setdefault(value, abs(arg))

        words.append((node_id, term))
        family = _ATOM_FAMILIES.get(node.op)
        if family and all(_width_allowed(encoder.terms[abs(arg)].sort(), max_width) for arg in node.args):
            atom = z3.simplify(encoder.bool_expr(node_id))
            atoms.setdefault(node_id, atom)
            opposite = {"equality": "disequality", "disequality": "equality"}.get(family, family)
            if family in {"equality", "disequality"} and any(
                _array_related(encoder, abs(arg)) for arg in node.args
            ):
                family = opposite = "array"
            yield Candidate(atom, family, "syntax:atom", (node_id,))
            yield Candidate(z3.Not(atom), opposite, "syntax:atom", (node_id,))
        elif node.op == "ite":
            guard = node.args[0]
            atoms.setdefault(abs(guard), encoder.bool_expr(guard))
        yield from _structural_candidates(encoder, node_id, max_width)

    implications = (
        Candidate(z3.Implies(left, right), "implication", "syntax:local", (left_id, right_id))
        for pair in combinations(atoms.items(), 2)
        for (left_id, left), (right_id, right) in (pair, pair[::-1])
    )
    # Keep quadratic pair templates from taking all slots before word bounds.
    for group in zip_longest(implications, _pair_candidates(encoder, words),
                             _constant_candidates(encoder, words, literals)):
        yield from (candidate for candidate in group if candidate is not None)


def _array_related(encoder: Encoder, node_id: int) -> bool:
    return z3.is_array(encoder.terms[node_id]) or encoder.model.nodes[node_id].op == "read"


def _pair_candidates(
    encoder: Encoder, words: list[tuple[int, z3.ExprRef]],
) -> Iterator[Candidate]:
    for (left_id, left), (right_id, right) in combinations(words, 2):
        if left.sort() != right.sort():
            continue
        sources = (left_id, right_id)
        equality, disequality = "equality", "disequality"
        if any(_array_related(encoder, node_id) for node_id in sources):
            equality = disequality = "array"
        yield Candidate(left == right, equality, "syntax:pair", sources)
        yield Candidate(left != right, disequality, "syntax:pair", sources)


def _constant_candidates(
    encoder: Encoder, words: list[tuple[int, z3.ExprRef]], literals: dict[int, dict[int, int]],
) -> Iterator[Candidate]:
    for node_id, term in words:
        if not z3.is_bv(term):
            continue
        width = term.size()
        top = (1 << width) - 1
        sign = 1 << (width - 1)
        constants = {}
        for value, source_id in literals[width].items():
            for neighbor in (value, value - 1, value + 1):
                if 0 <= neighbor <= top:
                    constants.setdefault(neighbor, source_id)
        for value in (0, 1, top, sign, sign - 1):
            constants.setdefault(value, None)
        equality, disequality = "equality", "disequality"
        if _array_related(encoder, node_id):
            equality = disequality = "array"
        for value, source_id in constants.items():
            sources = (node_id,) if source_id is None else (node_id, source_id)
            yield Candidate(term == value, equality, "syntax:constant", sources)
            yield Candidate(term != value, disequality, "syntax:constant", sources)
            if width > 1:
                yield Candidate(z3.ULE(term, value), "unsigned_bound", "syntax:constant", sources)
                yield Candidate(z3.UGE(term, value), "unsigned_bound", "syntax:constant", sources)
                yield Candidate(term <= value, "signed_bound", "syntax:constant", sources)
                yield Candidate(term >= value, "signed_bound", "syntax:constant", sources)


def _structural_candidates(encoder: Encoder, node_id: int, max_width: int) -> Iterator[Candidate]:
    node = encoder.model.nodes[node_id]
    term = encoder.terms[node_id]
    if node.op == "write":
        _, index, value = map(encoder.expr, node.args)
        yield Candidate(z3.Select(term, index) == value, "array", "syntax:array-identity", (node_id,))
    elif node.op == "read":
        write = encoder.model.nodes[abs(node.args[0])]
        if write.op != "write" or not _width_allowed(encoder.terms[write.id].sort(), max_width):
            return
        base, write_index, value = map(encoder.expr, write.args)
        read_index = encoder.expr(node.args[1])
        sources = (node_id, write.id)
        if read_index.eq(write_index):
            yield Candidate(term == value, "array", "syntax:array-identity", sources)
        else:
            yield Candidate(z3.Implies(read_index == write_index, term == value), "array",
                            "syntax:array-identity", sources)
            yield Candidate(z3.Implies(read_index != write_index, term == z3.Select(base, read_index)),
                            "array", "syntax:array-identity", sources)
    elif node.op == "and" and term.size() > 1:
        for word_ref, mask_ref in (node.args, node.args[::-1]):
            word = encoder.expr(word_ref)
            mask = z3.simplify(encoder.expr(mask_ref))
            if z3.is_bv_value(word) or not z3.is_bv_value(mask) or mask.as_long() == 0:
                continue
            bits = mask.as_long()
            # A full mask and its extreme set bits capture common alignment
            # patterns without enumerating subsets of the observed mask.
            masks = dict.fromkeys((bits, bits & -bits, 1 << (bits.bit_length() - 1)))
            for value in masks:
                for expected in (0, value):
                    yield Candidate((word & value) == expected, "masked_bits", "syntax:mask",
                                    (node_id, abs(word_ref), abs(mask_ref)))
    elif node.op == "slice":
        if encoder.expr(node.args[0]).size() <= max_width:
            for value in (0, (1 << term.size()) - 1):
                yield Candidate(term == value, "masked_bits", "syntax:slice", (node_id, abs(node.args[0])))


class _Discovery:
    def __init__(self, hypothesis: z3.BoolRef, options: GenerationOptions):
        self.solver = z3.Solver(ctx=hypothesis.ctx)
        self.solver.set(timeout=options.timeout_ms, random_seed=0)
        self.solver.add(hypothesis)
        self.remaining = options.max_queries

    def check(self, *assumptions: z3.BoolRef) -> z3.CheckSatResult | None:
        if not self.remaining:
            return None
        self.remaining -= 1
        result = self.solver.check(*assumptions)
        if result == z3.unknown:
            self.remaining = 0
        return result

    def bound(self, term: z3.BitVecRef, top: int, *, minimum: bool) -> tuple[int, bool]:
        low, high = 0, top
        while low < high:
            middle = (low + high) // 2
            query = z3.ULE(term, middle) if minimum else z3.UGT(term, middle)
            result = self.check(query)
            if result != z3.sat and result != z3.unsat:
                break
            if (result == z3.sat) == minimum:
                high = middle
            else:
                low = middle + 1
        # Only an UNSAT check moves the endpoint that represents the guarantee.
        return (low if minimum else high), low == high


def _semantic_candidates(
    encoder: Encoder, hypothesis: z3.BoolRef, terms: list[int], options: GenerationOptions,
) -> Iterator[Candidate]:
    if not options.semantic or not options.max_queries:
        return
    words = [node_id for node_id in terms if z3.is_bv(encoder.terms[node_id])
             and not z3.is_bv_value(encoder.terms[node_id])]
    if not words:
        return
    # Inspect word-level declarations and reads before intermediate words or
    # Boolean terms. A tight query budget should reach actual data.
    words.sort(key=lambda node_id: (
        encoder.terms[node_id].size() == 1, encoder.model.nodes[node_id].op not in _WORD_ANCHORS
    ))
    discovery = _Discovery(hypothesis, options)
    if discovery.check() != z3.sat:
        return
    witness = discovery.solver.model()

    for node_id in words:
        if not discovery.remaining:
            break
        term = encoder.terms[node_id]
        top = (1 << term.size()) - 1
        minimum, min_exact = discovery.bound(term, top, minimum=True)
        maximum, max_exact = discovery.bound(term, top, minimum=False)
        if minimum:
            origin = "semantic:interval" if min_exact else "semantic:interval-partial"
            yield Candidate(z3.UGE(term, minimum), "unsigned_bound", origin, (node_id,))
        if maximum != top:
            origin = "semantic:interval" if max_exact else "semantic:interval-partial"
            yield Candidate(z3.ULE(term, maximum), "unsigned_bound", origin, (node_id,))

        value = witness.eval(term, model_completion=True).as_long()
        mask = top if minimum == maximum else 0
        if not mask:
            for bit in range(term.size()):
                expected = (value >> bit) & 1
                result = discovery.check(z3.Extract(bit, bit, term) != expected)
                if result == z3.unsat:
                    mask |= 1 << bit
                elif result != z3.sat:
                    break
        if mask:
            yield Candidate((term & mask) == (value & mask), "masked_bits", "semantic:known-bits", (node_id,))


def _dedup_key(expr: z3.BoolRef) -> z3.BoolRef | tuple[bool, frozenset[z3.ExprRef]]:
    negated = z3.is_not(expr)
    atom = expr.arg(0) if negated else expr
    if z3.is_eq(atom):
        return negated, frozenset(atom.children())
    return expr


def generate_candidates(
    encoder: Encoder, hypothesis: z3.BoolRef, roots: Iterable[int], options: GenerationOptions | None = None,
) -> list[Candidate]:
    """Enumerate untrusted candidates in stable order with independent budgets."""
    options = options or GenerationOptions()
    if min(options.max_candidates, options.max_terms, options.max_width, options.max_queries) < 0:
        raise ValueError("generation budgets must be nonnegative")
    if options.timeout_ms <= 0:
        raise ValueError("timeout_ms must be positive")
    if not options.max_candidates or not options.max_terms or not options.max_width:
        return []
    terms = _cone_terms(encoder, tuple(roots), options)
    if not terms:
        return []

    found = []
    seen = {_dedup_key(z3.simplify(hypothesis))}
    semantic = _semantic_candidates(encoder, hypothesis, terms, options)
    syntax = _syntax_candidates(encoder, terms, options.max_width)
    for proposals in zip_longest(semantic, syntax):
        for candidate in proposals:
            if candidate is None:
                continue
            key = z3.simplify(candidate.expr)
            if z3.is_true(key) and candidate.origin == "syntax:array-identity":
                # Retain useful rewrite forms without merging different identities.
                key = candidate.expr
            elif z3.is_true(key) or z3.is_false(key):
                continue
            signature = _dedup_key(key)
            if signature in seen:
                continue
            seen.add(signature)
            found.append(candidate)
            if len(found) == options.max_candidates:
                return found
    return found
