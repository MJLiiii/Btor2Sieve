"""Portable, escaped reports; no server or external frontend dependencies."""

from collections import Counter
import csv
import html
import json
from pathlib import Path


def write_report(report: dict, output: Path) -> None:
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    fields = ["model", "scope", "property_id", "nodes", "array_sorts", "candidates", "accepted",
              "rejected", "unknown", "vacuous", "extraction_seconds", "validation_seconds",
              "hypothesis_result", "hypothesis_seconds"]
    with (output / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["summaries"])
    with (output / "constraints.csv").open("w", newline="") as stream:
        fields = ["id", "model", "scope", "family", "origin", "status", "expression",
                  "validation_seconds", "reuse_from", "obligation"]
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["records"])
    with (output / "families.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, ["model", "scope", "family", "candidates", "accepted", "rejected", "unknown", "vacuous"])
        writer.writeheader()
        for summary in report["summaries"]:
            for family, counts in summary["families"].items():
                writer.writerow({"model": summary["model"], "scope": summary["scope"], "family": family,
                                 "candidates": sum(counts.values()),
                                 **{k: counts.get(k, 0) for k in ("accepted", "rejected", "unknown", "vacuous")}})
    (output / "report.html").write_text(render_html(report))


def render_html(report: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    base = [r for r in report["records"] if not r["reuse_from"]]
    counts = Counter(r["status"] for r in base)
    cards = "".join(f'<div class="card"><strong>{counts[k]:,}</strong><span>{k.title()}</span></div>'
                    for k in ("accepted", "rejected", "unknown", "vacuous"))
    summaries = []
    for row in report["summaries"]:
        summaries.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in [
            Path(row["model"]).name, row["scope"], "BV + arrays" if row["array_sorts"] else "BV",
            row["candidates"], row["accepted"], row["rejected"], row["unknown"], row["vacuous"],
            f'{row["extraction_seconds"]:.4f}', f'{row["validation_seconds"]:.4f}', row["hypothesis_result"]]) + "</tr>")
    records = []
    for r in report["records"]:
        reuse = f' · reused from {esc(r["reuse_from"])}' if r["reuse_from"] else ""
        reason = f'<p>{esc(r["reason"])}</p>' if r["reason"] else ""
        witness = f'<pre>{esc(json.dumps(r["counterexample"], indent=2))}</pre>' if r["counterexample"] else ""
        records.append(f'''<details class="record" data-status="{esc(r['status'])}">
<summary><span class="badge {esc(r['status'])}">{esc(r['status'])}</span>
{esc(Path(r['model']).name)} · {esc(r['scope'])} · {esc(r['family'])}{reuse}</summary>
<pre>{esc(r['expression'])}</pre><p>Origin: {esc(r['origin'])} · BTOR2 nodes: {esc(r['source_nodes'])}
 · {r['validation_seconds']:.5f}s · <a href="{esc(r['obligation'])}">SMT obligation</a></p>{reason}{witness}</details>''')
    scope_rows = "".join(f"<li><b>{esc(k)}</b> — {esc(v)}</li>" for k, v in report["scope_definitions"].items())
    warnings = [f'{m["path"]}: {w}' for m in report["models"] for w in m["warnings"]]
    warnings += [f'{e["model"]}: {e["error"]}' for e in report["errors"]]
    warning_html = "".join(f'<p class="warning">{esc(w)}</p>' for w in warnings)
    reuse_counts = dict(Counter(r["status"] for r in report["records"] if r["reuse_from"]))
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
<p class="muted">Generated {esc(report['created_utc'])} · Btor2Sieve {esc(report['tool']['version'])} · Z3 {esc(report['tool']['z3'])} · {report['duration_seconds']:.2f}s</p></header>
{warning_html}<div class="cards">{cards}</div>
<p class="muted">Counts exclude cross-property reuse checks. Accepted means a non-vacuous implication, not proof that the hardware property is safe. Syntactic facts and direct property atoms may be included; these counts do not measure novelty.</p>
<h2>Model and property results</h2><div class="tablewrap"><table><thead><tr><th>Model</th><th>Scope</th><th>Theory</th><th>Candidates</th><th>Accepted</th><th>Rejected</th><th>Unknown</th><th>Vacuous</th><th>Extract (s)</th><th>Validate (s)</th><th>Hypothesis</th></tr></thead><tbody>{''.join(summaries)}</tbody></table></div>
<p>Cross-property revalidation: {esc(reuse_counts or 'not requested / no eligible source constraints')}. Each target uses its own safety predicate.</p>
<h2>What each result establishes</h2><ul>{scope_rows}</ul>
<p>Vacuous implications have an inconsistent hypothesis and are excluded from accepted counts. Unknown results establish no accepted constraint. This tool does not add property-derived constraints to a model's assumptions.</p>
<h2>Inspect the constraints</h2><div class="controls"><input id="search" aria-label="Search constraints" placeholder="Search models, expressions, families…"><select id="status" aria-label="Filter by status"><option value="">All statuses</option><option>accepted</option><option>rejected</option><option>unknown</option><option>vacuous</option></select></div>
<p id="visible" class="muted"></p>{''.join(records)}
<footer><a href="results.json">Full JSON evidence</a> · <a href="summary.csv">Summary CSV</a> · <a href="families.csv">Family CSV</a> · <a href="constraints.csv">Constraint CSV</a><br>
{esc(report['trust_boundary'])}. Replay with the CLI; artifact hashes detect changed obligations.</footer>
</main><script>
const search=document.getElementById('search'),status=document.getElementById('status'),records=[...document.querySelectorAll('.record')];
function filter(){{let count=0;for(const r of records){{const show=(!status.value||r.dataset.status===status.value)&&r.textContent.toLowerCase().includes(search.value.toLowerCase());r.hidden=!show;if(show)count++;}}document.getElementById('visible').textContent=count+' of '+records.length+' constraints shown';}}
search.addEventListener('input',filter);status.addEventListener('change',filter);filter();
</script></body></html>'''
