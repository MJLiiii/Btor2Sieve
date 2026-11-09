import pytest
import z3

from btor2sieve.btor2 import Btor2Error, parse
from btor2sieve.encoding import Encoder


@pytest.mark.parametrize("sign", ["", "-"])
def test_decimal_encoding_beyond_python_integer_string_limit(sign):
    width = 15000
    digits = "1" + "0" * 4499 + "7"
    encoder = Encoder(parse(f"1 sort bitvec {width}\n2 constd 1 {sign}{digits}"))
    expected = 10 ** 4500 + 7
    if sign:
        expected = -expected
    # Binary conversion has no decimal digit limit and checks every output bit.
    actual = int(z3.simplify(encoder.expr(2)).as_binary_string(), 2)
    assert actual == expected % (1 << width)


def _rotation_reference(word, amount, width, op):
    bits = f"{word:0{width}b}"
    shift = amount % width
    rotated = bits[shift:] + bits[:shift] if op == "rol" else bits[-shift:] + bits[:-shift]
    return int(rotated, 2)


@pytest.mark.parametrize("width", [1, 2, 3])
def test_small_width_arithmetic_overflow_and_rotation_exhaustively(width):
    word_ops = ("add", "sub", "mul", "sdiv", "udiv", "srem", "urem", "smod", "sll", "sra", "srl", "rol", "ror")
    overflow_ops = ("saddo", "ssubo", "smulo", "sdivo", "uaddo", "usubo", "umulo")
    ops = word_ops + overflow_ops
    program = f"1 sort bitvec {width}\n2 sort bitvec 1\n3 input 1\n4 input 1\n"
    for ref, op in enumerate(ops, start=5):
        result_sort = 2 if op in overflow_ops else 1
        program += f"{ref} {op} {result_sort} 3 4\n"
    encoder = Encoder(parse(program))
    modulus = 1 << width
    mask = modulus - 1
    minimum, maximum = -(modulus // 2), modulus // 2 - 1
    for left in range(modulus):
        signed_left = left if left <= maximum else left - modulus
        for right in range(modulus):
            signed_right = right if right <= maximum else right - modulus
            if signed_right:
                quotient = abs(signed_left) // abs(signed_right)
                if (signed_left < 0) != (signed_right < 0):
                    quotient = -quotient
                remainder = signed_left - quotient * signed_right
            else:
                quotient = 1 if signed_left < 0 else -1
                remainder = signed_left
            expected = {
                "add": left + right,
                "sub": left - right,
                "mul": left * right,
                "sdiv": quotient,
                "udiv": left // right if right else mask,
                "srem": remainder,
                "urem": left % right if right else left,
                "smod": signed_left % signed_right if signed_right else signed_left,
                "sll": left << right,
                "sra": signed_left >> right,
                "srl": left >> right,
                "rol": _rotation_reference(left, right, width, "rol"),
                "ror": _rotation_reference(left, right, width, "ror"),
                "saddo": not minimum <= signed_left + signed_right <= maximum,
                "ssubo": not minimum <= signed_left - signed_right <= maximum,
                "smulo": not minimum <= signed_left * signed_right <= maximum,
                "sdivo": signed_left == minimum and signed_right == -1,
                "uaddo": left + right > mask,
                "usubo": left < right,
                "umulo": left * right > mask,
            }
            substitutions = (
                (encoder.inputs[3], z3.BitVecVal(left, width)),
                (encoder.inputs[4], z3.BitVecVal(right, width)),
            )
            for ref, op in enumerate(ops, start=5):
                actual = z3.simplify(z3.substitute(encoder.expr(ref), *substitutions)).as_long()
                assert actual == (int(expected[op]) & mask), (width, op, left, right)


@pytest.mark.parametrize("width", [1, 3, 70])
def test_rotations_at_width_boundaries(width):
    encoder = Encoder(parse(
        f"1 sort bitvec {width}\n2 input 1\n3 input 1\n4 rol 1 2 3\n5 ror 1 2 3"
    ))
    mask = (1 << width) - 1
    words = {0, 1, mask, 1 << (width - 1), (1 << (width - 1)) | 1}
    amounts = {amount for amount in (0, 1, width - 1, width, width + 1, mask) if amount <= mask}
    for word in words:
        for amount in amounts:
            substitutions = (
                (encoder.inputs[2], z3.BitVecVal(word, width)),
                (encoder.inputs[3], z3.BitVecVal(amount, width)),
            )
            for ref, op in ((4, "rol"), (5, "ror")):
                term = z3.substitute(encoder.expr(ref), *substitutions)
                assert z3.simplify(term).as_long() == _rotation_reference(word, amount, width, op)


def test_wraparound_and_complement_use_bitvector_semantics():
    encoder = Encoder(parse("""1 sort bitvec 4
2 ones 1
3 one 1
4 add 1 2 3
5 add 1 -3 3
6 sort bitvec 1
7 neq 6 4 5
8 bad 7
"""))
    assert z3.simplify(encoder.expr(4)).as_long() == 0
    assert z3.simplify(encoder.expr(5)).as_long() == 15
    assert z3.is_false(z3.simplify(encoder.property(8)))
    with pytest.raises(Btor2Error):
        encoder.property(7)


def test_initial_array_literal_fills_every_index_and_write_updates_next_state():
    encoder = Encoder(parse("""1 sort bitvec 2
2 sort bitvec 4
3 sort array 1 2
4 consth 2 a
5 state 3 mem
6 init 3 5 -4
7 input 1 address
8 input 2 value
9 write 3 5 7 8
10 next 3 5 9
11 read 2 5 7
"""))
    solver = z3.Solver()
    solver.add(encoder.initial, encoder.expr(11) != 5)
    assert solver.check() == z3.unsat
    solver = z3.Solver()
    solver.add(encoder.transition, z3.Select(encoder.next_states[5], encoder.inputs[7]) != encoder.inputs[8])
    assert solver.check() == z3.unsat


def test_structural_sorts_and_array_ite_allow_nested_reads():
    encoder = Encoder(parse("""1 sort bitvec 1
2 sort bitvec 1
3 sort array 1 2
4 sort array 2 1
5 sort array 1 3
6 sort array 2 4
7 one 1
8 input 5 a
9 input 6 a
10 ite 6 7 8 9
11 read 4 10 7
12 read 2 11 7
"""))
    a, b = encoder.inputs[8], encoder.inputs[9]
    assert not a.eq(b)
    assert a.sort() == b.sort()
    assert z3.is_true(z3.simplify(encoder.expr(12) == z3.Select(z3.Select(a, 1), 1)))


def test_missing_init_and_next_are_free_and_prime_substitutes_inputs():
    encoder = Encoder(parse("""1 sort bitvec 1
2 state 1 latch
3 input 1 tick
4 xor 1 2 3
5 bad 4
"""))
    for value in (0, 1):
        solver = z3.Solver()
        solver.add(encoder.initial, encoder.transition, encoder.states[2] == value, encoder.next_states[2] != value)
        assert solver.check() == z3.sat
    primed = encoder.prime(encoder.property(5))
    assert primed.eq(encoder.prime(encoder.property(5)))
    assert not z3.substitute(primed, (encoder.next_states[2], encoder.states[2])).eq(primed)
    assert not encoder.prime(encoder.inputs[3]).eq(encoder.inputs[3])


def test_fair_and_justice_do_not_constrain_finite_safety_scopes():
    encoder = Encoder(parse("""1 sort bitvec 1
2 zero 1
3 fair 2
4 justice 1 2
5 bad -2
"""))
    assert z3.is_true(z3.simplify(encoder.assumptions))
    assert z3.is_false(z3.simplify(encoder.property(5)))


@pytest.mark.parametrize(
    ("op", "left", "right", "out_width", "expected"),
    [
        ("sdiv", -7, 3, 4, 14),
        ("srem", -7, 3, 4, 15),
        ("smod", -7, 3, 4, 2),
        ("smod", 7, -3, 4, 14),
        ("sdiv", -7, 0, 4, 1),
        ("udiv", 7, 0, 4, 15),
        ("urem", 7, 0, 4, 7),
        ("sra", -8, 9, 4, 15),
        ("srl", -8, 9, 4, 0),
        ("sll", -8, 9, 4, 0),
        ("rol", 9, 5, 4, 3),
        ("ror", 9, 5, 4, 12),
        ("slt", -1, 1, 1, 1),
        ("ult", -1, 1, 1, 0),
        ("saddo", -8, -1, 1, 1),
        ("saddo", -8, 7, 1, 0),
        ("ssubo", -8, 1, 1, 1),
        ("ssubo", 7, -1, 1, 1),
        ("smulo", -8, 1, 1, 0),
        ("smulo", -8, -1, 1, 1),
        ("sdivo", -8, -1, 1, 1),
        ("sdivo", -8, 0, 1, 0),
        ("uaddo", 15, 1, 1, 1),
        ("usubo", 1, 2, 1, 1),
        ("umulo", 4, 4, 1, 1),
    ],
)
def test_signed_unsigned_and_overflow_results(op, left, right, out_width, expected):
    encoder = Encoder(parse(
        f"1 sort bitvec 4\n2 sort bitvec {out_width}\n3 constd 1 {left}\n"
        f"4 constd 1 {right}\n5 {op} 2 3 4\n"
    ))
    assert z3.simplify(encoder.expr(5)).as_long() == expected


def test_indexed_operators_and_reductions():
    encoder = Encoder(parse("""1 sort bitvec 3
2 sort bitvec 5
3 sort bitvec 1
4 const 1 101
5 sext 2 4 2
6 uext 2 4 2
7 slice 1 5 3 1
8 redxor 3 7
9 redand 3 4
10 redor 3 4
"""))
    assert [z3.simplify(encoder.expr(ref)).as_long() for ref in range(5, 11)] == [29, 5, 6, 0, 0, 1]


def test_deep_dag_encodes_without_python_recursion():
    depth = 3000
    program = "1 sort bitvec 16\n2 zero 1\n" + "".join(
        f"{i} inc 1 {i - 1}\n" for i in range(3, depth + 3)
    )
    encoder = Encoder(parse(program))
    assert z3.simplify(encoder.expr(depth + 2)).as_long() == depth


def test_reductions_use_portable_smtlib_operators():
    encoder = Encoder(parse("""1 sort bitvec 4
2 sort bitvec 1
3 input 1
4 redand 2 3
5 redor 2 3
6 constraint 4
7 bad 5
"""))
    solver = z3.Solver()
    solver.add(encoder.assumptions, encoder.property(7))
    smt2 = solver.to_smt2()
    assert "bvredand" not in smt2 and "bvredor" not in smt2
    assert solver.check() == z3.unsat
