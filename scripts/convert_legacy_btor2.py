#!/usr/bin/env python3
"""Convert early Yosys BTOR2 output (for example the CAV'18 Btor2 artifact) to current BTOR2.

Yosys 0.7 wrote a pre-release BTOR2 dialect that differs from the format in three ways:

* ``output`` lines carry a sort: ``<id> output <sort> <node> [symbol]``;
* disequality is spelled ``ne`` instead of ``neq``;
* an ``init`` value may be defined after the state it initialises.

The converter rewrites outputs to ``<id> output <node> [symbol]``, renames
legacy operators, and renumbers every line in dependency order so that each
state follows its initial value. Nothing else changes: the same nodes, sorts,
operands, constants and symbols remain, and inputs, states, outputs and
properties keep their relative order, so property indices in witnesses
(``b0``, ``b1``, ...) still refer to the same properties.

Every conversion is checked before it is written: Pono must read the result
(``--pono``), and it must be node-for-node isomorphic to the source under the
id renumbering.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from btor2sieve.pono import check_readable  # noqa: E402


LEGACY_OPS = {"ne": "neq"}
_LITERALS = {"const", "constd", "consth"}
_SORT_ONLY = {"zero", "one", "ones", "input", "state"}
_PREDICATES = {"bad", "constraint", "fair"}
_INDEXED = {"uext": 1, "sext": 1, "slice": 2}
_OPERANDS = {
    **dict.fromkeys("not neg inc dec redand redor redxor".split(), 1),
    **dict.fromkeys((
        "iff implies eq neq sgt sgte slt slte ugt ugte ult ulte and nand nor or xnor xor "
        "rol ror sll sra srl add mul sdiv udiv smod srem urem sub "
        "saddo uaddo sdivo udivo smulo umulo ssubo usubo concat read init next"
    ).split(), 2),
    "ite": 3,
    "write": 3,
}
# Node kinds whose order of definition is observable (witness numbering, b0/j0, outputs).
ORDERED_KINDS = (("input", "state"), ("bad",), ("justice",), ("constraint",), ("fair",), ("output",))


class ConversionError(ValueError):
    """A legacy model that cannot be converted, or a conversion that fails its check."""


@dataclass(frozen=True)
class Line:
    """One BTOR2 line: fields are ("node", signed id), ("sort", id) or ("raw", token)."""

    id: int
    op: str
    fields: tuple[tuple[str, object], ...]
    symbol: str | None
    number: int

    def refs(self) -> list[int]:
        return [abs(value) for kind, value in self.fields if kind in ("node", "sort")]


def _int(token: str, label: str, number: int) -> int:
    try:
        return int(token)
    except ValueError:
        raise ConversionError(f"line {number}: invalid {label} {token!r}") from None


def _shape(op: str, rest: list[str], sorts: set[int]) -> list[str] | None:
    """Kinds of the tokens after the operation: raw, node, sort, or skip (dropped).

    Returns None for an unsupported operation.
    """
    if op == "sort":
        return {"bitvec": ["raw", "raw"], "array": ["raw", "sort", "sort"]}.get(rest[0] if rest else "", [])
    if op in _LITERALS:
        return ["sort", "raw"]
    if op in _SORT_ONLY:
        return ["sort"]
    if op == "output":
        # Legacy outputs name a sort first; current outputs name only the node.
        legacy = len(rest) >= 2 and rest[0].isdigit() and int(rest[0]) in sorts
        return ["skip", "node"] if legacy else ["node"]
    if op in _PREDICATES:
        return ["node"]
    if op == "justice":
        count = int(rest[0]) if rest and rest[0].isdigit() else 0
        return ["raw"] + ["node"] * count
    if op in _INDEXED:
        return ["sort", "node"] + ["raw"] * _INDEXED[op]
    if op in _OPERANDS:
        return ["sort"] + ["node"] * _OPERANDS[op]
    return None


def read(text: str) -> tuple[list[str], list[Line]]:
    """Return the leading comment block and the lines of a legacy or current BTOR2 model."""
    header: list[str] = []
    lines: list[Line] = []
    sorts: set[int] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        tokens: list[str] = []
        for token in raw.split():
            if token.startswith(";"):
                break
            tokens.append(token)
        if not tokens:
            if not lines and raw.strip():
                header.append(raw.strip())
            continue
        if len(tokens) < 2:
            raise ConversionError(f"line {number}: expected a line id and an operation")
        id_ = _int(tokens[0], "line id", number)
        op, rest = LEGACY_OPS.get(tokens[1], tokens[1]), tokens[2:]
        shape = _shape(op, rest, sorts)
        if shape is None:
            raise ConversionError(f"line {number}: unsupported operation {tokens[1]!r}")
        if op == "sort" and not shape:
            raise ConversionError(f"line {number}: expected bitvec or array sort")
        if op == "justice" and len(shape) == 1:
            raise ConversionError(f"line {number}: expected a positive justice condition count")
        if len(rest) < len(shape):
            raise ConversionError(f"line {number}: too few fields for {op}")
        fields = tuple((kind, token if kind == "raw" else _int(token, f"{kind} reference", number))
                       for kind, token in zip(shape, rest) if kind != "skip")
        extra = rest[len(shape):]
        if len(extra) > 1:
            raise ConversionError(f"line {number}: expected at most one symbol, got {' '.join(extra)!r}")
        if op == "sort":
            sorts.add(id_)
        lines.append(Line(id_, op, fields, extra[0] if extra else None, number))
    return header, lines


def _order(lines: list[Line]) -> list[Line]:
    """Topologically order lines, keeping source order where possible.

    Each state additionally depends on its initial value, so the value is
    emitted before the state.
    """
    by_id = {line.id: line for line in lines}
    if len(by_id) != len(lines):
        raise ConversionError("duplicate line ids")
    deps = {line.id: line.refs() for line in lines}
    for line in lines:
        if line.op == "init":
            state, value = (abs(v) for k, v in line.fields if k == "node")
            deps[state] = deps[state] + [value]
    for id_, refs in deps.items():
        for ref in refs:
            if ref not in by_id:
                raise ConversionError(f"line {by_id[id_].number}: undefined reference {ref}")
    emitted: set[int] = set()
    active: set[int] = set()
    order: list[Line] = []
    for line in lines:
        stack = [(line.id, iter(deps[line.id]))]
        if line.id in emitted:
            continue
        active.add(line.id)
        while stack:
            current, pending = stack[-1]
            for ref in pending:
                if ref in emitted:
                    continue
                if ref in active:
                    raise ConversionError(
                        f"line {by_id[ref].number}: dependency cycle (an initial value depends on its state)")
                active.add(ref)
                stack.append((ref, iter(deps[ref])))
                break
            else:
                stack.pop()
                active.discard(current)
                emitted.add(current)
                order.append(by_id[current])
    return order


def _render(line: Line, new_id: int, mapping: dict[int, int]) -> str:
    tokens = [str(new_id), line.op]
    for kind, value in line.fields:
        if kind == "raw":
            tokens.append(str(value))
        else:
            target = mapping[abs(value)]
            tokens.append(str(-target if value < 0 else target))
    if line.symbol is not None:
        tokens.append(line.symbol)
    return " ".join(tokens)


def convert(text: str, source: str = "<string>", pono: str = "pono") -> tuple[str, dict[int, int]]:
    """Return current BTOR2 text and the old-to-new id mapping, after checking the result."""
    header, lines = read(text)
    order = _order(lines)
    mapping = {line.id: new for new, line in enumerate(order, start=1)}
    body = [_render(line, mapping[line.id], mapping) for line in order]
    notes = [f"; converted from legacy Yosys BTOR2 by scripts/convert_legacy_btor2.py ({Path(source).name})"]
    output = "\n".join([*(h if h.startswith(";") else "; " + h for h in header), *notes, *body]) + "\n"
    check(lines, output, mapping, source, pono)
    return output, mapping


def check(original: list[Line], converted_text: str, mapping: dict[int, int], source: str = "<string>",
          pono: str = "pono") -> None:
    """Raise ConversionError unless Pono reads the converted model and it is isomorphic to the original."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / (Path(source).stem + ".btor2")
        path.write_text(converted_text, encoding="utf-8")
        try:
            check_readable(pono, path)
        except ValueError as exc:
            raise ConversionError(f"Pono cannot read the converted model: {exc}") from None
    _, converted = read(converted_text)
    by_id = {line.id: line for line in converted}
    if len(converted) != len(original) or sorted(mapping.values()) != sorted(by_id):
        raise ConversionError("converted model has a different number of lines")

    def mapped(fields: tuple[tuple[str, object], ...]) -> tuple[tuple[str, object], ...]:
        return tuple((kind, value if kind == "raw" else (-1 if value < 0 else 1) * mapping[abs(value)])
                     for kind, value in fields)

    for line in original:
        other = by_id.get(mapping[line.id])
        if other is None or (other.op, other.fields, other.symbol) != (line.op, mapped(line.fields), line.symbol):
            raise ConversionError(f"line {line.number}: converted line differs from the source")
    for kinds in ORDERED_KINDS:
        before = [mapping[line.id] for line in original if line.op in kinds]
        after = [line.id for line in converted if line.op in kinds]
        if before != after:
            raise ConversionError(f"converted model reorders {'/'.join(kinds)} lines")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", type=Path, nargs="+", help="legacy BTOR2 files (any extension)")
    parser.add_argument("--out", type=Path, required=True, help="directory for <name>.btor2 outputs")
    parser.add_argument("--pono", default="pono", help="Pono executable that must read every result")
    args = parser.parse_args(argv)

    targets = [args.out / (source.stem + ".btor2") for source in args.sources]
    clashes = [str(target) for target in targets if target.exists()]
    if len(set(targets)) != len(targets):
        parser.error("two sources would write the same output file")
    if clashes:
        parser.error("refusing to overwrite: " + ", ".join(clashes))
    converted = []
    for source, target in zip(args.sources, targets):
        try:
            text, mapping = convert(source.read_text(encoding="utf-8"), str(source), args.pono)
        except (ConversionError, OSError, UnicodeError) as exc:
            print(f"error: {source}: {exc}", file=sys.stderr)
            return 1
        converted.append((source, target, text, mapping))
    args.out.mkdir(parents=True, exist_ok=True)
    for source, target, text, mapping in converted:
        target.write_text(text, encoding="utf-8")
        moved = sum(1 for old, new in mapping.items() if old != new)
        print(f"{source} -> {target} ({len(mapping)} lines, {moved} renumbered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
