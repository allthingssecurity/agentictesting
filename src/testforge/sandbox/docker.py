"""Docker-based sandbox for isolated tool execution."""

import shutil
import subprocess
import time
from pathlib import Path

from testforge.sandbox.protocol import NetworkPolicy, SandboxResult

MAX_OUTPUT = 8000


class DockerSandbox:
    """Execute tools inside Docker containers with filesystem and network isolation."""

    def __init__(self, image: str = "testforge/sandbox:latest"):
        self.image = image

    def execute(
        self,
        command: list[str],
        project_root: Path,
        timeout: int = 120,
        filesystem_mode: str = "readwrite",
        network_policy: NetworkPolicy | None = None,
    ) -> SandboxResult:
        mount_flag = "ro" if filesystem_mode == "readonly" else "rw"
        network = "none" if (network_policy and network_policy.block_all) else "bridge"

        docker_cmd = [
            "docker", "run", "--rm",
            f"--network={network}",
            f"-v", f"{project_root}:/workspace:{mount_flag}",
            "-w", "/workspace",
            "--memory=512m",
            "--cpus=2",
            self.image,
        ] + command

        start = time.monotonic()
        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout=proc.stdout[:MAX_OUTPUT],
                stderr=proc.stderr[:MAX_OUTPUT],
                exit_code=proc.returncode,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr=f"Docker command timed out after {timeout}s",
                exit_code=-1,
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return SandboxResult(
                stdout="", stderr=f"Docker error: {e}", exit_code=-1, duration_ms=0,
            )

    def is_available(self) -> bool:
        return bool(shutil.which("docker"))
