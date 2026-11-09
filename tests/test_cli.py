"""End-to-end user workflows and report/evidence consistency."""

import csv
import json
import os
from pathlib import Path
import subprocess
import sys


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


def run_cli(*args):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    return subprocess.run([sys.executable, "-m", "btor2sieve", *map(str, args)],
                          text=True, capture_output=True, env=env, timeout=60)


def test_extract_reports_exact_counts_and_replayable_obligations(tmp_path):
    model = tmp_path / "counter.btor2"
    model.write_text(MODEL)
    out = tmp_path / "report"
    cmd = run_cli("extract", model, "--out", out, "--scopes", "property,model,initial,transition", "--max-candidates", 30)
    assert cmd.returncode == 0, cmd.stderr
    report = json.loads((out / "results.json").read_text())
    assert len(report["models"]) == 1
    assert report["models"][0]["features"]["properties"] == 2
    rows = report["records"]
    assert rows
    assert any(r["status"] == "accepted" for r in rows)
    assert any(r["status"] == "rejected" for r in rows)
    for summary in report["summaries"]:
        actual = [r for r in rows if r["scope"] == summary["scope"] and not r["reuse_from"]]
        assert len(actual) == summary["candidates"]
        assert sum(summary[k] for k in ("accepted", "rejected", "unknown", "vacuous")) == len(actual)
    assert len(list(csv.DictReader((out / "summary.csv").open()))) == 5
    assert (out / "report.html").exists()
    replay = run_cli("replay", out, "--accepted-only")
    assert replay.returncode == 0, replay.stderr + replay.stdout
    assert json.loads(replay.stdout)["mismatched"] == 0


def test_property_scope_does_not_silently_assume_environment(tmp_path):
    from btor2sieve.btor2 import parse
    from btor2sieve.encoding import Encoder
    from btor2sieve.validation import make_scopes, Validator

    enc = Encoder(parse(MODEL))
    scopes = {s.name: s for s in make_scopes(enc)}
    env = enc.bool_expr(14)
    assert Validator(scopes["model"].hypothesis).check(env).status == "accepted"
    assert Validator(scopes["property:13"].hypothesis).check(env).status == "rejected"


def test_inspect_and_batch_record_failures_without_losing_successes(tmp_path):
    good = tmp_path / "good.btor2"
    good.write_text(MODEL)
    bad = tmp_path / "bad.btor2"
    bad.write_text("1 sort bitvec 0\n")
    inspect = run_cli("inspect", good, "--json")
    assert inspect.returncode == 0, inspect.stderr
    assert json.loads(inspect.stdout)["properties"] == 2
    out = tmp_path / "batch"
    batch = run_cli("batch", good, bad, "--out", out, "--syntax-only", "--max-candidates", 8)
    assert batch.returncode == 1
    report = json.loads((out / "results.json").read_text())
    assert len(report["errors"]) == 1
    assert len(report["models"]) == 1
    assert report["records"]


def test_refuses_existing_output_and_reports_bad_options(tmp_path):
    model = tmp_path / "model.btor2"
    model.write_text(MODEL)
    out = tmp_path / "existing"
    out.mkdir()
    sentinel = out / "keep.txt"
    sentinel.write_text("keep me")
    assert run_cli("extract", model, "--out", out).returncode != 0
    assert sentinel.read_text() == "keep me"
    assert run_cli("extract", model, "--out", tmp_path / "new", "--timeout-ms", 0).returncode != 0


def test_reuse_is_explicitly_revalidated_and_output_is_html_escaped(tmp_path):
    model = tmp_path / "<img onerror=alert(1)>.btor2"
    model.write_text(MODEL)
    out = tmp_path / "reuse"
    cmd = run_cli("extract", model, "--out", out, "--reuse", "--max-candidates", 30)
    assert cmd.returncode == 0, cmd.stderr
    report = json.loads((out / "results.json").read_text())
    reused = [r for r in report["records"] if r["reuse_from"]]
    assert reused
    assert any(r["status"] == "rejected" for r in reused)
    assert all(r["scope"] != r["reuse_from"] for r in reused)
    assert "<img onerror" not in (out / "report.html").read_text()


def test_tampered_proof_is_detected_by_replay(tmp_path):
    model = tmp_path / "counter.btor2"
    model.write_text(MODEL)
    out = tmp_path / "report"
    assert run_cli("extract", model, "--out", out, "--max-candidates", 10).returncode == 0
    report = json.loads((out / "results.json").read_text())
    record = next(r for r in report["records"] if r["status"] == "accepted")
    (out / record["obligation"]).write_text("(assert true)\n(check-sat)\n")
    replay = run_cli("replay", out, "--accepted-only")
    assert replay.returncode == 1
    assert json.loads(replay.stdout)["mismatched"] >= 1


def test_replay_checks_nonvacuity_and_detects_tampered_hypothesis(tmp_path):
    model = tmp_path / "counter.btor2"
    model.write_text(MODEL)
    out = tmp_path / "report"
    assert run_cli("extract", model, "--out", out, "--max-candidates", 10).returncode == 0
    report = json.loads((out / "results.json").read_text())
    scope = report["models"][0]["scopes"][0]
    replay = run_cli("replay", out, "--accepted-only")
    assert any(c.get("kind") == "hypothesis" for c in json.loads(replay.stdout)["checks"])
    (out / scope["obligation"]).write_text("(assert false)\n(check-sat)\n")
    replay = run_cli("replay", out, "--accepted-only")
    assert replay.returncode == 1
    assert json.loads(replay.stdout)["mismatched"] >= 1


def test_failed_model_does_not_leave_inconsistent_partial_counts(tmp_path, monkeypatch):
    import z3
    from btor2sieve.methods.common import Candidate, GenerationOptions
    import btor2sieve.pipeline as pipeline

    model = tmp_path / "counter.btor2"
    model.write_text(MODEL)
    def broken_generator(enc, hypothesis, roots, options):
        return [Candidate(z3.ULE(enc.states[5], 10), "bound", "test"),
                Candidate(enc.states[5], "invalid", "test")]
    monkeypatch.setattr(pipeline, "generate_candidates", broken_generator)
    report = pipeline.analyze([model], tmp_path / "out", GenerationOptions())
    assert len(report["errors"]) == 1
    assert report["models"] == report["records"] == report["summaries"] == []
    assert list((tmp_path / "out" / "obligations").iterdir()) == []
