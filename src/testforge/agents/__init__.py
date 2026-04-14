from collections.abc import Callable

from langgraph.prebuilt import create_react_agent

from testforge.llm import get_llm
from testforge.state import TestForgeState


def make_agent_node(
    system_prompt: str,
    tools: list,
    state_key: str = "results",
    parse_fn: Callable | None = None,
):
    """Create a LangGraph node wrapping a ReAct agent with tools.

    Args:
        system_prompt: System instructions for the agent.
        tools: List of @tool-decorated functions.
        state_key: Which state field to write results to.
        parse_fn: Optional function(final_message, state) -> dict of state updates.
    """
    agent = create_react_agent(model=get_llm(), tools=tools, prompt=system_prompt)

    def node(state: TestForgeState) -> dict:
        agent_input = {"messages": state["messages"]}
        result = agent.invoke(agent_input)
        if parse_fn:
            return parse_fn(result["messages"], state)
        return {"messages": result["messages"]}

    return node
