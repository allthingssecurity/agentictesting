"""Reporter node — delegates to UnifiedReportBuilder for multi-format output."""

from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage

from testforge.models.enums import Status
from testforge.models.evidence import Report
from testforge.reporting.unified import UnifiedReportBuilder
from testforge.state import TestForgeState


def reporter_node(state: TestForgeState) -> dict:
    plan = state["plan"]
    results = state.get("results", [])
    healed = state.get("healed_results", [])
    findings = state.get("findings", [])

    total = len(results)
    passed = sum(1 for r in results if r.status == Status.PASSED)
    failed = sum(1 for r in results if r.status in (Status.FAILED, Status.ERROR))
    pass_rate = passed / total if total > 0 else 0.0

    healed_names = {r.name for r in healed if r.status == Status.HEALED}
    languages = set(r.language for r in results if r.language)
    tools_used = set(r.tool_adapter for r in results if r.tool_adapter)

    summary_parts = [
        f"Ran {total} tests across {len(languages)} languages ({', '.join(sorted(languages)) or 'none'}).",
        f"Tools: {', '.join(sorted(tools_used)) or 'none'}.",
        f"{passed} passed, {failed} failed, {len(healed_names)} healed.",
    ]
    if findings:
        by_sev = {}
        for f in findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        summary_parts.append("Findings: " + ", ".join(f"{v} {k}" for k, v in sorted(by_sev.items())))
    summary = " ".join(summary_parts)

    report = Report(
        plan=plan,
        results=results,
        findings=findings,
        summary=summary,
        pass_rate=pass_rate,
        generated_at=datetime.now(),
    )

    # Write reports in all formats
    artifacts_dir = Path(state["project_root"]) / "artifacts"
    formats = state.get("manifest", {}).get("reporting", {}).get("formats", ["json", "html", "junit_xml"])
    builder = UnifiedReportBuilder(artifacts_dir, formats=formats)
    output_paths = builder.build(report)

    paths_str = "\n".join(f"  {fmt}: {path}" for fmt, path in output_paths.items())

    return {
        "report": report,
        "messages": [HumanMessage(content=f"Report generated:\n{paths_str}\nSummary: {summary}")],
    }
