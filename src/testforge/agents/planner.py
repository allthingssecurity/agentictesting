"""Language-aware planner agent."""

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.models.evidence import TestPlan
from testforge.state import TestForgeState
from testforge.tools.file_tools import list_files, read_file

SYSTEM_PROMPT = """\
You are a test planning agent for a polyglot project.

Detected languages: {languages}
Available tools: {tools}

Analyze the project structure and create a TestPlan:
1. Use list_files to explore the project
2. Use read_file to examine key files (package files, test configs, source files)
3. Decide which test types to run based on what's available
4. Consider the manifest configuration for enabled/disabled test types

Available test types: unit, integration, browser, api, security
"""


def planner_node(state: TestForgeState) -> dict:
    model_name = state.get("manifest", {}).get("llm", {}).get("model", "gpt-5")
    llm = get_llm(model=model_name)
    tools = [read_file, list_files]
    llm_with_tools = llm.bind_tools(tools)

    languages = state.get("detected_languages", [])
    tool_snapshot = state.get("tool_registry_snapshot", {})
    tool_names = [a["name"] for a in tool_snapshot.get("adapters", [])]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(
            languages=", ".join(languages) or "unknown",
            tools=", ".join(tool_names) or "none detected",
        )),
        HumanMessage(content=(
            f"Project root: {state['project_root']}\n"
            f"Manifest config: {state['manifest']}\n\n"
            f"Analyze this project and create a test plan."
        )),
    ]

    # Tool-calling loop
    from langchain_core.messages import ToolMessage
    for _ in range(10):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for tc in response.tool_calls:
            tool_map = {"read_file": read_file, "list_files": list_files}
            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                result = tool_fn.invoke(tc["args"])
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # Structured output
    structured_llm = llm.with_structured_output(TestPlan)
    plan = structured_llm.invoke(messages + [HumanMessage(
        content="Output the TestPlan now. Only include enabled test types from the manifest."
    )])

    return {
        "plan": plan,
        "messages": [HumanMessage(content=f"Test plan: {plan.model_dump_json()}")],
    }
