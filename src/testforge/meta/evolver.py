"""Evolution loop: propose → evaluate → store → repeat.

Implements the Meta-Harness (arXiv:2603.28052) optimization loop.
"""

from pathlib import Path

from testforge.meta.evaluator import CandidateEvaluator
from testforge.meta.filesystem import CandidateFilesystem
from testforge.meta.proposer import HarnessProposer


class HarnessEvolver:
    """Run the Meta-Harness evolution loop.

    1. Evaluate the current (baseline) config
    2. Read evolution filesystem (all prior candidates)
    3. Propose a new config via GPT-5
    4. Evaluate the new config
    5. Compare scores, store result
    6. Repeat for N iterations
    """

    def __init__(self, project_root: Path, model: str = "gpt-5"):
        self.project_root = project_root
        self.filesystem = CandidateFilesystem(project_root)
        self.proposer = HarnessProposer(model=model)
        self.evaluator = CandidateEvaluator(project_root)

    def evolve(
        self,
        baseline_config: dict,
        iterations: int = 3,
        on_iteration: callable | None = None,
    ) -> dict:
        """Run the evolution loop.

        Args:
            baseline_config: Starting harness configuration
            iterations: Number of evolution iterations
            on_iteration: Callback(iteration, result) for progress

        Returns:
            best: dict with best candidate_id, config, scores
            history: list of all iteration results
        """
        self.filesystem.init()

        # Step 1: Evaluate baseline
        baseline_result = self.evaluator.evaluate(baseline_config)
        self.filesystem.append_evolution_log({
            "iteration": 0,
            "type": "baseline",
            "candidate_id": baseline_result["candidate_id"],
            "scores": baseline_result["scores"],
        })

        if on_iteration:
            on_iteration(0, baseline_result)

        best_score = baseline_result["scores"].get("composite_score", 0)
        best_config = baseline_config
        best_id = baseline_result["candidate_id"]
        history = [baseline_result]
        current_config = baseline_config

        # Step 2-N: Propose → Evaluate → Store
        for i in range(1, iterations + 1):
            # Propose
            proposal = self.proposer.propose(
                filesystem=self.filesystem,
                current_config=current_config,
            )

            self.filesystem.append_evolution_log({
                "iteration": i,
                "type": "proposal",
                "changes": proposal["changes"],
                "reasoning": proposal["reasoning"][:500],
            })

            # Evaluate proposed config
            proposed_config = proposal["proposed_config"]
            result = self.evaluator.evaluate(proposed_config)

            self.filesystem.append_evolution_log({
                "iteration": i,
                "type": "evaluation",
                "candidate_id": result["candidate_id"],
                "scores": result["scores"],
                "delta": result["scores"].get("composite_score", 0) - best_score,
            })

            # Track best
            score = result["scores"].get("composite_score", 0)
            if score > best_score:
                best_score = score
                best_config = proposed_config
                best_id = result["candidate_id"]
                current_config = proposed_config  # Continue from best

            history.append(result)

            if on_iteration:
                on_iteration(i, result)

        return {
            "best": {
                "candidate_id": best_id,
                "config": best_config,
                "scores": {"composite_score": best_score},
            },
            "history": history,
            "total_iterations": iterations,
        }
