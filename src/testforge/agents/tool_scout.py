"""ToolScout agent — GPT-5 dynamically discovers testing tools for each language.

Instead of relying only on hardcoded adapters, the scout:
1. Reads ecosystem files (Cargo.toml, package.json, go.mod, pom.xml, etc.)
2. Probes PATH for known tool binaries
3. Uses GPT-5 to reason about what tools are available and how to invoke them
4. Outputs DynamicToolAdapter specs that the executor can use at runtime

This means a Rust project automatically gets cargo-test, cargo-clippy, cargo-audit,
cargo-nextest, miri — without anyone writing adapter classes for each.
"""

import json
import shutil
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool as lc_tool

from testforge.llm import get_llm
from testforge.state import TestForgeState
from testforge.tools.file_tools import read_file, list_files

SCOUT_SYSTEM_PROMPT = """\
You are a Tool Scout agent. Your job is to discover what testing, linting, and security
tools are available for this project.

For each detected language, you must:
1. Read the ecosystem files (Cargo.toml, package.json, go.mod, pom.xml, Gemfile, etc.)
2. Check which tool binaries are on PATH using probe_binary
3. Determine what testing/lint/security tools are configured or available

For each tool you discover, output a JSON spec with:
{
    "name": "tool-name",
    "binary": "binary-on-path",
    "category": "unit_test|integration_test|e2e_test|api_fuzz|sast|dast|lint",
    "languages": ["rust"],
    "command_template": ["cargo", "test", "--", "--format=json"],
    "output_format": "json|jsonl|text|junit_xml",
    "parse_strategy": "generic|go_json|rust_diag|jest_json|jsonl_findings",
    "filesystem_mode": "readonly|readwrite",
    "timeout": 120,
    "detect_files": ["Cargo.toml"],
    "description": "what this tool does"
}

IMPORTANT parse_strategy guide:
- "generic": just check exit code (0=pass). Works for anything.
- "go_json": for `go test -json` newline-delimited events
- "rust_diag": for cargo clippy/build --message-format=json
- "jest_json": for jest/vitest --json output
- "jsonl_findings": for nuclei, custom security scanners with JSONL output

Common tools by language:
- Rust: cargo test, cargo clippy, cargo audit, cargo nextest, cargo miri
- Go: go test, golangci-lint, gosec, govulncheck
- Python: pytest, ruff, bandit, mypy, pyright
- JavaScript/TypeScript: jest, vitest, eslint, playwright
- Java: mvn test, gradle test, spotbugs, checkstyle
- Ruby: rspec, rubocop, brakeman
- C#: dotnet test, dotnet format
- C/C++: ctest, cppcheck, clang-tidy, valgrind

Output your discovered tools as a JSON array at the end of your analysis.
Start with ```json and end with ```.
"""


@lc_tool
def probe_binary(binary_name: str) -> str:
    """Check if a binary is available on PATH. Returns the full path or 'not found'."""
    path = shutil.which(binary_name)
    return path if path else f"{binary_name}: not found"


@lc_tool
def probe_binaries(binary_names: str) -> str:
    """Check multiple binaries at once. Input: comma-separated names. Returns status of each."""
    results = []
    for name in binary_names.split(","):
        name = name.strip()
        path = shutil.which(name)
        results.append(f"{name}: {path}" if path else f"{name}: not found")
    return "\n".join(results)


def tool_scout_node(state: TestForgeState) -> dict:
    """GPT-5 discovers available testing tools dynamically based on project languages."""
    model_name = state.get("manifest", {}).get("llm", {}).get("model", "gpt-5")
    llm = get_llm(model=model_name)
    tools = [read_file, list_files, probe_binary, probe_binaries]
    llm_with_tools = llm.bind_tools(tools)

    languages = state.get("detected_languages", [])
    project_root = state["project_root"]

    messages = [
        SystemMessage(content=SCOUT_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Project root: {project_root}\n"
            f"Detected languages: {', '.join(languages)}\n\n"
            f"Discover all available testing, linting, and security tools for this project.\n"
            f"Start by reading the ecosystem files, then probe for binaries."
        )),
    ]

    tool_map = {t.name: t for t in tools}

    for _ in range(15):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for tc in response.tool_calls:
            fn = tool_map.get(tc["name"])
            if fn:
                result = fn.invoke(tc["args"])
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # Parse discovered tools from the final response
    discovered_specs = _extract_tool_specs(messages)

    # Merge with any hardcoded adapters already in the registry
    existing_snapshot = state.get("tool_registry_snapshot", {})
    existing_adapters = existing_snapshot.get("adapters", [])
    existing_names = {a["name"] for a in existing_adapters}

    # Convert discovered specs to adapter format for the snapshot
    new_adapters = []
    for spec in discovered_specs:
        if spec["name"] not in existing_names:
            new_adapters.append({
                "name": spec["name"],
                "category": spec.get("category", "unit_test"),
                "languages": spec.get("languages", []),
                "binary": spec.get("binary", spec["name"]),
                "filesystem_mode": spec.get("filesystem_mode", "readwrite"),
                "timeout": spec.get("timeout", 120),
                "dynamic": True,  # Flag so executor knows to use DynamicToolAdapter
                "spec": spec,     # Full spec for DynamicToolAdapter construction
            })

    merged_snapshot = {
        "adapters": existing_adapters + new_adapters,
    }

    discovered_names = [s["name"] for s in discovered_specs]
    return {
        "tool_registry_snapshot": merged_snapshot,
        "messages": [HumanMessage(content=(
            f"ToolScout discovered {len(discovered_specs)} tools: {', '.join(discovered_names)}\n"
            f"(merged with {len(existing_adapters)} hardcoded adapters)"
        ))],
    }


def _extract_tool_specs(messages: list) -> list[dict]:
    """Extract tool spec JSON array from the last AI message."""
    # Search messages in reverse for a JSON array
    for msg in reversed(messages):
        content = msg.content if hasattr(msg, "content") and isinstance(msg.content, str) else ""
        if "```json" in content:
            try:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    specs = json.loads(content[start:end])
                    if isinstance(specs, list):
                        return [s for s in specs if isinstance(s, dict) and "name" in s]
            except (json.JSONDecodeError, ValueError):
                pass

        # Also try finding a raw JSON array
        if content.strip().startswith("["):
            try:
                specs = json.loads(content.strip())
                if isinstance(specs, list):
                    return [s for s in specs if isinstance(s, dict) and "name" in s]
            except json.JSONDecodeError:
                pass

    return []
