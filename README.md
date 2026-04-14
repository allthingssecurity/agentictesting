# TestForge v0.5 — Polyglot Agentic Testing Framework

A self-evolving, language-aware testing harness powered by LangGraph and GPT-5. TestForge dynamically discovers testing tools for any language, orchestrates them through specialized agents, and evolves its own configuration via Meta-Harness optimization.

## What Testing Does This Do?

TestForge covers **6 categories of testing** across any language — all orchestrated by LLM agents that decide what to run, how to interpret results, and what to do about failures.

### 1. Unit Testing
Runs the language-native test runner against your test suite. Catches logic bugs, regressions, and assertion failures.

| Language | Tool | What It Catches |
|----------|------|-----------------|
| Python | pytest | Function-level failures, exceptions, assertion errors |
| Rust | cargo test | Panics, assertion failures, `#[should_panic]` violations |
| JS/TS | jest / vitest | Expect mismatches, thrown errors, async failures |
| Go | go test | Table-driven test failures, benchmark regressions |
| Java | JUnit 5 (Maven/Gradle) | Assertion errors, exception tests |
| Ruby | RSpec | Example failures, matcher mismatches |
| C# | dotnet test | xUnit/NUnit assertion failures |

### 2. Static Analysis (SAST)
Scans source code without executing it. Finds security vulnerabilities, code smells, and bug patterns.

| Tool | Languages | What It Catches |
|------|-----------|-----------------|
| **Semgrep** | 30+ languages | SQL injection, XSS, hardcoded secrets, insecure patterns |
| **Bandit** | Python | Security anti-patterns (eval, exec, shell injection) |
| **Cargo Clippy** | Rust | Idiomatic issues, potential bugs, performance anti-patterns |
| **ESLint** | JS/TS | Code quality, security rules, unused variables |
| **golangci-lint** | Go | Lint aggregator (gosec, staticcheck, errcheck, etc.) |
| **RuboCop** | Ruby | Style violations, security cops |
| **SpotBugs** | Java | Null pointer, resource leaks, correctness bugs |

### 3. Dynamic Analysis (DAST)
Tests running applications by sending requests and probing for vulnerabilities.

| Tool | What It Does |
|------|-------------|
| **Nuclei** | Template-based vulnerability scanning against live URLs |
| **Cargo Miri** | Detects undefined behavior in Rust (memory safety, aliasing violations) |
| **Valgrind** | Memory leaks, invalid reads/writes in C/C++ |

### 4. API Testing & Fuzzing
Exercises HTTP/REST/GraphQL APIs with generated inputs to find contract violations and crashes.

| Tool | What It Does |
|------|-------------|
| **Schemathesis** | Property-based fuzzing from OpenAPI/GraphQL schemas |
| **Pact** | Consumer-driven contract testing |

### 5. Dependency & Supply Chain Auditing
Checks your dependencies for known vulnerabilities.

| Tool | Language | What It Catches |
|------|----------|-----------------|
| **npm audit** | JS/TS | CVEs in node_modules |
| **cargo audit** | Rust | RustSec advisory database |
| **pip-audit / safety** | Python | PyPI vulnerability database |
| **bundler-audit** | Ruby | Gem vulnerabilities |
| **govulncheck** | Go | Go vulnerability database |
| **OWASP dep-check** | Java | NVD vulnerability database |

### 6. End-to-End / Browser Testing
Drives a real browser to test user flows.

| Tool | What It Does |
|------|-------------|
| **Playwright** | Cross-browser E2E testing (Chromium, Firefox, WebKit) |
| **Cypress** | Component + E2E testing for web apps |

### What the Agents Add on Top

The testing tools above run as subprocesses. The LLM agents provide the **intelligence layer**:

| Agent | What It Does |
|-------|-------------|
| **ToolScout** | Dynamically discovers which tools are available — reads Cargo.toml, package.json, go.mod and probes PATH. No hardcoding needed. |
| **Planner** | Analyzes the project and decides which test categories to run and in what order |
| **Executor** | Invokes tools with the right arguments, interprets output |
| **Healer** | Reads failing tests, understands the bug, patches test files, re-runs to verify |
| **Triage** | Classifies each failure: severity (critical/high/medium/low), category (regression, security, flaky), recommendation |
| **Meta-Harness** | Evolves the harness configuration itself by analyzing prior execution traces (arXiv:2603.28052) |

## What Makes This Different

| Feature | Traditional CI | TestForge |
|---------|---------------|-----------|
| Tool discovery | Hardcoded per project | **GPT-5 ToolScout** reads ecosystem files, probes PATH, generates tool specs at runtime |
| Language support | Configure per language | **Auto-detects** languages from package files + file extensions |
| Test repair | Manual fix | **Healer agent** reads failures, patches tests, re-runs to verify |
| Finding triage | Manual review | **Triage agent** classifies severity, category, recommendations |
| Harness optimization | Manual tuning | **Meta-Harness** (arXiv:2603.28052) evolves configs from execution traces |
| Report format | Pick one | JSON + HTML + JUnit XML simultaneously |

## Quick Start

```bash
# Install
pip install -e .

# See available tools for your project
testforge tools list -r /path/to/your/project

# Dry-run: detect languages and plan
testforge plan -r /path/to/your/project

# Full pipeline
export OPENAI_API_KEY=sk-...
testforge run -m testforge.yaml -r /path/to/your/project

# Meta-Harness evolution (optimize the harness itself)
testforge evolve -r /path/to/your/project --iterations 3
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

```
START
  → detect_languages       (pure fn: scans project)
  → discover_tools          (pure fn: registry lookup)
  → tool_scout              (GPT-5: dynamic tool discovery)
  → planner                 (GPT-5: language-aware test plan)
  → compact_memory_pre      (pure fn: summarize context)
  → [parallel executors]    (one per detected language)
  → compact_memory_post     (pure fn: merge results)
  → healer                  (GPT-5: fix failing tests)
  → triage                  (GPT-5: classify findings)
  → reporter                (pure fn: JSON + HTML + JUnit XML)
  → meta_evaluate           (pure fn: score tool effectiveness)
  → END
```

## Supported Languages & Tools

TestForge has **12 built-in adapters** and discovers additional tools dynamically:

| Language | Built-in Adapters | Dynamically Discovered (examples) |
|----------|------------------|----------------------------------|
| Python | pytest, semgrep | ruff, bandit, mypy, pyright |
| JavaScript/TypeScript | jest, vitest, playwright | eslint, npm-audit |
| Rust | cargo-test | cargo clippy, cargo audit, cargo miri |
| Go | go-test | golangci-lint, gosec, govulncheck |
| Java/Kotlin | junit5 | spotbugs, checkstyle, gradle test |
| Ruby | rspec | rubocop, brakeman |
| C# | dotnet-test | dotnet format |
| C/C++ | — | ctest, cppcheck, clang-tidy |

## Documentation

- **[SETUP.md](docs/SETUP.md) — How to run TestForge against your project** (start here)
- [DESIGN.md](docs/DESIGN.md) — Why harnesses matter, theoretical foundations
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture and component design
- [WORKING.md](docs/WORKING.md) — How the pipeline works step-by-step
- [HARNESS_GUIDE.md](docs/HARNESS_GUIDE.md) — Designing harnesses for testing scenarios
- [TOOLS_REFERENCE.md](docs/TOOLS_REFERENCE.md) — Tool adapters per runtime/language
- [META_HARNESS.md](docs/META_HARNESS.md) — Meta-Harness evolution (arXiv:2603.28052)

## Example Results

We ran TestForge against three example projects. Each demonstrates different testing categories depending on what the ToolScout discovered and what was available on the machine.

### Python Project (`example_project/`) — FastAPI bookstore

| Category | Tool | Status |
|----------|------|--------|
| Unit Testing | pytest | 14 passed, 3 failed (division-by-zero, off-by-one bugs) |
| SAST | semgrep | 0 findings |
| DAST | — | Not run (no live server spun up) |
| API Fuzz | — | Not run (schemathesis not installed) |
| Dependency Audit | — | Not run |
| E2E / Browser | — | Not run |

**Coverage: 2 of 6 categories.** The app has FastAPI endpoints that *could* be tested with Schemathesis (API fuzz) and Nuclei (DAST) if a server were running and tools installed.

Healer patched failing tests: changed `test_zero_quantity` to expect `ZeroDivisionError`, updated pagination assertions to match the off-by-one behavior.

### Rust Project (`example_rust/`) — math library

| Category | Tool | Status |
|----------|------|--------|
| Unit Testing | cargo test | 8 passed, 4 failed (email validation, clamp logic bugs) |
| SAST | semgrep | 0 findings |
| SAST/Lint | cargo clippy (dynamic) | 0 warnings |
| DAST | cargo miri (dynamic) | **Critical: undefined behavior detected** |
| API Fuzz | — | N/A (no HTTP API) |
| Dependency Audit | — | Not run (cargo-audit not installed) |
| E2E / Browser | — | N/A (no UI) |

**Coverage: 3 of 6 categories.** ToolScout dynamically discovered cargo clippy and cargo miri — no adapter code was written for either. Miri found UB that no other tool caught.

Healer patched `lib.rs`: added `#[ignore = "Known bug"]` annotations to 3 failing tests with explanations.

### TypeScript Project (`example_ts/`) — task manager library

| Category | Tool | Status |
|----------|------|--------|
| Unit Testing | vitest | 6 passed, 4 failed (filterByPriority, completionPercentage, searchTasks bugs) |
| SAST | semgrep | 0 findings |
| DAST | — | Not run |
| API Fuzz | — | N/A (no HTTP API) |
| Dependency Audit | npm audit (dynamic) | **0 vulnerabilities** |
| E2E / Browser | playwright (dynamic) | Not run (no browser tests configured) |

**Coverage: 3 of 6 categories.** ToolScout dynamically discovered npm-audit and playwright. npm-audit confirmed clean dependencies. Playwright was detected but no E2E test files existed.

Triage classified all 4 failures as high-severity regressions with specific fix recommendations.

### What's Not Covered Yet

To exercise all 6 categories in one run, you'd need:
- A running HTTP server for DAST (Nuclei) and API fuzzing (Schemathesis)
- Playwright test files for E2E
- Security tools installed (`cargo-audit`, `bandit`, etc.)

The framework supports all 6 — the examples just don't have all the prerequisites installed.

## Generated Reports

Each example project has its reports in `artifacts/`:
- `report.html` — dark-themed dashboard ([Rust](example_rust/artifacts/report.html), [TypeScript](example_ts/artifacts/report.html), [Python](example_project/artifacts/report.html))
- `report.json` — machine-readable structured data
- `junit.xml` — CI-compatible (Jenkins, GitHub Actions, GitLab)

## License

MIT
