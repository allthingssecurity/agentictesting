# Meta-Harness: Self-Evolving Test Configuration

Based on [arXiv:2603.28052](https://arxiv.org/abs/2603.28052) — *"Meta-Harness: End-to-End Optimization of Model Harnesses"* (Lee et al., 2026).

## The Idea

Instead of manually tuning which tools to run, what rules to enable, and what timeouts to set — **let an LLM optimize the harness configuration itself** by reading the results of prior runs.

## How It Works

```
Iteration 0 (Baseline):
  config.yaml → TestForge pipeline → scores.json + traces.jsonl

Iteration 1:
  Proposer reads: candidate_001/{config.yaml, traces.jsonl, scores.json}
  Proposer outputs: candidate_002/config.yaml (with targeted changes)
  Evaluate: candidate_002 → scores.json
  Compare: if better, adopt as new baseline

Iteration 2:
  Proposer reads: candidate_001/ + candidate_002/
  Proposes: candidate_003/ (informed by both prior attempts)
  ...
```

## The Key Innovation: Filesystem Access

From the paper:
> The proposer accesses the **source code, scores, and execution traces** of all prior candidates through a filesystem.

This gives the proposer up to **10M tokens of diagnostic context per step** — far more than fitting everything into a prompt. The proposer can:
- Read the exact tool commands that were run
- See which tests passed/failed and why
- Compare configurations side-by-side
- Perform counterfactual diagnosis ("candidate_002 disabled semgrep rule X, and false positives dropped by 40%")

## Filesystem Structure

```
.testforge/evolution/
├── candidates/
│   ├── candidate_001/
│   │   ├── config.yaml        # The harness configuration
│   │   ├── trace.jsonl        # Every tool call + result
│   │   ├── scores.json        # Metrics: pass_rate, signal_noise, etc.
│   │   └── report.json        # Full TestForge report
│   ├── candidate_002/
│   │   └── ...
│   └── candidate_003/
│       └── ...
├── leaderboard.json           # Ranked by composite_score
└── evolution_log.jsonl        # Proposer reasoning + diffs
```

## Scoring Metrics

| Metric | What It Measures | Weight |
|--------|-----------------|--------|
| **pass_rate** | Fraction of tests passing | 30% |
| **signal_to_noise** | Actionable findings / total findings | 30% |
| **unique_coverage** | Findings only this tool found | 25% |
| **cost_efficiency** | Findings per second of execution | 15% |

Composite score = weighted sum, used to rank candidates on the leaderboard.

## What Gets Evolved

The proposer can modify any aspect of the harness configuration:
- **Enable/disable tools** — turn off tools that produce only noise
- **Change tool arguments** — add `--strict` to a linter, change timeout
- **Adjust test markers** — run only integration tests, skip flaky ones
- **Tune semgrep rules** — disable rules with high false-positive rates
- **Add nuclei templates** — target specific vulnerability types
- **Change execution order** — run fast tools first

## Running Evolution

```bash
# Run 3 iterations of Meta-Harness evolution
testforge evolve --iterations 3

# Output:
#   Iteration 0: composite=0.650 pass_rate=82%  (baseline)
#   Iteration 1: composite=0.720 pass_rate=88%  (disabled noisy rule)
#   Iteration 2: composite=0.735 pass_rate=90%  (added cargo clippy)
#   Best: candidate_003 (score: 0.735)
```

## Code Structure

```
testforge/meta/
├── filesystem.py    # CandidateFilesystem: save/load/query candidates
├── proposer.py      # HarnessProposer: GPT-5 reads FS, proposes new config
├── evaluator.py     # CandidateEvaluator: runs pipeline, collects scores
├── evolver.py       # HarnessEvolver: propose → evaluate → store loop
├── history.py       # EvolutionHistory: query past results
└── scorer.py        # MetricScorer: signal/noise, coverage, cost
```

## When to Use

- After initial setup, run `evolve` to find optimal tool configuration
- Periodically in CI to adapt to codebase changes
- When adding new tools to find the right balance
- When false positive rates are too high
