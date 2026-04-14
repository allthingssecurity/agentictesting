import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class GoTestAdapter(BaseToolAdapter):
    name = "go-test"
    category = ToolCategory.UNIT_TEST
    languages = [Language.GO]
    binary = "go"
    detect_files = ["go.mod"]

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        pkg = config.get("package", "./...")
        return ["go", "test", "-json", pkg]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse newline-delimited JSON events from `go test -json`."""
        tests: dict[str, dict] = {}
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                event = json.loads(line)
                action = event.get("Action", "")
                test_name = event.get("Test", "")
                pkg = event.get("Package", "")
                if not test_name:
                    continue
                key = f"{pkg}::{test_name}"
                if action in ("pass", "fail", "skip"):
                    tests[key] = {
                        "name": key,
                        "outcome": "passed" if action == "pass" else "failed" if action == "fail" else "skipped",
                        "duration": event.get("Elapsed", 0),
                    }
            except json.JSONDecodeError:
                continue

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=list(tests.values()),
            summary=f"{sum(1 for t in tests.values() if t['outcome'] == 'passed')}/{len(tests)} passed",
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
