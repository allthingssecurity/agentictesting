from pydantic import BaseModel, Field


class ToolOutput(BaseModel):
    """Unified output from any ToolAdapter.parse_output()."""

    tool_name: str
    exit_code: int
    success: bool = False
    tests: list[dict] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)
    summary: str = ""
    stdout: str = ""
    stderr: str = ""
    raw_data: dict = Field(default_factory=dict)
