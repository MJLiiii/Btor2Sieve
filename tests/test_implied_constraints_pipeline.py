"""The paper method has its own vocabulary and the same proof boundary."""

import json

import pytest
import z3

from btor2sieve.btor2 import parse
from btor2sieve.methods.common import GenerationOptions
from btor2sieve.encoding import Encoder
from btor2sieve.pipeline import analyze
from btor2sieve.reporting import write_report
from btor2sieve.replay import replay
from test_cli import run_cli


EQUIVALENCE = """1 sort bitvec 1
2 state 1 a
3 state 1 b
4 xor 1 2 3
5 bad 4
"""


def test_implied_cli_extracts_equivalence_and_replays_its_proofs(tmp_path):
    model = tmp_path / "equivalence.btor2"
    model.write_text(EQUIVALENCE)
    out = tmp_path / "implied"
    completed = run_cli("extract", model, "--method", "implied", "--out", out)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((out / "results.json").read_text())
    assert report["configuration"]["method"] == "implied"
    assert report["configuration"]["scopes"] == ["property"]
    assert {row["scope"] for row in report["records"]} == {"property:5"}
    assert all(row["origin"].startswith("implied:") for row in report["records"])
    equivalences = report["summaries"][0]["equivalences"]
    assert len(equivalences) == 1
    records = {row["id"]: row for row in report["records"]}
    assert len(equivalences[0]["implication_ids"]) == 2
    assert all(records[id_]["status"] == "accepted" for id_ in equivalences[0]["implication_ids"])
    document = (out / "report.html").read_text()
    assert "implied" in document and "Literal equivalences" in document
    result, status = replay(out, accepted_only=True)
    assert status == 0, result
    assert result["mismatched"] == 0


@pytest.mark.parametrize("extra", [("--scopes", "model"), ("--syntax-only",)])
def test_implied_cli_rejects_incompatible_options_before_creating_output(tmp_path, extra):
    model = tmp_path / "model.btor2"
    model.write_text(EQUIVALENCE)
    out = tmp_path / "out"
    result = run_cli("extract", model, "--method", "implied", "--out", out, *extra)
    assert result.returncode == 2
    assert "implied" in result.stderr
    assert "unrecognized arguments" not in result.stderr
    assert not out.exists()


def test_implied_property_proofs_do_not_assume_initial_transition_or_environment(tmp_path):
    text = ("1 sort bitvec 1\n2 zero 1\n3 state 1 a\n4 state 1 b\n"
            "5 xor 1 3 4\n6 bad 2\n7 constraint -5\n"
            "8 init 1 3 2\n9 init 1 4 2\n10 next 1 3 2\n11 next 1 4 2\n")
    model = tmp_path / "unconstrained-property.btor2"
    model.write_text(text)
    report = analyze([model], tmp_path / "out", GenerationOptions(method="implied"), ("property",))
    assert report["errors"] == []
    assert report["records"]
    assert {row["status"] for row in report["records"]} == {"rejected"}
    assert report["summaries"][0]["equivalences"] == []


def test_vacuous_property_has_no_accepted_equivalence(tmp_path):
    model = tmp_path / "false.btor2"
    model.write_text(EQUIVALENCE.replace("5 bad 4", "5 one 1\n6 bad 5"))
    report = analyze([model], tmp_path / "out", GenerationOptions(method="implied"), ("property",))
    assert report["records"]
    assert {row["status"] for row in report["records"]} == {"vacuous"}
    assert report["summaries"][0]["equivalences"] == []


def test_implied_unknown_proofs_never_become_equivalences(tmp_path, monkeypatch):
    import btor2sieve.validation as validation

    original = validation.Validator.check

    def unknown(self, expr):
        result = original(self, expr)
        result.status = "unknown"
        result.solver_result = "unknown"
        result.reason = "test timeout"
        return result

    monkeypatch.setattr(validation.Validator, "check", unknown)
    model = tmp_path / "equivalence.btor2"
    model.write_text(EQUIVALENCE)
    report = analyze([model], tmp_path / "out", GenerationOptions(method="implied"), ("property",))
    assert {row["status"] for row in report["records"]} == {"unknown"}
    assert report["summaries"][0]["equivalences"] == []


def test_implied_multiple_properties_and_reuse_keep_proofs_separate(tmp_path):
    model = tmp_path / "two-properties.btor2"
    model.write_text(EQUIVALENCE + "6 zero 1\n7 bad 6\n")
    report = analyze([model], tmp_path / "out", GenerationOptions(method="implied"), reuse=True)
    assert report["errors"] == []
    assert report["configuration"]["scopes"] == ("property",)
    summaries = {s["scope"]: s for s in report["summaries"]}
    assert len(summaries["property:5"]["equivalences"]) == 1
    assert summaries["property:7"]["accepted"] == 0
    assert summaries["property:7"]["equivalences"] == []
    reused = [row for row in report["records"] if row["reuse_from"]]
    assert reused and all(row["status"] == "rejected" for row in reused)


def test_word_level_method_keeps_default_candidates_and_obligations(tmp_path):
    model = tmp_path / "equivalence.btor2"
    model.write_text(EQUIVALENCE)
    # Fresh processes keep Z3's generated let names independent of previous
    # allocations, so identical SMT artifacts can be compared byte for byte.
    reports = []
    for name, args in (("default", ()), ("explicit", ("--method", "word-level"))):
        out = tmp_path / name
        result = run_cli("extract", model, "--out", out, *args)
        assert result.returncode == 0, result.stderr
        reports.append(json.loads((out / "results.json").read_text()))
    def semantic_rows(report):
        return [{key: value for key, value in row.items() if key != "validation_seconds"}
                for row in report["records"]]
    assert semantic_rows(reports[0]) == semantic_rows(reports[1])
    for record in reports[0]["records"]:
        assert (tmp_path / "default" / record["obligation"]).read_bytes() == (
            tmp_path / "explicit" / record["obligation"]).read_bytes()


def test_implied_reports_excluded_arrays_and_widths(tmp_path):
    model = tmp_path / "arrays.btor2"
    model.write_text("1 sort bitvec 1\n2 sort bitvec 8\n3 sort array 2 2\n"
                     "4 state 3 mem\n5 state 2 wide\n6 zero 1\n7 bad 6\n")
    report = analyze([model], tmp_path / "out",
                     GenerationOptions(method="implied", max_width=4), ("property",))
    assert report["errors"] == []
    warnings = " ".join(report["models"][0]["warnings"]).lower()
    assert "array" in warnings and "width" in warnings and "state bit" in warnings
    assert report["records"] == []
    write_report(report, tmp_path / "out")


@pytest.mark.parametrize("method, scopes", [("unknown", ("property",)), ("implied", ("model",))])
def test_invalid_method_or_scopes_rejected_before_output(tmp_path, method, scopes):
    out = tmp_path / "out"
    with pytest.raises(ValueError):
        analyze([tmp_path / "unused.btor2"], out, GenerationOptions(method=method), scopes)
    assert not out.exists()


def test_extracted_property_constraint_does_not_eliminate_first_bad_state():
    # The paper's downstream rule constrains sources only. Extraction does not
    # authorize imposing a property consequence on the next/terminal state.
    encoder = Encoder(parse("1 sort bitvec 1\n2 zero 1\n3 one 1\n4 state 1 q\n"
                            "5 init 1 4 2\n6 next 1 4 3\n7 bad 4\n"))
    prop = encoder.property(7)
    solver = z3.Solver()
    solver.add(encoder.initial, encoder.transition, prop, z3.Not(encoder.prime(prop)))
    assert solver.check() == z3.sat
