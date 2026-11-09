"""Report formats remain usable independently of their rendering helpers."""

import csv
import json

import pytest

from btor2sieve.candidates import GenerationOptions
from btor2sieve.pipeline import analyze
from btor2sieve.reporting import write_report


@pytest.fixture
def report_files(tmp_path):
    model = tmp_path / "counter<&>.btor2"
    model.write_text(
        "1 sort bitvec 1\n2 sort bitvec 4\n3 state 2 counter\n"
        "4 constd 2 10\n5 ult 1 3 4\n6 bad 5\n"
    )
    output = tmp_path / "report"
    report = analyze([model], output, GenerationOptions(max_candidates=8, semantic=False))
    write_report(report, output)
    return report, output


def test_json_and_csv_preserve_fields_and_record_counts(report_files):
    report, output = report_files
    saved = json.loads((output / "results.json").read_text())
    assert saved["schema_version"] == 1
    assert set(saved) == {
        "schema_version", "tool", "created_utc", "configuration", "models", "summaries",
        "records", "errors", "scope_definitions", "trust_boundary", "duration_seconds",
    }
    assert saved["records"] == report["records"]
    expected_headers = {
        "summary.csv": [
            "model", "scope", "property_id", "nodes", "array_sorts", "candidates", "accepted",
            "rejected", "unknown", "vacuous", "extraction_seconds", "validation_seconds",
            "hypothesis_result", "hypothesis_seconds",
        ],
        "constraints.csv": [
            "id", "model", "scope", "family", "origin", "status", "expression",
            "validation_seconds", "reuse_from", "obligation",
        ],
        "families.csv": [
            "model", "scope", "family", "candidates", "accepted", "rejected", "unknown", "vacuous",
        ],
    }
    tables = {}
    for filename, headers in expected_headers.items():
        with (output / filename).open(newline="") as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == headers
            tables[filename] = list(reader)
    assert len(tables["summary.csv"]) == 2
    assert [row["id"] for row in tables["constraints.csv"]] == [row["id"] for row in saved["records"]]
    for row in tables["families.csv"]:
        matching = [record for record in saved["records"]
                    if record["scope"] == row["scope"] and record["family"] == row["family"]]
        assert int(row["candidates"]) == len(matching)
        for status in ("accepted", "rejected", "unknown", "vacuous"):
            assert int(row[status]) == sum(record["status"] == status for record in matching)


def test_html_escapes_data_and_contains_local_controls_and_evidence(report_files):
    report, output = report_files
    document = (output / "report.html").read_text()
    assert "counter<&>.btor2" not in document
    assert "counter&lt;&amp;&gt;.btor2" in document
    assert document.count('<details class="record"') == len(report["records"])
    assert 'id="search"' in document
    assert 'id="status"' in document
    assert '<script src=' not in document
    assert '<link ' not in document
    for record in report["records"]:
        assert f'href="{record["obligation"]}"' in document
    for filename in ("results.json", "summary.csv", "constraints.csv", "families.csv"):
        assert f'href="{filename}"' in document
