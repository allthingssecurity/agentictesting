"""Subprocess-based sandbox with timeout and basic resource limits."""

import subprocess
import time
from pathlib import Path

from testforge.sandbox.protocol import NetworkPolicy, SandboxResult

MAX_OUTPUT = 8000


class SubprocessSandbox:
    """Execute tools as subprocesses with timeout enforcement.

    On macOS: timeout only (no cgroups).
    On Linux: could add resource.setrlimit in preexec_fn (not implemented yet).
    """

    def execute(
        self,
        command: list[str],
        project_root: Path,
        timeout: int = 120,
        filesystem_mode: str = "readwrite",
        network_policy: NetworkPolicy | None = None,
    ) -> SandboxResult:
        start = time.monotonic()

        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root),
            )
            duration_ms = (time.monotonic() - start) * 1000

            return SandboxResult(
                stdout=proc.stdout[:MAX_OUTPUT],
                stderr=proc.stderr[:MAX_OUTPUT],
                exit_code=proc.returncode,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s: {' '.join(command)}",
                exit_code=-1,
                duration_ms=duration_ms,
            )

        except FileNotFoundError:
            return SandboxResult(
                stdout="",
                stderr=f"Command not found: {command[0]}",
                exit_code=-1,
                duration_ms=0,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout="",
                stderr=f"Sandbox error: {e}",
                exit_code=-1,
                duration_ms=duration_ms,
            )

    def is_available(self) -> bool:
        return True
