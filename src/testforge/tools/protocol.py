from pathlib import Path
from typing import Protocol, runtime_checkable

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput


@runtime_checkable
class ToolAdapter(Protocol):
    """Protocol that all tool adapters must satisfy.

    Implement this directly or subclass BaseToolAdapter for convenience.
    Third-party adapters can implement this protocol without inheriting
    from any TestForge base class.
    """

    name: str
    category: ToolCategory
    languages: list[Language]
    binary: str

    def detect(self, project_root: Path) -> bool:
        """Return True if this tool is available and applicable to the project."""
        ...

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        """Build the CLI command list. Sandbox will wrap execution."""
        ...

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse raw CLI output into a structured ToolOutput."""
        ...

    @property
    def filesystem_mode(self) -> str:
        """'readonly' for SAST tools, 'readwrite' for test runners."""
        ...

    @property
    def default_timeout(self) -> int:
        """Default timeout in seconds for this tool."""
        ...
