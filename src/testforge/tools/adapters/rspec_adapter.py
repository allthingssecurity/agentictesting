import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class RspecAdapter(BaseToolAdapter):
    name = "rspec"
    category = ToolCategory.UNIT_TEST
    languages = [Language.RUBY]
    binary = "rspec"
    detect_files = ["Gemfile", ".rspec", "spec/"]

    def detect(self, project_root: Path) -> bool:
        import shutil
        if not shutil.which(self.binary):
            return False
        return (project_root / "spec").is_dir() or (project_root / "Gemfile").exists()

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        return ["rspec", "--format", "json"]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        tests = []
        try:
            data = json.loads(stdout)
            for example in data.get("examples", []):
                tests.append({
                    "name": example.get("full_description", ""),
                    "outcome": "passed" if example.get("status") == "passed" else "failed",
                    "duration": example.get("run_time", 0),
                    "message": example.get("exception", {}).get("message", "")[:500] if example.get("exception") else "",
                })
        except (json.JSONDecodeError, KeyError):
            pass

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
