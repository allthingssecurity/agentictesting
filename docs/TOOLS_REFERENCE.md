# Tools Reference — Per Runtime/Language

## How Tool Discovery Works

TestForge discovers tools in three tiers:

1. **Built-in adapters** — Python classes in `testforge/tools/adapters/`. Always available.
2. **Entry-point plugins** — Third-party packages register via `pyproject.toml` entry points.
3. **Dynamic discovery (ToolScout)** — GPT-5 reads ecosystem files and probes PATH at runtime.

Tier 3 is what makes TestForge truly polyglot — no code needed to support a new tool.

## Python

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **pytest** | unit_test | `pytest --json-report --json-report-file=report.json` | JSON (pytest-json-report plugin) |
| **semgrep** | sast | `semgrep scan --json --config auto` | JSON findings array |

### Dynamically Discovered (examples)
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| ruff | lint | `ruff check --output-format=json` | jsonl_findings |
| bandit | sast | `bandit -r . -f json` | jsonl_findings |
| mypy | lint | `mypy --output=json` | jsonl_findings |
| coverage | unit_test | `coverage run -m pytest && coverage json` | generic |

## Rust

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **cargo-test** | unit_test | `cargo test --message-format=json` | JSONL (cargo messages) |

### Dynamically Discovered
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| cargo clippy | lint | `cargo clippy --message-format=json` | rust_diag |
| cargo audit | sast | `cargo audit --json` | jsonl_findings |
| cargo miri | unit_test | `cargo +nightly miri test` | generic |
| cargo nextest | unit_test | `cargo nextest run --message-format=json` | generic |
| cargo deny | sast | `cargo deny check` | generic |

## JavaScript / TypeScript

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **jest** | unit_test | `npx jest --json --forceExit` | JSON (testResults array) |
| **vitest** | unit_test | `npx vitest run --reporter=json` | JSON |
| **playwright** | e2e_test | `npx playwright test --reporter=json` | JSON (suites/specs/tests) |

### Dynamically Discovered
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| eslint | lint | `npx eslint --format=json .` | jsonl_findings |
| npm audit | sast | `npm audit --json` | generic |
| tsc | lint | `npx tsc --noEmit` | generic |
| cypress | e2e_test | `npx cypress run --reporter=json` | jest_json |

## Go

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **go-test** | unit_test | `go test -json ./...` | NDJSON (TestEvent stream) |

### Dynamically Discovered
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| golangci-lint | lint | `golangci-lint run --out-format=json` | jsonl_findings |
| gosec | sast | `gosec -fmt=json ./...` | jsonl_findings |
| govulncheck | sast | `govulncheck ./...` | generic |
| staticcheck | lint | `staticcheck -f json ./...` | jsonl_findings |

## Java / Kotlin

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **junit5** | unit_test | `mvn test -B -q` or `gradle test` | JUnit XML (surefire-reports/) |

### Dynamically Discovered
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| spotbugs | sast | `mvn spotbugs:check` | generic |
| checkstyle | lint | `mvn checkstyle:check` | generic |
| pmd | sast | `mvn pmd:check` | generic |
| dependency-check | sast | `mvn dependency-check:check` | generic |

## Ruby

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **rspec** | unit_test | `rspec --format json` | JSON (examples array) |

### Dynamically Discovered
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| rubocop | lint | `rubocop --format json` | jsonl_findings |
| brakeman | sast | `brakeman --format json` | jsonl_findings |
| bundler-audit | sast | `bundle audit check --format=json` | jsonl_findings |

## C# / .NET

### Built-in Adapters
| Tool | Category | CLI Command | Output Format |
|------|----------|-------------|---------------|
| **dotnet-test** | unit_test | `dotnet test --verbosity normal` | Text (TRX via --logger) |

### Dynamically Discovered
| Tool | Category | CLI Command | Parse Strategy |
|------|----------|-------------|---------------|
| dotnet format | lint | `dotnet format --verify-no-changes` | generic |

## Security Tools (Cross-Language)

### Built-in
| Tool | Category | Languages | CLI Command |
|------|----------|-----------|-------------|
| **semgrep** | sast | All (30+ langs) | `semgrep scan --json --config auto` |
| **nuclei** | dast | N/A (URL target) | `nuclei -u <url> -jsonl -silent` |
| **schemathesis** | api_fuzz | N/A (OpenAPI) | `st run <spec>` |

## Parse Strategies

When the ToolScout creates a DynamicToolAdapter, it assigns a parse strategy:

| Strategy | When to Use | How It Parses |
|----------|------------|---------------|
| `generic` | Any tool | Exit code 0 = pass, else fail |
| `go_json` | `go test -json` | NDJSON events: Action, Test, Elapsed |
| `rust_diag` | cargo clippy/build | Compiler messages with spans/line numbers |
| `jest_json` | jest/vitest --json | testResults array with status/failureMessages |
| `jsonl_findings` | Security scanners | Each line is a JSON finding object |

## Adding a Custom Tool

### Option A: Python Adapter (for complex parsing)
```python
from testforge.tools.adapters._base import BaseToolAdapter

class MyToolAdapter(BaseToolAdapter):
    name = "my-tool"
    category = ToolCategory.UNIT_TEST
    languages = [Language.PYTHON]
    binary = "my-tool"

    def build_command(self, project_root, config):
        return ["my-tool", "run", "--json"]

    def parse_output(self, stdout, stderr, exit_code):
        return ToolOutput(tool_name=self.name, ...)
```

### Option B: Entry Point Plugin
```toml
# In your package's pyproject.toml:
[project.entry-points."testforge.tools"]
my_tool = "my_package.adapter:MyToolAdapter"
```

### Option C: Let ToolScout Discover It (zero code)
Just install the tool binary on PATH. The ToolScout will find it, read your project files, and generate a DynamicToolAdapter automatically.
