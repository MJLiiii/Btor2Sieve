"""Choose the terms and predicates that implied extraction talks about.

The vocabulary of a property comes from P itself, the formula Pono printed
for it (see `pono.py`): its subterms are the words, arrays, constants and
comparisons the property is built from, down to the states and inputs it
reads. A tautological or variable-free P gives an empty vocabulary.

* Uncapped (default): every subterm of P is used.
* Budgeted (``max_terms`` given): a deterministic breadth-first walk from P's
  root keeps at most ``max_terms`` subterms per category, and drops any
  subterm whose bit-vector widths (including array index/element widths)
  exceed ``max_width``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import islice, zip_longest

import z3

from .pono import VARIABLE


@dataclass
class Vocabulary:
    subterms: tuple[z3.ExprRef, ...]   # selected subterms of P
    terms: list[z3.ExprRef]            # words, constants and arrays
    words: list[z3.ExprRef]            # non-constant bit-vector terms
    predicates: list[z3.BoolRef]       # comparisons and one-bit values


# Boolean subterms that are comparisons, not connectives.
_ATOMS = {z3.Z3_OP_EQ, z3.Z3_OP_DISTINCT, z3.Z3_OP_ULEQ, z3.Z3_OP_ULT, z3.Z3_OP_UGEQ,
          z3.Z3_OP_UGT, z3.Z3_OP_SLEQ, z3.Z3_OP_SLT, z3.Z3_OP_SGEQ, z3.Z3_OP_SGT}


def variable_ids(expr: z3.ExprRef) -> tuple[int, ...]:
    """BTOR2 line IDs of the states and inputs an expression reads."""
    found, seen, pending = set(), set(), [expr]
    while pending:
        term = pending.pop()
        if term.get_id() in seen:
            continue
        seen.add(term.get_id())
        if z3.is_const(term) and term.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            match = VARIABLE.fullmatch(str(term))
            if match:
                found.add(int(match[2]))
        pending.extend(term.children())
    return tuple(sorted(found))


def _is_variable(term: z3.ExprRef) -> bool:
    return z3.is_const(term) and term.decl().kind() == z3.Z3_OP_UNINTERPRETED


def _one_bit_value(term: z3.ExprRef) -> bool:
    """A one-bit state, input, array read, or bit slice: a value, not circuit glue."""
    return (z3.is_bv(term) and term.size() == 1 and
            (_is_variable(term) or z3.is_select(term) or z3.is_app_of(term, z3.Z3_OP_EXTRACT)))


def _as_bool(term: z3.ExprRef) -> z3.BoolRef | None:
    """Read a one-bit circuit as a Boolean formula, or None if it is something else.

    Pono encodes BTOR2 comparisons and gates on one-bit words, for example
    `eq` as `bvcomp`, and `-x` as `bvnot`. Reading them back as Booleans gives
    plain predicates such as `x == y` instead of `(bvnot (bvcomp x y)) == #b1`.
    """
    if z3.is_bv_value(term):
        return z3.BoolVal(term.as_long() == 1)
    if _one_bit_value(term):
        return term == 1
    kind, args = term.decl().kind(), term.children()
    if kind == z3.Z3_OP_BCOMP:
        return args[0] == args[1]
    if kind == z3.Z3_OP_ITE and all(z3.is_bv_value(a) for a in args[1:]):
        then, otherwise = args[1].as_long(), args[2].as_long()
        if (then, otherwise) == (1, 0):
            return args[0]
        if (then, otherwise) == (0, 1):
            return z3.Not(args[0])
        return None
    parts = [_as_bool(arg) for arg in args] if kind in _GATES else []
    if not parts or any(part is None for part in parts):
        return None
    if kind == z3.Z3_OP_BNOT:
        return z3.Not(parts[0])
    if kind == z3.Z3_OP_BAND:
        return z3.And(parts)
    if kind == z3.Z3_OP_BOR:
        return z3.Or(parts)
    result = parts[0]
    for part in parts[1:]:
        result = z3.Xor(result, part)
    return result


_GATES = {z3.Z3_OP_BNOT, z3.Z3_OP_BAND, z3.Z3_OP_BOR, z3.Z3_OP_BXOR}


def _predicate(term: z3.ExprRef) -> z3.BoolRef | None:
    """The comparison a subterm states, with negations removed, or None."""
    if z3.is_bool(term):
        if term.decl().kind() not in _ATOMS:
            return None
        # `circuit == #b1` (or #b0) is the circuit read as a Boolean.
        if z3.is_eq(term) and z3.is_bv(term.arg(0)) and term.arg(0).size() == 1:
            for circuit, value in ((term.arg(0), term.arg(1)), (term.arg(1), term.arg(0))):
                if z3.is_bv_value(value):
                    read = _as_bool(circuit)
                    if read is not None:
                        term = read if value.as_long() == 1 else z3.Not(read)
                    break
        candidate = term
    elif z3.is_bv(term) and term.size() == 1:
        candidate = _as_bool(term)
        if candidate is None:
            return None
    else:
        return None
    while z3.is_not(candidate):  # Both polarities are proposed later.
        candidate = candidate.arg(0)
    # Keep comparisons and one-bit values; connectives are split into their parts elsewhere.
    if candidate.decl().kind() in _ATOMS:
        return candidate
    return None


def sort_width_allowed(sort: z3.SortRef, max_width: int | None) -> bool:
    """True if no bit-vector inside ``sort`` (including array sorts) is wider than max_width."""
    if max_width is None:
        return True
    pending, seen = [sort], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        if isinstance(current, z3.ArraySortRef):
            pending.extend((current.domain(), current.range()))
        elif isinstance(current, z3.BitVecSortRef) and current.size() > max_width:
            return False
    return True


def expression_width_allowed(expression: z3.ExprRef, max_width: int) -> bool:
    """Check every subterm, so a narrow result cannot hide wide operands."""
    pending, seen = [expression], set()
    while pending:
        current = pending.pop()
        if current.get_id() in seen:
            continue
        seen.add(current.get_id())
        if not z3.is_bool(current) and not sort_width_allowed(current.sort(), max_width):
            return False
        pending.extend(current.children())
    return True


def subterms(root: z3.ExprRef) -> list[z3.ExprRef]:
    """Every distinct subterm of root, breadth-first from the root."""
    order, seen, pending = [], {root.get_id()}, deque([root])
    while pending:
        term = pending.popleft()
        order.append(term)
        for child in term.children():
            if child.get_id() not in seen:
                seen.add(child.get_id())
                pending.append(child)
    return order


def select_subterms(root: z3.ExprRef, max_terms: int, max_width: int) -> list[z3.ExprRef]:
    """Pick a bounded, deterministic set of P's subterms for budgeted extraction.

    Each category (states/inputs/reads, comparisons, other words, constants)
    keeps its first max_terms subterms in breadth-first order, and the result
    takes them round-robin so that small budgets still see every category.
    Remaining slots go to one-bit values and arrays.
    """
    anchors, atoms, words, literals, fallback = [], [], [], [], []
    for term in subterms(root):
        if z3.is_bool(term):
            bucket = atoms if _predicate(term) is not None else None
        elif not sort_width_allowed(term.sort(), max_width):
            bucket = None
        elif z3.is_bv_value(term):
            bucket = literals
        elif _is_variable(term) or z3.is_select(term):
            bucket = anchors  # States, inputs and array reads of any width.
        elif z3.is_bv(term) and term.size() > 1:
            bucket = words
        elif z3.is_bv(term) and _predicate(term) is not None:
            bucket = atoms  # A one-bit comparison circuit, as Pono writes BTOR2 `eq` and friends.
        else:
            bucket = fallback
        if bucket is not None and len(bucket) < max_terms:
            bucket.append(term)
    ranked = (term for group in zip_longest(anchors, atoms, words, literals)
              for term in group if term is not None)
    selected = list(islice(ranked, max_terms))
    return selected + fallback[:max_terms - len(selected)]


def build_vocabulary(hypothesis: z3.BoolRef, max_terms: int | None = None,
                     max_width: int | None = None) -> Vocabulary:
    """Collect P's terms; pass max_terms and max_width to bound the selection."""
    root = hypothesis.arg(0) if z3.is_not(hypothesis) else hypothesis  # P = not bad.
    if max_terms is None:
        chosen = tuple(subterms(root))
    else:
        chosen = tuple(term for term in select_subterms(root, max_terms, max_width)
                       if expression_width_allowed(term, max_width))

    terms, words, predicates = [], [], []
    seen_terms, seen_predicates = set(), set()
    for term in chosen:
        predicate = _predicate(term)
        if predicate is not None:
            key = z3.simplify(predicate).sexpr()
            if not (z3.is_true(predicate) or z3.is_false(predicate)) and key not in seen_predicates:
                seen_predicates.add(key)
                predicates.append(predicate)

        # Booleans and one-bit circuit glue are not numeric words.
        if z3.is_bool(term) or (z3.is_bv(term) and term.size() == 1
                                and not (_one_bit_value(term) or z3.is_bv_value(term))):
            continue
        simplified = z3.simplify(term)
        key = simplified.sexpr()
        if key not in seen_terms:
            seen_terms.add(key)
            terms.append(term)
            if z3.is_bv(term) and not z3.is_bv_value(simplified):
                words.append(term)
    return Vocabulary(chosen, terms, words, predicates)
