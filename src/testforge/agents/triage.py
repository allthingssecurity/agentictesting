from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models import Severity, Status
from testforge.models.evidence import Finding
from testforge.state import TestForgeState

SYSTEM_PROMPT = """\
You are a test triage agent. Classify each test failure into a structured Finding.

For each failure, determine:
- severity: critical, high, medium, low, info
- category: e.g., "regression", "flaky-test", "sql-injection", "xss", "missing-validation",
  "api-contract-violation", "performance", "accessibility"
- recommendation: what should be done to fix this

Consider healed results too — mark those as healed in findings.
"""



def triage_node(state: TestForgeState) -> dict:
    failures = [r for r in state["results"] if r.status in (Status.FAILED, Status.ERROR)]
    healed_names = {r.name for r in state["healed_results"] if r.status == Status.HEALED}

    if not failures:
        return {
            "findings": [],
            "messages": [HumanMessage(content="No failures to triage")],
        }

    llm = get_llm()

    findings: list[Finding] = []

    # Build a summary for the LLM
    failure_summaries = []
    for i, f in enumerate(failures[:20]):
        failure_summaries.append(
            f"{i+1}. [{f.test_type}] {f.name}: {f.message[:300]}"
        )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Classify these {len(failures)} failures:\n\n"
            + "\n".join(failure_summaries)
            + "\n\nFor each, respond with a JSON array of objects with keys: "
            "index, severity, category, recommendation"
        )),
    ]

    response = llm.invoke(messages)

    # Parse LLM response for classifications
    import json
    try:
        # Try to extract JSON from the response
        content = response.content
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            classifications = json.loads(content[start:end])
        else:
            classifications = []
    except (json.JSONDecodeError, ValueError):
        classifications = []

    for i, failure in enumerate(failures[:20]):
        classification = next(
            (c for c in classifications if c.get("index") == i + 1),
            {"severity": "medium", "category": "unknown", "recommendation": "Investigate manually"},
        )

        findings.append(Finding(
            test_result=failure,
            severity=Severity(classification.get("severity", "medium")),
            category=classification.get("category", "unknown"),
            recommendation=classification.get("recommendation", "Investigate"),
            healed=failure.name in healed_names,
        ))

    return {
        "findings": findings,
        "messages": [HumanMessage(content=f"Triaged {len(findings)} findings")],
    }
