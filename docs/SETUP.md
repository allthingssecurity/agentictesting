# Setup Guide — Run TestForge Against Your Project

## Prerequisites

- **Python 3.11+**
- **OpenAI API key** with GPT-5 access (or GPT-4o)
- Your project's native tools installed (pytest, cargo, npm, etc.)

## Step 1: Install TestForge

```bash
git clone https://github.com/allthingssecurity/agentictesting.git
cd agentictesting

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify:
```bash
testforge --help
```

## Step 2: Set Your API Key

```bash
export OPENAI_API_KEY=sk-...
```

To use a different model (e.g., GPT-4o), add to your `testforge.yaml`:
```yaml
llm:
  model: gpt-4o
```

## Step 3: Create a testforge.yaml in Your Project

Create `testforge.yaml` in your project root:

```yaml
# Minimal — TestForge auto-detects everything else
project_name: my-project
test_types:
  - unit
  - security
```

That's it. TestForge will:
- Auto-detect your language(s) from package files
- Discover available tools via ToolScout
- Run what it finds

### Full Configuration (all options)

```yaml
project_name: my-project
project_root: .

# Which test categories to enable
test_types:
  - unit          # pytest, jest, cargo test, go test, etc.
  - security      # semgrep, nuclei, cargo clippy, etc.
  # - integration # pytest -m integration, etc.
  # - api         # schemathesis against OpenAPI spec
  # - browser     # playwright E2E tests

# Override auto-detection (optional)
# languages: [python, rust]

# Per-category settings
unit:
  enabled: true
  timeout: 60
  extra_args: []

security:
  enabled: true
  timeout: 120

api:
  enabled: false
  timeout: 90

browser:
  enabled: false
  timeout: 180

# API testing (if enabled)
openapi_spec: ./openapi.yaml
base_url: http://localhost:8000

# Healer: how many times to retry fixing a failing test
heal_max_attempts: 2

# LLM settings
llm:
  model: gpt-5
  temperature: 0.0

# Memory compaction
memory:
  window_size: 10        # Messages to keep in active window
  token_budget: 16000    # Max tokens per agent

# Sandbox mode
sandbox:
  mode: subprocess       # "subprocess" (default) or "docker"
  # image: testforge/sandbox:latest  # for Docker mode

# Reporting output
reporting:
  formats: [json, html, junit_xml]
  output_dir: artifacts

# Meta-Harness evolution (optional)
meta_harness:
  enabled: false
  auto_evolve: false
```

## Step 4: Check What TestForge Sees

Before running the full pipeline, preview what TestForge detects:

```bash
cd /path/to/your/project
testforge plan
```

Output:
```
Languages: python, typescript
Tools: pytest, semgrep, vitest, npm-audit (dynamic)
  pytest (unit_test) → python
  semgrep (sast) → python, javascript, typescript, ...
  vitest (unit_test) → javascript, typescript
  npm-audit (sast) → javascript, typescript
```

List all available adapters:
```bash
testforge tools list
```

## Step 5: Run the Full Pipeline

```bash
testforge run -m testforge.yaml
```

This will:
1. Detect languages in your project
2. Discover tools (builtin + dynamic via GPT-5 ToolScout)
3. Plan which tests to run
4. Execute tools in parallel (one executor per language)
5. Heal failing tests (patch + re-run)
6. Triage findings (classify severity + category)
7. Generate reports (JSON + HTML + JUnit XML)

Output goes to `artifacts/`:
```
artifacts/
├── report.html     # Open in browser — dark-themed dashboard
├── report.json     # Machine-readable structured data
└── junit.xml       # CI-compatible (Jenkins, GitHub Actions, GitLab)
```

## Step 6 (Optional): Evolve the Harness

After a few runs, use the Meta-Harness to optimize your configuration:

```bash
testforge evolve --iterations 3
```

This runs the [Meta-Harness loop](META_HARNESS.md): propose config changes → evaluate → keep the best.

Results stored in `.testforge/evolution/`.

## Common Scenarios

### Python project with pytest
```yaml
project_name: my-python-app
test_types: [unit, security]
```
TestForge auto-detects Python from `pyproject.toml` / `requirements.txt`, runs pytest + semgrep.

### Rust project
```yaml
project_name: my-rust-lib
test_types: [unit, security]
```
ToolScout discovers `cargo test`, `cargo clippy`, `cargo miri`, `cargo audit` based on what's installed.

### TypeScript/React project
```yaml
project_name: my-react-app
test_types: [unit, security, browser]
browser:
  enabled: true
```
Runs vitest/jest + semgrep + playwright (if configured).

### Full-stack with API
```yaml
project_name: my-api
test_types: [unit, api, security]
api:
  enabled: true
openapi_spec: ./openapi.yaml
base_url: http://localhost:8000
```
Start your server first, then run TestForge. Schemathesis will fuzz your API endpoints.

### Multi-language monorepo
```yaml
project_name: my-monorepo
test_types: [unit, security]
```
TestForge detects all languages in the repo and runs parallel executors — one per language.

## Troubleshooting

### "No tools detected"
- Make sure your language's test runner is installed and on PATH
- Check `testforge tools list` to see what's available
- The ToolScout needs at least one ecosystem file (Cargo.toml, package.json, etc.)

### "pytest not found on PATH"
```bash
pip install pytest pytest-json-report
```

### Tests run but no results parsed
- Check that `pytest-json-report` is installed (for Python)
- For Rust, `cargo test` output is parsed from stderr — this is normal

### API key errors
```bash
export OPENAI_API_KEY=sk-...
```
If using GPT-4o instead of GPT-5, set `llm.model: gpt-4o` in testforge.yaml.

### Docker sandbox mode
```bash
# Build the sandbox image first
docker build -t testforge/sandbox:latest .

# Then set in testforge.yaml:
sandbox:
  mode: docker
```
