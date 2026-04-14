import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class JestAdapter(BaseToolAdapter):
    name = "jest"
    category = ToolCategory.UNIT_TEST
    languages = [Language.JAVASCRIPT, Language.TYPESCRIPT]
    binary = "npx"
    detect_files = ["package.json", "jest.config.js", "jest.config.ts"]

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        cmd = ["npx", "jest", "--json", "--forceExit"]
        test_path = config.get("test_path", "")
        if test_path:
            cmd.append(test_path)
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        tests = []
        summary = ""
        try:
            data = json.loads(stdout)
            for suite in data.get("testResults", []):
                for t in suite.get("testResults", []):
                    tests.append({
                        "name": t.get("fullName", t.get("title", "")),
                        "outcome": "passed" if t.get("status") == "passed" else "failed",
                        "duration": t.get("duration", 0) / 1000,
                        "message": "\n".join(t.get("failureMessages", []))[:500],
                    })
            s = data.get("numPassedTests", 0)
            f = data.get("numFailedTests", 0)
            summary = f"{s} passed, {f} failed"
        except (json.JSONDecodeError, KeyError):
            summary = stderr[:1000]

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests, summary=summary,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
