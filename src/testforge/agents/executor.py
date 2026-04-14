"""Generic ExecutorAgent — replaces unit.py, integration.py, browser.py, api_agent.py, security.py.

Parameterized by language and tools via Send() payload in _executor_language and _executor_tools.
"""

import json

from langchain_core.messages import HumanMessage

from testforge.agents.base import BaseAgentNode
from testforge.models.enums import Status, TestType, ToolCategory
from testforge.models.evidence import TestResult
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file
from testforge.tools.registry import ToolRegistry

# Map ToolCategory to TestType
CATEGORY_TO_TEST_TYPE = {
    ToolCategory.UNIT_TEST: TestType.UNIT,
    ToolCategory.INTEGRATION_TEST: TestType.INTEGRATION,
    ToolCategory.E2E_TEST: TestType.BROWSER,
    ToolCategory.API_FUZZ: TestType.API,
    ToolCategory.SAST: TestType.SECURITY,
    ToolCategory.DAST: TestType.SECURITY,
    ToolCategory.LINT: TestType.SECURITY,
}

SYSTEM_PROMPT = """\
You are a test executor agent for {language} projects.

Available tools: {tool_names}

Your job:
1. Use the available testing tools to run tests on this project
2. Choose the right tool arguments based on the project structure
3. Parse and return all results

Use read_file to inspect project files if you need context.
Run each available tool at least once.
"""


class ExecutorAgent(BaseAgentNode):
    name = "executor"

    def _get_tools(self, state: TestForgeState) -> list:
        from langchain_core.tools import tool as lc_tool
        from testforge.sandbox.subprocess_sandbox import SubprocessSandbox
        from pathlib import Path

        executor_tools = state.get("_executor_tools", [])
        project_root = Path(state["project_root"])
        sandbox = SubprocessSandbox()

        # Resolve adapters: hardcoded from registry OR dynamic from scout
        registry = ToolRegistry()
        registry.auto_discover()

        langchain_tools = [read_file]

        for tool_info in executor_tools:
            # Dynamic adapter (from ToolScout)
            if tool_info.get("dynamic") and tool_info.get("spec"):
                from testforge.tools.dynamic_adapter import DynamicToolAdapter
                adapter = DynamicToolAdapter(tool_info["spec"])
            else:
                # Hardcoded adapter from registry
                adapter = registry.get(tool_info["name"])

            if not adapter:
                continue

            # Capture adapter in closure — use sanitized name for function
            def make_tool(adp, info):
                safe_name = adp.name.replace(" ", "_").replace("-", "_")

                @lc_tool
                def run_tool(config_json: str = "{}") -> str:
                    """Run the testing tool with given config JSON. Returns structured output."""
                    config = json.loads(config_json)
                    cmd = adp.build_command(project_root, config)
                    result = sandbox.execute(
                        command=cmd,
                        project_root=project_root,
                        timeout=adp.default_timeout,
                    )
                    output = adp.parse_output(result.stdout, result.stderr, result.exit_code)
                    return output.model_dump_json()

                # Override the tool name and description after decoration
                run_tool.name = f"run_{safe_name}"
                run_tool.description = f"Run {adp.name} ({info['category']})"
                return run_tool

            langchain_tools.append(make_tool(adapter, tool_info))

        return langchain_tools

    def _build_prompt(self, state: TestForgeState) -> tuple[str, str]:
        language = state.get("_executor_language", "unknown")
        executor_tools = state.get("_executor_tools", [])
        tool_names = ", ".join(t["name"] for t in executor_tools)

        system = SYSTEM_PROMPT.format(language=language, tool_names=tool_names)
        human = (
            f"Project root: {state['project_root']}\n"
            f"Language: {language}\n"
            f"Available tools: {tool_names}\n"
            f"Manifest: {json.dumps(state['manifest'], indent=2)[:2000]}\n\n"
            f"Run all applicable tests now."
        )
        return system, human

    def _produce_output(self, messages: list, state: TestForgeState) -> dict:
        language = state.get("_executor_language", "unknown")
        executor_tools = state.get("_executor_tools", [])
        results: list[TestResult] = []

        # Parse ToolOutput from tool call results in messages
        for msg in messages:
            if not hasattr(msg, "content") or not isinstance(msg.content, str):
                continue
            if msg.content.startswith('{"tool_name"'):
                try:
                    data = json.loads(msg.content)
                    tool_name = data.get("tool_name", "")

                    # Determine test type from tool category
                    tool_info = next((t for t in executor_tools if t["name"] == tool_name), None)
                    category = ToolCategory(tool_info["category"]) if tool_info else ToolCategory.UNIT_TEST
                    test_type = CATEGORY_TO_TEST_TYPE.get(category, TestType.UNIT)

                    # Parse individual tests
                    for t in data.get("tests", []):
                        status_map = {"passed": Status.PASSED, "failed": Status.FAILED, "error": Status.ERROR}
                        results.append(TestResult(
                            test_type=test_type,
                            name=t.get("name", ""),
                            status=status_map.get(t.get("outcome", ""), Status.ERROR),
                            duration_ms=t.get("duration", 0) * 1000,
                            message=t.get("message", ""),
                            language=language,
                            tool_adapter=tool_name,
                        ))

                    # Parse findings (security tools)
                    for f in data.get("findings", []):
                        results.append(TestResult(
                            test_type=test_type,
                            name=f.get("check_id", f.get("template_id", tool_name)),
                            status=Status.FAILED,
                            message=f.get("message", f.get("description", "")),
                            file_path=f.get("path", ""),
                            line_number=f.get("line", None),
                            language=language,
                            tool_adapter=tool_name,
                        ))

                    # If no individual results, create summary result
                    if not data.get("tests") and not data.get("findings"):
                        results.append(TestResult(
                            test_type=test_type,
                            name=f"{tool_name}_{language}",
                            status=Status.PASSED if data.get("success") else Status.FAILED,
                            message=data.get("summary", ""),
                            language=language,
                            tool_adapter=tool_name,
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

        if not results:
            results.append(TestResult(
                test_type=TestType.UNIT,
                name=f"{language}_suite",
                status=Status.SKIPPED,
                message=f"No results parsed for {language}",
                language=language,
            ))

        return {
            "results": results,
            "messages": [HumanMessage(content=f"Executor({language}): {len(results)} results")],
        }

    def _handle_error(self, error: Exception, state: TestForgeState) -> dict:
        language = state.get("_executor_language", "unknown")
        return {
            "results": [TestResult(
                test_type=TestType.UNIT,
                name=f"{language}_error",
                status=Status.ERROR,
                message=str(error),
                language=language,
            )],
            "messages": [HumanMessage(content=f"Executor({language}) error: {error}")],
        }
