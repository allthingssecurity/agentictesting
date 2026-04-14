from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter

MAX_OUTPUT = 4000


class SchemathesisAdapter(BaseToolAdapter):
    name = "schemathesis"
    category = ToolCategory.API_FUZZ
    languages = []  # Language-agnostic, targets OpenAPI specs
    binary = "st"
    detect_files = ["openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json"]

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        spec = config.get("openapi_url", config.get("openapi_spec", "openapi.yaml"))
        base_url = config.get("base_url", "")
        cmd = ["st", "run", str(spec)]
        if base_url:
            cmd.extend(["--base-url", base_url])
        for arg in config.get("extra_args", []):
            cmd.append(arg)
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        return ToolOutput(
            tool_name=self.name,
            exit_code=exit_code,
            success=exit_code == 0,
            summary="API fuzz passed" if exit_code == 0 else "API fuzz found issues",
            stdout=stdout[:MAX_OUTPUT],
            stderr=stderr[:MAX_OUTPUT],
        )
