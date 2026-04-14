from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class DotnetTestAdapter(BaseToolAdapter):
    """dotnet test for C# / .NET projects. Outputs TRX (XML), parsed from stdout."""
    name = "dotnet-test"
    category = ToolCategory.UNIT_TEST
    languages = [Language.CSHARP]
    binary = "dotnet"
    detect_files = ["*.csproj", "*.sln"]

    def detect(self, project_root: Path) -> bool:
        import shutil
        if not shutil.which("dotnet"):
            return False
        return bool(list(project_root.glob("*.csproj")) or list(project_root.glob("*.sln")))

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        return ["dotnet", "test", "--verbosity", "normal"]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        # dotnet test outputs to stdout in human-readable format
        # TRX XML requires --logger trx; for now parse stdout
        tests = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("Passed") or line.startswith("Failed"):
                parts = line.split()
                if len(parts) >= 2:
                    tests.append({
                        "name": parts[1] if len(parts) > 1 else "unknown",
                        "outcome": "passed" if parts[0] == "Passed" else "failed",
                        "duration": 0,
                    })

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
