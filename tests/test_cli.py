"""The command line: user workflows, option checks, budget profiles, and exit codes."""

import csv
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import z3

from btor2sieve.cli import main
from btor2sieve.implied import FAMILIES
from btor2sieve.replay import replay
from btor2sieve.reporting import render_html
from btor2sieve.validation import Validator


# An 8-bit counter with two properties and one environment constraint.
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
# P: x <= 15.
RANGE_MODEL = "1 sort bitvec 8\n2 sort bitvec 1\n3 state 1 x\n4 constd 1 15\n5 ulte 2 3 4\n6 bad -5\n"
# P: value <= 5 (4-bit).
SMALL_RANGE = "1 sort bitvec 4\n2 sort bitvec 1\n3 state 1 value\n4 constd 1 5\n5 ugt 2 3 4\n6 bad 5\n"
# P: x == y.
EQUIVALENCE = "1 sort bitvec 1\n2 sort bitvec 8\n3 state 2 x\n4 state 2 y\n5 eq 1 3 4\n6 bad -5\n"
BUDGETS = ("max_candidates", "max_terms", "max_width", "max_queries")


def run_cli(*args):
    """Run `python -m btor2sieve` in a fresh process (fresh Z3 state)."""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    return subprocess.run([sys.executable, "-m", "btor2sieve", *map(str, args)],
                          text=True, capture_output=True, env=env, timeout=60)


def write(tmp_path, text, name="model.btor2"):
    model = tmp_path / name
    model.write_text(text)
    return model


# --- End-to-end workflows ---------------------------------------------------------

def test_extract_reports_exact_counts_and_replayable_obligations(tmp_path):
    model = write(tmp_path, MODEL, "counter.btor2")
    out = tmp_path / "report"
    cmd = run_cli("extract", model, "--out", out, "--matched-budgets", "--max-candidates", 30)
    assert cmd.returncode == 0, cmd.stderr
    report = json.loads((out / "results.json").read_text())
    assert len(report["models"]) == 1
    assert report["models"][0]["features"]["properties"] == 2
    rows = report["records"]
    assert any(r["status"] == "accepted" for r in rows)
    assert any(r["status"] == "rejected" for r in rows)
    for summary in report["summaries"]:
        actual = [r for r in rows if r["scope"] == summary["scope"] and not r["reuse_from"]]
        assert len(actual) == summary["candidates"]
        assert sum(summary[k] for k in ("accepted", "rejected", "unknown", "vacuous")) == len(actual)
    assert len(list(csv.DictReader((out / "summary.csv").open()))) == 2
    assert (out / "report.html").exists()
    replay = run_cli("replay", out, "--accepted-only")
    assert replay.returncode == 0, replay.stderr + replay.stdout
    assert json.loads(replay.stdout)["mismatched"] == 0


def test_extract_finds_native_word_equality_and_it_replays(tmp_path):
    model = write(tmp_path, EQUIVALENCE)
    out = tmp_path / "implied"
    completed = run_cli("extract", model, "--out", out)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((out / "results.json").read_text())
    assert report["configuration"]["method"] == "implied"
    assert report["configuration"]["implied_workflow"] == "property-word-level-v1"
    assert report["configuration"]["scopes"] == ["property"]
    assert {row["scope"] for row in report["records"]} == {"property:6"}
    assert all(row["origin"].startswith("implied:") for row in report["records"])
    assert any(row["family"] == "equality" and row["status"] == "accepted"
               and row["expression"] in {"(= s_3 s_4)", "(= s_4 s_3)"}
               for row in report["records"])
    assert not any("extract" in row["expression"] for row in report["records"])
    result, status = replay(out, accepted_only=True)
    assert status == 0, result
    assert result["mismatched"] == 0


def test_inspect_and_batch_record_failures_without_losing_successes(tmp_path):
    good = write(tmp_path, MODEL, "good.btor2")
    bad = write(tmp_path, "1 sort bitvec 0\n", "bad.btor2")
    inspect = run_cli("inspect", good, "--json")
    assert inspect.returncode == 0, inspect.stderr
    assert json.loads(inspect.stdout)["properties"] == 2
    out = tmp_path / "batch"
    batch = run_cli("batch", good, bad, "--out", out, "--matched-budgets", "--max-candidates", 8)
    assert batch.returncode == 1
    report = json.loads((out / "results.json").read_text())
    assert len(report["errors"]) == 1
    assert len(report["models"]) == 1
    assert report["records"]


def test_reuse_is_explicitly_revalidated_and_output_is_html_escaped(tmp_path):
    model = write(tmp_path, MODEL, "<img onerror=alert(1)>.btor2")
    out = tmp_path / "reuse"
    cmd = run_cli("extract", model, "--out", out, "--reuse", "--matched-budgets", "--max-candidates", 30)
    assert cmd.returncode == 0, cmd.stderr
    report = json.loads((out / "results.json").read_text())
    reused = [r for r in report["records"] if r["reuse_from"]]
    assert reused
    assert any(r["status"] == "rejected" for r in reused)
    assert all(r["scope"] != r["reuse_from"] for r in reused)
    assert "<img onerror" not in (out / "report.html").read_text()


@pytest.mark.parametrize("target", ["implication", "hypothesis"])
def test_replay_detects_tampered_evidence(tmp_path, target):
    model = write(tmp_path, MODEL, "counter.btor2")
    out = tmp_path / "report"
    assert run_cli("extract", model, "--out", out, "--matched-budgets", "--max-candidates", 10).returncode == 0
    report = json.loads((out / "results.json").read_text())
    replay = run_cli("replay", out, "--accepted-only")
    # Hypotheses are replayed even with --accepted-only (non-vacuity).
    assert any(c.get("kind") == "hypothesis" for c in json.loads(replay.stdout)["checks"])
    if target == "implication":
        record = next(r for r in report["records"] if r["status"] == "accepted")
        (out / record["obligation"]).write_text("(assert true)\n(check-sat)\n")
    else:
        scope = report["models"][0]["scopes"][0]
        (out / scope["obligation"]).write_text("(assert false)\n(check-sat)\n")
    replay = run_cli("replay", out, "--accepted-only")
    assert replay.returncode == 1
    assert json.loads(replay.stdout)["mismatched"] >= 1


# --- Option checks (always before any output is written) ---------------------------

def test_refuses_existing_output_and_reports_bad_options(tmp_path):
    model = write(tmp_path, MODEL)
    out = tmp_path / "existing"
    out.mkdir()
    sentinel = out / "keep.txt"
    sentinel.write_text("keep me")
    assert run_cli("extract", model, "--out", out).returncode != 0
    assert sentinel.read_text() == "keep me"
    assert run_cli("extract", model, "--out", tmp_path / "new", "--timeout-ms", 0).returncode != 0


@pytest.mark.parametrize("extra, message", [
    (("--method", "word-level"), "invalid choice"),
    (("--syntax-only",), "unrecognized arguments: --syntax-only"),
])
def test_unknown_options_are_rejected(tmp_path, extra, message):
    out = tmp_path / "out"
    result = run_cli("extract", write(tmp_path, EQUIVALENCE), "--out", out, *extra)
    assert result.returncode == 2
    assert message in result.stderr
    assert not out.exists()


@pytest.mark.parametrize("profile", [[], ["--matched-budgets"], ["--unlimited"]])
def test_only_property_scopes_are_accepted(tmp_path, capsys, profile):
    output = tmp_path / "out"
    model = write(tmp_path, RANGE_MODEL)
    assert main(["extract", str(model), "--out", str(output), *profile,
                 "--scopes", "property,model"]) == 2
    assert "supports only property scopes" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("extra", [["--matched-budgets"], ["--max-candidates", "10"],
                                   ["--max-terms", "10"], ["--max-width", "10"], ["--max-queries", "10"]])
def test_unlimited_rejects_conflicting_options(tmp_path, extra):
    with pytest.raises(SystemExit) as error:
        main(["extract", "unused.btor2", "--out", str(tmp_path / "out"), "--unlimited", *extra])
    assert error.value.code == 2
    assert not (tmp_path / "out").exists()


# --- Budget profiles -------------------------------------------------------------------

def test_matched_limits_are_enforced_and_reported(tmp_path, capsys):
    model = write(tmp_path, RANGE_MODEL)
    out = tmp_path / "matched"
    assert main(["extract", str(model), "--matched-budgets", "--out", str(out),
                 "--max-candidates", "3", "--max-terms", "2", "--max-width", "8",
                 "--max-queries", "1", "--timeout-ms", "1000"]) == 0
    report = json.loads((out / "results.json").read_text())
    config = report["configuration"]
    assert config["budget_policy"] == "matched"
    assert config["scopes"] == ["property"]
    assert {k: config[k] for k in BUDGETS} == {
        "max_candidates": 3, "max_terms": 2, "max_width": 8, "max_queries": 1,
    }
    assert config["constraint_families"] == list(FAMILIES)
    assert config["implied_workflow"] == "property-word-level-budgeted-v1"
    assert len(report["records"]) <= 3
    assert {r["family"] for r in report["records"]} <= set(FAMILIES)
    assert set(report["summaries"][0]["families"]) == set(FAMILIES)
    search = report["summaries"][0]["search"]
    assert search["coverage"] == "budgeted"
    assert search["complete"] and search["validation_complete"]
    assert search["discovery_queries"] <= 1
    assert search["discovery_unknown"] == 0
    assert "budgeted search completed" in capsys.readouterr().out
    assert "budgeted search completed" in render_html(report)
    assert "caps are unused" not in " ".join(report["models"][0]["warnings"])


def test_unlimited_reports_null_limits_and_replays(tmp_path):
    model = write(tmp_path, RANGE_MODEL)
    output = tmp_path / "out"
    assert main(["extract", str(model), "--out", str(output), "--unlimited", "--timeout-ms", "1000"]) == 0
    report = json.loads((output / "results.json").read_text())
    config = report["configuration"]
    assert config["budget_policy"] == "unlimited"
    assert config["scopes"] == ["property"]
    assert config["timeout_ms"] == 1000
    assert all(config[key] is None for key in BUDGETS)
    assert config["constraint_families"] == list(FAMILIES)
    assert report["records"]
    assert all(record["family"] in FAMILIES for record in report["records"])
    assert set(report["summaries"][0]["families"]) == set(FAMILIES)
    search = report["summaries"][0]["search"]
    assert search["coverage"] == "finite-cone"
    assert search["budget_exhausted"] == []
    result, code = replay(output, accepted_only=True)
    assert code == 0 and result["mismatched"] == 0


# --- Exit codes -------------------------------------------------------------------------

def test_rejected_proposals_still_count_as_a_complete_search(tmp_path, capsys):
    output = tmp_path / "out"
    assert main(["extract", str(write(tmp_path, SMALL_RANGE)), "--out", str(output)]) == 0
    summary = json.loads((output / "results.json").read_text())["summaries"][0]
    assert summary["rejected"] > 0
    assert summary["search"]["validation_complete"] is True
    assert summary["search"]["complete"] is True
    assert "complete finite template coverage" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["extract", "batch"])
@pytest.mark.parametrize("phase", ["discovery", "validation"])
def test_solver_unknown_exits_1_and_keeps_partial_evidence(tmp_path, monkeypatch, capsys, command, phase):
    output = tmp_path / "out"
    if phase == "discovery":
        actual_check = z3.Solver.check
        # Discovery asks conditional SAT queries; hypothesis and independent
        # validation checks still run in the real solver without assumptions.
        monkeypatch.setattr(z3.Solver, "check", lambda self, *conditions:
                            z3.unknown if conditions else actual_check(self))
        monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: "test timeout")
    else:
        actual_check = Validator.check

        def timeout(self, expr):
            result = actual_check(self, expr)
            result.status = result.solver_result = "unknown"
            result.reason = "test timeout"
            return result

        monkeypatch.setattr(Validator, "check", timeout)

    assert main([command, str(write(tmp_path, SMALL_RANGE)), "--out", str(output)]) == 1
    report = json.loads((output / "results.json").read_text())
    assert not report["errors"]
    assert (output / "report.html").is_file()
    summary = report["summaries"][0]
    assert summary["search"]["complete"] is False
    assert "partial finite template coverage" in capsys.readouterr().out
    if phase == "discovery":
        assert summary["search"]["discovery_unknown"] > 0
        assert "test timeout" in summary["search"]["reason"]
    else:
        assert summary["search"]["validation_complete"] is False
        assert summary["unknown"] > 0
