import json

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models import Status, TestType
from testforge.models.evidence import TestResult
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file
from testforge.tools.schemathesis_tool import run_schemathesis

SYSTEM_PROMPT = """\
You are an API test executor agent. Run API tests using Schemathesis for OpenAPI fuzzing.

Steps:
1. Check if an OpenAPI spec is available in the manifest
2. Run Schemathesis against the spec for property-based API testing
3. Analyze and report results
"""


def api_node(state: TestForgeState) -> dict:
    llm = get_llm()
    tools = [run_schemathesis, read_file]
    llm_with_tools = llm.bind_tools(tools)

    manifest = state["manifest"]
    project_root = state["project_root"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Project root: {project_root}\n"
            f"API config: {manifest.get('api', {})}\n"
            f"OpenAPI spec: {manifest.get('openapi_spec', 'not specified')}\n"
            f"Base URL: {manifest.get('base_url', 'http://localhost:8000')}\n\n"
            f"Run API tests now."
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
            tool_map = {"run_schemathesis": run_schemathesis, "read_file": read_file}
            tool_fn = tool_map[tc["name"]]
            tool_result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

            if tc["name"] == "run_schemathesis":
                try:
                    data = json.loads(tool_result)
                    status = Status.PASSED if data.get("exit_code", 1) == 0 else Status.FAILED
                    results.append(TestResult(
                        test_type=TestType.API,
                        name="schemathesis_fuzz",
                        status=status,
                        message=data.get("stdout", "")[:2000],
                        stderr=data.get("stderr", "")[:1000],
                    ))
                except (json.JSONDecodeError, KeyError):
                    pass

    if not results:
        results.append(TestResult(
            test_type=TestType.API,
            name="api_suite",
            status=Status.SKIPPED,
            message="No API test results",
        ))

    return {
        "results": results,
        "messages": [HumanMessage(content=f"API tests complete: {len(results)} results")],
    }
