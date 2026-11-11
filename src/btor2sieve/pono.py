"""Pono is the BTOR2 frontend: it parses each model and says what each property means.

Btor2Sieve has no BTOR2 parser of its own. For each property, Pono reads the
model file and prints the SMT-LIB formula it uses for that property; that
formula is P, the hypothesis everything else works from. Candidate
constraints are built from P's subterms (`vocabulary.py`) and proved against
P with Z3 (`validation.py`).

How P is read: Pono runs BMC at bound 0 on the model without its init,
environment-constraint, fair and justice lines, with `--printing-smt-solver`.
Pono prints every SMT query to stderr; the first assertion after the first
`(push 1)` is "the selected bad holds at step 0", so P is its negation. Pono
names variables `state<ID>@0` and `input<ID>@0` after the BTOR2 line IDs;
they are renamed `s_<ID>` and `i_<ID>`. Pono is stopped as soon as the
assertion has been read; its verdict is not needed.

The only thing Btor2Sieve does with the model text itself is split lines into
words (`scan`), to find line IDs, keywords and symbol names: which lines are
`bad`, which to leave out before Pono reads the file, and the counts shown in
reports. It never interprets an expression.

The module also runs Pono as a model checker (`run_pono`) and writes Z3
constraints back into BTOR2 (`Btor2Writer`) for `verify.py`.
"""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from time import perf_counter

import z3


ENGINES = ("bmc", "bmc-sp", "dar", "ind", "interp", "ismc", "mbic3", "ic3bits", "ic3ia",
           "msat-ic3ia", "ic3sa", "sygus-pdr")
VERDICTS = ("sat", "unsat", "unknown")
# Lines left out before Pono reads a property: only the property itself is
# assumed, and liveness lines play no part.
PROPERTY_DROPPED = frozenset({"init", "constraint", "fair", "justice"})
# Operations Pono misreads, so models using them are refused. The hwmcc25
# binary encodes `rol`/`ror` as a fixed rotate by the second operand's line
# ID instead of by its value (tests/test_pono.py demonstrates this).
MISREAD_BY_PONO = frozenset({"rol", "ror"})
_PONO_VARIABLE = re.compile(r"(state|input)(\d+)@0")
VARIABLE = re.compile(r"([si])_(\d+)")


# --- Lines of a model file ---------------------------------------------------

@dataclass(frozen=True)
class Line:
    """One BTOR2 line split into words; nothing is interpreted."""
    number: int              # 1-based line number in the file
    id: int
    op: str
    words: tuple[str, ...]   # the words after the keyword


def scan(text: str) -> list[Line]:
    """Split a model into lines of words, ignoring blank lines and `;` comments."""
    lines = []
    for number, raw in enumerate(text.splitlines(), start=1):
        words = raw.split(";", 1)[0].split()
        if not words:
            continue
        if len(words) < 2 or not words[0].isdigit():
            raise ValueError(f"line {number}: expected a line ID and a keyword")
        lines.append(Line(number, int(words[0]), words[1], tuple(words[2:])))
    return lines


def without(text: str, lines: list[Line], ops: frozenset[str]) -> list[str]:
    """The model's text lines, leaving out lines whose keyword is in `ops`."""
    dropped = {line.number for line in lines if line.op in ops}
    return [raw for number, raw in enumerate(text.splitlines(), start=1) if number not in dropped]


def features(lines: list[Line]) -> dict:
    """Counts shown by `inspect` and stored in reports, taken from the keywords."""
    ops = Counter(line.op for line in lines if line.op != "sort")
    sorts = [line for line in lines if line.op == "sort"]
    widths = [int(line.words[1]) for line in sorts if line.words[:1] == ("bitvec",) and len(line.words) > 1
              and line.words[1].isdigit()]
    return {
        "nodes": sum(ops.values()), "states": ops["state"], "inputs": ops["input"],
        "properties": ops["bad"], "constraints": ops["constraint"],
        "array_sorts": sum(line.words[:1] == ("array",) for line in sorts),
        "max_bit_width": max(widths, default=0),
        "operations": dict(sorted(ops.items())),
        "liveness_nodes": ops["fair"] + ops["justice"],
    }


def symbols(lines: list[Line]) -> dict[str, str | None]:
    """User names of states and inputs (`<id> state <sort> <name>`)."""
    return {str(line.id): line.words[1] if len(line.words) > 1 else None
            for line in lines if line.op in {"state", "input"}}


# --- Reading properties with Pono ---------------------------------------------

@dataclass
class Property:
    id: int                   # line ID of the `bad` line
    index: int                # its position among the `bad` lines (Pono's -p)
    hypothesis: z3.BoolRef    # P = not bad, as Pono reads it


@dataclass
class PonoModel:
    path: Path
    lines: list[Line]
    properties: list[Property]
    seconds: float

    @property
    def bad_ids(self) -> list[int]:
        return [line.id for line in self.lines if line.op == "bad"]


def _read_bad_assertion(command: list[str], timeout: float) -> tuple[list[str], str]:
    """Stream Pono's query dump; return its declarations and the first assertion after `(push 1)`.

    Pono prints parse errors on stdout and the dump on stderr, so both are read
    as one stream, and any other message becomes part of the error.
    """
    declarations: list[str] = []
    messages: list[str] = []
    seen_push = False
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # Kill from a timer: a silent Pono would otherwise block the read forever.
    timer = threading.Timer(timeout, process.kill)
    timer.start()
    try:
        assert process.stdout is not None
        for line in process.stdout:
            if line.startswith("(declare-fun "):
                declarations.append(line.rstrip("\n"))
            elif line.startswith("(push"):
                seen_push = True
            elif seen_push and line.startswith("(assert "):
                return declarations, line.rstrip("\n")
            elif not line.startswith("("):
                messages.append(line.strip())
    finally:
        timed_out = not timer.is_alive()
        timer.cancel()
        process.kill()
        process.wait()
    if timed_out:
        raise ValueError(f"Pono did not print the property within {timeout:g}s")
    detail = "\n".join(m for m in messages if m not in {"error", "b0"})[-500:]
    raise ValueError("Pono could not read the property" + (f": {detail}" if detail else ""))


def free_constants(expr: z3.ExprRef) -> set[z3.ExprRef]:
    found, seen, stack = set(), set(), [expr]
    while stack:
        term = stack.pop()
        if term.get_id() in seen:
            continue
        seen.add(term.get_id())
        if z3.is_const(term) and term.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            found.add(term)
        stack.extend(term.children())
    return found


def _property(pono: str, path: Path, index: int, property_id: int, timeout: float) -> z3.BoolRef:
    command = [pono, "-e", "bmc", "-k", "0", "-p", str(index),
               "--printing-smt-solver", "--logging-smt-solver", str(path)]
    declarations, assertion = _read_bad_assertion(command, timeout)
    try:
        (bad,) = z3.parse_smt2_string("\n".join([*declarations, assertion]))
    except z3.Z3Exception as exc:
        raise ValueError(f"cannot read Pono's property {property_id}: {exc}") from exc
    pairs = []
    for constant in free_constants(bad):
        match = _PONO_VARIABLE.fullmatch(str(constant))
        if match is None:
            raise ValueError(f"Pono's property {property_id} uses {constant}, "
                             "which is not a state or input at step 0")
        name = f"{match[1][0]}_{match[2]}"  # state12@0 -> s_12, input3@0 -> i_3
        pairs.append((constant, z3.Const(name, constant.sort())))
    return z3.Not(z3.substitute(bad, *pairs) if pairs else bad)


def read_model(pono: str, path: Path, *, property_ids: list[int] | None = None,
               timeout: float = 300.0) -> PonoModel:
    """Have Pono read every selected property of a model file."""
    start = perf_counter()
    text = path.read_text()
    lines = scan(text)
    misread = sorted({line.op for line in lines} & MISREAD_BY_PONO)
    if misread:
        raise ValueError(f"{path}: uses {', '.join(misread)}, which Pono misreads "
                         "(it rotates by the operand's line ID, not its value)")
    bads = [line.id for line in lines if line.op == "bad"]  # File order; Pono's -p counts the same way.
    selected = bads if property_ids is None else list(property_ids)
    for property_id in selected:
        if property_id not in bads:
            raise ValueError(f"bad directive {property_id} not found in {path}")
    properties = []
    with tempfile.TemporaryDirectory() as directory:
        stripped = Path(directory) / path.name
        stripped.write_text("\n".join(without(text, lines, PROPERTY_DROPPED)) + "\n")
        if not bads:
            _parses_without_property(pono, path, timeout)  # Pono must still accept the file.
        for property_id in selected:
            index = bads.index(property_id)
            properties.append(Property(property_id, index,
                                       _property(pono, stripped, index, property_id, timeout)))
    return PonoModel(path, lines, properties, perf_counter() - start)


def _parses_without_property(pono: str, path: Path, timeout: float) -> None:
    # Without a property, Pono still parses the whole file before it notices.
    try:
        process = subprocess.run([pono, "-e", "bmc", "-k", "0", str(path)], capture_output=True,
                                 text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ValueError(f"Pono did not finish reading {path} within {timeout:g}s") from None
    if "greater than the number of properties" not in process.stdout + process.stderr:
        output = (process.stdout + process.stderr).replace("error\nb0", "").strip()[-500:]
        raise ValueError(f"Pono could not read {path}: {output}")


def check_readable(pono: str, path: Path, timeout: float = 300.0) -> None:
    """Raise ValueError unless Pono parses the file and reads every property."""
    read_model(pono, path, timeout=timeout)


# --- Writing Z3 formulas back into BTOR2 ---------------------------------------

class EmitError(ValueError):
    """A constraint uses a Z3 operator that has no BTOR2 counterpart here."""


_DIRECT = {
    z3.Z3_OP_NOT: "not", z3.Z3_OP_BNOT: "not", z3.Z3_OP_BNEG: "neg",
    z3.Z3_OP_BREDOR: "redor", z3.Z3_OP_BREDAND: "redand",
    z3.Z3_OP_IMPLIES: "implies", z3.Z3_OP_EQ: "eq", z3.Z3_OP_IFF: "eq", z3.Z3_OP_BCOMP: "eq",
    z3.Z3_OP_ULEQ: "ulte", z3.Z3_OP_ULT: "ult", z3.Z3_OP_UGEQ: "ugte", z3.Z3_OP_UGT: "ugt",
    z3.Z3_OP_SLEQ: "slte", z3.Z3_OP_SLT: "slt", z3.Z3_OP_SGEQ: "sgte", z3.Z3_OP_SGT: "sgt",
    z3.Z3_OP_BSUB: "sub", z3.Z3_OP_BSDIV: "sdiv", z3.Z3_OP_BUDIV: "udiv",
    z3.Z3_OP_BSREM: "srem", z3.Z3_OP_BUREM: "urem", z3.Z3_OP_BSMOD: "smod",
    z3.Z3_OP_BSHL: "sll", z3.Z3_OP_BLSHR: "srl", z3.Z3_OP_BASHR: "sra",
    z3.Z3_OP_BNAND: "nand", z3.Z3_OP_BNOR: "nor", z3.Z3_OP_BXNOR: "xnor",
    z3.Z3_OP_SELECT: "read", z3.Z3_OP_STORE: "write", z3.Z3_OP_ITE: "ite",
}
# N-ary Z3 operators folded left into binary BTOR2 lines.
_FOLD = {
    z3.Z3_OP_AND: "and", z3.Z3_OP_OR: "or", z3.Z3_OP_XOR: "xor",
    z3.Z3_OP_BAND: "and", z3.Z3_OP_BOR: "or", z3.Z3_OP_BXOR: "xor",
    z3.Z3_OP_BADD: "add", z3.Z3_OP_BMUL: "mul", z3.Z3_OP_CONCAT: "concat",
}


def _sort_key(sort: z3.SortRef) -> tuple:
    if sort.kind() == z3.Z3_BOOL_SORT:
        return ("bv", 1)
    if sort.kind() == z3.Z3_BV_SORT:
        return ("bv", sort.size())
    if sort.kind() == z3.Z3_ARRAY_SORT:
        return ("array", _sort_key(sort.domain()), _sort_key(sort.range()))
    raise EmitError(f"unsupported sort {sort}")


class Btor2Writer:
    """Append BTOR2 lines for Z3 formulas over `s_<ID>` and `i_<ID>`.

    New lines are numbered from `first_id`, after the model's largest ID.
    `s_<ID>` and `i_<ID>` are written as references to line `<ID>`; every
    operator gets a new line, with new sort lines as needed.
    """

    def __init__(self, first_id: int):
        self.lines: list[str] = []
        self.next_id = first_id
        self._sorts: dict[tuple, int] = {}
        self._memo: dict[int, int] = {}
        # Z3 reuses an AST ID once its term is freed, so pin every memoized
        # term; otherwise a stale entry could match an unrelated later term.
        self._pinned: list[z3.ExprRef] = []

    def line(self, op: str, *fields: object) -> int:
        id_ = self.next_id
        self.next_id += 1
        self.lines.append(" ".join(map(str, (id_, op, *fields))))
        return id_

    def sort(self, sort: z3.SortRef | tuple) -> int:
        key = sort if isinstance(sort, tuple) else _sort_key(sort)
        if key not in self._sorts:
            if key[0] == "bv":
                self._sorts[key] = self.line("sort", "bitvec", key[1])
            else:
                index, element = self.sort(key[1]), self.sort(key[2])
                self._sorts[key] = self.line("sort", "array", index, element)
        return self._sorts[key]

    def const(self, value: int, width: int) -> int:
        return self.line("const", self.sort(("bv", width)), format(value % (1 << width), "b").zfill(width))

    def bit(self, expr: z3.ExprRef) -> int:
        """Emit a Boolean or one-bit expression and return its line ID."""
        if not (z3.is_bool(expr) or (z3.is_bv(expr) and expr.size() == 1)):
            raise EmitError(f"expected a Boolean or one-bit term, got {expr.sort()}")
        return self.ref(expr)

    def ref(self, root: z3.ExprRef) -> int:
        stack = [(root, False)]
        while stack:
            expr, ready = stack.pop()
            key = expr.get_id()
            if key in self._memo:
                continue
            if not ready:
                stack.append((expr, True))
                stack.extend((child, False) for child in expr.children()
                             if child.get_id() not in self._memo)
                continue
            self._memo[key] = self._emit(expr, [self._memo[c.get_id()] for c in expr.children()])
            self._pinned.append(expr)
        return self._memo[root.get_id()]

    def _emit(self, expr: z3.ExprRef, args: list[int]) -> int:
        kind = expr.decl().kind()
        if kind == z3.Z3_OP_UNINTERPRETED and not args:
            match = VARIABLE.fullmatch(str(expr))
            if match is None:
                raise EmitError(f"symbol {expr} is not a state or input of this model")
            return int(match[2])
        sort = self.sort(expr.sort())
        if kind == z3.Z3_OP_TRUE:
            return self.const(1, 1)
        if kind == z3.Z3_OP_FALSE:
            return self.const(0, 1)
        if kind == z3.Z3_OP_BNUM:
            return self.const(expr.as_long(), expr.size())
        if kind in _FOLD:
            op, children = _FOLD[kind], expr.children()
            result, width = args[0], _sort_key(children[0].sort())[1] if kind == z3.Z3_OP_CONCAT else 0
            for child, arg in zip(children[1:], args[1:]):
                if kind == z3.Z3_OP_CONCAT:  # Intermediate results are narrower than the whole.
                    width += child.size()
                    result = self.line(op, self.sort(("bv", width)), result, arg)
                else:
                    result = self.line(op, sort, result, arg)
            return result
        if kind == z3.Z3_OP_DISTINCT:
            pairs = [self.line("neq", self.sort(("bv", 1)), a, b)
                     for i, a in enumerate(args) for b in args[i + 1:]]
            result = pairs[0]
            for pair in pairs[1:]:
                result = self.line("and", self.sort(("bv", 1)), result, pair)
            return result
        if kind == z3.Z3_OP_EXTRACT:
            high, low = expr.params()
            return self.line("slice", sort, args[0], high, low)
        if kind in (z3.Z3_OP_ZERO_EXT, z3.Z3_OP_SIGN_EXT):
            return self.line("uext" if kind == z3.Z3_OP_ZERO_EXT else "sext", sort, args[0],
                             expr.params()[0])
        if kind == z3.Z3_OP_REPEAT:
            width, result = expr.children()[0].size(), args[0]
            for copy in range(1, expr.params()[0]):
                result = self.line("concat", self.sort(("bv", width * (copy + 1))), result, args[0])
            return result
        if kind in (z3.Z3_OP_ROTATE_LEFT, z3.Z3_OP_ROTATE_RIGHT,
                    z3.Z3_OP_EXT_ROTATE_LEFT, z3.Z3_OP_EXT_ROTATE_RIGHT):
            # Written with shifts: Pono misreads BTOR2 `rol`/`ror` (see MISREAD_BY_PONO).
            width = expr.size()
            if kind in (z3.Z3_OP_ROTATE_LEFT, z3.Z3_OP_ROTATE_RIGHT):
                amount = self.const(expr.params()[0] % width, width)
            else:
                amount = self.line("urem", sort, args[1], self.const(width, width))
            rest = self.line("sub", sort, self.const(width, width), amount)
            first, second = ("sll", "srl") if kind in (z3.Z3_OP_ROTATE_LEFT, z3.Z3_OP_EXT_ROTATE_LEFT) \
                else ("srl", "sll")
            # A shift by the full width gives 0 in BTOR2, so a zero rotate stays exact.
            return self.line("or", sort, self.line(first, sort, args[0], amount),
                             self.line(second, sort, args[0], rest))
        if kind in _DIRECT:
            return self.line(_DIRECT[kind], sort, *args)
        raise EmitError(f"no BTOR2 counterpart for Z3 operator {expr.decl().name()}")


# --- Running Pono as a model checker ----------------------------------------

@dataclass
class PonoResult:
    verdict: str  # sat, unsat, unknown, timeout or error
    seconds: float
    returncode: int | None = None
    detail: str | None = None


def run_pono(pono: str, path: Path, engine: str, bound: int, timeout: float) -> PonoResult:
    """Run Pono once and read its verdict from the first verdict line.

    Backend solvers may print warnings to stdout first (Bitwuzla does for
    constant arrays). Pono's exit status is not a safety verdict (it returns
    0 for sat), so it is recorded but not interpreted.
    """
    command = [pono, "-e", engine, "-k", str(bound), str(path)]
    start = perf_counter()
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return PonoResult("timeout", perf_counter() - start)
    elapsed = perf_counter() - start
    for line in process.stdout.splitlines():
        if line.strip() in VERDICTS:
            warnings = [w for w in process.stdout.splitlines() if "warning" in w.lower()]
            return PonoResult(line.strip(), elapsed, process.returncode,
                              "; ".join(dict.fromkeys(warnings)) or None)
    detail = (process.stderr.strip() or process.stdout.strip())[-500:] or None
    if process.returncode < 0:  # Killed by a signal, e.g. a segmentation fault inside Pono.
        detail = f"Pono crashed with signal {-process.returncode}" + (f": {detail}" if detail else "")
    return PonoResult("error", elapsed, process.returncode, detail)


def pono_identity(pono: str) -> dict:
    """Resolve the executable and fingerprint it, since --version is not descriptive."""
    resolved = shutil.which(pono)
    if resolved is None:
        raise ValueError(f"Pono executable not found: {pono} (enter nix-shell or pass --pono)")
    digest = hashlib.sha256(Path(resolved).read_bytes()).hexdigest()
    try:
        version = subprocess.run([resolved, "--version"], capture_output=True, text=True,
                                 timeout=30).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return {"path": resolved, "sha256": digest, "version_output": version}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
