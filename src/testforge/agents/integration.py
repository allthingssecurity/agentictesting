import json

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models import Status, TestType
from testforge.models.evidence import TestResult
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file
from testforge.tools.pytest_tool import run_pytest

SYSTEM_PROMPT = """\
You are an integration test executor agent. Run integration tests using pytest.

Integration tests are typically marked with @pytest.mark.integration or located in
tests/integration/. Use the -m integration marker when appropriate.

Steps:
1. Determine integration test paths
2. Run pytest with integration markers
3. Collect results
"""


def integration_node(state: TestForgeState) -> dict:
    llm = get_llm()
    tools = [run_pytest, read_file]
    llm_with_tools = llm.bind_tools(tools)

    manifest = state["manifest"]
    project_root = state["project_root"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Project root: {project_root}\n"
            f"Integration config: {manifest.get('integration', {})}\n\n"
            f"Run integration tests now."
        )),
    ]

    results: list[TestResult] = []

    for _ in range(10):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        from langchain_core.messages import ToolMessage
        for tc in response.tool_calls:
            tool_map = {"run_pytest": run_pytest, "read_file": read_file}
            tool_fn = tool_map[tc["name"]]
            tool_result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

            if tc["name"] == "run_pytest":
                try:
                    data = json.loads(tool_result)
                    for t in data.get("tests", []):
                        status_map = {"passed": Status.PASSED, "failed": Status.FAILED, "error": Status.ERROR}
                        results.append(TestResult(
                            test_type=TestType.INTEGRATION,
                            name=t.get("name", ""),
                            status=status_map.get(t.get("outcome", ""), Status.ERROR),
                            duration_ms=t.get("duration", 0) * 1000,
                            message=t.get("message", ""),
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

    if not results:
        results.append(TestResult(
            test_type=TestType.INTEGRATION,
            name="integration_suite",
            status=Status.SKIPPED,
            message="No integration test results parsed",
        ))

    return {
        "results": results,
        "messages": [HumanMessage(content=f"Integration tests complete: {len(results)} results")],
    }
