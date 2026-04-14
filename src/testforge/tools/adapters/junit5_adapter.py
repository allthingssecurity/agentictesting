import xml.etree.ElementTree as ET
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.models.tool_result import ToolOutput
from testforge.tools.adapters._base import BaseToolAdapter


class JUnit5Adapter(BaseToolAdapter):
    """JUnit 5 via Maven Surefire or Gradle. Parses JUnit XML reports."""
    name = "junit5"
    category = ToolCategory.UNIT_TEST
    languages = [Language.JAVA, Language.KOTLIN]
    binary = "mvn"
    detect_files = ["pom.xml", "build.gradle", "build.gradle.kts"]

    def detect(self, project_root: Path) -> bool:
        import shutil
        has_maven = shutil.which("mvn") and (project_root / "pom.xml").exists()
        has_gradle = shutil.which("gradle") and (
            (project_root / "build.gradle").exists() or
            (project_root / "build.gradle.kts").exists()
        )
        return has_maven or has_gradle

    def build_command(self, project_root: Path, config: dict) -> list[str]:
        if (project_root / "pom.xml").exists():
            return ["mvn", "test", "-B", "-q"]
        return ["gradle", "test", "--no-daemon", "-q"]

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> ToolOutput:
        """Try to parse JUnit XML reports from standard locations."""
        tests = []

        # Maven: target/surefire-reports/*.xml
        # Gradle: build/test-results/test/*.xml
        # We can't access filesystem here, so parse from stdout/stderr
        # The agent should call read_file on the XML reports separately

        return ToolOutput(
            tool_name=self.name, exit_code=exit_code,
            success=exit_code == 0, tests=tests,
            summary="Tests completed" if exit_code == 0 else "Tests failed",
            stdout=stdout[:4000], stderr=stderr[:4000],
        )

    @property
    def default_timeout(self) -> int:
        return 300
