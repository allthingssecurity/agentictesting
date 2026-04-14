import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter

MAX_OUTPUT = 4000


class PlaywrightAdapter(BaseToolAdapter):
    name = "playwright"
    category = ToolCategory.E2E_TEST
    languages = [Language.JAVASCRIPT, Language.TYPESCRIPT, Language.PYTHON]
    binary = "npx"
    detect_files = ["playwright.config.ts", "playwright.config.js"]

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        test_path = config.get("test_path", "")
        cmd = ["npx", "playwright", "test", "--reporter=json"]
        if test_path:
            cmd.insert(3, test_path)
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        tests = []
        try:
            report = json.loads(stdout)
            for suite in report.get("suites", []):
                for spec in suite.get("specs", []):
                    for t in spec.get("tests", []):
                        for r in t.get("results", []):
                            tests.append({
                                "name": spec.get("title", ""),
                                "outcome": r.get("status", ""),
                                "duration": r.get("duration", 0),
                            })
        except (json.JSONDecodeError, KeyError):
            pass

        passed = sum(1 for t in tests if t["outcome"] == "passed")
        return ToolOutput(
            tool_name=self.name,
            exit_code=exit_code,
            success=exit_code == 0,
            tests=tests,
            summary=f"{passed}/{len(tests)} passed",
            stdout=stdout[:MAX_OUTPUT],
            stderr=stderr[:MAX_OUTPUT],
        )

    @property
    def default_timeout(self) -> int:
        return 180
