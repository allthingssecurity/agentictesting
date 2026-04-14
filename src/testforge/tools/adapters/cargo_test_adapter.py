import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class CargoTestAdapter(BaseToolAdapter):
    name = "cargo-test"
    category = ToolCategory.UNIT_TEST
    languages = [Language.RUST]
    binary = "cargo"
    detect_files = ["Cargo.toml"]

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        return ["cargo", "test", "--message-format=json"]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse cargo test JSON message stream."""
        tests = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get("type") == "test":
                    event = msg.get("event", "")
                    tests.append({
                        "name": msg.get("name", ""),
                        "outcome": "passed" if event == "ok" else "failed",
                        "duration": msg.get("exec_time", 0),
                    })
                elif msg.get("type") == "suite" and msg.get("event") == "failed":
                    pass  # Suite-level summary
            except json.JSONDecodeError:
                continue

        # Fallback: parse from stderr (cargo test outputs to stderr)
        if not tests and "test result:" in stderr:
            for line in stderr.split("\n"):
                if line.strip().startswith("test ") and " ... " in line:
                    parts = line.strip().split(" ... ")
                    name = parts[0].replace("test ", "")
                    outcome = "passed" if "ok" in parts[-1] else "failed"
                    tests.append({"name": name, "outcome": outcome, "duration": 0})

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
