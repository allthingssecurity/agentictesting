import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter

MAX_OUTPUT = 4000


class SemgrepAdapter(BaseToolAdapter):
    name = "semgrep"
    category = ToolCategory.SAST
    languages = [
        Language.PYTHON, Language.JAVASCRIPT, Language.TYPESCRIPT,
        Language.GO, Language.RUST, Language.JAVA, Language.KOTLIN,
        Language.RUBY, Language.CSHARP, Language.CPP,
    ]
    binary = "semgrep"

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        rules = config.get("rules", "auto")
        target = config.get("target_path", str(project_root))
        return ["semgrep", "scan", "--json", "--config", rules, target]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        findings = []
        total = 0
        try:
            data = json.loads(stdout)
            results = data.get("results", [])
            total = len(results)
            for f in results[:50]:
                findings.append({
                    "check_id": f.get("check_id", ""),
                    "path": f.get("path", ""),
                    "line": f.get("start", {}).get("line", 0),
                    "message": f.get("extra", {}).get("message", "")[:500],
                    "severity": f.get("extra", {}).get("severity", ""),
                })
        except (json.JSONDecodeError, KeyError):
            pass

        return ToolOutput(
            tool_name=self.name,
            exit_code=exit_code,
            success=total == 0,
            findings=findings,
            summary=f"{total} findings",
            stdout=stdout[:MAX_OUTPUT],
            stderr=stderr[:MAX_OUTPUT],
            raw_data={"total_findings": total},
        )
