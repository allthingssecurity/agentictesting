"""JSON report writer."""

from pathlib import Path

from testforge.models.evidence import Report


def write_json_report(report: Report, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "report.json"
    path.write_text(report.model_dump_json(indent=2))
    return path
