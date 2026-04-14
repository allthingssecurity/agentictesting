import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class VitestAdapter(BaseToolAdapter):
    name = "vitest"
    category = ToolCategory.UNIT_TEST
    languages = [Language.JAVASCRIPT, Language.TYPESCRIPT]
    binary = "npx"
    detect_files = ["vitest.config.ts", "vitest.config.js", "vite.config.ts"]

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        return ["npx", "vitest", "run", "--reporter=json"]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        tests = []
        try:
            data = json.loads(stdout)
            for file_result in data.get("testResults", []):
                for suite in file_result.get("assertionResults", []):
                    tests.append({
                        "name": suite.get("fullName", suite.get("title", "")),
                        "outcome": "passed" if suite.get("status") == "passed" else "failed",
                        "duration": suite.get("duration", 0) / 1000,
                    })
        except (json.JSONDecodeError, KeyError):
            pass

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
