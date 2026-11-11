"""scripts/parallel_evaluate.py: workers, resource limits, failures, and interruption."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL = "1 sort bitvec 1\n2 state 1 flag\n3 bad 2\n"
# Stands in for an extraction: it writes a partial obligation, then misbehaves.
WORKER = """import os, pathlib, subprocess, sys, time
behavior, pids = sys.argv[1:3]
out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
(out / "obligations").mkdir(parents=True)
(out / "obligations" / "m0000-00001.smt2").write_text("(check-sat)\\n")
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
pathlib.Path(pids).write_text(f"{os.getpid()} {child.pid}")
if behavior == "memory":
    hoard = bytearray(256 << 20)
    time.sleep(60)
elif behavior == "cpu":
    while True:
        pass
elif behavior == "wall":
    time.sleep(60)
elif behavior == "killed":
    os.kill(os.getpid(), 9)
"""


def runner():
    """Load scripts/parallel_evaluate.py as a module."""
    spec = importlib.util.spec_from_file_location("parallel_evaluate", ROOT / "scripts/parallel_evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def options(**changes):
    """The evaluate.py arguments that run_parallel reads."""
    values = dict(jobs=1, scopes="property", timeout_ms=1000, skip_cvc5=True,
                  budget_policy="unlimited", memory_limit_mib=512, cpu_limit_s=30, wall_limit_s=30)
    return SimpleNamespace(**{**values, **changes})


def alive(pid):
    stat = Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


# --- Resource limits ---------------------------------------------------------------

def run_with_worker(tmp_path, monkeypatch, behavior, **limits):
    module = runner()
    model = tmp_path / "one.btor2"
    model.write_text(MODEL)
    worker = tmp_path / "worker.py"
    worker.write_text(WORKER)
    pids = tmp_path / "pids"
    launched = []
    real_popen = module.subprocess.Popen

    def launch(command, **kwargs):
        launched.append(command)
        if command[3] == "batch":
            command = [sys.executable, str(worker), behavior, str(pids), *command]
        return real_popen(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", launch)
    out = tmp_path / "evaluation/implied-constraints"
    begin = time.monotonic()
    result = module.run_parallel(options(**limits), [str(model)], out)
    return result, out, launched, [int(pid) for pid in pids.read_text().split()], time.monotonic() - begin


@pytest.mark.parametrize("behavior, limits, outcome", [
    ("memory", {"memory_limit_mib": 64}, "memory-limit"),
    ("cpu", {"cpu_limit_s": 1}, "cpu-limit"),
    ("wall", {"wall_limit_s": 1}, "wall-limit"),
])
def test_exceeded_limit_kills_worker_and_is_recorded_as_outcome(tmp_path, monkeypatch, behavior, limits, outcome):
    (run, rows, failed), out, launched, pids, seconds = run_with_worker(tmp_path, monkeypatch, behavior, **limits)
    assert seconds < 20
    assert failed and run["status"] == "failed"
    assert run["outcomes"] == {outcome: 1}
    assert run["errors"] == [] and run["returncode"] == 1
    assert not run["search"]["complete"] and not run["search"]["validation_complete"]
    receipt = json.loads((out / "run-status.json").read_text())["models"][0]
    assert receipt["status"] == outcome
    usage = receipt["resources"]
    assert usage["exceeded"] == outcome
    if behavior == "memory":
        assert usage["peak_memory_bytes"] > 64 << 20
    elif behavior == "cpu":
        assert 1 <= usage["cpu_seconds"] < 2.5
    else:
        assert usage["wall_seconds"] >= 1 and usage["cpu_seconds"] < 1
    # The whole process group is gone, and nothing was replayed.
    assert not any(alive(pid) for pid in pids)
    assert not any(command[3] == "replay" for command in launched)
    directory = out / "models/m0000"
    assert receipt["discarded_obligations"] == 1
    assert not (directory / "obligations").exists()
    assert (directory / "extract.stdout.txt").is_file()
    entry = run["resource_limits"][0]
    assert entry["resource_limit"] == outcome and entry["model"] == str(tmp_path / "one.btor2")
    report = json.loads((out / "results.json").read_text())
    assert report["errors"] == [entry] and report["models"] == [] and report["records"] == []
    assert report["parallel_execution"]["outcomes"] == {outcome: 1}
    assert [row["outcome"] for row in rows] == [outcome]
    assert rows[0]["model"] == str(tmp_path / "one.btor2") and rows[0]["cpu_seconds"] is not None
    assert outcome in (out / "report.html").read_text()


def test_external_sigkill_below_limits_remains_a_failure(tmp_path, monkeypatch):
    (run, rows, failed), out, launched, pids, _ = run_with_worker(tmp_path, monkeypatch, "killed")
    assert failed and run["status"] == "failed"
    receipt = json.loads((out / "run-status.json").read_text())["models"][0]
    assert receipt["status"] == "failed" and receipt["returncode"] == -9
    assert receipt["resources"]["exceeded"] is None
    assert run["resource_limits"] == []
    assert any("Cannot read extraction report" in error["error"] for error in run["errors"])


def test_completed_extraction_records_exact_usage_and_replays(tmp_path, monkeypatch):
    module = runner()
    model = tmp_path / "one.btor2"
    model.write_text(MODEL)
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    out = tmp_path / "evaluation/implied-constraints"
    run, rows, failed = module.run_parallel(options(), [str(model)], out)
    assert not failed and run["outcomes"] == {"completed": 1}
    usage = json.loads((out / "run-status.json").read_text())["models"][0]["resources"]
    assert usage["exceeded"] is None
    assert 0 < usage["cpu_seconds"] < 30 and 0 < usage["wall_seconds"] < 30
    assert usage["peak_memory_bytes"] > 1 << 20
    assert run["replay"]["z3"]["checked"] > 0 and run["replay"]["z3"]["mismatched"] == 0
    assert rows and all(row["outcome"] == "completed" and row["peak_memory_mib"] > 1 for row in rows)


# --- Failures and interruption -----------------------------------------------------

@pytest.mark.parametrize("failure", ["returncode", "malformed", "missing", "mismatch"])
def test_failed_replay_is_visible_and_does_not_erase_extraction(tmp_path, monkeypatch, failure):
    module = runner()
    model = tmp_path / "one.btor2"
    model.write_text(MODEL)
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    real_popen = module.subprocess.Popen

    def fail_replay(command, **kwargs):
        if command[3] == "replay":
            payload = {"backend": "z3", "solver_version": "test", "solver_options": {},
                       "checked": 1, "mismatched": int(failure == "mismatch"),
                       "incomplete_run_errors": 0, "checks": []}
            text = "broken" if failure == "malformed" else json.dumps(payload)
            if failure == "missing":
                text = ""
            code = 1 if failure == "returncode" else 0
            command = [sys.executable, "-c", f"import sys; print({text!r}); sys.exit({code})"]
        return real_popen(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", fail_replay)
    out = tmp_path / "evaluation/implied-constraints"
    run, rows, failed = module.run_parallel(options(), [str(model)], out)
    assert failed
    assert run["replay"]["z3"]["returncode"] != 0
    assert run["models"] == 1
    assert rows[0]["model"] == str(model)
    assert (out / "models/m0000/results.json").is_file()
    status = json.loads((out / "run-status.json").read_text())
    assert status["status"] == "failed"
    assert status["models"][0]["status"] == "failed"


@pytest.mark.parametrize("stubborn, stop_signal", [(False, signal.SIGINT), (True, signal.SIGINT),
                                                   (True, signal.SIGTERM)])
def test_interrupt_stops_descendants_and_never_launches_queued_models(tmp_path, stubborn, stop_signal):
    runner()  # Fail early if the script cannot be loaded.
    corpus = tmp_path / "models"
    corpus.mkdir()
    for index in range(5):
        (corpus / f"{index}.btor2").write_text(MODEL)
    out = tmp_path / "evaluation"
    pid_log = tmp_path / "pids"
    fake = tmp_path / "fake_worker.py"
    fake.write_text("""import os, pathlib, signal, subprocess, sys, time
pids = pathlib.Path(sys.argv[1])
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(90)'])
with pids.open('a') as stream:
    stream.write(f'{os.getpid()} {child.pid}\\n')
# Reap the descendant after the runner terminates the whole process group.
def stop(*args):
    child.wait(timeout=3)
    sys.exit(130)
signal.signal(signal.SIGTERM, stop)
time.sleep(90)
""")
    if stubborn:
        fake.write_text(fake.read_text().replace(
            "'import time; time.sleep(90)'",
            "'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(90)'",
        ).replace("    child.wait(timeout=3)", "    pass"))
    controller = tmp_path / "controller.py"
    controller.write_text(f"""import sys
sys.path.insert(0, {str(ROOT / 'scripts')!r})
import evaluate, parallel_evaluate
original = parallel_evaluate.subprocess.Popen
def launch(command, **kwargs):
    return original([sys.executable, {str(fake)!r}, {str(pid_log)!r}], **kwargs)
parallel_evaluate.subprocess.Popen = launch
raise SystemExit(evaluate.main())
""")
    process = subprocess.Popen([sys.executable, str(controller), "--benchmarks", str(corpus),
                                "--out", str(out), "--jobs", "2",
                                "--skip-cvc5", "--memory-limit-mib", "512"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    pids = []
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if pid_log.exists():
                lines = pid_log.read_text().splitlines()
                if len(lines) == 2:
                    pids = [int(pid) for line in lines for pid in line.split()]
                    break
            if process.poll() is not None:
                pytest.fail(f"Controller exited early: {process.communicate()}")
            time.sleep(0.02)
        assert len(pids) == 4, "two extraction workers and their descendants must start"
        process.send_signal(stop_signal)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 130, (stdout, stderr)
        assert len(pid_log.read_text().splitlines()) == 2
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            running = [pid for pid in pids if Path(f"/proc/{pid}/stat").exists()
                       and Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"]
            if not running:
                break
            time.sleep(0.02)
        assert not running, f"surviving workers or descendants: {running}"
        status = json.loads((out / "implied-constraints/run-status.json").read_text())
        assert status["status"] == "interrupted"
        assert all(row["status"] in {"interrupted", "cancelled"} for row in status["models"])
        assert json.loads((out / "run-status.json").read_text())["status"] == "interrupted"
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize("failure", ["replay-failure", "aggregation-interrupt"])
def test_evaluation_status_survives_replay_failure_and_aggregation_interrupt(tmp_path, failure):
    model = tmp_path / "one.btor2"
    model.write_text(MODEL)
    controller = tmp_path / "controller.py"
    setup = """original = parallel_evaluate.subprocess.Popen
def launch(command, **kwargs):
    if command[3] == 'replay' and '/implied-constraints/' in command[4]:
        command = [sys.executable, '-c', 'raise SystemExit(1)']
    return original(command, **kwargs)
parallel_evaluate.subprocess.Popen = launch
""" if failure == "replay-failure" else """def stop(*args):
    raise KeyboardInterrupt
parallel_evaluate._Aggregate.add = stop
"""
    controller.write_text(f"import sys\nsys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
                          "import evaluate, parallel_evaluate\n" + setup + "raise SystemExit(evaluate.main())\n")
    output = tmp_path / "evaluation"
    completed = subprocess.run([sys.executable, str(controller), "--benchmarks", str(tmp_path),
                                "--out", str(output), "--jobs", "2",
                                "--skip-cvc5", "--budget-policy", "matched", "--max-candidates", "2", "--max-queries", "2",
                                "--memory-limit-mib", "512"],
                               env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
                               text=True, capture_output=True, timeout=30)
    expected = "failed" if failure == "replay-failure" else "interrupted"
    assert completed.returncode == (1 if failure == "replay-failure" else 130)
    assert json.loads((output / "run-status.json").read_text())["status"] == expected
    assert json.loads((output / "implied-constraints/run-status.json").read_text())["status"] == expected
