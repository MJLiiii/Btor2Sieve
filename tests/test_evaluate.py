"""Evaluation discovers local benchmark collections without a fixed corpus list."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL = "1 sort bitvec 1\n2 input 1 flag\n3 bad 2\n"


def run_evaluation(corpus, output):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/evaluate.py"),
         "--benchmarks", str(corpus), "--out", str(output), "--skip-cvc5",
         "--max-candidates", "2", "--max-terms", "2", "--max-queries", "2"],
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
        for mode in ("syntax", "semantic"):
            report = json.loads((output / mode / "results.json").read_text())
            assert [m["path"] for m in report["models"]] == [str(p) for p in expected]
            assert all(m["sha256"] == hashlib.sha256(MODEL.encode()).hexdigest()
                       for m in report["models"])
            assert not report["errors"]
            assert (output / mode / "replay-z3.json").is_file()


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
    for mode in ("syntax", "semantic"):
        report = json.loads((output / mode / "results.json").read_text())
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
