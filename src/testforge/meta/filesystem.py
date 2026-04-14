"""Candidate filesystem manager for Meta-Harness evolution.

Structure:
  .testforge/evolution/
  ├── candidates/
  │   ├── candidate_001/
  │   │   ├── config.yaml      # Harness configuration
  │   │   ├── trace.jsonl      # Execution traces
  │   │   ├── scores.json      # Metrics
  │   │   └── report.json      # Full TestForge report
  │   └── ...
  ├── leaderboard.json          # Ranked candidates
  └── evolution_log.jsonl       # Proposer reasoning
"""

import json
from datetime import datetime
from pathlib import Path

import yaml


class CandidateFilesystem:
    """Manages the evolution filesystem for the Meta-Harness proposer."""

    def __init__(self, project_root: Path):
        self.base = project_root / ".testforge" / "evolution"
        self.candidates_dir = self.base / "candidates"

    def init(self) -> None:
        """Create the filesystem structure."""
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        leaderboard = self.base / "leaderboard.json"
        if not leaderboard.exists():
            leaderboard.write_text("[]")

    def next_candidate_id(self) -> str:
        """Get the next candidate ID."""
        existing = sorted(self.candidates_dir.iterdir()) if self.candidates_dir.exists() else []
        n = len(existing) + 1
        return f"candidate_{n:03d}"

    def save_candidate(
        self,
        candidate_id: str,
        config: dict,
        traces: list[dict],
        scores: dict,
        report: dict,
    ) -> Path:
        """Save a complete candidate run."""
        cdir = self.candidates_dir / candidate_id
        cdir.mkdir(parents=True, exist_ok=True)

        (cdir / "config.yaml").write_text(yaml.dump(config, default_flow_style=False))

        with open(cdir / "trace.jsonl", "w") as f:
            for trace in traces:
                f.write(json.dumps(trace, default=str) + "\n")

        (cdir / "scores.json").write_text(json.dumps(scores, indent=2))
        (cdir / "report.json").write_text(json.dumps(report, indent=2, default=str))

        return cdir

    def load_candidate(self, candidate_id: str) -> dict:
        """Load a candidate's full data."""
        cdir = self.candidates_dir / candidate_id
        if not cdir.exists():
            return {}

        result = {"id": candidate_id}

        config_path = cdir / "config.yaml"
        if config_path.exists():
            result["config"] = yaml.safe_load(config_path.read_text())

        scores_path = cdir / "scores.json"
        if scores_path.exists():
            result["scores"] = json.loads(scores_path.read_text())

        report_path = cdir / "report.json"
        if report_path.exists():
            result["report"] = json.loads(report_path.read_text())

        traces_path = cdir / "trace.jsonl"
        if traces_path.exists():
            result["traces"] = [
                json.loads(line) for line in traces_path.read_text().strip().split("\n") if line
            ]

        return result

    def list_candidates(self) -> list[str]:
        """List all candidate IDs."""
        if not self.candidates_dir.exists():
            return []
        return sorted(d.name for d in self.candidates_dir.iterdir() if d.is_dir())

    def get_leaderboard(self) -> list[dict]:
        """Get ranked leaderboard."""
        lb_path = self.base / "leaderboard.json"
        if lb_path.exists():
            return json.loads(lb_path.read_text())
        return []

    def update_leaderboard(self, entries: list[dict]) -> None:
        """Update the leaderboard (sorted by composite_score desc)."""
        entries.sort(key=lambda e: e.get("composite_score", 0), reverse=True)
        (self.base / "leaderboard.json").write_text(json.dumps(entries, indent=2))

    def append_evolution_log(self, entry: dict) -> None:
        """Append to the evolution log."""
        entry["timestamp"] = datetime.now().isoformat()
        with open(self.base / "evolution_log.jsonl", "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def get_filesystem_summary(self, max_candidates: int = 10) -> str:
        """Build a text summary of the filesystem for the proposer.

        This is what the proposer agent reads — following the Meta-Harness
        pattern of giving the proposer full filesystem access to prior
        candidates' source code, execution traces, and scores.
        """
        candidates = self.list_candidates()[-max_candidates:]
        parts = [f"=== Evolution Filesystem ({len(candidates)} candidates) ===\n"]

        for cid in candidates:
            data = self.load_candidate(cid)
            parts.append(f"\n--- {cid} ---")
            if "scores" in data:
                parts.append(f"Scores: {json.dumps(data['scores'])}")
            if "config" in data:
                parts.append(f"Config: {yaml.dump(data['config'], default_flow_style=True)[:500]}")
            if "traces" in data:
                # Show last 5 traces
                for trace in data["traces"][-5:]:
                    parts.append(f"  Trace: {json.dumps(trace, default=str)[:200]}")

        leaderboard = self.get_leaderboard()
        if leaderboard:
            parts.append(f"\n=== Leaderboard (top {min(5, len(leaderboard))}) ===")
            for entry in leaderboard[:5]:
                parts.append(f"  {entry.get('candidate_id', '?')}: {entry.get('composite_score', 0):.3f}")

        return "\n".join(parts)
