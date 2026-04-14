# TestForge v0.5 — Polyglot Agentic Testing Framework

A self-evolving, language-aware testing harness powered by LangGraph and GPT-5. TestForge dynamically discovers testing tools for any language, orchestrates them through specialized agents, and evolves its own configuration via Meta-Harness optimization.

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

- [DESIGN.md](docs/DESIGN.md) — Why harnesses matter, theoretical foundations
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture and component design
- [WORKING.md](docs/WORKING.md) — How the pipeline works step-by-step
- [HARNESS_GUIDE.md](docs/HARNESS_GUIDE.md) — Designing harnesses for testing scenarios
- [TOOLS_REFERENCE.md](docs/TOOLS_REFERENCE.md) — Tool adapters per runtime/language
- [META_HARNESS.md](docs/META_HARNESS.md) — Meta-Harness evolution (arXiv:2603.28052)

## Example Results

### Rust Project (`example_rust/`)
- **ToolScout discovered**: cargo test, cargo clippy, cargo miri (dynamic)
- **cargo miri found critical undefined behavior** — a finding no other tool produced
- Pass rate: 50% → Healer patched tests with `#[ignore]` + bug documentation

### TypeScript Project (`example_ts/`)
- **ToolScout discovered**: npm-audit, playwright (dynamic)
- **npm-audit confirmed zero vulnerabilities**
- Vitest caught 4 bugs: filterByPriority, completionPercentage, searchTasks
- Pass rate: 57% → Triage classified all as regression/high-severity

## License

MIT
