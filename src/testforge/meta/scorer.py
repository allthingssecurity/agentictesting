"""Scoring metrics for Meta-Harness evaluation."""


class MetricScorer:
    """Score tool/harness effectiveness across multiple dimensions."""

    @staticmethod
    def signal_to_noise(findings: list[dict], false_positives: int = 0) -> float:
        """Ratio of actionable findings to total findings.

        Actionable = severity >= medium and not marked false positive.
        """
        if not findings:
            return 1.0
        actionable = sum(
            1 for f in findings
            if f.get("severity", "info") in ("critical", "high", "medium")
        )
        total = len(findings)
        if total == 0:
            return 1.0
        return (actionable - false_positives) / total

    @staticmethod
    def unique_coverage(findings: list[dict], other_findings: list[list[dict]]) -> float:
        """Fraction of findings only this tool found (not duplicated by others)."""
        if not findings:
            return 0.0

        other_names = set()
        for other in other_findings:
            for f in other:
                other_names.add(f.get("name", "") or f.get("check_id", ""))

        unique = sum(
            1 for f in findings
            if (f.get("name", "") or f.get("check_id", "")) not in other_names
        )
        return unique / len(findings)

    @staticmethod
    def cost_efficiency(findings_count: int, execution_time_ms: float) -> float:
        """Findings per second of execution time."""
        if execution_time_ms <= 0:
            return 0.0
        return findings_count / (execution_time_ms / 1000)

    @staticmethod
    def composite_score(
        pass_rate: float,
        signal_noise: float,
        unique_coverage: float,
        cost_efficiency: float,
        weights: dict | None = None,
    ) -> float:
        """Weighted composite score across all dimensions."""
        w = weights or {
            "pass_rate": 0.3,
            "signal_noise": 0.3,
            "unique_coverage": 0.25,
            "cost_efficiency": 0.15,
        }
        return (
            w["pass_rate"] * pass_rate
            + w["signal_noise"] * signal_noise
            + w["unique_coverage"] * unique_coverage
            + w["cost_efficiency"] * min(cost_efficiency, 1.0)
        )
