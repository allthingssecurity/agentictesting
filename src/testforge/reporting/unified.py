"""Unified report builder — dispatches to format-specific writers."""

from pathlib import Path

from testforge.models.evidence import Report
from testforge.reporting.html_reporter import write_html_report
from testforge.reporting.json_reporter import write_json_report
from testforge.reporting.junit_xml import write_junit_xml


class UnifiedReportBuilder:
    """Write reports in multiple formats."""

    def __init__(self, output_dir: Path, formats: list[str] | None = None):
        self.output_dir = output_dir
        self.formats = formats or ["json", "html", "junit_xml"]

    def build(self, report: Report) -> dict[str, Path]:
        """Write report in all configured formats. Returns format → path mapping."""
        writers = {
            "json": write_json_report,
            "html": write_html_report,
            "junit_xml": write_junit_xml,
        }

        results = {}
        for fmt in self.formats:
            writer = writers.get(fmt)
            if writer:
                results[fmt] = writer(report, self.output_dir)

        return results
