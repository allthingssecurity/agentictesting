import json

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models import Status, TestType
from testforge.models.evidence import TestResult
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file
from testforge.tools.patch_tool import apply_patch
from testforge.tools.pytest_tool import run_pytest

SYSTEM_PROMPT = """\
You are a test healer agent. Your job is to fix failing tests.

For each failing test:
1. Read the test file to understand what's being tested
2. Read the source file to understand the implementation
3. Determine if the test or the test assertion needs updating
4. Apply a patch to fix the test
5. Re-run the test to verify the fix

IMPORTANT: Only modify test files, never modify production code.
Only attempt to heal unit and integration test failures (not security findings).
"""


def healer_node(state: TestForgeState) -> dict:
    failures = [
        r for r in state["results"]
        if r.status == Status.FAILED
        and r.test_type in (TestType.UNIT, TestType.INTEGRATION)
    ]

    if not failures:
        return {
            "healed_results": [],
            "messages": [HumanMessage(content="No test failures to heal")],
        }

    llm = get_llm()
    tools = [read_file, apply_patch, run_pytest]
    llm_with_tools = llm.bind_tools(tools)

    max_attempts = state["manifest"].get("heal_max_attempts", 2)
    healed: list[TestResult] = []

    for failure in failures[:5]:  # Cap at 5 failures
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Failing test: {failure.name}\n"
                f"Type: {failure.test_type}\n"
                f"Message: {failure.message}\n"
                f"File: {failure.file_path or 'unknown'}\n"
                f"Stdout: {failure.stdout[:1000]}\n\n"
                f"Attempt to heal this test. Max {max_attempts} attempts."
            )),
        ]

        healed_this = False
        for attempt in range(max_attempts):
            for _ in range(10):
                response = llm_with_tools.invoke(messages)
                messages.append(response)

                if not response.tool_calls:
                    break

                from langchain_core.messages import ToolMessage
                for tc in response.tool_calls:
                    tool_map = {"read_file": read_file, "apply_patch": apply_patch, "run_pytest": run_pytest}
                    tool_fn = tool_map[tc["name"]]
                    tool_result = tool_fn.invoke(tc["args"])
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

                    if tc["name"] == "run_pytest":
                        try:
                            data = json.loads(tool_result)
                            if data.get("exit_code", 1) == 0:
                                healed_this = True
                        except json.JSONDecodeError:
                            pass

            if healed_this:
                break

        healed.append(TestResult(
            test_type=failure.test_type,
            name=failure.name,
            status=Status.HEALED if healed_this else Status.FAILED,
            message=f"Heal {'succeeded' if healed_this else 'failed'} after {attempt + 1} attempts",
            file_path=failure.file_path,
        ))

    return {
        "healed_results": healed,
        "messages": [HumanMessage(content=f"Healer processed {len(healed)} failures")],
    }
