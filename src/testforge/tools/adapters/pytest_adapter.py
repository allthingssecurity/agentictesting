import json
import tempfile
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter

MAX_OUTPUT = 4000


class PytestAdapter(BaseToolAdapter):
    name = "pytest"
    category = ToolCategory.UNIT_TEST
    languages = [Language.PYTHON]
    binary = "pytest"
    detect_files = ["pyproject.toml", "setup.py", "setup.cfg", "pytest.ini", "tox.ini", "conftest.py"]

    def detect(self, project_root: Path) -> bool:
        if not super().detect(project_root):
            # Also detect if tests/ directory exists with .py files
            import shutil
            if shutil.which(self.binary) and (project_root / "tests").is_dir():
                return True
            return False
        return True

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        _, report_path = tempfile.mkstemp(suffix=".json")
        self._report_path = report_path
        cmd = [
            "pytest", str(config.get("test_path", "tests/")),
            "-q", "--tb=short",
            "--json-report", f"--json-report-file={report_path}",
        ]
        markers = config.get("markers", "")
        if markers:
            cmd.extend(["-m", markers])
        for arg in config.get("extra_args", []):
            cmd.append(arg)
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        tests = []
        summary = ""
        raw = {}

        report_path = getattr(self, "_report_path", None)
        if report_path and Path(report_path).exists():
            try:
                raw = json.loads(Path(report_path).read_text())
                for t in raw.get("tests", []):
                    call = t.get("call", {}) or {}
                    tests.append({
                        "name": t.get("nodeid", ""),
                        "outcome": t.get("outcome", ""),
                        "duration": t.get("duration", 0),
                        "message": call.get("longrepr", "")[:1000],
                    })
                s = raw.get("summary", {})
                summary = f"{s.get('passed', 0)} passed, {s.get('failed', 0)} failed, {s.get('total', 0)} total"
            except (json.JSONDecodeError, OSError):
                pass
            finally:
                Path(report_path).unlink(missing_ok=True)

        return ToolOutput(
            tool_name=self.name,
            exit_code=exit_code,
            success=exit_code == 0,
            tests=tests,
            summary=summary or stdout[:MAX_OUTPUT],
            stdout=stdout[:MAX_OUTPUT],
            stderr=stderr[:MAX_OUTPUT],
            raw_data={"report_summary": raw.get("summary", {})},
        )
