"""Evolution history persistence and querying."""

import json
from pathlib import Path


class EvolutionHistory:
    """Query the evolution history from .testforge/evolution/."""

    def __init__(self, project_root: Path):
        self.base = project_root / ".testforge" / "evolution"
        self.log_file = self.base / "evolution_log.jsonl"

    def get_all(self) -> list[dict]:
        """Get all evolution log entries."""
        if not self.log_file.exists():
            return []
        entries = []
        for line in self.log_file.read_text().strip().split("\n"):
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def get_recent(self, n: int = 10) -> list[dict]:
        """Get the N most recent entries."""
        return self.get_all()[-n:]

    def get_best_config(self) -> dict | None:
        """Get the config of the best-scoring candidate."""
        leaderboard_path = self.base / "leaderboard.json"
        if not leaderboard_path.exists():
            return None

        leaderboard = json.loads(leaderboard_path.read_text())
        if not leaderboard:
            return None

        best = leaderboard[0]  # Already sorted by composite_score desc
        best_id = best.get("candidate_id")
        if not best_id:
            return None

        from testforge.meta.filesystem import CandidateFilesystem
        fs = CandidateFilesystem(self.base.parent.parent)
        candidate = fs.load_candidate(best_id)
        return candidate.get("config")

    def summary(self) -> str:
        """Human-readable summary of evolution history."""
        entries = self.get_all()
        if not entries:
            return "No evolution history."

        baselines = [e for e in entries if e.get("type") == "baseline"]
        proposals = [e for e in entries if e.get("type") == "proposal"]
        evals = [e for e in entries if e.get("type") == "evaluation"]

        parts = [
            f"Evolution History: {len(entries)} entries",
            f"  Baselines: {len(baselines)}",
            f"  Proposals: {len(proposals)}",
            f"  Evaluations: {len(evals)}",
        ]

        if evals:
            scores = [e["scores"]["composite_score"] for e in evals if "scores" in e]
            if scores:
                parts.append(f"  Best score: {max(scores):.3f}")
                parts.append(f"  Worst score: {min(scores):.3f}")
                if len(scores) > 1:
                    delta = scores[-1] - scores[0]
                    parts.append(f"  Net improvement: {delta:+.3f}")

        return "\n".join(parts)
