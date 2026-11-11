"""The pipeline: exact property scopes, evidence files, reuse, and rollback.

Every model is read by Pono, which must be on PATH (inside nix-shell)."""

import hashlib
from types import SimpleNamespace

import pytest
import z3

from btor2sieve.implied import Candidate, GenerationOptions, ImpliedDiscovery
import btor2sieve.pipeline as pipeline
from btor2sieve.replay import replay
from btor2sieve.reporting import write_report
from btor2sieve.validation import Validator


# A 3-bit counter with two properties and one environment constraint.
MODEL = """1 sort bitvec 3
2 sort bitvec 1
3 zero 1
4 state 1 word
5 one 1
6 add 1 4 5
7 next 1 4 6
8 constd 1 2
9 eq 2 4 8
10 bad -9
11 init 1 4 3
12 eq 2 4 3
13 bad 12
14 ugte 2 4 5
15 constraint 14
"""
# P: x == y.
EQUIVALENCE = """1 sort bitvec 1
2 sort bitvec 8
3 state 2 x
4 state 2 y
5 eq 1 3 4
6 bad -5
"""
# P: pc <= 15, plus an unrelated state.
PC_MODEL = """1 sort bitvec 10
2 sort bitvec 1
3 state 1 pc
4 constd 1 15
5 ulte 2 3 4
6 bad -5
7 state 1 unrelated
"""



WORD = z3.BitVec("s_4", 3)  # The counter in MODEL, as Pono's variable is renamed.
# MODEL's properties: P10 = (word == 2), P13 = (word != 0).
MODEL_PROPERTIES = {10: WORD == 2, 13: WORD != 0}


def _same_formula(saved: str, expected: z3.BoolRef) -> bool:
    """A stored hypothesis means the same as the expected formula."""
    (formula,) = z3.parse_smt2_string(f"(assert {saved})", decls={"s_4": WORD})
    solver = z3.Solver()
    solver.add(formula != expected)
    return solver.check() == z3.unsat

def make_unknown(monkeypatch, applies=lambda validator: True):
    """Make independent validation return UNKNOWN (where `applies` holds)."""
    original = Validator.check

    def check(self, candidate):
        result = original(self, candidate)
        if applies(self):
            result.status = result.solver_result = "unknown"
            result.reason = "test timeout"
        return result

    monkeypatch.setattr(Validator, "check", check)


# --- What each property scope sees -------------------------------------------

def test_uncapped_search_keeps_native_words_and_ignores_budget_values(tmp_path):
    model = tmp_path / "pc.btor2"
    model.write_text(PC_MODEL)
    out = tmp_path / "native"
    # Budgets are ignored (and reported as null) without matched_budgets.
    report = pipeline.analyze([model], out, GenerationOptions(max_terms=1,
                              max_candidates=1, max_width=1, max_queries=1))
    assert report["errors"] == []
    summary = report["summaries"][0]
    search = summary["search"]
    assert search["kind"] == "property-word-level"
    assert search["complete"] and search["validation_complete"]
    assert search["total_candidates"] == summary["candidates"] > 1
    accepted = [r for r in report["records"] if r["status"] == "accepted"]
    # Here the known mask is equivalent to the native bound; dedup keeps one.
    assert "unsigned_bound" in {r["family"] for r in accepted}
    assert all("s_7" not in r["expression"] for r in report["records"])
    assert all("extract" not in r["expression"] for r in report["records"])
    assert all(report["configuration"][key] is None for key in
               ("max_candidates", "max_terms", "max_width", "max_queries"))
    assert set(summary["families"]) == {
        "unsigned_bound", "signed_bound", "equality", "disequality",
        "implication", "masked_bits", "array",
    }
    for evidence in report["models"][0]["scopes"] + report["records"]:
        content = (out / evidence["obligation"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == evidence["sha256"]
    write_report(report, out)
    result, code = replay(out, accepted_only=True)
    assert code == 0 and result["mismatched"] == 0


def test_untrusted_candidates_are_checked_under_the_property_alone(tmp_path, monkeypatch):
    # Initialization, transitions, and the constraint force x=0, but P only requires x=y.
    text = """1 sort bitvec 8
2 sort bitvec 1
3 zero 1
4 state 1 x
5 state 1 y
6 eq 2 4 5
7 bad -6
8 eq 2 4 3
9 constraint 8
10 init 1 4 3
11 next 1 4 3
"""
    model = tmp_path / "scope.btor2"
    model.write_text(text)

    x, y = z3.BitVec("s_4", 8), z3.BitVec("s_5", 8)

    def propose(hypothesis, options):
        return SimpleNamespace(candidates=[
            Candidate(x == y, "equality", "implied:test", (4, 5)),
            Candidate(x == 0, "equality", "implied:test", (4,)),
        ], statistics={"kind": "property-word-level", "total_candidates": 2,
                       "term_count": 2, "predicate_count": 1, "discovery_queries": 0,
                       "discovery_unknown": 0, "hypothesis_result": "sat",
                       "complete": True, "reason": None})

    monkeypatch.setattr(pipeline, "discover_implied_candidates", propose)
    out = tmp_path / "out"
    report = pipeline.analyze([model], out, GenerationOptions())
    assert not report["errors"]
    # Rejections are resolved checks, so validation is still complete.
    assert [row["status"] for row in report["records"]] == ["accepted", "rejected"]
    summary = report["summaries"][0]
    assert summary["search"]["validation_complete"] and summary["search"]["complete"]
    for row in report["records"]:
        assertions = z3.parse_smt2_file(str(out / row["obligation"]))
        assert len(assertions) == 2  # P and not C, nothing else.
        solver = z3.Solver()
        x, y = z3.BitVecs("s_4 s_5", 8)
        solver.add(z3.Xor(assertions[0], x == y))
        assert solver.check() == z3.unsat


def test_vacuous_property_has_no_accepted_constraint(tmp_path):
    model = tmp_path / "false.btor2"
    model.write_text(EQUIVALENCE.replace("6 bad -5", "6 one 1\n7 bad 6"))
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions())
    assert report["records"] == []
    search = report["summaries"][0]["search"]
    assert search["complete"] and search["hypothesis_result"] == "unsat"
    assert search["total_candidates"] == 0


def test_unrelated_states_are_not_projected_into_candidates(tmp_path):
    model = tmp_path / "arrays.btor2"
    model.write_text("1 sort bitvec 1\n2 sort bitvec 8\n3 sort array 2 2\n"
                     "4 state 3 mem\n5 state 2 wide\n6 zero 1\n7 bad 6\n")
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions(max_width=4))
    assert report["errors"] == []
    assert report["records"] == []
    assert report["configuration"]["max_width"] is None
    assert all("s_4" not in r["expression"] and "s_5" not in r["expression"] for r in report["records"])
    assert report["summaries"][0]["search"]["total_candidates"] == 0
    write_report(report, tmp_path / "out")


def test_property_filter_keeps_only_the_selected_scope(tmp_path):
    model = tmp_path / "model.btor2"
    model.write_text(MODEL)
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions(), property_id=10)
    assert report["errors"] == []
    scopes = report["models"][0]["scopes"]
    assert [(scope["name"], scope["property_id"]) for scope in scopes] == [("property:10", 10)]
    assert _same_formula(scopes[0]["hypothesis"], MODEL_PROPERTIES[10])
    assert [summary["scope"] for summary in report["summaries"]] == ["property:10"]
    assert {row["property_id"] for row in report["records"]} == {10}


def test_unknown_validation_is_never_accepted_or_complete(tmp_path, monkeypatch):
    make_unknown(monkeypatch)
    model = tmp_path / "pc.btor2"
    model.write_text(PC_MODEL)
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions())
    summary = report["summaries"][0]
    assert {row["status"] for row in report["records"]} == {"unknown"}
    assert summary["accepted"] == 0 and summary["unknown"] > 0
    assert not summary["search"]["validation_complete"]
    assert not summary["search"]["complete"]


# --- Cross-property reuse ------------------------------------------------------

def test_reuse_rechecks_facts_under_each_target_property(tmp_path):
    model = tmp_path / "two-properties.btor2"
    model.write_text(EQUIVALENCE + "7 zero 1\n8 bad 7\n")
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions(), reuse=True)
    assert report["errors"] == []
    assert report["configuration"]["scopes"] == ["property"]
    summaries = {s["scope"]: s for s in report["summaries"]}
    assert summaries["property:6"]["accepted"] > 0
    assert summaries["property:8"]["accepted"] == 0
    reused = [row for row in report["records"] if row["reuse_from"]]
    assert reused and all(row["status"] == "rejected" for row in reused)


def test_unknown_during_reuse_marks_only_the_target_incomplete(tmp_path, monkeypatch):
    # Property 8 is "not 0", i.e. true: make only its checks UNKNOWN.
    make_unknown(monkeypatch, lambda validator: z3.is_true(z3.simplify(validator.hypothesis)))
    model = tmp_path / "reuse.btor2"
    model.write_text(EQUIVALENCE + "7 zero 1\n8 bad 7\n")
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions(), reuse=True)
    reused = [row for row in report["records"] if row["reuse_from"]]
    assert reused and {row["status"] for row in reused} == {"unknown"}
    summaries = {summary["scope"]: summary for summary in report["summaries"]}
    assert summaries["property:6"]["search"]["validation_complete"]
    assert not summaries["property:8"]["search"]["validation_complete"]
    assert not summaries["property:8"]["search"]["complete"]


# --- Failures and rollback -------------------------------------------------------

def test_failed_model_rolls_back_all_properties_and_files_and_keeps_next_model(tmp_path, monkeypatch):
    failed = tmp_path / "failed.btor2"
    good = tmp_path / "good.btor2"
    failed.write_text(MODEL)
    good.write_text(MODEL)
    output = tmp_path / "out"
    original = pipeline.discover_implied_candidates
    calls = 0

    def fail_in_second_scope(hypothesis, options):
        nonlocal calls
        calls += 1
        if calls == 2:
            # The first property's records and both hypotheses have been written.
            return ImpliedDiscovery([Candidate(WORD, "equality", "test")], {})  # Not Boolean.
        return original(hypothesis, options)

    monkeypatch.setattr(pipeline, "discover_implied_candidates", fail_in_second_scope)
    options = GenerationOptions(matched_budgets=True, max_candidates=3)
    report = pipeline.analyze([failed, good], output, options)
    assert len(report["errors"]) == 1
    assert report["errors"][0]["model"] == str(failed)
    assert report["errors"][0]["discarded_partial_records"] == 3
    assert [model["id"] for model in report["models"]] == ["m0001"]
    saved_scopes = report["models"][0]["scopes"]
    names = [f"property:{bad}" for bad in MODEL_PROPERTIES]
    assert [scope["name"] for scope in saved_scopes] == names
    assert all(_same_formula(saved["hypothesis"], MODEL_PROPERTIES[saved["property_id"]])
               for saved in saved_scopes)
    assert [summary["scope"] for summary in report["summaries"]] == names
    assert all(row["model_id"] == "m0001" for row in report["records"])
    evidence = saved_scopes + report["records"]
    assert {str(path.relative_to(output)) for path in (output / "obligations").iterdir()} == {
        row["obligation"] for row in evidence
    }
    for row in evidence:
        data = (output / row["obligation"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]


def test_invalid_candidate_rolls_back_the_model(tmp_path, monkeypatch):
    def broken_generator(hypothesis, options):
        return ImpliedDiscovery([
            Candidate(z3.ULE(WORD, 2), "unsigned_bound", "test"),
            Candidate(WORD, "equality", "test"),  # Not Boolean.
        ], {})

    monkeypatch.setattr(pipeline, "discover_implied_candidates", broken_generator)
    model = tmp_path / "model.btor2"
    model.write_text(MODEL)
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions())
    assert len(report["errors"]) == 1
    assert report["models"] == report["records"] == report["summaries"] == []
    assert list((tmp_path / "out" / "obligations").iterdir()) == []


def test_partial_obligation_write_failure_removes_every_model_artifact(tmp_path, monkeypatch):
    model = tmp_path / "model.btor2"
    model.write_text(MODEL)
    output = tmp_path / "out"
    original = type(output).write_bytes

    def fail_second_record(path, data):
        if path.name == "m0000-00002.smt2":
            original(path, data[:10])
            raise OSError("interrupted evidence write")
        return original(path, data)

    monkeypatch.setattr(type(output), "write_bytes", fail_second_record)
    report = pipeline.analyze([model], output, GenerationOptions(matched_budgets=True, max_candidates=3))
    assert report["models"] == report["records"] == report["summaries"] == []
    assert report["errors"] == [{"model": str(model), "error": "interrupted evidence write",
                                  "discarded_partial_records": 1}]
    assert list((output / "obligations").iterdir()) == []


@pytest.mark.parametrize("options", [GenerationOptions(timeout_ms=0),
                                     GenerationOptions(matched_budgets=True, max_queries=0)])
def test_invalid_options_rejected_before_output(tmp_path, options):
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="positive"):
        pipeline.analyze([tmp_path / "unused.btor2"], out, options)
    assert not out.exists()
