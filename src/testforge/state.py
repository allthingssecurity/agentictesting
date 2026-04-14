import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage

from testforge.models.evidence import Finding, Report, TestPlan, TestResult


class CompactedMemory(TypedDict):
    """Structured memory that persists across agent nodes."""
    summary: str
    key_findings: list[dict]
    decisions: list[dict]
    errors: list[dict]
    token_count: int


def _merge_memory(left: CompactedMemory, right: CompactedMemory) -> CompactedMemory:
    """Custom reducer for CompactedMemory during parallel fan-in."""
    summaries = []
    if left.get("summary"):
        summaries.append(left["summary"])
    if right.get("summary"):
        summaries.append(right["summary"])

    seen_findings = set()
    merged_findings = []
    for f in left.get("key_findings", []) + right.get("key_findings", []):
        key = str(f)
        if key not in seen_findings:
            seen_findings.add(key)
            merged_findings.append(f)

    return CompactedMemory(
        summary=" | ".join(summaries),
        key_findings=merged_findings,
        decisions=left.get("decisions", []) + right.get("decisions", []),
        errors=left.get("errors", []) + right.get("errors", []),
        token_count=left.get("token_count", 0) + right.get("token_count", 0),
    )


class TestForgeState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    project_root: str
    manifest: dict

    # Language detection
    detected_languages: list[str]
    tool_registry_snapshot: dict

    # Planning
    plan: TestPlan | None

    # Executor routing (injected per-language via Send)
    _executor_language: str
    _executor_tools: list[dict]

    # Results (accumulated via operator.add across parallel executors)
    results: Annotated[list[TestResult], operator.add]
    healed_results: Annotated[list[TestResult], operator.add]
    findings: Annotated[list[Finding], operator.add]

    # Memory
    memory: CompactedMemory

    # Meta-harness
    meta_scores: dict

    # Output
    report: Report | None
