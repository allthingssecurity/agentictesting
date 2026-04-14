from datetime import datetime

from pydantic import BaseModel, Field

from testforge.models.enums import Severity, Status, TestType


class TestResult(BaseModel):
    test_type: TestType
    name: str
    status: Status
    duration_ms: float = 0.0
    message: str = ""
    stdout: str = ""
    stderr: str = ""
    file_path: str | None = None
    line_number: int | None = None
    language: str = ""
    tool_adapter: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class Finding(BaseModel):
    test_result: TestResult
    severity: Severity
    category: str = ""
    recommendation: str = ""
    healed: bool = False
    heal_diff: str | None = None


class TestPlan(BaseModel):
    test_types: list[TestType]
    rationale: str = ""
    target_paths: list[str] = Field(default_factory=list)


class Report(BaseModel):
    plan: TestPlan
    results: list[TestResult] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    pass_rate: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.now)
