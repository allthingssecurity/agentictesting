import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput


class BaseToolAdapter(ABC):
    """Convenience ABC implementing common detection logic.

    Subclass this for built-in adapters. Third-party adapters can
    implement ToolAdapter protocol directly instead.
    """

    name: str = ""
    category: ToolCategory = ToolCategory.UNIT_TEST
    languages: list[Language] = []
    binary: str = ""

    # Override in subclasses for project-specific detection files
    # e.g. ["pyproject.toml", "setup.py"] for pytest
    detect_files: list[str] = []

    def detect(self, project_root: Path) -> bool:
        """Check binary on PATH and project-specific files exist."""
        if not shutil.which(self.binary):
            return False
        if self.detect_files:
            return any((project_root / f).exists() for f in self.detect_files)
        return True

    @abstractmethod
    def build_command(self, project_root: Path, config: dict) -> list[str]:
        ...

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        ...

    @property
    def filesystem_mode(self) -> str:
        if self.category in (ToolCategory.SAST, ToolCategory.LINT):
            return "readonly"
        return "readwrite"

    @property
    def default_timeout(self) -> int:
        return 120
