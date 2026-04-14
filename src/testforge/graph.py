"""TestForge v0.5 LangGraph — polyglot, pluggable, self-evolving.

Topology:
  START → detect_languages → discover_tools → tool_scout (GPT-5 dynamic discovery)
    → planner → compact_memory_pre
    → route_by_language (parallel Send per language)
    → compact_memory_post → healer → triage → reporter
    → meta_evaluate → END
"""

from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from testforge.agents.executor import ExecutorAgent
from testforge.agents.healer import healer_node
from testforge.agents.planner import planner_node
from testforge.agents.reporter import reporter_node
from testforge.agents.tool_scout import tool_scout_node
from testforge.agents.triage import triage_node
from testforge.detection.detector import LanguageDetector
from testforge.detection.routing import LanguageRouter
from testforge.state import CompactedMemory, TestForgeState
from testforge.tools.registry import ToolRegistry


# --- Pure function nodes ---

def detect_languages_node(state: TestForgeState) -> dict:
    """Scan project and detect languages."""
    detector = LanguageDetector()
    project_root = Path(state["project_root"])
    languages = detector.detect(project_root)
    lang_list = sorted(l.value for l in languages)
    return {
        "detected_languages": lang_list,
        "messages": [HumanMessage(content=f"Detected languages: {', '.join(lang_list) or 'none'}")],
    }


def discover_tools_node(state: TestForgeState) -> dict:
    """Discover applicable tools from registry."""
    registry = ToolRegistry()
    registry.auto_discover()

    project_root = Path(state["project_root"])
    registry.discover_project_tools(project_root)

    from testforge.models.enums import Language
    languages = {Language(l) for l in state.get("detected_languages", [])}
    applicable = registry.detect_applicable(project_root, languages)

    tool_names = [a.name for a in applicable]
    snapshot = registry.snapshot()
    # Filter snapshot to only applicable tools
    snapshot["adapters"] = [a for a in snapshot["adapters"] if a["name"] in tool_names]

    return {
        "tool_registry_snapshot": snapshot,
        "messages": [HumanMessage(content=f"Discovered tools: {', '.join(tool_names) or 'none'}")],
    }


def compact_memory_pre_node(state: TestForgeState) -> dict:
    """Compact planner context before fan-out to executors."""
    plan = state.get("plan")
    memory = state.get("memory") or CompactedMemory(
        summary="", key_findings=[], decisions=[], errors=[], token_count=0,
    )

    if plan:
        memory = CompactedMemory(
            summary=f"Plan: test types={plan.test_types}, rationale={plan.rationale[:200]}",
            key_findings=[],
            decisions=[{"type": "plan", "test_types": [t.value for t in plan.test_types]}],
            errors=[],
            token_count=memory.get("token_count", 0),
        )

    return {"memory": memory}


def compact_memory_post_node(state: TestForgeState) -> dict:
    """Merge parallel executor memories after fan-in."""
    results = state.get("results", [])
    memory = state.get("memory") or CompactedMemory(
        summary="", key_findings=[], decisions=[], errors=[], token_count=0,
    )

    from testforge.models.enums import Status
    failed = [r for r in results if r.status in (Status.FAILED, Status.ERROR)]
    passed_count = sum(1 for r in results if r.status == Status.PASSED)

    findings = [{"name": r.name, "type": r.test_type, "msg": r.message[:200]} for r in failed[:10]]

    return {
        "memory": CompactedMemory(
            summary=f"{memory.get('summary', '')} | Executors: {passed_count} passed, {len(failed)} failed",
            key_findings=findings,
            decisions=memory.get("decisions", []),
            errors=memory.get("errors", []),
            token_count=memory.get("token_count", 0),
        ),
    }


def meta_evaluate_node(state: TestForgeState) -> dict:
    """Score tool effectiveness after pipeline run."""
    results = state.get("results", [])
    scores: dict[str, dict] = {}

    for r in results:
        adapter = r.tool_adapter or "unknown"
        if adapter not in scores:
            scores[adapter] = {"total": 0, "passed": 0, "failed": 0, "findings": 0}
        scores[adapter]["total"] += 1
        if r.status == "passed":
            scores[adapter]["passed"] += 1
        elif r.status in ("failed", "error"):
            scores[adapter]["failed"] += 1

    return {
        "meta_scores": scores,
        "messages": [HumanMessage(content=f"Meta scores: {scores}")],
    }


# --- Routing ---

def route_by_language(state: TestForgeState) -> list[Send]:
    """Fan-out to parallel executors, one per detected language."""
    languages = state.get("detected_languages", [])
    tool_snapshot = state.get("tool_registry_snapshot", {})
    all_adapters = tool_snapshot.get("adapters", [])

    sends = []
    for lang in languages:
        lang_tools = [
            a for a in all_adapters
            if lang in a.get("languages", []) or not a.get("languages")
        ]
        if lang_tools:
            sends.append(Send("language_executor", {
                **state,
                "_executor_language": lang,
                "_executor_tools": lang_tools,
            }))

    return sends if sends else [Send("compact_memory_post", state)]


# --- Build graph ---

executor_agent = ExecutorAgent()


def build_graph() -> StateGraph:
    g = StateGraph(TestForgeState)

    # Nodes
    g.add_node("detect_languages", detect_languages_node)
    g.add_node("discover_tools", discover_tools_node)
    g.add_node("tool_scout", tool_scout_node)
    g.add_node("planner", planner_node)
    g.add_node("compact_memory_pre", compact_memory_pre_node)
    g.add_node("language_executor", executor_agent)
    g.add_node("compact_memory_post", compact_memory_post_node)
    g.add_node("healer", healer_node)
    g.add_node("triage", triage_node)
    g.add_node("reporter", reporter_node)
    g.add_node("meta_evaluate", meta_evaluate_node)

    # Edges
    g.add_edge(START, "detect_languages")
    g.add_edge("detect_languages", "discover_tools")
    g.add_edge("discover_tools", "tool_scout")     # GPT-5 discovers tools dynamically
    g.add_edge("tool_scout", "planner")
    g.add_edge("planner", "compact_memory_pre")
    g.add_conditional_edges("compact_memory_pre", route_by_language)
    g.add_edge("language_executor", "compact_memory_post")
    g.add_edge("compact_memory_post", "healer")
    g.add_edge("healer", "triage")
    g.add_edge("triage", "reporter")
    g.add_edge("reporter", "meta_evaluate")
    g.add_edge("meta_evaluate", END)

    return g.compile()
