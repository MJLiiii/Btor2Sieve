"""The paper's Boolean state-literal implication candidate family.

Cabodi et al., DATE 2009, section V-C, propose SAT checks of literal
implications under the property. Here generation stays untrusted: the existing
Validator performs those checks independently. State-bit selection and budgets
are BTOR2 implementation choices, not algorithms specified by the paper.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from itertools import combinations
from typing import TYPE_CHECKING

import z3

from .common import Candidate, GenerationOptions

if TYPE_CHECKING:
    from ..encoding import Encoder


def _state_bits(
    encoder: Encoder, roots: Iterable[int], options: GenerationOptions,
) -> list[tuple[int, z3.BoolRef]]:
    eligible = [node_id for node_id, word in sorted(encoder.states.items())
                if z3.is_bv(word) and word.size() <= options.max_width]
    if not eligible:
        return []

    cone = set()
    pending = list(roots)
    while pending:
        node_id = abs(pending.pop())
        if node_id in cone:
            continue
        cone.add(node_id)
        pending.extend(encoder.model.nodes[node_id].args)

    selected = []
    # Exhaust cone bits before considering other states, but share each tier's
    # bit budget round-robin among words instead of consuming one wide word.
    for in_cone in (True, False):
        words = deque((node_id, 0) for node_id in eligible if (node_id in cone) == in_cone)
        while words and len(selected) < options.max_terms:
            node_id, index = words.popleft()
            word = encoder.states[node_id]
            bit = word if word.size() == 1 else z3.Extract(index, index, word)
            selected.append((node_id, bit == 1))
            if index + 1 < word.size():
                words.append((node_id, index + 1))
    return selected


def generate_implied_candidates(
    encoder: Encoder, roots: Iterable[int], options: GenerationOptions | None = None,
) -> list[Candidate]:
    """Enumerate bounded, non-tautological clauses without a discovery solver.

    For n selected bits the complete pool has 2*n*n clauses: two unit clauses
    per bit and four binary clauses per distinct bit pair. Contrapositive
    duplicates are omitted by construction. Implies ASTs are retained for
    identifying reciprocal clauses after independent validation. max_queries
    and semantic control word-level discovery only and are unused here.
    """
    options = options or GenerationOptions()
    if min(options.max_candidates, options.max_terms, options.max_width) < 0:
        raise ValueError("generation budgets must be nonnegative")
    if not options.max_candidates or not options.max_terms or not options.max_width:
        return []

    bits = _state_bits(encoder, roots, options)
    candidates = []

    def add(left: z3.BoolRef, right: z3.BoolRef, sources: tuple[int, ...]) -> bool:
        candidates.append(Candidate(z3.Implies(left, right), "implication",
                                    "implied:literal", sources))
        return len(candidates) == options.max_candidates

    for node_id, bit in bits:
        if add(bit, z3.Not(bit), (node_id,)) or add(z3.Not(bit), bit, (node_id,)):
            return candidates
    for (left_id, left), (right_id, right) in combinations(bits, 2):
        sources = tuple(dict.fromkeys((left_id, right_id)))
        # Each adjacent pair proves ordinary or complemented equivalence if
        # both clauses are accepted. The last clause is a contrapositive form.
        for antecedent, consequent in (
            (left, right), (right, left),
            (left, z3.Not(right)), (z3.Not(left), right),
        ):
            if add(antecedent, consequent, sources):
                return candidates
    return candidates


def _literal(expr: z3.BoolRef) -> tuple[z3.BoolRef, bool]:
    positive = True
    while z3.is_not(expr):
        positive = not positive
        expr = expr.arg(0)
    return expr, positive


def find_equivalences(accepted: list[tuple[Candidate, str]]) -> list[dict]:
    """Pair accepted complementary binary clauses and retain both proof IDs.

    The caller supplies only independently accepted, non-vacuous implications.
    These equivalences hold under that same hypothesis; they are not permission
    to merge state variables globally or rewrite the original safety property.
    """
    clauses = {}
    emitted = set()
    equivalences = []
    for candidate, proof_id in accepted:
        if not z3.is_implies(candidate.expr):
            continue
        left, left_positive = _literal(candidate.expr.arg(0))
        right, right_positive = _literal(candidate.expr.arg(1))
        if left.eq(right):
            continue
        literals = sorted(((left, not left_positive), (right, right_positive)),
                          key=lambda literal: literal[0].sexpr())
        key = tuple((atom.sexpr(), positive) for atom, positive in literals)
        opposite = tuple((atom, not positive) for atom, positive in key)
        partner = clauses.get(opposite)
        clauses.setdefault(key, (candidate, proof_id))
        if partner is None:
            continue
        other, other_id = partner
        if proof_id == other_id:
            continue
        (first, first_positive), (second, second_positive) = literals
        complemented = first_positive == second_positive
        signature = (key[0][0], key[1][0], complemented)
        if signature in emitted:
            continue
        emitted.add(signature)
        equality = first == (z3.Not(second) if complemented else second)
        equivalences.append({
            "expression": equality.sexpr(),
            "source_nodes": sorted(set(candidate.source_nodes + other.source_nodes)),
            "implication_ids": [other_id, proof_id],
        })
    return equivalences
