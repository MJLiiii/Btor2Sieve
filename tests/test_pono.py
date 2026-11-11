"""Pono as the frontend, the BTOR2 writer, and the verification runner.

Tests that read real models need Pono on PATH (inside nix-shell). Runner and
dump-parsing edge cases use a fake Pono script.
"""

from pathlib import Path
import sys

import pytest
import z3

from btor2sieve.cli import main
from btor2sieve.implied import GenerationOptions
from btor2sieve.pipeline import analyze
from btor2sieve.pono import (Btor2Writer, EmitError, check_readable, features, free_constants, read_model,
                             run_pono, scan, symbols, without)
from btor2sieve.reporting import write_report
import btor2sieve.verify as verify


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.btor2"))

# P: counter < 10, plus an input and an environment constraint.
COUNTER = """; a counter
1 sort bitvec 1
2 sort bitvec 8
3 zero 2
4 constd 2 10
5 state 2 counter
6 init 2 5 3
7 one 2
8 add 2 5 7
9 next 2 5 8
10 ugte 1 5 4
11 bad 10 bound
12 input 2 noise
13 ult 1 12 4
14 constraint 13 environment
"""
COUNTER_P = z3.ULT(z3.BitVec("s_5", 8), 10)
# Declarations only, for writing formulas back and having Pono read them.
WIDE = """1 sort bitvec 1
2 sort bitvec 4
3 sort bitvec 8
4 sort array 2 3
5 state 3 x
6 state 3 y
7 input 2 i
8 state 4 mem
"""


def _write(tmp_path: Path, text: str, name: str = "model.btor2") -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def _equivalent(left: z3.BoolRef, right: z3.BoolRef) -> bool:
    solver = z3.Solver()
    solver.add(left != right)
    return solver.check() == z3.unsat


def _fake_pono(tmp_path: Path, script: str) -> str:
    path = tmp_path / "fake-pono"
    path.write_text(f"#!{sys.executable}\nimport sys\nargs = sys.argv[1:]\nname = args[-1] if args else ''\n"
                    + script)
    path.chmod(0o755)
    return str(path)


# --- Lines of a model file ----------------------------------------------------

def test_scan_splits_lines_without_interpreting_them():
    lines = scan(COUNTER)
    assert [line.id for line in lines] == list(range(1, 15))
    bad = next(line for line in lines if line.op == "bad")
    assert (bad.number, bad.id, bad.words) == (12, 11, ("10", "bound"))
    assert symbols(lines) == {"5": "counter", "12": "noise"}
    assert features(lines)["properties"] == 1 and features(lines)["constraints"] == 1
    assert features(lines)["max_bit_width"] == 8 and features(lines)["states"] == 1
    kept = without(COUNTER, lines, frozenset({"init", "constraint"}))
    assert "6 init 2 5 3" not in kept and "14 constraint 13 environment" not in kept
    with pytest.raises(ValueError, match="line 2"):
        scan("1 sort bitvec 1\nsort bitvec 8\n")


# --- Reading P with Pono --------------------------------------------------------

def test_pono_reads_p_without_init_or_environment_constraints(tmp_path):
    model = read_model("pono", _write(tmp_path, COUNTER))
    (prop,) = model.properties
    assert (prop.id, prop.index) == (11, 0)
    assert _equivalent(prop.hypothesis, COUNTER_P)  # Not counter < 10 and noise < 10.
    assert model.bad_ids == [11]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_pono_reads_every_example_property(path):
    model = read_model("pono", path)
    assert [p.id for p in model.properties] == model.bad_ids
    for prop in model.properties:
        assert z3.is_bool(prop.hypothesis)
        assert all(str(v)[:2] in {"s_", "i_"} for v in free_constants(prop.hypothesis))


def test_pono_parse_errors_are_reported(tmp_path):
    path = _write(tmp_path, "1 sort bitvec 8\n2 state 1 x\n3 add 1 2 9\n4 bad 3\n")
    with pytest.raises(ValueError, match="Pono could not read the property: .*line 3"):
        read_model("pono", path)
    with pytest.raises(ValueError, match="line 3"):
        check_readable("pono", path)
    check_readable("pono", _write(tmp_path, "1 sort bitvec 8\n2 state 1 x\n", "nobad.btor2"))
    with pytest.raises(ValueError, match="bad directive 99"):
        read_model("pono", _write(tmp_path, COUNTER), property_ids=[99])


DUMP = """
sys.stderr.write('(declare-fun state5@0 () (_ BitVec 8))\\n(assert true)\\n(push 1)\\n')
sys.stderr.write('(assert (or false (not (not (bvuge state5@0 #b00001010)))))\\n')
print('sat')
"""


def test_unexpected_dump_contents_are_errors(tmp_path):
    path = _write(tmp_path, COUNTER)
    (prop,) = read_model(_fake_pono(tmp_path, DUMP), path).properties
    assert _equivalent(prop.hypothesis, COUNTER_P)
    with pytest.raises(ValueError, match="not a state or input"):
        read_model(_fake_pono(tmp_path, DUMP.replace("state5@0", "other5")), path)
    with pytest.raises(ValueError, match="within 0.3s"):
        read_model(_fake_pono(tmp_path, "import time; time.sleep(30)\n"), path, timeout=0.3)


def test_extract_records_pono_and_needs_it(tmp_path, capsys):
    path = _write(tmp_path, COUNTER)
    report = analyze([path], tmp_path / "run", GenerationOptions())
    assert report["frontend"]["name"] == "pono" and report["frontend"]["pono"]["sha256"]
    (scope,) = report["models"][0]["scopes"]
    assert "bvuge s_5 #x0a" in scope["hypothesis"]
    assert report["models"][0]["symbols"] == {"5": "counter", "12": "noise"}
    assert any(r["status"] == "accepted" for r in report["records"])
    assert main(["extract", str(path), "--out", str(tmp_path / "out"),
                 "--pono", str(tmp_path / "missing")]) == 2
    assert "Pono executable not found" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# --- Writing Z3 formulas back into BTOR2 -----------------------------------------

def test_writer_references_states_and_numbers_after_the_model():
    writer = Btor2Writer(9)
    node = writer.bit(z3.ULE(z3.BitVec("s_5", 8), 9))
    assert writer.lines[0].split()[0] == "9"
    ulte = next(line for line in writer.lines if " ulte " in line)
    assert ulte.split()[3] == "5"
    assert node == int(writer.lines[-1].split()[0])


X, Y = z3.BitVec("s_5", 8), z3.BitVec("s_6", 8)
I = z3.BitVec("i_7", 4)
MEM = z3.Array("s_8", z3.BitVecSort(4), z3.BitVecSort(8))


@pytest.mark.parametrize("formula", [
    z3.ULE(X, 9),
    z3.And(X != 3, Y != 4, X > -2),
    z3.Or(z3.Xor(X == 0, Y == 0), z3.Implies(X == 1, z3.BoolVal(False))),
    (X & 0xF0) == 0x30,
    z3.Concat(I, z3.Extract(3, 0, X)) == Y,
    z3.ZeroExt(4, I) == z3.SignExt(4, z3.Extract(3, 0, Y)),
    z3.Distinct(X, Y, z3.Select(MEM, I)),
    z3.RotateLeft(X, 3) == z3.RotateRight(Y, 2),
    z3.RotateLeft(X, z3.ZeroExt(4, I)) == z3.RotateRight(Y, X),
    z3.RepeatBitVec(2, I) == X,
    z3.If(X == 0, Y, X + Y * 3) == 7,
    z3.UDiv(X, Y) == z3.URem(X, 3),
    X / Y == z3.SRem(X, Y) + X % Y,
    (X << 1) == (z3.LShR(Y, 2) ^ (X >> 1)),
    -X == ~Y,
    z3.Select(z3.Store(MEM, I, X), I) == X,
    MEM == z3.Store(MEM, I, z3.Select(MEM, I)),
], ids=["ule", "and-ne-sgt", "xor-implies", "mask", "concat-extract", "ext", "distinct3",
        "rotate", "rotate-variable", "repeat", "ite-arith", "udiv-urem", "sdiv-srem-smod", "shifts", "neg-not",
        "select-store", "array-eq"])
def test_pono_reads_written_formulas_back_unchanged(tmp_path, formula):
    writer = Btor2Writer(9)
    node = writer.bit(formula)
    # `bad not C` makes Pono's P equal C.
    text = WIDE + "\n".join(writer.lines) + f"\n{writer.next_id} bad -{node}\n"
    (prop,) = read_model("pono", _write(tmp_path, text)).properties
    assert _equivalent(prop.hypothesis, formula)


def test_models_with_rotates_are_refused_because_pono_misreads_them(tmp_path):
    # BTOR2 rotates x by the value of k. This Pono build rotates by k's line ID
    # instead, so P below would silently become "rotate_left(x, 3) == x".
    path = _write(tmp_path, "1 sort bitvec 8\n2 state 1 x\n3 input 1 k\n4 rol 1 2 3\n"
                            "5 sort bitvec 1\n6 eq 5 4 2\n7 bad 6\n")
    with pytest.raises(ValueError, match="rol, which Pono misreads"):
        read_model("pono", path)


def test_unknown_symbols_and_operators_are_reported():
    writer = Btor2Writer(9)
    with pytest.raises(EmitError, match="not a state or input"):
        writer.bit(z3.BitVec("stranger", 8) == 0)
    with pytest.raises(EmitError, match="no BTOR2 counterpart"):
        writer.bit(z3.BVMulNoOverflow(X, Y, False))
    with pytest.raises(EmitError, match="unsupported sort"):
        writer.bit(z3.BV2Int(X) == 3)


# --- Running Pono and the verification experiment -----------------------------------

def test_run_pono_reads_the_verdict_after_solver_warnings(tmp_path):
    fake = _fake_pono(tmp_path, "print('[bzla] warning: constant arrays'); print('unsat'); print('b0')\n")
    result = run_pono(fake, tmp_path / "m.btor2", "ic3ia", 10, 10)
    assert result.verdict == "unsat"
    assert "constant arrays" in result.detail


def test_run_pono_reports_errors_and_timeouts(tmp_path):
    broken = _fake_pono(tmp_path, "sys.stderr.write('parse failure'); sys.exit(1)\n")
    assert (result := run_pono(broken, tmp_path / "m", "bmc", 0, 10)).verdict == "error"
    assert result.detail == "parse failure"
    crash = _fake_pono(tmp_path, "import os, signal; os.kill(os.getpid(), signal.SIGSEGV)\n")
    assert run_pono(crash, tmp_path / "m", "ic3ia", 10, 10).detail == "Pono crashed with signal 11"
    slow = _fake_pono(tmp_path, "import time; time.sleep(5)\n")
    assert run_pono(slow, tmp_path / "m", "bmc", 0, 0.2).verdict == "timeout"


def test_verification_file_adds_p_implies_c_and_keeps_the_model(tmp_path):
    model = verify._Model(_write(tmp_path, COUNTER), "pono", 30)
    formula = model.formula("(bvule s_5 #x09)")
    text = "\n".join(model.file(11, [formula])) + "\n"
    lines = scan(text)
    assert [l.op for l in lines].count("init") == 1 and [l.op for l in lines].count("constraint") == 2
    assert [l.words for l in lines if l.op == "bad"] == [("10",)]
    # Have Pono read the added constraint's term: as `bad -term`, its P is the term itself.
    added = [line for line in lines if line.op == "constraint"][-1]
    probe = without(text, lines, frozenset({"bad"})) + [f"{lines[-1].id + 1} bad -{added.words[0]}"]
    (prop,) = read_model("pono", _write(tmp_path, "\n".join(probe) + "\n", "probe.btor2")).properties
    assert _equivalent(prop.hypothesis, z3.Or(z3.UGE(z3.BitVec("s_5", 8), 10), formula))


VERIFY_PONO = """
if '--printing-smt-solver' in args:
""" + "\n".join("    " + line for line in DUMP.strip().splitlines()) + """
else:
    print(VERDICT)
"""


def _report(tmp_path: Path) -> Path:
    path = _write(tmp_path, COUNTER, "counter.btor2")
    write_report(analyze([path], tmp_path / "run", GenerationOptions()), tmp_path / "run")
    return tmp_path / "run"


def test_verify_summarizes_matching_verdicts(tmp_path):
    report = _report(tmp_path)
    fake = _fake_pono(tmp_path, "VERDICT = 'unsat'\n" + VERIFY_PONO)
    result, code = verify.run(report, tmp_path / "verify", pono=fake, engines=["ic3ia", "ind"])
    assert code == 0, result
    assert result["summary"]["runs"] == 2 and result["summary"]["inconsistent"] == 0
    assert all(row["constraints"] > 0 and row["constraints_unsupported"] == 0 for row in result["runs"])
    assert (tmp_path / "verify" / "verify.json").is_file() and (tmp_path / "verify" / "verify.csv").is_file()
    assert not list((tmp_path / "verify" / "btor2").iterdir())  # Nothing kept without a reason.
    with pytest.raises(FileExistsError):
        verify.run(report, tmp_path / "verify", pono=fake)


def test_verify_flags_verdicts_changed_by_the_constraints(tmp_path):
    report = _report(tmp_path)
    fake = _fake_pono(tmp_path, "VERDICT = 'unsat' if 'constrained' in name else 'sat'\n" + VERIFY_PONO)
    result, code = verify.run(report, tmp_path / "verify", pono=fake)
    assert code == 1
    (row,) = result["runs"]
    assert not row["consistent"]
    assert (tmp_path / "verify" / row["baseline_file"]).is_file()
    assert (tmp_path / "verify" / row["constrained_file"]).is_file()


def test_verify_rejects_a_changed_model(tmp_path):
    report = _report(tmp_path)
    (tmp_path / "counter.btor2").write_text(COUNTER.replace("constd 2 10", "constd 2 11"))
    result, code = verify.run(report, tmp_path / "verify", pono=_fake_pono(tmp_path, "VERDICT = 'unsat'\n" + VERIFY_PONO))
    assert code == 1
    assert "SHA-256 mismatch" in result["errors"][0]["error"]


def test_real_pono_gives_matching_verdicts_on_the_examples(tmp_path):
    write_report(analyze(EXAMPLES, tmp_path / "run", GenerationOptions()), tmp_path / "run")
    result, code = verify.run(tmp_path / "run", tmp_path / "verify", timeout=30)
    assert code == 0, result["summary"]
    assert result["summary"]["constrained_solved"] == result["summary"]["baseline_solved"] > 0
