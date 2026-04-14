# How It Works — Step by Step

This document walks through a complete TestForge run against a Rust project.

## Step 0: Configuration

The user creates a `testforge.yaml`:
```yaml
project_name: mathlib-rust
test_types: [unit, security]
unit:
  enabled: true
security:
  enabled: true
```

Run with: `testforge run -m testforge.yaml`

## Step 1: Language Detection (Pure Function)

The `LanguageDetector` scans the project root:
- Finds `Cargo.toml` → marks **Rust**
- Counts `.rs` files (≥3) → confirms **Rust**
- Result: `detected_languages: ["rust"]`

No LLM call needed. This is a pure deterministic scan.

## Step 2: Tool Registry Lookup (Pure Function)

The `ToolRegistry` auto-discovers built-in adapters from `testforge/tools/adapters/`:
- Finds `cargo_test_adapter.py` → registers `cargo-test`
- Finds `semgrep_adapter.py` → registers `semgrep`
- Checks which are applicable to Rust + available on PATH

Result: `tool_registry_snapshot: {adapters: [cargo-test, semgrep]}`

## Step 3: ToolScout — Dynamic Discovery (GPT-5)

This is the key differentiator. The ToolScout agent:

1. **Reads `Cargo.toml`** via `read_file` tool:
   ```toml
   [package]
   name = "mathlib"
   edition = "2021"
   ```

2. **Probes PATH** via `probe_binaries` tool:
   ```
   cargo: /Users/I074560/.cargo/bin/cargo
   clippy: not found (but cargo clippy works)
   cargo-audit: not found
   miri: not found (but cargo +nightly miri works)
   ```

3. **GPT-5 reasons** about what tools are available:
   > "Cargo is on PATH. `cargo clippy` is available via cargo subcommand.
   > `cargo miri` requires nightly but let's try. I'll generate specs for
   > cargo test, cargo clippy, and cargo miri."

4. **Outputs dynamic specs**:
   ```json
   [
     {"name": "cargo test", "binary": "cargo",
      "command_template": ["cargo", "test"],
      "parse_strategy": "generic", "category": "unit_test"},
     {"name": "cargo clippy", "binary": "cargo",
      "command_template": ["cargo", "clippy", "--message-format=json"],
      "parse_strategy": "rust_diag", "category": "lint"},
     {"name": "cargo miri", "binary": "cargo",
      "command_template": ["cargo", "+nightly", "miri", "test"],
      "parse_strategy": "generic", "category": "unit_test"}
   ]
   ```

These become `DynamicToolAdapter` instances — no Python class was written for any of them.

## Step 4: Planner (GPT-5)

The planner sees:
- Languages: `[rust]`
- Available tools: `[cargo-test, semgrep, cargo test, cargo clippy, cargo miri]`
- Manifest: `test_types: [unit, security]`

It reads `src/lib.rs` to understand the project, then produces:
```json
{
  "test_types": ["unit", "security"],
  "rationale": "Unit tests via cargo test + cargo miri for UB detection. Security via semgrep SAST + cargo clippy linting.",
  "target_paths": ["src/lib.rs"]
}
```

## Step 5: Memory Compaction (Pure Function)

Before fanning out to executors, the planner's conversation (10+ messages from tool-calling) is compacted:
- Summary: `"Plan: test types=[unit, security], targeting src/lib.rs"`
- Decisions: `[{type: "plan", test_types: ["unit", "security"]}]`

This prevents executors from inheriting a bloated message history.

## Step 6: Parallel Execution (LangGraph Send)

`route_by_language` creates a `Send("language_executor", state)` for each detected language. For Rust, one executor runs with:
- `_executor_language: "rust"`
- `_executor_tools: [cargo-test, semgrep, cargo test, cargo clippy, cargo miri]`

The executor wraps each adapter as a LangChain `@tool` and lets GPT-5 decide the invocation order:

```
GPT-5: "Let me run cargo test first to get the test baseline."
  → calls run_cargo_test(config_json='{}')
    → SubprocessSandbox runs: cargo test
    → DynamicToolAdapter.parse_output() → ToolOutput

GPT-5: "Now let me run cargo clippy for linting."
  → calls run_cargo_clippy(config_json='{}')
    → runs: cargo clippy --message-format=json
    → rust_diag parser extracts warnings

GPT-5: "Let me check for UB with miri."
  → calls run_cargo_miri(config_json='{}')
    → runs: cargo +nightly miri test
```

Each tool runs through the **SubprocessSandbox** with timeout enforcement and output truncation.

## Step 7: Fan-In (LangGraph Reducer)

All executor results merge via `operator.add` on the `results` field:
```python
results: Annotated[list[TestResult], operator.add]
```

If there were 3 languages running in parallel, their result lists would be automatically concatenated.

## Step 8: Healer (GPT-5)

The healer filters `results` for `status == FAILED`:
- Reads the failing test source
- Reads the production source
- Reasons about the fix
- Applies a patch via `apply_patch` tool
- Re-runs the test to verify

In the Rust example, it added `#[ignore = "Known bug"]` annotations to failing tests.

**Safety constraint**: Only modifies test files, never production code. Maximum heal attempts: 2.

## Step 9: Triage (GPT-5)

The triage agent classifies remaining failures:
```
[critical] undefined-behavior: cargo miri found UB
[high]     test-failure: cargo test had 4 assertion failures
```

Each finding gets: severity, category, recommendation.

## Step 10: Reporter (Pure Function)

The `UnifiedReportBuilder` writes three formats simultaneously:
- `artifacts/report.json` — machine-readable
- `artifacts/report.html` — dark-themed dashboard with tables
- `artifacts/junit.xml` — CI-compatible (Jenkins, GitHub Actions, GitLab)

## Step 11: Meta-Evaluate (Pure Function)

Scores each tool's effectiveness:
```json
{
  "cargo-test": {"total": 1, "passed": 0, "failed": 1},
  "semgrep": {"total": 1, "passed": 1, "failed": 0},
  "cargo clippy": {"total": 1, "passed": 1, "failed": 0},
  "cargo miri": {"total": 1, "passed": 0, "failed": 1}
}
```

This feeds into the Meta-Harness evolution loop for future optimization.

## What GPT-5 Does vs What's Deterministic

| Node | GPT-5 | Deterministic |
|------|-------|--------------|
| detect_languages | — | Scans files |
| discover_tools | — | Registry lookup |
| tool_scout | Reads project files, reasons about tools | — |
| planner | Decides what to test | — |
| compact_memory_pre | — | Summarizes context |
| executor | Decides tool invocation order + args | Subprocess runs the tool |
| compact_memory_post | — | Merges results |
| healer | Reasons about fix, writes patch | Re-runs test to verify |
| triage | Classifies severity/category | — |
| reporter | — | Writes JSON/HTML/XML |
| meta_evaluate | — | Computes scores |
