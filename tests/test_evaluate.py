"""Evaluation discovers local benchmark collections without a fixed corpus list."""

import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL = "1 sort bitvec 1\n2 state 1 flag\n3 bad 2\n"
OUTPUT_DIRECTORIES = {
    "syntax": "word-level/syntax",
    "semantic": "word-level/semantic",
    "implied": "implied-constraints",
}


def run_evaluation(corpus, output, *extra):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/evaluate.py"),
         "--benchmarks", str(corpus), "--out", str(output), "--skip-cvc5",
         "--max-candidates", "2", "--max-terms", "2", "--max-queries", "2", *extra],
        cwd=corpus.parent, text=True, capture_output=True, timeout=60,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
    )


def test_evaluate_includes_nested_and_newly_added_models(tmp_path):
    corpus = tmp_path / "benchmark models"
    nested = corpus / "track" / "family"
    nested.mkdir(parents=True)
    first = nested / "first model.btor2"
    first.write_text(MODEL)
    (corpus / "README.txt").write_text("Not a model")
    # A directory with the suffix must not be passed to the parser.
    (corpus / "directory.btor2").mkdir()

    for index, expected in enumerate(([first], [corpus / "added.btor2", first])):
        if index:
            expected[0].write_text(MODEL)
        output = tmp_path / f"evaluation-{index}"
        completed = run_evaluation(corpus, output)
        assert completed.returncode == 0, completed.stderr
        evaluation = json.loads((output / "evaluation.json").read_text())
        assert evaluation["benchmarks"] == len(expected)
        assert evaluation["input_files"] == [str(p) for p in expected]
        assert list(evaluation["runs"]) == ["semantic", "implied"]
        assert not any((output / mode).exists() for mode in OUTPUT_DIRECTORIES)
        for mode in ("semantic", "implied"):
            run_directory = OUTPUT_DIRECTORIES[mode]
            assert evaluation["runs"][mode]["output_directory"] == run_directory
            report = json.loads((output / run_directory / "results.json").read_text())
            assert [m["path"] for m in report["models"]] == [str(p) for p in expected]
            assert all(m["sha256"] == hashlib.sha256(MODEL.encode()).hexdigest()
                       for m in report["models"])
            assert not report["errors"]
            assert report["configuration"]["scopes"] == ["property"]
            assert report["configuration"]["method"] == ("implied" if mode == "implied" else "word-level")
            assert (output / run_directory / "replay-z3.json").is_file()
        with (output / "comparison.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(expected) * 2
        assert {(row["mode"], row["model"], row["scope"]) for row in rows} == {
            (mode, str(path), "property:3") for mode in ("semantic", "implied") for path in expected
        }
        assert all(int(row["candidates"]) == sum(int(row[status]) for status in
                   ("accepted", "rejected", "unknown", "vacuous")) for row in rows)
        for row in rows:
            assert row["output_directory"] == OUTPUT_DIRECTORIES[row["mode"]]
            assert (output / row["output_directory"] / "report.html").is_file()


def test_default_corpus_covers_collections_relative_to_project_not_cwd(tmp_path):
    project = tmp_path / "project"
    script = project / "scripts" / "evaluate.py"
    script.parent.mkdir(parents=True)
    script.write_bytes((ROOT / "scripts/evaluate.py").read_bytes())
    models = [project / "benchmarks" / collection / "example.btor2"
              for collection in ("hwmcc/2025/bv", "other/2026/arrays")]
    for model in models:
        model.parent.mkdir(parents=True)
        model.write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = subprocess.run(
        [sys.executable, str(script), "--out", str(output), "--skip-cvc5",
         "--max-candidates", "2", "--max-terms", "2", "--max-queries", "2"],
        cwd=tmp_path, text=True, capture_output=True, timeout=60,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
    )
    assert completed.returncode == 0, completed.stderr
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert evaluation["input_files"] == [str(p) for p in models]
    for mode in ("semantic", "implied"):
        report = json.loads((output / OUTPUT_DIRECTORIES[mode] / "results.json").read_text())
        assert [m["path"] for m in report["models"]] == [str(p) for p in models]


@pytest.mark.parametrize("exists", [False, True])
def test_evaluate_rejects_missing_or_empty_corpus_before_creating_output(tmp_path, exists):
    corpus = tmp_path / "models"
    if exists:
        corpus.mkdir()
    output = tmp_path / "evaluation"
    completed = run_evaluation(corpus, output)
    assert completed.returncode == 2
    assert "No .btor2 files" in completed.stderr
    assert not output.exists()


def test_explicit_prior_modes_keep_requested_scopes_and_budgets(tmp_path):
    model = tmp_path / "one.btor2"
    model.write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = run_evaluation(tmp_path, output, "--methods", "syntax", "semantic",
                               "--scopes", "property,model", "--max-width", "4")
    assert completed.returncode == 0, completed.stderr
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert list(evaluation["runs"]) == ["syntax", "semantic"]
    assert not (output / "implied-constraints").exists()
    assert not any((output / mode).exists() for mode in OUTPUT_DIRECTORIES)
    for mode in ("syntax", "semantic"):
        assert evaluation["runs"][mode]["output_directory"] == OUTPUT_DIRECTORIES[mode]
        report = json.loads((output / OUTPUT_DIRECTORIES[mode] / "results.json").read_text())
        assert report["configuration"]["scopes"] == ["property", "model"]
        assert report["configuration"]["max_width"] == 4
        assert report["configuration"]["semantic"] is (mode == "semantic")
    with (output / "comparison.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["output_directory"] for row in rows} == {"word-level/syntax", "word-level/semantic"}


def test_filter_and_limit_select_same_sorted_models_for_both_methods(tmp_path):
    corpus = tmp_path / "models"
    for name in ("bv/z.btor2", "bv/family/a.btor2", "arrays/b.btor2"):
        model = corpus / name
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = run_evaluation(corpus, output, "--filter", "bv/*.btor2", "--limit", "1")
    assert completed.returncode == 0, completed.stderr
    evaluation = json.loads((output / "evaluation.json").read_text())
    expected = str(corpus / "bv/family/a.btor2")
    assert evaluation["input_files"] == [expected]
    assert evaluation["benchmarks"] == 1
    for mode in ("semantic", "implied"):
        report = json.loads((output / OUTPUT_DIRECTORIES[mode] / "results.json").read_text())
        assert [model["path"] for model in report["models"]] == [expected]


@pytest.mark.parametrize("extra", [
    ["--scopes", "property,model"], ["--scopes", "unknown"],
    ["--limit", "0"], ["--max-width", "0"], ["--filter", "missing/*"],
])
def test_invalid_selection_does_not_create_output(tmp_path, extra):
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = run_evaluation(tmp_path, output, *extra)
    assert completed.returncode == 2
    assert not output.exists()


def test_batch_input_errors_preserve_successes_and_continue_next_method(tmp_path):
    good = tmp_path / "good.btor2"
    good.write_text(MODEL)
    bad = tmp_path / "bad.btor2"
    bad.write_text("1 sort bitvec 0\n")
    output = tmp_path / "evaluation"
    completed = run_evaluation(tmp_path, output)
    assert completed.returncode == 1
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert list(evaluation["runs"]) == ["semantic", "implied"]
    for mode, run in evaluation["runs"].items():
        assert run["output_directory"] == OUTPUT_DIRECTORIES[mode]
        assert run["returncode"] == 1
        assert run["models"] == 1
        assert run["errors"][0]["model"] == str(bad)
        assert run["replay"]["z3"]["returncode"] == 1
        assert run["replay"]["z3"]["incomplete_run_errors"] == 1
        assert run["replay"]["z3"]["mismatched"] == 0
        assert run["replay"]["z3"]["checked"] > 0
    with (output / "comparison.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert all(row["model"] == str(good) for row in rows)


@pytest.mark.parametrize("failure", ["extraction", "replay", "malformed-replay"])
def test_subprocess_failure_is_recorded_and_next_method_runs(tmp_path, monkeypatch, failure):
    spec = importlib.util.spec_from_file_location("evaluate", ROOT / "scripts/evaluate.py")
    evaluate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluate)
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    monkeypatch.setattr(sys, "argv", [str(ROOT / "scripts/evaluate.py"),
                        "--benchmarks", str(tmp_path), "--out", str(output), "--skip-cvc5",
                        "--methods", "syntax", "semantic", "--max-candidates", "2",
                        "--max-terms", "2", "--max-queries", "2"])
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    real_run = subprocess.run

    def fail_one_process(command, **kwargs):
        syntax = str(output / "word-level/syntax") in command
        if syntax and command[3] == "batch" and failure == "extraction":
            return subprocess.CompletedProcess(command, 2, "", "synthetic extraction failure")
        if syntax and command[3] == "replay" and failure != "extraction":
            if failure == "malformed-replay":
                return subprocess.CompletedProcess(command, 1, "", "synthetic replay failure")
            completed = real_run(command, **kwargs)
            result = json.loads(completed.stdout)
            result["mismatched"] = 1
            return subprocess.CompletedProcess(command, 1, json.dumps(result), "synthetic replay failure")
        return real_run(command, **kwargs)

    monkeypatch.setattr(evaluate.subprocess, "run", fail_one_process)
    assert evaluate.main() == 1
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert list(evaluation["runs"]) == ["syntax", "semantic"]
    syntax = evaluation["runs"]["syntax"]
    assert syntax["output_directory"] == "word-level/syntax"
    assert not any((output / mode).exists() for mode in OUTPUT_DIRECTORIES)
    if failure == "extraction":
        assert syntax["returncode"] == 2
        assert syntax["errors"]
        assert "synthetic extraction failure" in (output / "word-level/syntax/extract.stderr.txt").read_text()
    else:
        assert syntax["replay"]["z3"]["returncode"] == 1
        assert (output / "word-level/syntax/replay-z3.stderr.txt").read_text() == "synthetic replay failure"
    assert evaluation["runs"]["semantic"]["returncode"] == 0
    assert evaluation["runs"]["semantic"]["replay"]["z3"]["returncode"] == 0
    assert (output / "word-level/semantic/results.json").is_file()
