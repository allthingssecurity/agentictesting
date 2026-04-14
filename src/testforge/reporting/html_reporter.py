"""HTML report writer with dark theme dashboard."""

from pathlib import Path
from string import Template

from testforge.models.enums import Status
from testforge.models.evidence import Report

HTML_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TestForge Report</title>
<style>
  :root { --bg: #0a0a0a; --card: #141414; --border: #2a2a2a; --text: #e0e0e0;
          --green: #22c55e; --red: #ef4444; --yellow: #eab308; --blue: #3b82f6; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
         padding: 2rem; max-width: 1200px; margin: 0 auto; }
  h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
  .meta { color: #888; margin-bottom: 2rem; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
           gap: 1rem; margin-bottom: 2rem; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
          padding: 1.2rem; text-align: center; }
  .stat .value { font-size: 2rem; font-weight: bold; }
  .stat .label { color: #888; font-size: 0.85rem; margin-top: 0.3rem; }
  .pass-rate .value { color: var(--green); }
  .fail-count .value { color: var(--red); }
  .lang-count .value { color: var(--blue); }
  table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
  th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }
  th { background: var(--card); color: #aaa; font-size: 0.8rem; text-transform: uppercase; }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-passed { background: #166534; color: #bbf7d0; }
  .badge-failed { background: #7f1d1d; color: #fecaca; }
  .badge-healed { background: #1e3a5f; color: #93c5fd; }
  .badge-skipped { background: #3f3f46; color: #d4d4d8; }
  .badge-error { background: #7f1d1d; color: #fecaca; }
  .badge-critical { background: #7f1d1d; color: #fecaca; }
  .badge-high { background: #92400e; color: #fed7aa; }
  .badge-medium { background: #854d0e; color: #fef08a; }
  .badge-low { background: #1e3a5f; color: #93c5fd; }
  .badge-info { background: #3f3f46; color: #d4d4d8; }
  .section-title { font-size: 1.2rem; margin: 2rem 0 1rem; padding-bottom: 0.5rem;
                   border-bottom: 1px solid var(--border); }
  .summary { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
             padding: 1.5rem; margin-bottom: 2rem; line-height: 1.6; }
</style>
</head>
<body>
<h1>TestForge v0.5 Report</h1>
<p class="meta">Generated: $generated_at</p>

<div class="stats">
  <div class="stat pass-rate"><div class="value">$pass_rate_pct</div><div class="label">Pass Rate</div></div>
  <div class="stat"><div class="value">$total_tests</div><div class="label">Total Tests</div></div>
  <div class="stat fail-count"><div class="value">$failed_count</div><div class="label">Failures</div></div>
  <div class="stat lang-count"><div class="value">$languages_count</div><div class="label">Languages</div></div>
  <div class="stat"><div class="value">$findings_count</div><div class="label">Findings</div></div>
  <div class="stat"><div class="value">$tools_count</div><div class="label">Tools Used</div></div>
</div>

<div class="summary">$summary</div>

<h2 class="section-title">Test Results</h2>
<table>
<thead><tr><th>Language</th><th>Tool</th><th>Type</th><th>Name</th><th>Status</th><th>Duration</th></tr></thead>
<tbody>$results_rows</tbody>
</table>

$findings_section
</body>
</html>
""")


def write_html_report(report: Report, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(report.results)
    passed = sum(1 for r in report.results if r.status == Status.PASSED)
    failed = sum(1 for r in report.results if r.status in (Status.FAILED, Status.ERROR))
    pass_rate = passed / total if total > 0 else 0.0

    languages = set(r.language for r in report.results if r.language)
    tools_used = set(r.tool_adapter for r in report.results if r.tool_adapter)

    results_rows = ""
    for r in report.results:
        badge = r.status.value
        results_rows += (
            f"<tr><td>{r.language or '-'}</td><td>{r.tool_adapter or '-'}</td>"
            f"<td>{r.test_type}</td><td>{r.name}</td>"
            f"<td><span class='badge badge-{badge}'>{badge}</span></td>"
            f"<td>{r.duration_ms:.0f}ms</td></tr>\n"
        )

    findings_section = ""
    if report.findings:
        findings_section = "<h2 class='section-title'>Findings</h2>\n<table>\n"
        findings_section += "<thead><tr><th>Severity</th><th>Category</th><th>Test</th><th>Recommendation</th><th>Healed</th></tr></thead>\n<tbody>\n"
        for f in report.findings:
            findings_section += (
                f"<tr><td><span class='badge badge-{f.severity}'>{f.severity}</span></td>"
                f"<td>{f.category}</td><td>{f.test_result.name}</td>"
                f"<td>{f.recommendation[:200]}</td>"
                f"<td>{'Yes' if f.healed else 'No'}</td></tr>\n"
            )
        findings_section += "</tbody></table>"

    html = HTML_TEMPLATE.substitute(
        generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        pass_rate_pct=f"{pass_rate:.0%}",
        total_tests=total,
        failed_count=failed,
        languages_count=len(languages),
        findings_count=len(report.findings),
        tools_count=len(tools_used),
        summary=report.summary,
        results_rows=results_rows,
        findings_section=findings_section,
    )

    path = output_dir / "report.html"
    path.write_text(html)
    return path
