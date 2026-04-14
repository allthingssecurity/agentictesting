"""Evaluate a harness candidate by running the full TestForge pipeline."""

import json
from pathlib import Path

from testforge.meta.filesystem import CandidateFilesystem
from testforge.meta.scorer import MetricScorer


class CandidateEvaluator:
    """Run a candidate harness configuration and collect scores."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.filesystem = CandidateFilesystem(project_root)

    def evaluate(self, config: dict) -> dict:
        """Run the TestForge pipeline with a given config and score it.

        Returns dict with:
            candidate_id: str
            scores: dict (pass_rate, signal_noise, etc.)
            report: dict (full report data)
            traces: list[dict] (execution traces)
        """
        from testforge.config import load_manifest
        from testforge.graph import build_graph

        # Build initial state from config
        graph = build_graph()

        initial_state = {
            "messages": [],
            "project_root": str(self.project_root),
            "manifest": config,
            "detected_languages": [],
            "tool_registry_snapshot": {},
            "plan": None,
            "_executor_language": "",
            "_executor_tools": [],
            "results": [],
            "healed_results": [],
            "findings": [],
            "memory": {"summary": "", "key_findings": [], "decisions": [], "errors": [], "token_count": 0},
            "meta_scores": {},
            "report": None,
        }

        # Run pipeline
        final_state = graph.invoke(initial_state)

        # Extract results
        report = final_state.get("report")
        results = final_state.get("results", [])
        findings = final_state.get("findings", [])
        meta_scores = final_state.get("meta_scores", {})

        # Compute scores
        total = len(results)
        passed = sum(1 for r in results if r.status == "passed")
        pass_rate = passed / total if total > 0 else 0.0

        finding_dicts = [f.model_dump() for f in findings] if findings else []
        signal_noise = MetricScorer.signal_to_noise(finding_dicts)

        composite = MetricScorer.composite_score(
            pass_rate=pass_rate,
            signal_noise=signal_noise,
            unique_coverage=1.0,  # No comparison in single eval
            cost_efficiency=0.5,  # Placeholder
        )

        scores = {
            "pass_rate": pass_rate,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "signal_noise": signal_noise,
            "composite_score": composite,
        }

        # Build traces from meta_scores
        traces = [{"tool": k, **v} for k, v in meta_scores.items()]

        # Save candidate
        candidate_id = self.filesystem.next_candidate_id()
        report_dict = report.model_dump() if report else {}
        self.filesystem.save_candidate(candidate_id, config, traces, scores, report_dict)

        # Update leaderboard
        leaderboard = self.filesystem.get_leaderboard()
        leaderboard.append({
            "candidate_id": candidate_id,
            "composite_score": composite,
            "pass_rate": pass_rate,
            "signal_noise": signal_noise,
        })
        self.filesystem.update_leaderboard(leaderboard)

        return {
            "candidate_id": candidate_id,
            "scores": scores,
            "report": report_dict,
            "traces": traces,
        }
