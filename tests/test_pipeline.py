"""Characterize scope composition and atomic model evidence."""

import hashlib

import pytest
import z3

from btor2sieve.btor2 import parse
from btor2sieve.candidates import Candidate, GenerationOptions, generate_candidates, select_scope_candidates
from btor2sieve.encoding import Encoder
import btor2sieve.pipeline as pipeline
from btor2sieve.validation import make_scopes


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


def test_scope_sequence_keeps_transition_first_and_candidate_metadata():
    encoder = Encoder(parse(MODEL))
    options = GenerationOptions(max_candidates=9)
    raw = generate_candidates(encoder, encoder.property(10), [9], options)
    candidates = select_scope_candidates(encoder, raw, options, transition=True)
    word, nxt = encoder.expr(4), encoder.next_states[4]
    expected = [
        (nxt == word + 1, "transition", "next-equation", (7,)),
        (nxt == word, "equality", "transition-stability-guess", (7,)),
        (nxt == 0, "equality", "next-value-guess", (7,)),
        (z3.ULE(nxt, word + 1), "unsigned_bound", "next-bound", (7,)),
        (z3.UGE(word, 2), "unsigned_bound", "semantic:interval", (4,)),
        (z3.ULE(word, 2), "unsigned_bound", "semantic:interval", (4,)),
        (z3.Not(word == 2), "disequality", "syntax:atom", (9,)),
        (word <= 2, "signed_bound", "syntax:constant", (4, 8)),
        (word >= 2, "signed_bound", "syntax:constant", (4, 8)),
    ]
    assert [(c.expr.sexpr(), c.family, c.origin, c.source_nodes) for c in candidates] == [
        (expr.sexpr(), family, origin, sources) for expr, family, origin, sources in expected
    ]


def test_final_filter_removes_raw_array_identities_without_refilling():
    encoder = Encoder(parse("""1 sort bitvec 2
2 sort bitvec 4
3 sort array 1 2
4 input 3 mem
5 input 1 index
6 input 2 data
7 write 3 4 5 6
8 read 2 7 5
"""))
    options = GenerationOptions(semantic=False, max_candidates=1)
    raw = generate_candidates(encoder, z3.BoolVal(True), [8], options)
    assert len(raw) == 1
    assert raw[0].origin == "syntax:array-identity"
    assert z3.is_true(z3.simplify(raw[0].expr))
    assert select_scope_candidates(encoder, raw, options) == []
    # More proposals exist, but the raw budget was already spent on the identity.
    assert len(generate_candidates(encoder, z3.BoolVal(True), [8],
                                   GenerationOptions(semantic=False, max_candidates=2))) == 2


@pytest.mark.parametrize("max_width, count", [(0, 2), (2, 2), (3, 4)])
def test_transition_equations_ignore_width_but_value_guesses_honor_it(max_width, count):
    encoder = Encoder(parse(MODEL))
    options = GenerationOptions(max_width=max_width, max_terms=1, max_candidates=4, semantic=False)
    raw = generate_candidates(encoder, encoder.property(10), [9], options)
    candidates = select_scope_candidates(encoder, raw, options, transition=True)
    candidates = [candidate for candidate in candidates if candidate.source_nodes == (7,)]
    assert len(candidates) == count
    assert [c.origin for c in candidates[:2]] == ["next-equation", "transition-stability-guess"]


def test_scope_selection_preserves_the_supplied_pool_without_transition():
    encoder = Encoder(parse(MODEL))
    options = GenerationOptions(max_candidates=7)
    hypothesis = encoder.property(10)
    raw = generate_candidates(encoder, hypothesis, [9], options)
    assert len(raw) == 7
    assert select_scope_candidates(encoder, raw, options) == raw


def test_failed_model_rolls_back_all_scopes_and_files_and_keeps_next_model(tmp_path, monkeypatch):
    failed = tmp_path / "failed.btor2"
    good = tmp_path / "good.btor2"
    failed.write_text(MODEL)
    good.write_text(MODEL)
    output = tmp_path / "out"
    original = pipeline.generate_candidates
    calls = 0

    def fail_in_fourth_scope(encoder, hypothesis, roots, options):
        nonlocal calls
        calls += 1
        if calls == 4:
            # The first three scopes have already written records and hypotheses.
            return [Candidate(encoder.expr(4), "invalid", "test")]
        return original(encoder, hypothesis, roots, options)

    monkeypatch.setattr(pipeline, "generate_candidates", fail_in_fourth_scope)
    kinds = ("property", "model", "initial", "transition")
    report = pipeline.analyze([failed, good], output, GenerationOptions(max_candidates=3), kinds)
    assert len(report["errors"]) == 1
    assert report["errors"][0]["model"] == str(failed)
    assert report["errors"][0]["discarded_partial_records"] == 9
    assert [model["id"] for model in report["models"]] == ["m0001"]
    expected_scopes = make_scopes(Encoder(parse(MODEL)), kinds)
    saved_scopes = report["models"][0]["scopes"]
    assert [scope["name"] for scope in saved_scopes] == [scope.name for scope in expected_scopes]
    assert [scope["hypothesis"] for scope in saved_scopes] == [scope.hypothesis.sexpr() for scope in expected_scopes]
    assert [summary["scope"] for summary in report["summaries"]] == [scope.name for scope in expected_scopes]
    assert all(row["model_id"] == "m0001" for row in report["records"])
    evidence = saved_scopes + report["records"]
    assert {str(path.relative_to(output)) for path in (output / "obligations").iterdir()} == {
        row["obligation"] for row in evidence
    }
    for row in evidence:
        data = (output / row["obligation"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]


def test_scope_selection_does_not_generate_more_candidates(monkeypatch):
    import btor2sieve.candidates as candidates

    encoder = Encoder(parse(MODEL))
    options = GenerationOptions(max_candidates=1)
    raw = [Candidate(encoder.expr(4) == 2, "equality", "test", (4,))]

    def unexpected_generation(*args, **kwargs):
        raise AssertionError("selection must use the supplied pool")

    monkeypatch.setattr(candidates, "generate_candidates", unexpected_generation)
    assert select_scope_candidates(encoder, raw, options) == raw


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
    report = pipeline.analyze([model], output, GenerationOptions(max_candidates=3))
    assert report["models"] == report["records"] == report["summaries"] == []
    assert report["errors"] == [{"model": str(model), "error": "interrupted evidence write",
                                  "discarded_partial_records": 1}]
    assert list((output / "obligations").iterdir()) == []


def test_property_filter_keeps_requested_scope_order_and_exact_contexts(tmp_path):
    model = tmp_path / "model.btor2"
    model.write_text(MODEL)
    encoder = Encoder(parse(MODEL))
    kinds = ("transition", "property", "model", "property", "initial")
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions(max_candidates=2),
                              kinds, property_id=10)
    assert report["errors"] == []
    expected = [
        ("transition", None, z3.And(encoder.transition, encoder.assumptions)),
        ("property:10", 10, encoder.property(10)),
        ("model", None, encoder.assumptions),
        ("initial", None, z3.And(encoder.initial, encoder.assumptions)),
    ]
    scopes = report["models"][0]["scopes"]
    assert [(scope["name"], scope["property_id"], scope["hypothesis"]) for scope in scopes] == [
        (name, property_id, hypothesis.sexpr()) for name, property_id, hypothesis in expected
    ]
    assert [summary["scope"] for summary in report["summaries"]] == [item[0] for item in expected]
    assert {row["property_id"] for row in report["records"] if row["scope"].startswith("property:")} == {10}
