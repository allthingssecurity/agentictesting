from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float = 0.0


class NetworkPolicy(BaseModel):
    allowed_urls: list[str] = []
    block_all: bool = False


class FilesystemPolicy(BaseModel):
    mode: str = "readwrite"  # "readonly" or "readwrite"
    allowed_paths: list[str] = []


class SandboxExecutor(Protocol):
    def execute(
        self,
        command: list[str],
        project_root: Path,
        timeout: int = 120,
        filesystem_mode: str = "readwrite",
        network_policy: NetworkPolicy | None = None,
    ) -> SandboxResult: ...

    def is_available(self) -> bool: ...
