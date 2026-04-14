"""Meta-Harness proposer: GPT-5 agent that reads the evolution filesystem
and proposes improved harness configurations.

Following arXiv:2603.28052 — the proposer gets up to 10M tokens of diagnostic
context per step via filesystem access to all prior candidates' source code,
execution traces, and scores. It performs counterfactual diagnosis across
execution traces and proposes targeted fixes.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from testforge.llm import get_llm
from testforge.meta.filesystem import CandidateFilesystem

PROPOSER_SYSTEM_PROMPT = """\
You are a Meta-Harness Proposer agent. Your job is to optimize the testing harness
configuration by analyzing the results of prior candidates.

You have access to the complete evolution filesystem containing:
- Source configuration (config.yaml) of each prior candidate
- Execution traces (trace.jsonl) showing every tool call and result
- Scores (scores.json) with metrics like pass_rate, signal_noise, unique_coverage
- Full reports with test results and findings

Your task:
1. Analyze the performance of prior candidates
2. Identify what worked and what didn't via counterfactual diagnosis
3. Propose a NEW configuration that should perform better
4. Explain your reasoning

Focus on:
- Which tools found real issues vs produced noise
- Which tool configurations (args, rules, timeouts) were effective
- What test types or markers to add/remove
- Whether to enable/disable specific tools

Output your proposed config as a YAML block.
"""


class HarnessProposer:
    """GPT-5 proposer that reads the evolution filesystem and proposes changes."""

    def __init__(self, model: str = "gpt-5"):
        self.model = model

    def propose(
        self,
        filesystem: CandidateFilesystem,
        current_config: dict,
        max_context_candidates: int = 10,
    ) -> dict:
        """Read the filesystem, analyze prior runs, propose a new config.

        Returns dict with:
            proposed_config: dict — the new harness configuration
            reasoning: str — why these changes were proposed
            changes: list[str] — list of specific changes made
        """
        llm = get_llm(model=self.model)

        # Build filesystem context (the key Meta-Harness innovation)
        fs_summary = filesystem.get_filesystem_summary(max_candidates=max_context_candidates)

        import yaml
        current_yaml = yaml.dump(current_config, default_flow_style=False)

        messages = [
            SystemMessage(content=PROPOSER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"=== CURRENT CONFIG ===\n{current_yaml}\n\n"
                f"=== EVOLUTION HISTORY ===\n{fs_summary}\n\n"
                f"Analyze the prior candidates and propose an improved configuration. "
                f"Output your proposed config as a ```yaml block, then explain your reasoning."
            )),
        ]

        response = llm.invoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)

        # Parse proposed config from YAML block
        proposed_config = current_config.copy()
        reasoning = content
        changes = []

        try:
            yaml_start = content.find("```yaml")
            yaml_end = content.find("```", yaml_start + 7)
            if yaml_start >= 0 and yaml_end > yaml_start:
                yaml_block = content[yaml_start + 7:yaml_end].strip()
                proposed_config = yaml.safe_load(yaml_block) or current_config
                reasoning = content[yaml_end + 3:].strip()
        except Exception:
            pass

        # Identify changes
        for key in set(list(proposed_config.keys()) + list(current_config.keys())):
            old_val = current_config.get(key)
            new_val = proposed_config.get(key)
            if old_val != new_val:
                changes.append(f"{key}: {old_val} → {new_val}")

        return {
            "proposed_config": proposed_config,
            "reasoning": reasoning,
            "changes": changes,
        }
