"""Write results as JSON, CSV, and one self-contained, escaped HTML page.

No server or external frontend dependencies are needed to view a report.
"""

from collections import Counter
from collections.abc import Iterable, Iterator
import csv
import html
import json
from pathlib import Path


STATUSES = ("accepted", "rejected", "unknown", "vacuous")
SUMMARY_FIELDS = [
    "model", "scope", "property_id", "nodes", "array_sorts", "candidates", "accepted",
    "rejected", "unknown", "vacuous", "extraction_seconds", "validation_seconds",
    "hypothesis_result", "hypothesis_seconds",
]
CONSTRAINT_FIELDS = [
    "id", "model", "scope", "family", "origin", "status", "expression",
    "validation_seconds", "reuse_from", "obligation",
]
FAMILY_FIELDS = [
    "model", "scope", "family", "candidates", "accepted", "rejected", "unknown", "vacuous",
]


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def family_rows(summaries: list[dict]) -> Iterator[dict]:
    """One CSV row per (model, scope, family) with counts by status."""
    for summary in summaries:
        for family, counts in summary["families"].items():
            yield {
                "model": summary["model"], "scope": summary["scope"], "family": family,
                "candidates": sum(counts.values()),
                **{status: counts.get(status, 0) for status in STATUSES},
            }


def write_report(report: dict, output: Path) -> None:
    """Write the evidence and a self-contained HTML view to an existing run directory."""
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    _write_csv(output / "summary.csv", SUMMARY_FIELDS, report["summaries"])
    _write_csv(output / "constraints.csv", CONSTRAINT_FIELDS, report["records"])
    _write_csv(output / "families.csv", FAMILY_FIELDS, family_rows(report["summaries"]))
    (output / "report.html").write_text(render_html(report))


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _render_summary(row: dict) -> str:
    values = [
        Path(row["model"]).name, row["scope"], "BV + arrays" if row["array_sorts"] else "BV",
        row["candidates"], row["accepted"], row["rejected"], row["unknown"], row["vacuous"],
        f'{row["extraction_seconds"]:.4f}', f'{row["validation_seconds"]:.4f}', row["hypothesis_result"],
    ]
    return _row(values)


def _render_record(r: dict) -> str:
    reuse = f' · reused from {_escape(r["reuse_from"])}' if r["reuse_from"] else ""
    reason = f'<p>{_escape(r["reason"])}</p>' if r["reason"] else ""
    witness = f'<pre>{_escape(json.dumps(r["counterexample"], indent=2))}</pre>' if r["counterexample"] else ""
    return f'''<details class="record" data-status="{_escape(r['status'])}">
<summary><span class="badge {_escape(r['status'])}">{_escape(r['status'])}</span>
{_escape(Path(r['model']).name)} · {_escape(r['scope'])} · {_escape(r['family'])}{reuse}</summary>
<pre>{_escape(r['expression'])}</pre><p>Origin: {_escape(r['origin'])} · BTOR2 nodes: {_escape(r['source_nodes'])}
 · {r['validation_seconds']:.5f}s · <a href="{_escape(r['obligation'])}">SMT obligation</a></p>{reason}{witness}</details>'''


def _row(values: Iterable[object]) -> str:
    return "<tr>" + "".join(f"<td>{_escape(value)}</td>" for value in values) + "</tr>"


def _render_implied_search(summaries: list[dict]) -> str:
    native = [summary for summary in summaries
              if summary.get("search", {}).get("kind") == "property-word-level"]
    if not native:
        return ""
    rows = []
    for summary in native:
        search = summary["search"]
        complete = search["complete"] and search["validation_complete"]
        if search.get("coverage") == "budgeted":
            coverage = f"budgeted search {'completed' if complete else 'partial'}"
        else:
            coverage = "complete" if complete else "partial"
        reason = "; ".join(filter(None, [search["reason"], ", ".join(search.get("budget_exhausted", []))]))
        rows.append(_row([Path(summary["model"]).name, summary["scope"], search["term_count"],
                          search["predicate_count"], search["total_candidates"],
                          search["discovery_queries"], search["discovery_unknown"], coverage,
                          "yes" if search["validation_complete"] else "no", reason]))
    families = [_row([Path(row["model"]).name, row["scope"], row["family"], row["candidates"],
                      *(row[status] for status in STATUSES)])
                for row in family_rows(native)]
    return ("<h2>Property word-level search</h2><p>Coverage refers to the finite template "
            "procedure over native terms in this property's dependency cone. It does not "
            "claim all possible word-level consequences. Every proposal is independently "
            "checked under P = not bad. Rejected proposals are resolved checks; unknown "
            "discovery, hypothesis, or validation results leave coverage partial. In the "
            "matched profile, 'budgeted search completed' means execution finished within "
            "the configured limits; it does not claim full dependency-cone coverage. "
            "Budget exhaustion is reported separately from UNKNOWN.</p>"
            '<div class="tablewrap"><table><thead><tr><th>Model</th><th>Scope</th>'
            "<th>Native terms</th><th>Predicates</th><th>Proposals</th><th>Discovery queries</th>"
            "<th>Discovery unknown</th><th>Coverage</th><th>Validation complete</th><th>Reason</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<h2>Constraint families</h2><p>Counts describe independently validated proposals, "
            "including bounds, equalities, disequalities, implications, masks, and array relations.</p>"
            '<div class="tablewrap"><table><thead><tr><th>Model</th><th>Scope</th>'
            "<th>Family</th><th>Candidates</th><th>Accepted</th><th>Rejected</th><th>Unknown</th>"
            "<th>Vacuous</th></tr></thead><tbody>" + "".join(families)
            + "</tbody></table></div>")


def render_html(report: dict) -> str:
    base = [r for r in report["records"] if not r["reuse_from"]]
    counts = Counter(r["status"] for r in base)
    cards = "".join(f'<div class="card"><strong>{counts[k]:,}</strong><span>{k.title()}</span></div>'
                    for k in STATUSES)
    summaries = "".join(_render_summary(row) for row in report["summaries"])
    records = "".join(_render_record(row) for row in report["records"])
    scope_rows = "".join(f"<li><b>{_escape(k)}</b> — {_escape(v)}</li>" for k, v in report["scope_definitions"].items())
    warnings = [f'{m["path"]}: {w}' for m in report["models"] for w in m["warnings"]]
    warnings += [f'{e["model"]}: {e["error"]}' for e in report["errors"]]
    warning_html = "".join(f'<p class="warning">{_escape(w)}</p>' for w in warnings)
    reuse_counts = dict(Counter(r["status"] for r in report["records"] if r["reuse_from"]))
    workflow = report["configuration"].get("implied_workflow")
    workflow_html = f"<p>Workflow: {_escape(workflow)}</p>" if workflow else ""
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Btor2Sieve · Constraint report</title><style>
:root{{color-scheme:light;--ink:#18313d;--muted:#54717c;--line:#d7e3e6;--accent:#096b63}}
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7f6;color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
main{{max-width:1260px;margin:auto;padding:44px 28px}}header{{border-top:5px solid var(--accent);padding:24px 0 8px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--accent);font-weight:700}}
h1{{font-size:40px;line-height:1.2;margin:8px 0}}h2{{font-size:22px;margin:30px 0 12px}}
p{{max-width:920px}}.muted{{color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}}
.card{{background:white;border:1px solid var(--line);border-radius:10px;padding:18px}}.card strong{{display:block;font-size:30px}}.card span{{color:var(--muted)}}
.tablewrap{{overflow:auto;background:white;border:1px solid var(--line);border-radius:8px}}table{{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}}th,td{{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line)}}th{{background:#e8f0ef;font-weight:650}}td:nth-child(n+4){{font-variant-numeric:tabular-nums}}
.controls{{display:flex;gap:12px;margin:18px 0}}input,select{{font:inherit;padding:10px 12px;border:1px solid #9db6bc;border-radius:6px;background:white}}input{{flex:1;min-width:0}}
.record{{background:white;border:1px solid var(--line);border-radius:6px;margin:8px 0;padding:12px 16px}}summary{{cursor:pointer}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf3f4;padding:14px;border-radius:4px;font:13px/1.5 ui-monospace,monospace}}
.badge{{display:inline-block;font-size:12px;border-radius:4px;padding:2px 7px;margin-right:8px;background:#e8edf0}}.accepted{{background:#dcf4e9;color:#176447}}.rejected{{background:#ffe8dc;color:#984722}}.unknown,.vacuous{{background:#fff2cf;color:#795f09}}
a{{color:var(--accent)}}.warning{{padding:12px;border-left:4px solid #bd6d1d;background:#fff0df}}footer{{margin-top:35px;border-top:1px solid var(--line);padding:20px 0;color:var(--muted);font-size:13px}}
@media(max-width:650px){{main{{padding:24px 14px}}h1{{font-size:30px}}.cards{{grid-template-columns:repeat(2,1fr)}}.controls{{flex-direction:column}}}}
</style></head><body><main>
<header><div class="eyebrow">Word-level analysis · auditable SMT evidence</div><h1>Btor2Sieve</h1>
<p>Constraint extraction report for {len(report['models'])} model(s). Every accepted implication was checked with a fresh SMT solver.</p>
<p>Method: {_escape(report['configuration'].get('method', 'implied'))}</p>
{workflow_html}
<p class="muted">Generated {_escape(report['created_utc'])} · Btor2Sieve {_escape(report['tool']['version'])} · Z3 {_escape(report['tool']['z3'])} · {report['duration_seconds']:.2f}s</p></header>
{warning_html}<div class="cards">{cards}</div>
<p class="muted">Counts exclude cross-property reuse checks. Accepted means a non-vacuous implication, not proof that the hardware property is safe. Syntactic facts and direct property atoms may be included; these counts do not measure novelty.</p>
{_render_implied_search(report['summaries'])}
<h2>Model and property results</h2><div class="tablewrap"><table><thead><tr><th>Model</th><th>Scope</th><th>Theory</th><th>Candidates</th><th>Accepted</th><th>Rejected</th><th>Unknown</th><th>Vacuous</th><th>Extract (s)</th><th>Validate (s)</th><th>Hypothesis</th></tr></thead><tbody>{summaries}</tbody></table></div>
<p>Cross-property revalidation: {_escape(reuse_counts or 'not requested / no eligible source constraints')}. Each target uses its own safety predicate.</p>
<h2>What each result establishes</h2><ul>{scope_rows}</ul>
<p>Vacuous implications have an inconsistent hypothesis and are excluded from accepted counts. Unknown results establish no accepted constraint. This tool does not add property-derived constraints to a model's assumptions.</p>
<h2>Inspect the constraints</h2><div class="controls"><input id="search" aria-label="Search constraints" placeholder="Search models, expressions, families…"><select id="status" aria-label="Filter by status"><option value="">All statuses</option><option>accepted</option><option>rejected</option><option>unknown</option><option>vacuous</option></select></div>
<p id="visible" class="muted"></p>{records}
<footer><a href="results.json">Full JSON evidence</a> · <a href="summary.csv">Summary CSV</a> · <a href="families.csv">Family CSV</a> · <a href="constraints.csv">Constraint CSV</a><br>
{_escape(report['trust_boundary'])}. Replay with the CLI; artifact hashes detect changed obligations.</footer>
</main><script>
const search=document.getElementById('search'),status=document.getElementById('status'),records=[...document.querySelectorAll('.record')];
function filter(){{let count=0;for(const r of records){{const show=(!status.value||r.dataset.status===status.value)&&r.textContent.toLowerCase().includes(search.value.toLowerCase());r.hidden=!show;if(show)count++;}}document.getElementById('visible').textContent=count+' of '+records.length+' constraints shown';}}
search.addEventListener('input',filter);status.addEventListener('change',filter);filter();
</script></body></html>'''
