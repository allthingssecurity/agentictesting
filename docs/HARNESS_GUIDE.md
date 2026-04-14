# Designing Harnesses for Testing Scenarios

## What Is a Testing Harness?

A testing harness is the infrastructure layer between the LLM agent and the testing tools. It decides:
- **What tools** to run (and discovers new ones dynamically)
- **In what environment** (sandboxed, resource-limited)
- **How to parse** tool output into structured evidence
- **What to do** with results (heal, triage, report, evolve)

The harness is NOT the tests themselves — it's the system that orchestrates testing.

## Harness Design Patterns

### Pattern 1: Language-Specific Tool Chain

Each language ecosystem has a standard testing stack. The harness must know these idioms:

```
Python:    pytest → bandit/semgrep → mypy → coverage.py
Rust:      cargo test → cargo clippy → cargo audit → cargo miri
Go:        go test → golangci-lint → gosec → govulncheck
JS/TS:     jest/vitest → eslint → npm audit → playwright
Java:      JUnit5/Maven → SpotBugs → checkstyle → OWASP dep-check
Ruby:      rspec → rubocop → brakeman → bundler-audit
C#:        dotnet test → dotnet format → security scan
C/C++:     ctest/gtest → cppcheck → clang-tidy → valgrind
```

TestForge's ToolScout discovers these dynamically by reading ecosystem files.

### Pattern 2: Layered Execution

Run tools in cost-order:
1. **Fast lane** (< 30s): Linters, static analysis, unit tests
2. **Medium lane** (< 5min): Integration tests, API fuzzing
3. **Slow lane** (< 30min): E2E browser tests, DAST scans, miri/valgrind

The planner decides the layers. Fast failures stop expensive tools from running.

### Pattern 3: Evidence Normalization

Every tool outputs a different format. The harness normalizes everything into one model:

```python
class TestResult:
    test_type: TestType      # unit, integration, browser, api, security
    name: str                # test identifier
    status: Status           # passed, failed, error, skipped, healed
    duration_ms: float
    message: str             # failure/error details
    language: str            # which language this result is from
    tool_adapter: str        # which tool produced this result
```

This means the reporter, healer, and triage agent all work with the same data regardless of whether it came from pytest, cargo test, or jest.

### Pattern 4: Repair Loop

```
failure detected
  → read test source
  → read production source
  → reason about fix (GPT-5)
  → apply patch
  → re-run test
  → pass? → mark as healed
  → fail? → try again (up to N attempts)
  → still fail? → escalate to triage
```

**Safety constraints:**
- Only modify test files, never production code
- Maximum attempts configurable (default: 2)
- Security findings are never auto-fixed

### Pattern 5: Meta-Harness Evolution

From [arXiv:2603.28052](https://arxiv.org/abs/2603.28052):

```
candidate_001/config.yaml   → run pipeline → scores.json
candidate_002/config.yaml   → run pipeline → scores.json
  ...
proposer reads ALL prior candidates' source + traces + scores
  → proposes candidate_N+1/config.yaml
  → evaluate → compare → keep best
```

The proposer has access to the complete filesystem of prior runs — up to 10M tokens of diagnostic context per step. It performs counterfactual diagnosis across execution traces.

## Designing a Harness for Your Scenario

### Step 1: Define the Test Types

What kinds of testing does your project need?
- Unit tests (always)
- Integration tests (if services/databases)
- E2E/browser tests (if web UI)
- API tests (if HTTP APIs)
- Security scans (always recommended)

### Step 2: Choose the Manifest

```yaml
project_name: my-project
test_types: [unit, security]   # Start small

unit:
  enabled: true
  timeout: 60
security:
  enabled: true
  timeout: 120

# Let ToolScout discover tools dynamically:
# No need to list specific tools
```

### Step 3: Let the Scout Run

`testforge plan` will:
1. Detect your language(s)
2. Discover available tools
3. Show you what would run

```bash
$ testforge plan
Languages: rust
Tools: cargo-test, semgrep, cargo clippy (dynamic), cargo miri (dynamic)
```

### Step 4: Run and Iterate

```bash
$ testforge run
# First run establishes baseline

$ testforge evolve --iterations 3
# Meta-Harness optimizes the configuration
```

### Step 5: Customize Policies

```yaml
sandbox:
  mode: docker          # Full isolation
  image: testforge/sandbox:latest

memory:
  window_size: 10       # Messages to keep in active window
  token_budget: 16000   # Max tokens per agent

reporting:
  formats: [json, html, junit_xml]
  output_dir: artifacts
```

## Common Harness Configurations

### Minimal (CI Pipeline)
```yaml
test_types: [unit]
unit:
  enabled: true
  timeout: 30
heal_max_attempts: 0     # No healing in CI
```

### Standard (Development)
```yaml
test_types: [unit, security]
heal_max_attempts: 2
reporting:
  formats: [json, html]
```

### Comprehensive (Release Gate)
```yaml
test_types: [unit, integration, browser, api, security]
heal_max_attempts: 3
meta_harness:
  enabled: true
  auto_evolve: true
sandbox:
  mode: docker
```
