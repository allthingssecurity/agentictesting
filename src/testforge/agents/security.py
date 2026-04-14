import json

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models import Status, TestType
from testforge.models.evidence import TestResult
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file
from testforge.tools.nuclei_tool import run_nuclei
from testforge.tools.semgrep_tool import run_semgrep

SYSTEM_PROMPT = """\
You are a security test executor agent. Run both SAST (Semgrep) and DAST (Nuclei) scans.

Steps:
1. Run Semgrep for static analysis on the source code
2. Run Nuclei for dynamic vulnerability scanning if a base_url is provided
3. Collect and report all security findings
"""


def security_node(state: TestForgeState) -> dict:
    llm = get_llm()
    tools = [run_semgrep, run_nuclei, read_file]
    llm_with_tools = llm.bind_tools(tools)

    manifest = state["manifest"]
    project_root = state["project_root"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Project root: {project_root}\n"
            f"Security config: {manifest.get('security', {})}\n"
            f"Base URL: {manifest.get('base_url', 'not specified')}\n\n"
            f"Run security scans now."
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
            tool_map = {"run_semgrep": run_semgrep, "run_nuclei": run_nuclei, "read_file": read_file}
            tool_fn = tool_map[tc["name"]]
            tool_result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

            if tc["name"] == "run_semgrep":
                try:
                    data = json.loads(tool_result)
                    n_findings = data.get("total_findings", 0)
                    status = Status.PASSED if n_findings == 0 else Status.FAILED
                    findings_detail = json.dumps(data.get("findings", [])[:10], indent=2)
                    results.append(TestResult(
                        test_type=TestType.SECURITY,
                        name="semgrep_sast",
                        status=status,
                        message=f"{n_findings} findings\n{findings_detail}",
                    ))
                except (json.JSONDecodeError, KeyError):
                    pass

            elif tc["name"] == "run_nuclei":
                try:
                    data = json.loads(tool_result)
                    n_findings = data.get("total_findings", 0)
                    status = Status.PASSED if n_findings == 0 else Status.FAILED
                    findings_detail = json.dumps(data.get("findings", [])[:10], indent=2)
                    results.append(TestResult(
                        test_type=TestType.SECURITY,
                        name="nuclei_dast",
                        status=status,
                        message=f"{n_findings} findings\n{findings_detail}",
                    ))
                except (json.JSONDecodeError, KeyError):
                    pass

    if not results:
        results.append(TestResult(
            test_type=TestType.SECURITY,
            name="security_suite",
            status=Status.SKIPPED,
            message="No security scan results",
        ))

    return {
        "results": results,
        "messages": [HumanMessage(content=f"Security scans complete: {len(results)} results")],
    }
