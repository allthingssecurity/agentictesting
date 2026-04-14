import json

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models import Status, TestType
from testforge.models.evidence import TestResult
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file
from testforge.tools.playwright_tool import run_playwright

SYSTEM_PROMPT = """\
You are a browser/E2E test executor agent. Run end-to-end tests using Playwright.

Steps:
1. Identify Playwright test files in the project
2. Run them using the run_playwright tool
3. Parse and return results
"""


def browser_node(state: TestForgeState) -> dict:
    llm = get_llm()
    tools = [run_playwright, read_file]
    llm_with_tools = llm.bind_tools(tools)

    manifest = state["manifest"]
    project_root = state["project_root"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Project root: {project_root}\n"
            f"Browser config: {manifest.get('browser', {})}\n\n"
            f"Run browser/E2E tests now."
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
            tool_map = {"run_playwright": run_playwright, "read_file": read_file}
            tool_fn = tool_map[tc["name"]]
            tool_result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

            if tc["name"] == "run_playwright":
                try:
                    data = json.loads(tool_result)
                    for t in data.get("tests", []):
                        status_map = {"passed": Status.PASSED, "failed": Status.FAILED, "expected": Status.PASSED}
                        results.append(TestResult(
                            test_type=TestType.BROWSER,
                            name=t.get("name", ""),
                            status=status_map.get(t.get("status", ""), Status.ERROR),
                            duration_ms=t.get("duration", 0),
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

    if not results:
        results.append(TestResult(
            test_type=TestType.BROWSER,
            name="browser_suite",
            status=Status.SKIPPED,
            message="No browser test results parsed",
        ))

    return {
        "results": results,
        "messages": [HumanMessage(content=f"Browser tests complete: {len(results)} results")],
    }
