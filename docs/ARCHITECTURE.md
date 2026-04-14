# Architecture

## System Overview

TestForge is a LangGraph StateGraph with 11 nodes connected in a pipeline with parallel fan-out:

```
START
  │
  ▼
detect_languages ─────── Pure fn: scan package files + extensions
  │
  ▼
discover_tools ────────── Pure fn: registry finds builtin adapters
  │
  ▼
tool_scout ────────────── GPT-5: reads ecosystem files, probes PATH,
  │                       generates DynamicToolAdapter specs
  ▼
planner ───────────────── GPT-5: language-aware test planning
  │
  ▼
compact_memory_pre ────── Pure fn: summarize planner context
  │
  ▼
route_by_language ─┬──── executor(python)     ─┐
                   ├──── executor(rust)        ─┤  Parallel Send()
                   ├──── executor(typescript)  ─┤  per language
                   └──── executor(go)          ─┘
                                               │
  ┌────────────────────────────────────────────┘
  ▼
compact_memory_post ───── Pure fn: merge parallel memories
  │
  ▼
healer ────────────────── GPT-5: fix failing tests
  │
  ▼
triage ────────────────── GPT-5: classify findings
  │
  ▼
reporter ──────────────── Pure fn: JSON + HTML + JUnit XML
  │
  ▼
meta_evaluate ─────────── Pure fn: score tool effectiveness
  │
  ▼
END
```

## Package Structure (72 files)

```
src/testforge/
├── cli.py                    # Typer CLI: run, plan, evolve, tools
├── config.py                 # TestForgeManifest (Pydantic)
├── graph.py                  # LangGraph StateGraph definition
├── state.py                  # TestForgeState + CompactedMemory
├── llm.py                    # Configurable ChatOpenAI factory
├── logging.py                # Structured JSON logger
├── defaults.py               # Per-language default configs
│
├── models/
│   ├── enums.py              # Language(11), ToolCategory(7), TestType, Severity, Status
│   ├── evidence.py           # TestResult, Finding, TestPlan, Report
│   └── tool_result.py        # ToolOutput (unified adapter output)
│
├── detection/
│   ├── detector.py           # LanguageDetector (package files + extensions)
│   └── routing.py            # Language → tools mapping
│
├── tools/
│   ├── protocol.py           # ToolAdapter Protocol (@runtime_checkable)
│   ├── registry.py           # ToolRegistry (builtins + entry_points + project tools/)
│   ├── dynamic_adapter.py    # DynamicToolAdapter (runtime-generated from LLM specs)
│   ├── file_tools.py         # read_file, list_files (@tool)
│   ├── patch_tool.py         # apply_patch (@tool)
│   └── adapters/
│       ├── _base.py          # BaseToolAdapter ABC
│       ├── pytest_adapter.py
│       ├── jest_adapter.py
│       ├── vitest_adapter.py
│       ├── go_test_adapter.py
│       ├── cargo_test_adapter.py
│       ├── junit5_adapter.py
│       ├── rspec_adapter.py
│       ├── dotnet_adapter.py
│       ├── semgrep_adapter.py
│       ├── nuclei_adapter.py
│       ├── playwright_adapter.py
│       └── schemathesis_adapter.py
│
├── agents/
│   ├── base.py               # BaseAgentNode (unified tool loop + logging)
│   ├── tool_scout.py         # ToolScout (GPT-5 dynamic tool discovery)
│   ├── planner.py            # PlannerAgent (language-aware)
│   ├── executor.py           # ExecutorAgent (generic, per-language)
│   ├── healer.py             # HealerAgent (fix failing tests)
│   ├── triage.py             # TriageAgent (classify findings)
│   └── reporter.py           # ReporterNode (delegates to reporting/)
│
├── memory/
│   ├── compactor.py          # SlidingWindowCompactor + LLM summarizer
│   ├── store.py              # StructuredMemoryStore (dedup by hash)
│   └── budget.py             # TokenBudgetEnforcer (tiktoken)
│
├── sandbox/
│   ├── protocol.py           # SandboxExecutor protocol + SandboxResult
│   ├── docker.py             # DockerSandbox (container isolation)
│   ├── subprocess_sandbox.py # SubprocessSandbox (timeout + limits)
│   └── policy.py             # NetworkPolicy, FilesystemPolicy
│
├── meta/                     # Meta-Harness (arXiv:2603.28052)
│   ├── filesystem.py         # Candidate filesystem manager
│   ├── proposer.py           # GPT-5 proposer (reads FS, proposes configs)
│   ├── evaluator.py          # Run candidate, collect scores
│   ├── evolver.py            # Evolution loop: propose → evaluate → store
│   ├── history.py            # .testforge/evolution/ persistence
│   └── scorer.py             # Signal/noise, coverage, cost metrics
│
└── reporting/
    ├── json_reporter.py
    ├── html_reporter.py      # Dark theme dashboard
    ├── junit_xml.py          # CI-compatible JUnit XML
    └── unified.py            # UnifiedReportBuilder (multi-format)
```

## Key Interfaces

### ToolAdapter Protocol
```python
class ToolAdapter(Protocol):
    name: str                     # "pytest", "cargo-clippy"
    category: ToolCategory        # UNIT_TEST, SAST, DAST, LINT, ...
    languages: list[Language]     # [Language.RUST]
    binary: str                   # "cargo"

    def detect(self, project_root: Path) -> bool: ...
    def build_command(self, project_root: Path, config: dict) -> list[str]: ...
    def parse_output(self, stdout, stderr, exit_code) -> ToolOutput: ...
    def filesystem_mode -> str: ...   # "readonly" or "readwrite"
    def default_timeout -> int: ...
```

### DynamicToolAdapter
Generated at runtime by the ToolScout agent. No Python class needed per tool — the LLM outputs a spec dict:
```json
{
  "name": "cargo-clippy",
  "binary": "cargo",
  "command_template": ["cargo", "clippy", "--message-format=json"],
  "parse_strategy": "rust_diag",
  "category": "lint"
}
```

### Shared State
```python
class TestForgeState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    project_root: str
    manifest: dict
    detected_languages: list[str]
    tool_registry_snapshot: dict    # builtin + dynamic adapters
    plan: TestPlan | None
    results: Annotated[list[TestResult], operator.add]  # fan-in via reducer
    healed_results: Annotated[list[TestResult], operator.add]
    findings: Annotated[list[Finding], operator.add]
    memory: CompactedMemory
    meta_scores: dict
    report: Report | None
```

## Data Flow

1. **detect_languages** writes `detected_languages: ["rust"]`
2. **discover_tools** writes `tool_registry_snapshot: {adapters: [...]}`
3. **tool_scout** enriches snapshot with dynamically discovered tools
4. **planner** writes `plan: TestPlan(test_types=[unit, security])`
5. **executors** (parallel) each append to `results: [TestResult, ...]` via `operator.add` reducer
6. **healer** appends to `healed_results`
7. **triage** appends to `findings`
8. **reporter** writes `report: Report` + artifact files
9. **meta_evaluate** writes `meta_scores: {tool → {total, passed, failed}}`
