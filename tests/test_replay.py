"""Public replay operation and report evidence integrity."""

import json
from importlib.metadata import version

import pytest

from btor2sieve.candidates import GenerationOptions
from btor2sieve.pipeline import analyze
from btor2sieve.replay import replay


MODEL = """1 sort bitvec 1
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
12 eq 1 5 3
13 bad 12 nonzero
14 ult 1 5 4
15 constraint 14 environment
"""


@pytest.fixture
def report_files(tmp_path):
    model = tmp_path / "counter.btor2"
    model.write_text(MODEL)
    output = tmp_path / "report"
    report = analyze([model], output, GenerationOptions(semantic=False, max_candidates=12))
    assert not report["errors"]
    (output / "results.json").write_text(json.dumps(report))
    return output, report


@pytest.mark.parametrize("text,status,code", [
    ("; expected unsat\n(assert true)\n(check-sat)\n", "sat", 0),
    ("(assert false)\n(check-sat)\n", "unsat", 0),
    ("not SMT-LIB", "error", 1),
])
def test_standalone_smt_returns_solver_result(tmp_path, text, status, code):
    path = tmp_path / "obligation.smt2"
    path.write_text(text)
    result, exit_code = replay(path)
    assert exit_code == code
    assert result["status"] == status
    assert result["duration_seconds"] >= 0
    assert set(result) == {"status", "duration_seconds", "reason"}


@pytest.mark.parametrize("manifest_input", [False, True])
def test_generated_report_replays_from_directory_or_manifest(report_files, manifest_input):
    output, report = report_files
    path = output / "results.json" if manifest_input else output
    result, code = replay(path, timeout_ms=3210)
    assert code == 0
    assert result["backend"] == "z3"
    assert result["solver_version"] == version("z3-solver")
    assert result["solver_options"] == {"timeout": 3210, "random_seed": 0}
    assert result["mismatched"] == result["incomplete_run_errors"] == 0
    assert result["checked"] == len(report["records"]) + 3
    assert {row["kind"] for row in result["checks"]} == {"implication", "hypothesis"}
    assert all(row["matches"] and row["status"] == row["expected"] for row in result["checks"])


def test_accepted_only_skips_rejected_obligations_but_checks_every_hypothesis(report_files):
    output, report = report_files
    accepted = {row["id"] for row in report["records"] if row["status"] == "accepted"}
    rejected = [row for row in report["records"] if row["status"] == "rejected"]
    assert accepted and rejected
    for row in rejected:
        (output / row["obligation"]).unlink()
    result, code = replay(output, accepted_only=True)
    assert code == 0
    assert {row["id"] for row in result["checks"] if row["kind"] == "implication"} == accepted
    assert {row["id"] for row in result["checks"] if row["kind"] == "hypothesis"} == {
        "m0000:property:11:hypothesis", "m0000:property:13:hypothesis", "m0000:model:hypothesis",
    }


def test_accepted_only_replays_hypotheses_when_no_implication_is_accepted(report_files):
    output, report = report_files
    for row in report["records"]:
        row["status"] = "rejected"
    (output / "results.json").write_text(json.dumps(report))
    result, code = replay(output, accepted_only=True)
    assert code == 0
    assert result["checked"] == 3
    assert all(row["kind"] == "hypothesis" for row in result["checks"])


def test_missing_and_tampered_obligations_are_reported_without_losing_other_checks(report_files):
    output, report = report_files
    missing, tampered = report["records"][:2]
    (output / missing["obligation"]).unlink()
    (output / tampered["obligation"]).write_text("(assert true)\n(check-sat)\n")
    result, code = replay(output)
    checks = {row["id"]: row for row in result["checks"]}
    assert code == 1
    assert result["mismatched"] == 2
    assert checks[missing["id"]]["status"] == checks[tampered["id"]]["status"] == "error"
    assert "No such file" in checks[missing["id"]]["reason"]
    assert checks[tampered["id"]]["reason"] == "obligation SHA-256 mismatch"
    assert result["checked"] == len(report["records"]) + 3


@pytest.mark.parametrize("symlink", [False, True])
def test_obligation_cannot_escape_report_directory(report_files, symlink):
    output, report = report_files
    row = report["records"][0]
    original = output / row["obligation"]
    external = output.parent / "external.smt2"
    external.write_bytes(original.read_bytes())
    if symlink:
        original.unlink()
        original.symlink_to(external)
    else:
        row["obligation"] = "../external.smt2"
        (output / "results.json").write_text(json.dumps(report))
    result, code = replay(output)
    check = next(check for check in result["checks"] if check["id"] == row["id"])
    assert code == 1
    assert result["mismatched"] == 1
    assert check["status"] == "error"
    assert check["reason"] == "obligation path escapes report directory"


def test_solver_result_disagreement_is_a_mismatch(report_files):
    output, report = report_files
    row = report["records"][0]
    row["solver_result"] = "sat" if row["solver_result"] == "unsat" else "unsat"
    (output / "results.json").write_text(json.dumps(report))
    result, code = replay(output)
    check = next(check for check in result["checks"] if check["id"] == row["id"])
    assert code == 1
    assert result["mismatched"] == 1
    assert not check["matches"]
    assert check["status"] != check["expected"]


def test_empty_report_is_not_success(tmp_path):
    manifest = tmp_path / "results.json"
    manifest.write_text(json.dumps({"records": [], "models": [], "errors": []}))
    result, code = replay(manifest)
    assert code == 1
    assert result["checked"] == result["mismatched"] == 0
    assert result["checks"] == []


def test_partial_report_fails_even_when_all_available_obligations_match(report_files):
    output, report = report_files
    report["errors"].append({"model": "missing.btor2", "error": "input missing"})
    (output / "results.json").write_text(json.dumps(report))
    result, code = replay(output)
    assert code == 1
    assert result["incomplete_run_errors"] == 1
    assert result["mismatched"] == 0
    assert result["checked"] > 0


def test_unreadable_or_malformed_manifest_errors_propagate(tmp_path):
    manifest = tmp_path / "results.json"
    with pytest.raises(FileNotFoundError):
        replay(manifest)
    manifest.write_text("not JSON")
    with pytest.raises(ValueError):
        replay(manifest)


def test_optional_cvc5_report_backend_preserves_metadata(report_files):
    pytest.importorskip("cvc5")
    output, _ = report_files
    result, code = replay(output, backend="cvc5", timeout_ms=2345, accepted_only=True)
    assert code == 0
    assert result["backend"] == "cvc5"
    assert result["solver_version"] == version("cvc5")
    assert result["solver_options"] == {"tlimit-per": 2345, "arrays-exp": True, "produce-models": True}
    assert result["mismatched"] == 0
