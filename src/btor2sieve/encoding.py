"""Encode BTOR2 expressions and safety scopes as quantifier-free Z3 terms."""

from __future__ import annotations

import operator
from decimal import Decimal

import z3

from .btor2 import DIRECTIVES, Btor2Error, Model, Node, _OVERFLOWS


_WORD_OPS = {
    "not": operator.invert,
    "neg": operator.neg,
    "inc": lambda a: a + 1,
    "dec": lambda a: a - 1,
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "and": operator.and_,
    "or": operator.or_,
    "xor": operator.xor,
    "nand": lambda a, b: ~(a & b),
    "nor": lambda a, b: ~(a | b),
    "xnor": lambda a, b: ~(a ^ b),
    "implies": lambda a, b: ~a | b,
    "sdiv": operator.truediv,
    "smod": operator.mod,
    "srem": z3.SRem,
    "udiv": z3.UDiv,
    "urem": z3.URem,
    "sll": operator.lshift,
    "sra": operator.rshift,
    "srl": z3.LShR,
    "concat": z3.Concat,
    "read": z3.Select,
    "write": z3.Store,
}
_BOOL_OPS = {
    "eq": operator.eq,
    "iff": operator.eq,
    "neq": operator.ne,
    "sgt": operator.gt,
    "sgte": operator.ge,
    "slt": operator.lt,
    "slte": operator.le,
    "ugt": z3.UGT,
    "ugte": z3.UGE,
    "ult": z3.ULT,
    "ulte": z3.ULE,
    "redand": lambda a: a == -1,
    "redor": lambda a: a != 0,
}


def _bit(predicate: z3.BoolRef) -> z3.BitVecRef:
    return z3.If(predicate, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))


def _xor_reduce(value: z3.BitVecRef) -> z3.BitVecRef:
    # Fold disjoint groups by doubling the shift until the low bit is parity.
    shift = 1
    while shift < value.size():
        value = value ^ z3.LShR(value, shift)
        shift *= 2
    return z3.Extract(0, 0, value)


def _rotate(op: str, word: z3.BitVecRef, amount: z3.BitVecRef) -> z3.BitVecRef:
    # Lower variable rotates to standard SMT-LIB shifts for external replay.
    width = word.size()
    shift = z3.URem(amount, width)
    if op == "rol":
        return (word << shift) | z3.LShR(word, width - shift)
    return z3.LShR(word, shift) | (word << (width - shift))


def _overflow(op: str, a: z3.BitVecRef, b: z3.BitVecRef) -> z3.BitVecRef:
    width = a.size()
    if op == "usubo":
        return _bit(z3.ULT(a, b))
    if op == "sdivo":
        minimum = z3.BitVecVal(1, width) << (width - 1)
        return _bit(z3.And(a == minimum, b == -1))

    extend = z3.SignExt if op.startswith("s") else z3.ZeroExt
    # Exact products require twice the input width. Sums and differences
    # need one extra bit. A result fits iff truncating preserves its value.
    extra = width if op in {"smulo", "umulo"} else 1
    wide_a, wide_b = extend(extra, a), extend(extra, b)
    wide = _WORD_OPS[op[1:-1]](wide_a, wide_b)
    return _bit(wide != extend(extra, z3.Extract(width - 1, 0, wide)))


class Encoder:
    """Translate a parsed model in line order and expose its safety scopes."""

    def __init__(self, model: Model):
        self.model = model
        self.terms: dict[int, z3.ExprRef] = {}
        self.states: dict[int, z3.ExprRef] = {}
        self.inputs: dict[int, z3.ExprRef] = {}
        self.next_states: dict[int, z3.ExprRef] = {}
        self._prime_pairs: list[tuple[z3.ExprRef, z3.ExprRef]] = []
        self._sorts: dict[int, z3.SortRef] = {}
        for id_, sort in model.sorts.items():
            if sort.kind == "bitvec":
                self._sorts[id_] = z3.BitVecSort(sort.width)
            else:
                self._sorts[id_] = z3.ArraySort(self._sorts[sort.index], self._sorts[sort.element])

        for id_, node in model.nodes.items():
            if node.op in {"state", "input"}:
                prefix = "s" if node.op == "state" else "i"
                symbol = z3.Const(f"{prefix}_{id_}", self._sorts[node.sort_id])
                primed = z3.Const(f"{prefix}_{id_}_next", symbol.sort())
                self._prime_pairs.append((symbol, primed))
                self.terms[id_] = symbol
                if node.op == "state":
                    self.states[id_] = symbol
                    self.next_states[id_] = primed
                else:
                    self.inputs[id_] = symbol
            elif node.op not in DIRECTIVES:
                self.terms[id_] = self._encode(node)

        assumptions = [self.bool_expr(node.args[0]) for node in model.constraints]
        inits = [self._init_equation(node) for node in model.inits]
        nexts = [self.next_states[state] == self.expr(rhs) for state, rhs in (n.args for n in model.nexts)]
        self.assumptions: z3.BoolRef = z3.And(assumptions) if assumptions else z3.BoolVal(True)
        self.initial: z3.BoolRef = z3.And(inits) if inits else z3.BoolVal(True)
        self.transition: z3.BoolRef = z3.And(nexts) if nexts else z3.BoolVal(True)

    def expr(self, ref: int) -> z3.ExprRef:
        """Resolve a signed term ID. Negative BV IDs denote bitwise complement."""
        term = self.terms.get(abs(ref))
        if term is None:
            raise Btor2Error(f"invalid expression reference {ref}")
        if ref < 0:
            if not z3.is_bv(term):
                raise Btor2Error(f"negative array reference {ref}")
            return ~term
        return term

    def bool_expr(self, ref: int) -> z3.BoolRef:
        """Convert a one-bit BTOR2 term to a Z3 Boolean."""
        term = self.expr(ref)
        if not z3.is_bv(term) or term.size() != 1:
            raise Btor2Error(f"expected bitvec 1 for condition {ref}")
        return term == 1

    def property(self, bad_id: int) -> z3.BoolRef:
        """Return the safety condition corresponding to a bad directive ID."""
        node = self.model.nodes.get(bad_id)
        if node is None or node.op != "bad":
            raise Btor2Error(f"expected a bad directive ID, got {bad_id}")
        return z3.Not(self.bool_expr(node.args[0]))

    def prime(self, expr: z3.ExprRef) -> z3.ExprRef:
        """Replace current state and input symbols with their primed symbols."""
        return z3.substitute(expr, *self._prime_pairs)

    def _init_equation(self, node: Node) -> z3.BoolRef:
        state_ref, rhs_ref = node.args
        state, rhs = self.states[state_ref], self.expr(rhs_ref)
        if z3.is_array(state) and z3.is_bv(rhs):
            rhs = z3.K(state.domain(), rhs)
        return state == rhs

    def _encode(self, node: Node) -> z3.ExprRef:
        op = node.op
        args = tuple(map(self.expr, node.args))
        if op in _WORD_OPS:
            return _WORD_OPS[op](*args)
        if op in _BOOL_OPS:
            return _bit(_BOOL_OPS[op](*args))
        if op in {"rol", "ror"}:
            return _rotate(op, *args)
        if op in _OVERFLOWS:
            return _overflow(op, *args)
        if op == "redxor":
            return _xor_reduce(args[0])
        if op == "ite":
            return z3.If(args[0] == 1, args[1], args[2])
        if op == "slice":
            return z3.Extract(*node.params, args[0])
        if op in {"uext", "sext"}:
            extend = z3.ZeroExt if op == "uext" else z3.SignExt
            return extend(node.params[0], args[0])
        if op in {"zero", "one", "ones"}:
            value = {"zero": 0, "one": 1, "ones": -1}[op]
            return z3.BitVecVal(value, self._sorts[node.sort_id])
        if op in {"const", "constd", "consth"}:
            # Z3 takes decimal numeral strings, including beyond Python's
            # configurable integer-to-string digit limit.
            return z3.BitVecVal(str(Decimal(node.params[0])), self._sorts[node.sort_id])
        raise Btor2Error(f"{self.model.source}:{node.line}: unsupported operation {op!r}")
