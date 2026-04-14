"""BaseAgentNode — unified tool-calling loop with memory integration and logging."""

from abc import ABC, abstractmethod

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from testforge.llm import get_llm
from testforge.logging import TimingContext, log_agent_end, log_agent_start, log_error, log_tool_call
from testforge.state import TestForgeState

MAX_TOOL_ITERATIONS = 15


class BaseAgentNode(ABC):
    """Base class for all agent nodes in the TestForge graph.

    Subclasses implement:
        _get_tools(state) -> list of @tool-decorated functions
        _build_prompt(state) -> (system_message, human_message)
        _produce_output(messages, state) -> dict of state updates
    """

    name: str = "base"
    max_iterations: int = MAX_TOOL_ITERATIONS

    def __call__(self, state: TestForgeState) -> dict:
        """LangGraph node entry point."""
        log_agent_start(self.name, self.name)

        try:
            tools = self._get_tools(state)
            system_msg, human_msg = self._build_prompt(state)

            # Build tool map for dispatch
            tool_map = {t.name: t for t in tools}

            # Get LLM with tools bound
            model_name = state.get("manifest", {}).get("llm", {}).get("model", "gpt-5")
            llm = get_llm(model=model_name)
            llm_with_tools = llm.bind_tools(tools) if tools else llm

            messages = [SystemMessage(content=system_msg), HumanMessage(content=human_msg)]

            # Unified tool-calling loop
            for _ in range(self.max_iterations):
                response = llm_with_tools.invoke(messages)
                messages.append(response)

                if not response.tool_calls:
                    break

                for tc in response.tool_calls:
                    tool_fn = tool_map.get(tc["name"])
                    if not tool_fn:
                        messages.append(ToolMessage(
                            content=f"Error: tool '{tc['name']}' not found",
                            tool_call_id=tc["id"],
                        ))
                        log_error(self.name, f"Tool not found: {tc['name']}")
                        continue

                    with TimingContext() as timing:
                        try:
                            result = tool_fn.invoke(tc["args"])
                        except Exception as e:
                            result = f"Error executing {tc['name']}: {e}"
                            log_error(self.name, str(e), tool=tc["name"])

                    result_str = str(result)
                    messages.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))
                    log_tool_call(self.name, tc["name"], tc["args"], result_str, timing.duration_ms)

            output = self._produce_output(messages, state)
            results_count = len(output.get("results", output.get("findings", output.get("healed_results", []))))
            log_agent_end(self.name, self.name, results_count)
            return output

        except Exception as e:
            log_error(self.name, str(e))
            return self._handle_error(e, state)

    @abstractmethod
    def _get_tools(self, state: TestForgeState) -> list:
        """Return list of @tool-decorated functions for this agent."""
        ...

    @abstractmethod
    def _build_prompt(self, state: TestForgeState) -> tuple[str, str]:
        """Return (system_message, human_message) for the agent."""
        ...

    @abstractmethod
    def _produce_output(self, messages: list, state: TestForgeState) -> dict:
        """Parse messages and produce state updates dict."""
        ...

    def _handle_error(self, error: Exception, state: TestForgeState) -> dict:
        """Graceful degradation on error. Override in subclasses if needed."""
        return {
            "messages": [HumanMessage(content=f"{self.name} error: {error}")],
        }
