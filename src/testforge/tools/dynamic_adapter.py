"""Runtime-generated tool adapter from LLM-discovered tool specifications.

Instead of hardcoding every possible tool as a Python class, the ToolScout agent
discovers tools dynamically by reading project ecosystem files and probing PATH,
then generates DynamicToolAdapter instances at runtime.
"""

import json
import shutil
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput


class DynamicToolAdapter:
    """A tool adapter generated at runtime from a tool specification dict.

    The spec comes from the ToolScout agent (GPT-5) which reads the project's
    ecosystem files and determines what tools are available.

    Spec format:
    {
        "name": "cargo-clippy",
        "binary": "cargo",
        "category": "lint",
        "languages": ["rust"],
        "command_template": ["cargo", "clippy", "--message-format=json"],
        "output_format": "jsonl",       # "json", "jsonl", "text", "junit_xml"
        "parse_strategy": "rust_diag",  # or "generic", "go_json", "jest_json", etc.
        "filesystem_mode": "readonly",
        "timeout": 120,
        "detect_files": ["Cargo.toml"],
        "description": "Rust linter — catches common mistakes and style issues"
    }
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.name: str = spec["name"]
        self.binary: str = spec.get("binary", spec["name"])
        self.category: ToolCategory = ToolCategory(spec.get("category", "unit_test"))
        self.languages: list[Language] = [Language(l) for l in spec.get("languages", [])]
        self._command_template: list[str] = spec.get("command_template", [self.binary])
        self._output_format: str = spec.get("output_format", "text")
        self._parse_strategy: str = spec.get("parse_strategy", "generic")
        self._detect_files: list[str] = spec.get("detect_files", [])
        self._timeout: int = spec.get("timeout", 120)
        self._fs_mode: str = spec.get("filesystem_mode", "readwrite")
        self.description: str = spec.get("description", f"Dynamically discovered: {self.name}")

    def detect(self, project_root: Path) -> bool:
        if not shutil.which(self.binary):
            return False
        if self._detect_files:
            return any((project_root / f).exists() for f in self._detect_files)
        return True

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        cmd = list(self._command_template)
        # Allow config overrides
        for arg in config.get("extra_args", []):
            cmd.append(arg)
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        MAX = 4000
        strategy = self._parse_strategy

        if strategy == "generic":
            return self._parse_generic(stdout, stderr, exit_code)
        elif strategy == "go_json":
            return self._parse_go_json(stdout, stderr, exit_code)
        elif strategy == "rust_diag":
            return self._parse_rust_diag(stdout, stderr, exit_code)
        elif strategy == "jest_json":
            return self._parse_jest_json(stdout, stderr, exit_code)
        elif strategy == "jsonl_findings":
            return self._parse_jsonl_findings(stdout, stderr, exit_code)
        else:
            return self._parse_generic(stdout, stderr, exit_code)

    @property
    def filesystem_mode(self) -> str:
        return self._fs_mode

    @property
    def default_timeout(self) -> int:
        return self._timeout

    # --- Parse strategies ---

    def _parse_generic(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Generic parser: treat exit_code == 0 as success, everything else as failure."""
        return ToolOutput(
            tool_name=self.name,
            exit_code=exit_code,
            success=exit_code == 0,
            summary=f"{'passed' if exit_code == 0 else 'failed'} (exit {exit_code})",
            stdout=stdout[:4000],
            stderr=stderr[:4000],
        )

    def _parse_go_json(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse `go test -json` newline-delimited JSON events."""
        tests: dict[str, dict] = {}
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                event = json.loads(line)
                action = event.get("Action", "")
                test = event.get("Test", "")
                if test and action in ("pass", "fail", "skip"):
                    tests[test] = {
                        "name": f"{event.get('Package', '')}::{test}",
                        "outcome": {"pass": "passed", "fail": "failed", "skip": "skipped"}[action],
                        "duration": event.get("Elapsed", 0),
                    }
            except json.JSONDecodeError:
                continue
        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=list(tests.values()),
            stdout=stdout[:4000], stderr=stderr[:4000],
        )

    def _parse_rust_diag(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse Rust compiler/clippy JSON diagnostics."""
        findings = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get("reason") == "compiler-message":
                    diag = msg.get("message", {})
                    if diag.get("level") in ("warning", "error"):
                        spans = diag.get("spans", [{}])
                        primary = next((s for s in spans if s.get("is_primary")), spans[0] if spans else {})
                        findings.append({
                            "check_id": diag.get("code", {}).get("code", "unknown") if diag.get("code") else "unknown",
                            "message": diag.get("message", "")[:500],
                            "severity": "high" if diag.get("level") == "error" else "medium",
                            "path": primary.get("file_name", ""),
                            "line": primary.get("line_start", 0),
                        })
            except json.JSONDecodeError:
                continue
        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=len(findings) == 0, findings=findings,
            summary=f"{len(findings)} diagnostics",
            stdout=stdout[:4000], stderr=stderr[:4000],
        )

    def _parse_jest_json(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse Jest/Vitest JSON output."""
        tests = []
        try:
            data = json.loads(stdout)
            for suite in data.get("testResults", []):
                for t in suite.get("testResults", suite.get("assertionResults", [])):
                    tests.append({
                        "name": t.get("fullName", t.get("title", "")),
                        "outcome": "passed" if t.get("status") == "passed" else "failed",
                        "duration": t.get("duration", 0) / 1000,
                        "message": "\n".join(t.get("failureMessages", []))[:500],
                    })
        except (json.JSONDecodeError, KeyError):
            pass
        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )

    def _parse_jsonl_findings(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Parse newline-delimited JSON findings (nuclei, custom scanners)."""
        findings = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                f = json.loads(line)
                findings.append({
                    "check_id": f.get("id", f.get("check_id", f.get("template-id", ""))),
                    "message": f.get("message", f.get("info", {}).get("name", ""))[:500],
                    "severity": f.get("severity", f.get("info", {}).get("severity", "medium")),
                    "path": f.get("path", f.get("matched-at", "")),
                })
            except json.JSONDecodeError:
                continue
        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=len(findings) == 0, findings=findings,
            stdout=stdout[:4000], stderr=stderr[:4000],
        )
