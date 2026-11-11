"""Run one extraction process per benchmark in parallel, then merge the reports.

How it works:

1. ``run_parallel`` starts up to ``args.jobs`` worker threads. Each worker runs
   ``btor2sieve batch`` for one model in a fresh process (so every model gets
   its own solver state), then replays its obligations with Z3 (and cvc5).
2. ``_supervise`` enforces each extraction's memory, CPU and wall-time limits
   (Linux only) and records the resources it used.
3. ``_Aggregate`` merges the per-model reports one at a time into combined
   JSON/CSV files, streaming large lists to disk instead of holding them.

Worker threads never import the solver; they only handle paths and exit codes.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import resource
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
from time import perf_counter

from btor2sieve.reporting import CONSTRAINT_FIELDS, FAMILY_FIELDS, SUMMARY_FIELDS, family_rows


ROOT = Path(__file__).resolve().parents[1]
MODE = "implied"
OUTPUT_DIRECTORY = "implied-constraints"
LIMIT_STATUSES = ("memory-limit", "cpu-limit", "wall-limit")
FINISHED = {"completed", "failed", *LIMIT_STATUSES}
POLL_SECONDS = 0.1
_CLOCK_TICKS = os.sysconf("SC_CLK_TCK")
SEARCH_COUNTS = ("term_count", "predicate_count", "total_candidates", "discovery_queries", "discovery_unknown")


def _save_status(path, status):
    """Write JSON atomically so a reader never sees a half-written file."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2) + "\n")
    temporary.replace(path)


def _command(args, path, directory):
    """The `btor2sieve batch` command line for one model."""
    command = [sys.executable, "-m", "btor2sieve", "batch", path, "--out", str(directory),
               "--method", "implied", "--scopes", args.scopes,
               "--timeout-ms", str(args.timeout_ms), "--reuse", "--max-reuse", "30"]
    if args.budget_policy == "unlimited":
        command.append("--unlimited")
    else:
        command.extend(["--max-width", str(args.max_width), "--max-candidates", str(args.max_candidates),
                        "--max-terms", str(args.max_terms), "--max-queries", str(args.max_queries)])
    if args.budget_policy == "matched":
        command.append("--matched-budgets")
    return command


def _sample(pid):
    """Return CPU seconds and the larger of resident+swapped and peak resident bytes."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        status = Path(f"/proc/{pid}/status").read_text()
        # Fields after the parenthesized command name start at field 3 (state).
        fields = stat.rsplit(")", 1)[1].split()
        cpu = (int(fields[11]) + int(fields[12])) / _CLOCK_TICKS
        memory = {}
        for line in status.splitlines():
            key, _, value = line.partition(":")
            if key in {"VmHWM", "VmRSS", "VmSwap"}:
                memory[key] = int(value.split()[0]) << 10
    except (OSError, IndexError, ValueError):
        return None
    return cpu, max(memory.get("VmRSS", 0) + memory.get("VmSwap", 0), memory.get("VmHWM", 0))


def _supervise(process, launched, limits):
    """Reap one extraction, killing its process group at the first exceeded limit.

    /proc samples enforce memory and CPU between polls; VmHWM catches residency
    spikes. wait4 then supplies exact CPU time and peak resident memory.
    """
    try:
        resource.prlimit(process.pid, resource.RLIMIT_CORE, (0, 0))
        # Kernel backstop in case sampling is delayed; SIGKILL never dumps core.
        backstop = limits["cpu_limit_s"] + 1
        resource.prlimit(process.pid, resource.RLIMIT_CPU, (backstop, backstop))
    except ProcessLookupError:
        pass
    memory_limit = limits["memory_limit_mib"] << 20
    exceeded, cpu, peak, status, usage = None, 0.0, 0, None, None
    try:
        # A pidfd becomes readable at exit, so wall time is not rounded to a poll.
        pidfd = os.pidfd_open(process.pid)
    except (AttributeError, OSError):
        pidfd = None
    try:
        while True:
            try:
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
            except ChildProcessError:
                # Interruption cleanup reaped it first; the run is discarded anyway.
                status = usage = None
                break
            if pid:
                break
            sample = _sample(process.pid)
            if sample is not None:
                cpu, peak = max(cpu, sample[0]), max(peak, sample[1])
            if exceeded is None:
                if peak > memory_limit:
                    exceeded = "memory-limit"
                elif cpu >= limits["cpu_limit_s"]:
                    exceeded = "cpu-limit"
                elif perf_counter() - launched >= limits["wall_limit_s"]:
                    exceeded = "wall-limit"
                if exceeded is not None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            if pidfd is None:
                time.sleep(POLL_SECONDS)
            else:
                select.select([pidfd], [], [], POLL_SECONDS)
    finally:
        if pidfd is not None:
            os.close(pidfd)
    wall = perf_counter() - launched
    if usage is None:
        code = process.returncode if process.returncode is not None else -signal.SIGKILL
    else:
        code = process.returncode = os.waitstatus_to_exitcode(status)
        cpu = usage.ru_utime + usage.ru_stime
        peak = max(peak, usage.ru_maxrss << 10)
    if exceeded is None and code == -signal.SIGKILL and cpu >= limits["cpu_limit_s"]:
        exceeded = "cpu-limit"  # The kernel backstop fired between samples.
    return code, {"cpu_seconds": cpu, "wall_seconds": wall, "peak_memory_bytes": peak,
                  "exceeded": exceeded}


def _discard_partial_output(directory):
    """Delete a killed extraction's unreported files and return its obligation count."""
    obligations = directory / "obligations"
    count = sum(1 for _ in obligations.iterdir()) if obligations.is_dir() else 0
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir()
    return count


def _usage(receipt):
    """Per-benchmark resource columns for comparison rows."""
    resources = receipt.get("resources") or {}
    seconds = {key: None if resources.get(key) is None else round(resources[key], 3)
               for key in ("cpu_seconds", "wall_seconds")}
    peak = resources.get("peak_memory_bytes")
    return {**seconds, "peak_memory_mib": None if peak is None else round(peak / (1 << 20), 1)}


def _remap(value, model_id, prefix):
    """Rewrite identifiers and relative evidence paths, never SMT text/hashes."""
    if isinstance(value, list):
        for child in value:
            _remap(child, model_id, prefix)
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in {"id", "model_id"} and isinstance(child, str):
                if child == "m0000" or child.startswith(("m0000-", "m0000:")):
                    value[key] = model_id + child[5:]
            elif key == "implication_ids":
                value[key] = [model_id + item[5:] if item.startswith("m0000-") else item for item in child]
            elif key == "obligation" or (key == "path" and "sha256" in value and "id" not in value):
                value[key] = f"{prefix}/{child}"
            else:
                _remap(child, model_id, prefix)


class _Aggregate:
    """Spool large collections to disk and retain only small evaluation rows."""

    def __init__(self, out, jobs, limits):
        self.out, self.limits = out, limits
        self.header = {"schema_version": 1, "configuration": {}, "scope_definitions": {}}
        self.parts = {key: (out / f".{key}.json.part").open("w")
                      for key in ("models", "summaries", "records", "errors")}
        self.lengths = Counter()
        self.csv_streams, self.writers = [], {}
        for name, fields in (("summary", SUMMARY_FIELDS), ("constraints", CONSTRAINT_FIELDS),
                             ("families", FAMILY_FIELDS)):
            stream = (out / f"{name}.csv").open("w", newline="")
            self.csv_streams.append(stream)
            self.writers[name] = csv.DictWriter(stream, fields, extrasaction="ignore")
            self.writers[name].writeheader()
        self.run = {"method": MODE,
                    "output_directory": OUTPUT_DIRECTORY, "jobs": jobs, "returncode": 0,
                    "errors": [], "replay": {}, "models": 0, "scopes": 0, "candidates": 0,
                    "counts": Counter(), "reuse": Counter(), "families": {}, "analysis_seconds": 0,
                    "extraction_seconds": 0, "validation_seconds": 0, "worker_seconds": 0,
                    "resource_limits": []}
        self.rows, self.links = [], []
        self.searches = []

    def append(self, key, row):
        if self.lengths[key]:
            self.parts[key].write(",\n")
        json.dump(row, self.parts[key])
        self.lengths[key] += 1

    def error(self, path, message):
        row = {"model": path, "error": message}
        self.run["errors"].append(row)
        self.append("errors", row)
        self.run["returncode"] = 1

    def limit(self, receipt):
        """Record a benchmark whose extraction was stopped at a resource limit."""
        resources = receipt["resources"]
        limits = {"memory-limit": f"{self.limits['memory_limit_mib']} MiB memory",
                  "cpu-limit": f"{self.limits['cpu_limit_s']} s CPU time",
                  "wall-limit": f"{self.limits['wall_limit_s']} s wall time"}
        entry = {"model": receipt["path"], "resource_limit": receipt["status"],
                 "error": f"{receipt['status']}: extraction exceeded {limits[receipt['status']]}",
                 **{key: resources[key] for key in ("cpu_seconds", "wall_seconds", "peak_memory_bytes")},
                 "discarded_obligations": receipt.get("discarded_obligations", 0)}
        # Listed with errors so replaying the aggregate still reports missing evidence.
        self.append("errors", entry)
        self.run["resource_limits"].append(entry)
        self.rows.append({"mode": MODE, "method": MODE, "workflow": None,
                          "output_directory": OUTPUT_DIRECTORY, "model": receipt["path"]})

    def add(self, receipt):
        directory = self.out / "models" / receipt["id"]
        self.run["worker_seconds"] += receipt.get("duration_seconds", 0)
        self.links.append(receipt)
        if receipt["status"] in LIMIT_STATUSES:
            self.limit(receipt)
            return
        self.run["returncode"] |= int(bool(receipt.get("returncode") or receipt.get("error") or
                                          receipt["status"] in {"cancelled", "interrupted"}))
        if receipt.get("error"):
            self.error(receipt["path"], receipt["error"])
        try:
            with (directory / "results.json").open() as stream:
                report = json.load(stream)
            for key in ("models", "summaries", "records", "errors"):
                if not isinstance(report[key], list):
                    raise ValueError(f"{key} must be an array")
            if not report["models"] and not report["errors"]:
                raise ValueError("extraction contains no model or input error")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.error(receipt["path"], f"Cannot read extraction report: {exc}")
            receipt["status"] = "failed"
            return
        self.header = {key: value for key, value in report.items()
                       if key not in {*self.parts, "duration_seconds"}}
        _remap(report, receipt["id"], f"models/{receipt['id']}")
        for key in self.parts:
            for row in report[key]:
                self.append(key, row)
        if report["errors"]:
            receipt["status"] = "failed"
        self.run["errors"].extend(report["errors"])
        self.run["returncode"] |= int(bool(report["errors"]))
        self.run["models"] += len(report["models"])
        self.run["scopes"] += len(report["summaries"])
        self.run["analysis_seconds"] += report["duration_seconds"]
        self.run["workflow"] = report["configuration"].get("implied_workflow")
        configuration = report["configuration"]
        if ("extraction_configuration" in self.run and
                self.run["extraction_configuration"] != configuration):
            self.error(receipt["path"], "Extraction settings differ between model workers")
            receipt["status"] = "failed"
        self.run["extraction_configuration"] = configuration
        for record in report["records"]:
            self.writers["constraints"].writerow(record)
            if record["reuse_from"]:
                self.run["reuse"][record["status"]] += 1
            else:
                self.run["candidates"] += 1
                self.run["counts"][record["status"]] += 1
                self.run["families"].setdefault(record["family"], Counter())[record["status"]] += 1
        for summary in report["summaries"]:
            self.writers["summary"].writerow(summary)
            self.writers["families"].writerows(family_rows([summary]))
            for key in ("extraction_seconds", "validation_seconds"):
                self.run[key] += summary[key]
            search = summary.get("search", {})
            self.searches.append(search)
            self.rows.append({"mode": MODE, "method": MODE,
                "workflow": self.run.get("workflow"), "output_directory": OUTPUT_DIRECTORY,
                **{key: summary.get(key) for key in SUMMARY_FIELDS},
                **{f"search_{key}": value for key, value in search.items()}})
        del report

    def replay(self, receipts, backend):
        result = {"backend": backend, "checked": 0, "mismatched": 0,
                  "incomplete_run_errors": 0, "returncode": 0}
        part = self.out / f".replay-{backend}.checks.part"
        checks_written = 0
        with part.open("w") as stream:
            for receipt in receipts:
                if receipt["status"] in LIMIT_STATUSES:
                    continue
                code = receipt.get("replay", {}).get(backend, {}).get("returncode", 1)
                try:
                    with (self.out / "models" / receipt["id"] / f"replay-{backend}.json").open() as source:
                        replay = json.load(source)
                    if not isinstance(replay, dict) or not isinstance(replay.get("checks"), list):
                        raise ValueError("expected replay object with checks")
                    for key in ("checked", "mismatched", "incomplete_run_errors"):
                        if not isinstance(replay.get(key), int):
                            raise ValueError(f"missing replay counter: {key}")
                        result[key] += replay[key]
                    if (not replay["checked"] or replay["mismatched"] or
                            replay["incomplete_run_errors"] or len(replay["checks"]) != replay["checked"]):
                        code = code or 1
                    for key in ("solver_version", "solver_options"):
                        result[key] = replay.get(key)
                    _remap(replay["checks"], receipt["id"], f"models/{receipt['id']}")
                    for check in replay["checks"]:
                        if checks_written:
                            stream.write(",\n")
                        json.dump(check, stream)
                        checks_written += 1
                    del replay
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    result.setdefault("errors", []).append({"model": receipt["path"], "error": str(exc)})
                    code = code or 1
                if code:
                    receipt["status"] = "failed"
                result["returncode"] |= int(bool(code))
        with (self.out / f"replay-{backend}.json").open("w") as stream:
            stream.write(json.dumps(result)[:-1] + ', "checks": [')
            with part.open() as source:
                shutil.copyfileobj(source, stream)
            stream.write("]}\n")
        part.unlink()
        self.run["replay"][backend] = result

    def finish(self, wall_seconds, interrupted):
        self.run["duration_seconds"] = self.run["parallel_wall_seconds"] = wall_seconds
        complete = sum(bool(s.get("complete")) for s in self.searches)
        validated = sum(bool(s.get("validation_complete")) for s in self.searches)
        self.run["search"] = {"kind": "property-word-level",
            **{key: sum(search.get(key, 0) for search in self.searches) for key in SEARCH_COUNTS},
            "complete_scopes": complete, "incomplete_scopes": len(self.searches) - complete,
            "complete": bool(self.searches) and complete == len(self.searches),
            "validation_complete": bool(self.searches) and validated == len(self.searches),
            "coverage": "budgeted" if self.header["configuration"].get("matched_budgets") else "finite-cone",
            "budget_exhausted": dict(Counter(limit for search in self.searches
                                             for limit in search.get("budget_exhausted", [])))}
        self.run["returncode"] |= int(not (
            self.run["search"]["complete"] and self.run["search"]["validation_complete"]))
        failed = bool(interrupted or self.run["returncode"] or
                      any(replay["returncode"] for replay in self.run["replay"].values()))
        self.run["status"] = "interrupted" if interrupted else "failed" if failed else "completed"
        self.run["outcomes"] = dict(Counter(receipt["status"] for receipt in self.links))
        receipts = {receipt["path"]: receipt for receipt in self.links}
        for row in self.rows:
            receipt = receipts[row["model"]]
            row.update(outcome=receipt["status"], **_usage(receipt))
            if row["workflow"] is None:
                row["workflow"] = self.run.get("workflow")
        self.header.update({"duration_seconds": wall_seconds,
                            "parallel_execution": {"jobs": self.run["jobs"], "status": self.run["status"],
                                "worker_seconds": self.run["worker_seconds"],
                                "analysis_seconds": self.run["analysis_seconds"],
                                "resource_limits": self.limits, "outcomes": self.run["outcomes"]}})
        for stream in [*self.parts.values(), *self.csv_streams]:
            stream.close()
        temporary = self.out / "results.json.tmp"
        with temporary.open("w") as stream:
            stream.write(json.dumps(self.header)[:-1])
            for key in self.parts:
                stream.write(f', "{key}": [')
                with (self.out / f".{key}.json.part").open() as source:
                    shutil.copyfileobj(source, stream)
                stream.write("]")
            stream.write("}\n")
        temporary.replace(self.out / "results.json")
        for key in self.parts:
            (self.out / f".{key}.json.part").unlink()
        self._write_index(wall_seconds)
        return self.run, self.rows, failed

    def _write_index(self, wall_seconds):
        """A small top-level report.html linking to each model's own report."""
        def item(row):
            label = html.escape(row["path"])
            if (self.out / "models" / row["id"] / "report.html").is_file():
                label = f'<a href="models/{row["id"]}/report.html">{label}</a>'
            return f'<li>{label} ({html.escape(row["status"])})</li>'

        links = "".join(item(row) for row in self.links)
        outcomes = " · ".join(f"{count} {html.escape(name)}" for name, count in sorted(self.run["outcomes"].items()))
        (self.out / "report.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Btor2Sieve parallel report</title>'
            '<h1>Btor2Sieve parallel report</h1>'
            f'<p>{html.escape(self.run["status"])} · {self.run["models"]} models · '
            f'{self.run["candidates"]} candidates · {wall_seconds:.2f}s parallel wall time</p>'
            f'<p>Limits per benchmark: {self.limits["memory_limit_mib"]} MiB memory · '
            f'{self.limits["cpu_limit_s"]} s CPU · {self.limits["wall_limit_s"]} s wall. '
            f'Outcomes: {outcomes}</p>'
            '<p><a href="results.json">Full JSON evidence</a> · <a href="summary.csv">Summary CSV</a> · '
            '<a href="families.csv">Family CSV</a> · <a href="constraints.csv">Constraint CSV</a> · '
            '<a href="run-status.json">Execution status</a></p>'
            '<p>Model reports retain complete constraint details and SMT evidence.</p><ul>' + links + '</ul></html>')


def _interrupt(signum, frame):
    raise KeyboardInterrupt


def run_parallel(args, files, out):
    """Run one fresh extraction and independent replays per file, then aggregate.

    Returns (run summary, comparison rows, failed). SIGTERM is treated like Ctrl+C.
    """
    previous = signal.signal(signal.SIGTERM, _interrupt)
    try:
        return _run_parallel(args, files, out)
    finally:
        signal.signal(signal.SIGTERM, previous)


def _run_parallel(args, files, out):
    started = perf_counter()
    (out / "models").mkdir(parents=True)
    backends = ("z3",) if args.skip_cvc5 else ("z3", "cvc5")
    limits = {"memory_limit_mib": args.memory_limit_mib, "cpu_limit_s": args.cpu_limit_s,
              "wall_limit_s": args.wall_limit_s}
    status = {"status": "running", "jobs": args.jobs, "limits": limits, "total": len(files), "completed": 0,
              "started_utc": datetime.now(timezone.utc).isoformat(), "models": [
                  {"id": f"m{index:04d}", "path": path, "status": "queued", "replay": {}}
                  for index, path in enumerate(files)]}
    lock, stopping, processes = threading.Lock(), threading.Event(), {}

    def update(receipt, **values):
        with lock:
            receipt.update(values)
            status["completed"] = sum(row["status"] in FINISHED for row in status["models"])
            status["elapsed_seconds"] = perf_counter() - started
            _save_status(out / "run-status.json", status)

    def execute(command, stdout, stderr, receipt, phase, limited=False):
        with stdout.open("w") as output, stderr.open("w") as errors:
            with lock:
                if stopping.is_set():
                    raise InterruptedError("evaluation interrupted")
                launched = perf_counter()
                process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=errors,
                                           start_new_session=True)
                processes[process.pid] = process
            update(receipt, status=phase, pid=process.pid)
            try:
                if not limited:
                    return process.wait()
                code, resources = _supervise(process, launched, limits)
                update(receipt, resources=resources)
                return code
            finally:
                with lock:
                    processes.pop(process.pid, None)

    def worker(receipt):
        begin = perf_counter()
        directory = out / "models" / receipt["id"]
        logs = [out / "models" / f'{receipt["id"]}.extract.{kind}.txt' for kind in ("stdout", "stderr")]
        try:
            command = _command(args, receipt["path"], directory)
            update(receipt, command=command)
            code = execute(command, *logs, receipt, "extracting", limited=True)
            if stopping.is_set():
                raise InterruptedError("evaluation interrupted")
            update(receipt, returncode=code)
            exceeded = receipt["resources"]["exceeded"]
            if exceeded:
                # A run stopped at a limit has no report, so its partial
                # obligations cannot be replayed; large models write gigabytes.
                update(receipt, status=exceeded, discarded_obligations=_discard_partial_output(directory))
                return receipt
            directory.mkdir(exist_ok=True)
            for backend in backends:
                command = [sys.executable, "-m", "btor2sieve", "replay", str(directory),
                           "--accepted-only", "--backend", backend, "--timeout-ms", "5000"]
                code = execute(command, directory / f"replay-{backend}.json",
                               directory / f"replay-{backend}.stderr.txt", receipt, f"replaying-{backend}")
                update(receipt, replay={**receipt["replay"], backend: {"returncode": code}})
            if stopping.is_set():
                raise InterruptedError("evaluation interrupted")
            failed = receipt["returncode"] or any(r["returncode"] for r in receipt["replay"].values())
            update(receipt, status="failed" if failed else "completed")
        except InterruptedError:
            update(receipt, status="interrupted")
        except Exception as exc:
            update(receipt, status="failed", error=f"Worker failed: {type(exc).__name__}: {exc}")
        finally:
            directory.mkdir(exist_ok=True)
            for path in logs:
                if path.exists():
                    path.replace(directory / path.name.split(".", 1)[1])
            update(receipt, duration_seconds=perf_counter() - begin, pid=None)
        return receipt

    _save_status(out / "run-status.json", status)
    pool = ThreadPoolExecutor(max_workers=args.jobs)
    futures = []
    interrupted = False
    try:
        for receipt in status["models"]:
            futures.append(pool.submit(worker, receipt))
        for future in as_completed(futures):
            receipt = future.result()
            print(f"{MODE}: {status['completed']}/{len(files)} {receipt['status']} {receipt['path']}", flush=True)
    except BaseException:
        interrupted = True
        stopping.set()
        for future in futures:
            future.cancel()
        with lock:
            active = list(processes.values())
        for process in active:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in active:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            # The leader can exit while a descendant ignores SIGTERM. Kill the
            # original group even when wait() already reaped its leader.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        # SIGINT is deliberately reported as interrupted; unexpected scheduler
        # exceptions are re-raised after the finally block has stopped workers.
        if not isinstance(sys.exception(), KeyboardInterrupt):
            raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        if interrupted:
            for receipt in status["models"]:
                if receipt["status"] == "queued":
                    receipt["status"] = "cancelled"
                elif receipt["status"] not in FINISHED:
                    receipt["status"] = "interrupted"
            status["status"] = "interrupted"
            _save_status(out / "run-status.json", status)
    if interrupted:
        raise KeyboardInterrupt
    status["status"] = "aggregating"
    _save_status(out / "run-status.json", status)
    aggregation = _Aggregate(out, args.jobs, limits)
    try:
        for receipt in status["models"]:
            aggregation.add(receipt)
        for backend in backends:
            aggregation.replay(status["models"], backend)
        run, rows, failed = aggregation.finish(perf_counter() - started, interrupted)
        status["status"] = run["status"]
        status["elapsed_seconds"] = run["parallel_wall_seconds"]
        _save_status(out / "run-status.json", status)
        return run, rows, failed
    except BaseException as exc:
        status["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        _save_status(out / "run-status.json", status)
        raise
    finally:
        for stream in [*aggregation.parts.values(), *aggregation.csv_streams]:
            stream.close()
