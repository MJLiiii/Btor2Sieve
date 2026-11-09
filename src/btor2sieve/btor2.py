"""Parse and sort-check BTOR2 models, including their safety directives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


class Btor2Error(ValueError):
    """An invalid BTOR2 line or expression reference."""


@dataclass(frozen=True)
class Sort:
    id: int
    kind: str
    width: int | None = None
    index: int | None = None
    element: int | None = None


@dataclass(frozen=True)
class Node:
    id: int
    op: str
    sort_id: int | None = None
    args: tuple[int, ...] = ()
    params: tuple[int, ...] = ()
    symbol: str | None = None
    line: int = 0


@dataclass
class Model:
    sorts: dict[int, Sort]
    nodes: dict[int, Node]
    source: str = "<string>"

    def _select(self, op: str) -> list[Node]:
        return [node for node in self.nodes.values() if node.op == op]

    @property
    def states(self) -> list[Node]:
        return self._select("state")

    @property
    def inputs(self) -> list[Node]:
        return self._select("input")

    @property
    def bads(self) -> list[Node]:
        return self._select("bad")

    @property
    def constraints(self) -> list[Node]:
        return self._select("constraint")

    @property
    def inits(self) -> list[Node]:
        return self._select("init")

    @property
    def nexts(self) -> list[Node]:
        return self._select("next")


_DECLARATIONS = {"input", "state"}
_DIGITS = {"const": (r"[01]+", 2), "constd": (r"-?[0-9]+", 10), "consth": (r"[0-9a-fA-F]+", 16)}
_LITERALS = set(_DIGITS) | {"zero", "one", "ones"}
_PREDICATES = {"bad", "constraint", "fair", "justice"}
_UNSORTED = _PREDICATES | {"output"}
DIRECTIVES = _UNSORTED | {"init", "next"}

_UNARY = {"not", "neg", "inc", "dec"}
_REDUCTIONS = {"redand", "redor", "redxor"}
_INDEXED = {"uext": 1, "sext": 1, "slice": 2}
_BINARY = set("and nand or nor xor xnor add sub mul sdiv udiv smod srem urem sll sra srl rol ror".split())
_COMPARISONS = set("sgt sgte slt slte ugt ugte ult ulte".split())
OVERFLOW_OPS = set("saddo ssubo smulo sdivo uaddo usubo umulo".split())
_ARITY = {
    **dict.fromkeys(_DECLARATIONS | _LITERALS, 0),
    **dict.fromkeys(_UNARY | _REDUCTIONS | _INDEXED.keys() | _UNSORTED, 1),
    **dict.fromkeys(_BINARY | _COMPARISONS | OVERFLOW_OPS, 2),
    **dict.fromkeys({"init", "next", "read", "concat", "eq", "neq", "iff", "implies"}, 2),
    "ite": 3,
    "write": 3,
}


def _number(token: str, label: str, *, signed: bool = False, maximum: int = (1 << 40) - 1) -> int:
    pattern = r"-?(?:0|[1-9][0-9]*)" if signed else r"0|[1-9][0-9]*"
    if re.fullmatch(pattern, token) is None or len(token.lstrip("-")) > len(str(maximum)):
        raise Btor2Error(f"invalid {label}: {token}")
    value = int(token)
    if abs(value) > maximum:
        raise Btor2Error(f"{label} exceeds maximum of {maximum}: {token}")
    return value


def _parameter(token: str, label: str) -> int:
    return _number(token, label, maximum=(1 << 31) - 2)


def _check_arity(op: str, fields: list[str], required: int) -> None:
    if len(fields) not in (required, required + 1):
        raise Btor2Error(f"invalid arity for {op}, expected {required} fields and an optional symbol")


def _constant(op: str, token: str, width: int) -> int:
    pattern, base = _DIGITS[op]
    if re.fullmatch(pattern, token) is None or (op == "const" and len(token) != width):
        raise Btor2Error(f"invalid {op} constant {token} for bitvec {width}")
    # Decimal handles valid constants wider than Python's int-string digit limit.
    value = int(Decimal(token)) if base == 10 else int(token, base)
    fits = (~value).bit_length() < width if value < 0 else value.bit_length() <= width
    if not fits:
        raise Btor2Error(f"{op} constant {token} does not fit bitvec {width}")
    return value


class _Parser:
    def __init__(self, source: str):
        self.model = Model({}, {}, source)
        self._last_id = 0
        self._sort_shapes: dict[tuple[str, int, int], int] = {}
        self._canonical_sorts: dict[int, int] = {}
        self._input_dependent: set[int] = set()
        self._assigned: set[tuple[str, int]] = set()

    def _sort_ref(self, token: str) -> int:
        ref = _number(token, "sort reference")
        if ref not in self.model.sorts:
            raise Btor2Error(f"undefined sort reference {ref}")
        return ref

    def _term_ref(self, token: str) -> int:
        ref = _number(token, "expression reference", signed=True)
        target = self.model.nodes.get(abs(ref))
        if target is None or target.op in DIRECTIVES:
            raise Btor2Error(f"invalid expression reference {ref}, expected an earlier expression")
        if ref < 0 and self.model.sorts[target.sort_id].kind == "array":
            raise Btor2Error(f"negative array reference {ref}")
        return ref

    def _parse_sort(self, id_: int, fields: list[str]) -> None:
        if fields and fields[0] == "bitvec":
            _check_arity("sort bitvec", fields, 2)
            width = _parameter(fields[1], "bit-vector width")
            if width == 0:
                raise Btor2Error("bit-vector width must be positive")
            sort = Sort(id_, "bitvec", width=width)
            shape = ("bitvec", width, 0)
        elif fields and fields[0] == "array":
            _check_arity("sort array", fields, 3)
            index, element = map(self._sort_ref, fields[1:3])
            sort = Sort(id_, "array", index=index, element=element)
            shape = ("array", self._canonical_sorts[index], self._canonical_sorts[element])
        else:
            raise Btor2Error("expected bitvec or array sort")
        self.model.sorts[id_] = sort
        self._canonical_sorts[id_] = self._sort_shapes.setdefault(shape, id_)

    def parse_line(self, fields: list[str], line: int) -> None:
        if len(fields) < 2:
            raise Btor2Error("expected a line id and an operation")
        id_ = _number(fields[0], "line id")
        if id_ <= self._last_id:
            raise Btor2Error("line ids must be positive and strictly increasing")
        self._last_id = id_
        op, operands = fields[1], fields[2:]
        if op == "sort":
            self._parse_sort(id_, operands)
            return
        if op not in _ARITY:
            raise Btor2Error(f"unsupported operation {op!r}")

        sort_id, params = None, ()
        arity = _ARITY[op]
        if op == "justice":
            if not operands:
                raise Btor2Error("invalid arity for justice, expected a condition count")
            arity = _parameter(operands[0], "justice condition count")
            if arity == 0:
                raise Btor2Error("invalid arity for justice, expected at least one condition")
            params, operands = (arity,), operands[1:]
        elif op not in _UNSORTED:
            if not operands:
                raise Btor2Error(f"invalid arity for {op}, expected a sort reference")
            sort_id, operands = self._sort_ref(operands[0]), operands[1:]

        if op in _INDEXED:
            param_count = _INDEXED[op]
        elif op in _DIGITS:
            param_count = 1
        else:
            param_count = 0
        required = arity + param_count
        _check_arity(op, operands, required)
        args = tuple(map(self._term_ref, operands[:arity]))
        if op in _INDEXED:
            params = tuple(_parameter(token, op) for token in operands[arity:required])
        elif op in _DIGITS:
            width = self.model.sorts[sort_id].width
            if width is None:
                raise Btor2Error(f"expected bitvec sort for {op}")
            params = (_constant(op, operands[arity], width),)
        symbol = operands[required] if len(operands) > required else None
        node = Node(id_, op, sort_id, args, params, symbol, line)
        self._validate(node)
        self.model.nodes[id_] = node
        if op == "input" or any(abs(arg) in self._input_dependent for arg in args):
            self._input_dependent.add(id_)

    def _validate(self, node: Node) -> None:
        op = node.op
        sorts = self.model.sorts
        result = sorts.get(node.sort_id)
        terms = [self.model.nodes[abs(arg)] for arg in node.args]
        arguments = [sorts[term.sort_id] for term in terms]

        def same_sort(first: Sort, second: Sort) -> bool:
            return self._canonical_sorts[first.id] == self._canonical_sorts[second.id]

        def require(condition: bool, message: str = "incompatible sorts") -> None:
            if not condition:
                raise Btor2Error(f"{op}: {message}")

        if op in _PREDICATES:
            require(all(arg.width == 1 for arg in arguments), "expected bitvec 1 condition")
        elif op == "output":
            require(arguments[0].width is not None, "expected bitvec output")
        elif op in _DECLARATIONS:
            return
        elif op in _LITERALS:
            require(result.width is not None, "expected bitvec sort")
        elif op in {"init", "next"}:
            state, rhs = node.args
            require(state > 0 and terms[0].op == "state", "first operand must be a positive state reference")
            require(same_sort(result, arguments[0]))
            if op == "init" and result.kind == "array" and arguments[1].kind == "bitvec":
                require(terms[1].op in _LITERALS, "array init requires a bit-vector constant or array")
                require(same_sort(sorts[result.element], arguments[1]))
            else:
                require(same_sort(result, arguments[1]))
            if op == "init":
                require(abs(rhs) < state, "initial expression must precede the state")
                require(abs(rhs) not in self._input_dependent, "initial expression cannot depend on an input")
            require((op, state) not in self._assigned, f"duplicate assignment for state {state}")
            self._assigned.add((op, state))
        elif op in {"read", "write"}:
            array, index = arguments[:2]
            require(array.kind == "array", "first operand must be an array")
            require(same_sort(sorts[array.index], index))
            if op == "read":
                require(same_sort(result, sorts[array.element]))
            else:
                require(same_sort(result, array) and same_sort(sorts[array.element], arguments[2]))
        elif op == "ite":
            require(arguments[0].width == 1)
            require(all(same_sort(result, branch) for branch in arguments[1:]))
        elif op in {"eq", "neq"}:
            require(result.width == 1 and same_sort(*arguments))
        else:
            require(result.width is not None and all(arg.width is not None for arg in arguments),
                    "expected bitvec sorts")
            widths = [arg.width for arg in arguments]
            if op in _UNARY or op in _BINARY:
                require(all(width == result.width for width in widths))
            elif op in _REDUCTIONS:
                require(result.width == 1)
            elif op in _COMPARISONS or op in OVERFLOW_OPS:
                require(result.width == 1 and widths[0] == widths[1])
            elif op in {"iff", "implies"}:
                require(result.width == 1 and widths == [1, 1])
            elif op == "concat":
                require(result.width == sum(widths))
            elif op == "slice":
                high, low = node.params
                require(low <= high < widths[0] and result.width == high - low + 1, "invalid slice bounds or result width")
            elif op in {"uext", "sext"}:
                require(result.width == widths[0] + node.params[0])


def parse(text: str, source: str = "<string>") -> Model:
    """Parse BTOR2 with source and line information on syntax or sort errors.

    Token separators may be arbitrary whitespace and the final newline is optional.
    Fair and justice declarations are retained for inspection. Safety analysis
    uses only bad properties and constraint assumptions.
    """
    parser = _Parser(source)
    for line, raw in enumerate(text.splitlines(), start=1):
        fields = []
        for token in raw.split():
            if token.startswith(";"):
                break
            fields.append(token)
        if not fields:
            continue
        try:
            parser.parse_line(fields, line)
        except Btor2Error as exc:
            raise Btor2Error(f"{source}:{line}: {exc}") from None
    return parser.model


def parse_file(path: str | Path) -> Model:
    """Read and parse a UTF-8 BTOR2 file."""
    file = Path(path)
    try:
        text = file.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise Btor2Error(f"{file}: invalid UTF-8: {exc}") from exc
    return parse(text, str(file))
