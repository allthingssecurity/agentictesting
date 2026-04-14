import json
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter

MAX_OUTPUT = 4000


class NucleiAdapter(BaseToolAdapter):
    name = "nuclei"
    category = ToolCategory.DAST
    languages = []  # Language-agnostic, targets URLs
    binary = "nuclei"

    def detect(self, project_root: Path) -> bool:
        import shutil
        return bool(shutil.which(self.binary))

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        target = config.get("target_url", "http://localhost:8000")
        cmd = ["nuclei", "-u", target, "-jsonl", "-silent"]
        templates = config.get("templates", "")
        if templates:
            cmd.extend(["-t", templates])
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        findings = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                f = json.loads(line)
                findings.append({
                    "template_id": f.get("template-id", ""),
                    "name": f.get("info", {}).get("name", ""),
                    "severity": f.get("info", {}).get("severity", ""),
                    "matched_at": f.get("matched-at", ""),
                    "description": f.get("info", {}).get("description", "")[:500],
                })
            except json.JSONDecodeError:
                continue

        return ToolOutput(
            tool_name=self.name,
            exit_code=exit_code,
            success=len(findings) == 0,
            findings=findings[:50],
            summary=f"{len(findings)} vulnerabilities",
            stdout=stdout[:MAX_OUTPUT],
            stderr=stderr[:MAX_OUTPUT],
        )

    @property
    def default_timeout(self) -> int:
        return 180
