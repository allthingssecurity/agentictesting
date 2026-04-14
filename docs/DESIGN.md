# Design: Why Harnesses Are the Key

## The Core Insight

From [Zhou et al., 2026 (arXiv:2604.08224)](https://arxiv.org/abs/2604.08224) — *"Externalization in LLM Agents"*:

> A harness is the **persistent infrastructure that envelops the model** and coordinates memory, skills, and protocols into a coherent runtime environment. It transforms hard cognitive burdens into forms that the model can solve more reliably.

The paper's Figure 3 shows a harnessed LLM agent where the **Harness sits at the center**, surrounded by three externalization dimensions:

```
                    ┌──────────────┐
                    │    Memory    │
                    │  (state)     │
                    └──────┬───────┘
                           │
        ┌──────────┐  ┌────┴────┐  ┌──────────┐
        │  Skills  │──│ HARNESS │──│ Protocols│
        │(expertise)│  └────┬────┘  │(interact)│
        └──────────┘       │       └──────────┘
                           │
              ┌────────────┴────────────┐
              │  Operational Elements   │
              │  • Sandboxing           │
              │  • Observability        │
              │  • Compression          │
              │  • Evaluation           │
              │  • Approval gates       │
              │  • Sub-agent orchestr.  │
              └─────────────────────────┘
```

## Why Harness > Prompt Engineering

Traditional approaches focus on *what to tell the model* (prompt engineering). Harness engineering asks a fundamentally different question: **what environment should the model operate in?**

| Approach | What it optimizes | Limitation |
|----------|------------------|------------|
| Prompt engineering | The input text | Brittle, doesn't scale across tools |
| Fine-tuning | Model weights | Expensive, static after training |
| **Harness engineering** | **The runtime infrastructure** | Adapts to any tool, language, project |

For testing specifically, the harness determines:
- **Which tools** to invoke (pytest? cargo test? jest?)
- **In what order** (unit first, then security? or parallel?)
- **How to parse** each tool's output (JSON? JSONL? JUnit XML?)
- **What to do** with failures (heal? triage? report?)
- **How to evolve** the configuration based on results

## The Six Dimensions of Harness Design

From the paper, adapted for testing:

### 1. Agent Loop and Control Flow
The testing pipeline is a directed graph:
```
detect → scout → plan → execute → heal → triage → report → evolve
```
Each node is either a pure function (deterministic) or an LLM agent (reasoning). The control flow is defined by LangGraph's StateGraph with conditional edges for fan-out/fan-in.

### 2. Sandboxing and Execution Isolation
Testing tools execute untrusted code. The harness must:
- Isolate tool execution in containers or sandboxed subprocesses
- Enforce filesystem policies (SAST tools get readonly, test runners get readwrite)
- Apply network policies (block internet for unit tests, allow localhost for API tests)
- Set resource limits (memory, CPU, timeout)

### 3. Human Oversight and Approval Gates
The healer agent modifies test files. The harness enforces:
- Never modify production code (only test files)
- Maximum heal attempts per failure
- Report findings for human review rather than auto-fixing security issues

### 4. Observability and Structured Feedback
Every agent action produces structured JSON logs:
```json
{"event": "tool_call", "agent": "executor", "tool": "cargo-test",
 "args": {"test_path": "."}, "duration_ms": 1234}
```
This enables the Meta-Harness to analyze what worked and what didn't.

### 5. Configuration and Policy Encoding
The `testforge.yaml` manifest encodes policies:
- Which test types are enabled/disabled
- Timeouts per tool
- Memory budgets per agent
- Sandbox mode (docker/subprocess/none)
- Reporting formats

### 6. Context Budget Management
LLM context windows are finite. The harness manages this via:
- Memory compaction nodes between pipeline phases
- Sliding window over recent messages
- LLM summarization of older context
- Token budget enforcement (default 16K tokens per agent)

## Why This Matters for Testing

Testing is a uniquely good fit for harness engineering because:

1. **Tools are diverse**: Every language has different test runners, linters, security scanners. The harness abstracts this.

2. **Output formats vary**: pytest gives JSON, cargo test gives JSONL, JUnit gives XML. The harness normalizes them into one evidence model.

3. **Judgment is needed**: Is a failing test a real bug or a flaky test? Is a semgrep finding a true positive? LLM agents in the harness make these calls.

4. **Evolution is natural**: Testing configurations drift. Rules get stale. The Meta-Harness continuously optimizes by reading execution traces and proposing improvements.

5. **Safety boundaries are critical**: You can't let an agent `rm -rf /` while fixing a test. The harness enforces sandboxing and policy.

## Design Principles

1. **Tools are pluggable, not hardcoded** — The ToolScout discovers tools dynamically. You never need to write adapter code for a new tool.

2. **Languages are detected, not configured** — The harness scans for package files and file extensions. A Rust project automatically gets Rust tools.

3. **Memory is compacted, not accumulated** — Context is summarized between phases to prevent token overflow in long pipelines.

4. **Execution is sandboxed, not trusted** — Every tool runs in an isolated environment with explicit policies.

5. **The harness evolves itself** — The Meta-Harness reads prior execution traces and proposes improved configurations, following the optimization loop from [arXiv:2603.28052](https://arxiv.org/abs/2603.28052).
