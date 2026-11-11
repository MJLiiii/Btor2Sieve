"""scripts/evaluate.py end to end: model selection, settings, results, and failures."""

from collections import Counter
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
RUN_DIRECTORY = "implied-constraints"
LIMITS = ("max_candidates", "max_terms", "max_width", "max_queries")
FAMILIES = {"unsigned_bound", "signed_bound", "equality", "disequality", "implication", "masked_bits", "array"}
# Fast settings: one worker and tiny matched budgets.
MATCHED = ("--jobs", "1", "--budget-policy", "matched",
           "--max-candidates", "2", "--max-terms", "2", "--max-queries", "2")
# Runs a real extraction, then marks the second benchmark's search incomplete
# when requested.
INJECT_SEARCH = """import json, pathlib, subprocess, sys
search_complete, validation_complete = (flag == "True" for flag in sys.argv[1:3])
command = sys.argv[3:]
code = subprocess.run(command).returncode
out = pathlib.Path(command[command.index("--out") + 1])
report = json.loads((out / "results.json").read_text())
report["configuration"]["implied_workflow"] = "property-word-level-v1"
first = out.name == "m0000"
for summary in report["summaries"]:
    summary["search"] = {
        "kind": "property-word-level", "term_count": 3, "predicate_count": 1,
        "total_candidates": summary["candidates"], "discovery_queries": 3,
        "discovery_unknown": 0 if search_complete or first else 1,
        "complete": search_complete or first,
        "validation_complete": validation_complete or first,
        "hypothesis_result": "sat",
        "reason": None if search_complete or first else "timeout",
    }
(out / "results.json").write_text(json.dumps(report))
sys.exit(code)
"""
# Replays for real, then reports one mismatch.
MISMATCHED_REPLAY = """import json, subprocess, sys
completed = subprocess.run(sys.argv[1:], capture_output=True, text=True)
result = json.loads(completed.stdout)
result["mismatched"] = 1
print(json.dumps(result))
sys.stderr.write("synthetic replay failure")
sys.exit(1)
"""
BV = "1 sort bitvec 1\n2 sort bitvec 4\n3 state 2 x\n4 constd 2 5\n5 ulte 1 3 4\n6 bad -5\n"
ARRAY = """1 sort bitvec 1
2 sort bitvec 2
3 sort bitvec 8
4 sort array 2 3
5 state 4 mem
6 input 2 addr
7 read 3 5 6
8 constd 3 42
9 eq 1 7 8
10 bad -9
11 constd 3 7
12 eq 1 7 11
13 bad -12
"""


def evaluate(corpus, output, *args, cwd=ROOT):
    """Run scripts/evaluate.py in a subprocess with Z3-only replay and 512 MiB per benchmark."""
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/evaluate.py"), "--benchmarks", str(corpus),
         "--out", str(output), "--skip-cvc5", "--memory-limit-mib", "512", *args],
        cwd=cwd, text=True, capture_output=True, timeout=90,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
    )


def run_evaluation(corpus, output, *extra):
    """A fast matched-budget evaluation, run from outside the project directory."""
    return evaluate(corpus, output, *MATCHED, *extra, cwd=corpus.parent)


def load_evaluate(monkeypatch):
    """Import the script in-process; it loads its runner from scripts/."""
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("evaluate", ROOT / "scripts/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_corpus(tmp_path):
    """Two models with the same filename in different tracks (and a space in the path)."""
    corpus = tmp_path / "corpus with spaces"
    files = [corpus / track / "same.btor2" for track in ("array", "bv")]
    for file, text in zip(files, (ARRAY, BV)):
        file.parent.mkdir(parents=True)
        file.write_text(text)
    return corpus, files


def load_results(output):
    evaluation = json.loads((output / "evaluation.json").read_text())
    report = json.loads((output / RUN_DIRECTORY / "results.json").read_text())
    with (output / "comparison.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    return evaluation, report, rows


# --- Selecting models -------------------------------------------------------------------

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
        evaluation, report, rows = load_results(output)
        assert evaluation["benchmarks"] == len(expected)
        assert evaluation["input_files"] == [str(p) for p in expected]
        assert list(evaluation["runs"]) == ["implied"]
        run = evaluation["runs"]["implied"]
        assert run["output_directory"] == RUN_DIRECTORY
        assert [m["path"] for m in report["models"]] == [str(p) for p in expected]
        assert all(m["sha256"] == hashlib.sha256(MODEL.encode()).hexdigest() for m in report["models"])
        assert not report["errors"]
        configuration = report["configuration"]
        assert configuration["scopes"] == ["property"] and configuration["method"] == "implied"
        assert configuration["matched_budgets"] is True
        assert configuration["max_candidates"] == configuration["max_queries"] == 2
        assert (output / RUN_DIRECTORY / "replay-z3.json").is_file()
        search = run["search"]
        assert search["complete"] and search["validation_complete"]
        assert search["total_candidates"] == run["candidates"]
        assert search["term_count"] > 0
        assert run["workflow"] == "property-word-level-budgeted-v1"
        stdouts = [path.read_text() for path in
                   (output / RUN_DIRECTORY / "models").glob("*/extract.stdout.txt")]
        assert len(stdouts) == len(expected)
        assert all("Implied search:" in stdout and "budgeted" in stdout for stdout in stdouts)
        assert {(row["mode"], row["model"], row["scope"]) for row in rows} == {
            ("implied", str(path), "property:3") for path in expected
        }
        assert all(int(row["candidates"]) == sum(int(row[status]) for status in
                   ("accepted", "rejected", "unknown", "vacuous")) for row in rows)
        assert all(row["output_directory"] == RUN_DIRECTORY for row in rows)
        assert (output / RUN_DIRECTORY / "report.html").is_file()


def test_default_corpus_is_relative_to_the_project_not_the_cwd(tmp_path):
    project = tmp_path / "project"
    script = project / "scripts" / "evaluate.py"
    script.parent.mkdir(parents=True)
    for name in ("evaluate.py", "parallel_evaluate.py"):
        (script.parent / name).write_bytes((ROOT / "scripts" / name).read_bytes())
    models = [project / "benchmarks" / collection / "example.btor2"
              for collection in ("hwmcc/2025/bv", "other/2026/arrays")]
    for model in models:
        model.parent.mkdir(parents=True)
        model.write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = subprocess.run(
        [sys.executable, str(script), "--out", str(output), "--skip-cvc5",
         "--memory-limit-mib", "512", *MATCHED],
        cwd=tmp_path, text=True, capture_output=True, timeout=60,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
    )
    assert completed.returncode == 0, completed.stderr
    evaluation, report, _ = load_results(output)
    assert evaluation["input_files"] == [str(p) for p in models]
    assert [m["path"] for m in report["models"]] == [str(p) for p in models]


def test_filter_and_limit_select_the_same_sorted_models(tmp_path):
    corpus = tmp_path / "models"
    for name in ("bv/z.btor2", "bv/family/a.btor2", "arrays/b.btor2"):
        model = corpus / name
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = run_evaluation(corpus, output, "--filter", "bv/*.btor2", "--limit", "1")
    assert completed.returncode == 0, completed.stderr
    evaluation, report, _ = load_results(output)
    expected = str(corpus / "bv/family/a.btor2")
    assert evaluation["input_files"] == [expected]
    assert evaluation["benchmarks"] == 1
    assert [model["path"] for model in report["models"]] == [expected]


# --- Invalid arguments (rejected before any output is created) ------------------------

@pytest.mark.parametrize("exists", [False, True])
def test_missing_or_empty_corpus_is_rejected(tmp_path, exists):
    corpus = tmp_path / "models"
    if exists:
        corpus.mkdir()
    output = tmp_path / "evaluation"
    completed = run_evaluation(corpus, output)
    assert completed.returncode == 2
    assert "No .btor2 files" in completed.stderr
    assert not output.exists()


@pytest.mark.parametrize("extra, message", [
    (["--methods", "word-level"], "invalid choice"),
    (["--scopes", "property,model"], "--scopes property"),
    (["--scopes", "unknown"], "--scopes property"),
    (["--limit", "0"], "--limit must be positive"),
    (["--max-width", "0"], "must be positive"),
    (["--filter", "missing/*"], "No .btor2 files"),
    (["--budget-policy", "unlimited"], "unlimited"),  # MATCHED already sets --max-* limits.
    (["--jobs", "0"], "--jobs"),
    (["--jobs", "many"], "--jobs"),
    (["--jobs", "1", "--memory-limit-mib", str(1 << 40)], "memory"),
    (["--jobs", "100000", "--memory-limit-mib", "1"], "usable CPUs"),
    (["--memory-limit-mib", "0"], "--memory-limit-mib must be positive"),
    (["--cpu-limit-s", "0"], "--cpu-limit-s must be positive"),
    (["--wall-limit-s", "-1"], "--wall-limit-s must be positive"),
])
def test_invalid_arguments_do_not_create_output(tmp_path, extra, message):
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    completed = run_evaluation(tmp_path, output, *extra)
    assert completed.returncode == 2
    assert message in completed.stderr
    assert not output.exists()


def test_defaults_are_unlimited_with_4_gib_300_s_cpu_600_s_wall_and_automatic_jobs():
    spec = importlib.util.spec_from_file_location("evaluate", ROOT / "scripts/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module._parser().parse_args(["--out", "unused"])
    assert (args.memory_limit_mib, args.cpu_limit_s, args.wall_limit_s) == (4096, 300, 600)
    assert args.jobs == "auto"
    assert (args.timeout_ms, args.budget_policy) == (1000, "unlimited")


# --- Budget policies and recorded settings ------------------------------------------------

def test_default_unlimited_policy_exceeds_old_caps_and_records_null_limits(tmp_path):
    # A sum of 14 inputs: far more terms, proposals, and queries than the old caps.
    lines = ["1 sort bitvec 1", "2 sort bitvec 8"]
    lines += [f"{node} input 2 word{node}" for node in range(3, 17)]
    total = 3
    for node, word in enumerate(range(4, 17), 17):
        lines.append(f"{node} add 2 {total} {word}")
        total = node
    lines += ["30 constd 2 100", f"31 ulte 1 {total} 30", "32 bad -31"]
    (tmp_path / "many-terms.btor2").write_text("\n".join(lines) + "\n")
    output = tmp_path / "out"
    completed = evaluate(tmp_path, output, "--jobs", "1")
    assert completed.returncode == 0, completed.stderr + completed.stdout
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert evaluation["configuration"]["budget_policy"] == "unlimited"
    assert all(evaluation["configuration"][key] is None for key in LIMITS)
    run = evaluation["runs"]["implied"]
    settings = run["effective_settings"]
    assert settings["budget_policy"] == "unlimited"
    assert all(settings[key] is None for key in LIMITS)
    assert settings["timeout_ms"] == 1000 and settings["jobs"] == 1
    assert settings["scopes"] == ["property"]
    assert set(settings["constraint_families"]) == FAMILIES
    assert run["candidates"] > 80
    assert run["replay"]["z3"]["mismatched"] == 0
    status = json.loads((output / RUN_DIRECTORY / "run-status.json").read_text())
    commands = [row["command"] for row in status["models"]]
    assert all("--unlimited" in command for command in commands)
    assert all(not any(f"--{key.replace('_', '-')}" in command for key in LIMITS)
               for command in commands)
    assert run["search"]["term_count"] > 12
    assert run["search"]["discovery_queries"] > 96
    assert run["search"]["coverage"] == "finite-cone"
    assert run["search"]["budget_exhausted"] == {}


def test_matched_settings_are_applied_and_record_budgeted_coverage(tmp_path):
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    result = run_evaluation(tmp_path, output, "--max-candidates", "1", "--max-queries", "1",
                            "--max-width", "4")
    assert result.returncode == 0, result.stderr + result.stdout
    run = json.loads((output / "evaluation.json").read_text())["runs"]["implied"]
    settings = run["effective_settings"]
    assert settings["jobs"] == 1
    assert settings["timeout_ms"] == 1000
    assert settings["max_candidates"] == settings["max_queries"] == 1
    assert settings["max_width"] == 4
    assert settings["budget_policy"] == "matched"
    assert settings["scopes"] == ["property"]
    assert settings["reuse"] is True and settings["max_reuse"] == 30
    assert settings["replay_timeout_ms"] == 5000
    assert settings["replay_backends"] == ["z3"]
    assert set(settings["constraint_families"]) == FAMILIES
    status = json.loads((output / RUN_DIRECTORY / "run-status.json").read_text())
    assert all("--matched-budgets" in row["command"] for row in status["models"])
    assert run["search"]["coverage"] == "budgeted"
    assert run["search"]["complete"]
    assert run["search"]["discovery_unknown"] == 0
    assert run["search"]["discovery_queries"] <= 1
    assert run["candidates"] <= 1
    assert run["search"]["budget_exhausted"]["max_queries"] == 1


def test_method_defaults_policy_keeps_the_uncapped_extractor(tmp_path):
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    result = run_evaluation(tmp_path, output, "--budget-policy", "method-defaults")
    assert result.returncode == 0, result.stderr
    evaluation, report, _ = load_results(output)
    run = evaluation["runs"]["implied"]
    assert not report["configuration"]["matched_budgets"]
    assert run["effective_settings"]["budget_policy"] == "method-defaults"
    assert run["effective_settings"]["max_queries"] is None
    assert run["workflow"] == "property-word-level-v1"
    assert run["search"]["coverage"] == "finite-cone"


def test_resource_limits_and_usage_are_recorded(tmp_path):
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "out"
    result = evaluate(tmp_path, output, "--cpu-limit-s", "60", "--wall-limit-s", "120")
    assert result.returncode == 0, result.stderr
    evaluation, _, rows = load_results(output)
    run = evaluation["runs"]["implied"]
    settings = run["effective_settings"]
    assert (settings["memory_limit_mib"], settings["cpu_limit_s"], settings["wall_limit_s"]) == (512, 60, 120)
    assert run["outcomes"] == {"completed": 1}
    status = json.loads((output / RUN_DIRECTORY / "run-status.json").read_text())
    assert status["limits"] == {"memory_limit_mib": 512, "cpu_limit_s": 60, "wall_limit_s": 120}
    assert {row["mode"] for row in rows} == {"implied"}
    assert all(row["outcome"] == "completed" and float(row["cpu_seconds"]) > 0
               and float(row["wall_seconds"]) > 0 and float(row["peak_memory_mib"]) > 1 for row in rows)


def test_default_worker_count_fits_the_memory_limit(tmp_path):
    corpus, _ = make_corpus(tmp_path)
    output = tmp_path / "default"
    result = evaluate(corpus, output)
    assert result.returncode == 0, result.stderr
    evaluation = json.loads((output / "evaluation.json").read_text())
    configuration = evaluation["configuration"]
    # Every worker must be able to hold its full 512 MiB limit at the same time.
    expected = min(16, len(os.sched_getaffinity(0)), configuration["memory_available_bytes"] // (512 << 20))
    assert configuration["requested_jobs"] == "auto"
    assert configuration["jobs"] == expected >= 1
    run = evaluation["runs"]["implied"]
    assert run["jobs"] == run["effective_settings"]["jobs"] == expected
    assert json.loads((output / RUN_DIRECTORY / "run-status.json").read_text())["jobs"] == expected


# --- Parallel results and aggregation -------------------------------------------------------

def counts(report):
    return Counter((r["model"], r["scope"], r["family"], r["status"], r["reuse_from"])
                   for r in report["records"])


def test_parallel_matches_single_batch_and_aggregate_evidence_replays(tmp_path):
    corpus, files = make_corpus(tmp_path)
    parallel = tmp_path / "parallel"
    completed = evaluate(corpus, parallel, "--jobs", "2", "--timeout-ms", "2000")
    assert completed.returncode == 0, completed.stderr
    evaluation, report, _ = load_results(parallel)
    assert evaluation["configuration"]["jobs"] == 2
    assert evaluation["input_files"] == [str(file) for file in files]
    assert evaluation["benchmarks"] == 2
    # The same models in one `batch` process, with the evaluation's settings.
    single = tmp_path / "batch"
    baseline = subprocess.run(
        [sys.executable, "-m", "btor2sieve", "batch", *map(str, files), "--out", str(single),
         "--timeout-ms", "2000", "--reuse", "--max-reuse", "30", "--unlimited"],
        cwd=ROOT, text=True, capture_output=True, timeout=90,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
    )
    assert baseline.returncode == 0, baseline.stderr
    expected = json.loads((single / "results.json").read_text())
    run = evaluation["runs"]["implied"]
    out = parallel / RUN_DIRECTORY
    assert not report["errors"]
    assert [model["id"] for model in report["models"]] == ["m0000", "m0001"]
    assert [model["path"] for model in report["models"]] == [str(file) for file in files]
    assert counts(report) == counts(expected)
    assert len({row["id"] for row in report["records"]}) == len(report["records"])
    assert {row["model_id"] for row in report["records"]} == {"m0000", "m0001"}
    assert run["models"] == 2 and run["scopes"] == 3
    assert run["replay"]["z3"]["mismatched"] == 0
    assert len(list((out / "models").glob("*/results.json"))) == 2
    for row in report["records"] + [scope for model in report["models"] for scope in model["scopes"]]:
        artifact = (out / row["obligation"]).resolve()
        assert artifact.is_relative_to(out.resolve())
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == row["sha256"]
    replay = subprocess.run(
        [sys.executable, "-m", "btor2sieve", "replay", str(out), "--accepted-only"],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    assert replay.returncode == 0, replay.stderr + replay.stdout
    checks = json.loads(replay.stdout)
    assert checks["mismatched"] == 0
    assert len({row["id"] for row in checks["checks"]}) == checks["checked"]


def test_bad_model_is_reported_without_losing_other_models(tmp_path):
    corpus, files = make_corpus(tmp_path)
    malformed = corpus / "bad.btor2"
    malformed.write_text("not a BTOR2 model\n")
    output = tmp_path / "failed"
    result = evaluate(corpus, output, "--jobs", "2")
    assert result.returncode == 1, result.stderr
    evaluation, report, rows = load_results(output)
    assert evaluation["benchmarks"] == 3
    run = evaluation["runs"]["implied"]
    assert run["returncode"] == 1
    assert run["models"] == 2
    assert [error["model"] for error in run["errors"]] == [str(malformed)]
    # The aggregate replay reports the missing model as an incomplete run.
    assert run["replay"]["z3"]["returncode"] == 1
    assert run["replay"]["z3"]["incomplete_run_errors"] == 1
    assert run["replay"]["z3"]["mismatched"] == 0
    assert run["replay"]["z3"]["checked"] > 0
    assert {model["path"] for model in report["models"]} == {str(file) for file in files}
    assert report["errors"] and report["records"]
    assert {row["model"] for row in rows} == {str(file) for file in files}


@pytest.mark.parametrize("search_complete,validation_complete,exit_code", [
    (True, True, 0), (False, True, 1), (True, False, 1),
])
def test_search_coverage_is_preserved_separately_from_validation_counts(
    tmp_path, monkeypatch, search_complete, validation_complete, exit_code,
):
    evaluate_script = load_evaluate(monkeypatch)
    for name in ("first", "second"):
        (tmp_path / f"{name}.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    monkeypatch.setattr(sys, "argv", [str(ROOT / "scripts/evaluate.py"),
                        "--benchmarks", str(tmp_path), "--out", str(output), "--skip-cvc5", "--jobs", "1",
                        "--memory-limit-mib", "512"])
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    inject = tmp_path / "inject_search.py"
    inject.write_text(INJECT_SEARCH)
    real_popen = subprocess.Popen

    def extraction_with_search_metadata(command, **kwargs):
        if command[3] == "batch":
            # Inject discovery coverage at the subprocess boundary: real extraction
            # and replay retain their files, records, hashes, and validation counts.
            command = [sys.executable, str(inject), str(search_complete), str(validation_complete), *command]
        return real_popen(command, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", extraction_with_search_metadata)
    assert evaluate_script.main() == exit_code
    evaluation, _, rows = load_results(output)
    run = evaluation["runs"]["implied"]
    search = run["search"]
    assert search["kind"] == "property-word-level"
    assert run["workflow"] == "property-word-level-v1"
    assert search["total_candidates"] == run["candidates"]
    assert search["term_count"] == 6
    assert search["predicate_count"] == 2
    assert search["discovery_unknown"] == (0 if search_complete else 1)
    assert search["discovery_queries"] == 6
    assert search["complete"] is search_complete
    assert search["validation_complete"] is validation_complete
    assert search["complete_scopes"] == (2 if search_complete else 1)
    assert search["incomplete_scopes"] == (0 if search_complete else 1)
    assert run["candidates"] == sum(run["counts"].values())
    assert run["replay"]["z3"]["returncode"] == 0
    assert len(rows) == 2
    assert all(row["workflow"] == "property-word-level-v1" for row in rows)
    assert all(row["search_kind"] == "property-word-level" for row in rows)
    assert all(row["search_total_candidates"] == row["candidates"] for row in rows)
    assert all(row["search_term_count"] == "3" for row in rows)
    assert all(row["search_predicate_count"] == "1" for row in rows)
    assert rows[1]["search_complete"] == str(search_complete)
    assert rows[1]["search_validation_complete"] == str(validation_complete)
    assert rows[1]["search_reason"] == ("" if search_complete else "timeout")
    assert all(int(row["candidates"]) == sum(int(row[status]) for status in
               ("accepted", "rejected", "unknown", "vacuous")) for row in rows)


@pytest.mark.parametrize("failure", ["extraction", "replay", "malformed-replay"])
def test_subprocess_failure_is_recorded(tmp_path, monkeypatch, failure):
    evaluate_script = load_evaluate(monkeypatch)
    (tmp_path / "one.btor2").write_text(MODEL)
    output = tmp_path / "evaluation"
    monkeypatch.setattr(sys, "argv", [str(ROOT / "scripts/evaluate.py"),
                        "--benchmarks", str(tmp_path), "--out", str(output), "--skip-cvc5",
                        "--memory-limit-mib", "512", *MATCHED])
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    mismatched = tmp_path / "mismatched_replay.py"
    mismatched.write_text(MISMATCHED_REPLAY)
    real_popen = subprocess.Popen

    def fail_one_process(command, **kwargs):
        if command[3] == "batch" and failure == "extraction":
            command = [sys.executable, "-c",
                       "import sys; sys.stderr.write('synthetic extraction failure'); sys.exit(2)"]
        elif command[3] == "replay" and failure == "malformed-replay":
            command = [sys.executable, "-c", "import sys; sys.stderr.write('synthetic replay failure'); sys.exit(1)"]
        elif command[3] == "replay" and failure == "replay":
            command = [sys.executable, str(mismatched), *command]
        return real_popen(command, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", fail_one_process)
    assert evaluate_script.main() == 1
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert list(evaluation["runs"]) == ["implied"]
    run = evaluation["runs"]["implied"]
    assert run["output_directory"] == RUN_DIRECTORY
    model = output / RUN_DIRECTORY / "models/m0000"
    receipt = json.loads((output / RUN_DIRECTORY / "run-status.json").read_text())["models"][0]
    assert receipt["status"] == "failed"
    if failure == "extraction":
        assert receipt["returncode"] == 2
        assert run["returncode"] == 1
        assert run["errors"]
        assert "synthetic extraction failure" in (model / "extract.stderr.txt").read_text()
    else:
        assert run["replay"]["z3"]["returncode"] == 1
        assert (model / "replay-z3.stderr.txt").read_text() == "synthetic replay failure"
