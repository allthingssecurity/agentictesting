"""Structured memory store for key findings, decisions, and errors."""

import hashlib
import json
from datetime import datetime


class StructuredMemoryStore:
    """In-memory store for structured information extracted from agent runs.

    Deduplicates entries by content hash.
    """

    def __init__(self):
        self.findings: list[dict] = []
        self.decisions: list[dict] = []
        self.errors: list[dict] = []
        self._seen_hashes: set[str] = set()

    def add_finding(self, name: str, test_type: str, message: str, severity: str = "medium") -> None:
        entry = {"name": name, "test_type": test_type, "message": message[:500],
                 "severity": severity, "timestamp": datetime.now().isoformat()}
        if self._dedup(entry):
            self.findings.append(entry)

    def add_decision(self, decision: str, rationale: str = "") -> None:
        entry = {"decision": decision, "rationale": rationale,
                 "timestamp": datetime.now().isoformat()}
        if self._dedup(entry):
            self.decisions.append(entry)

    def add_error(self, agent: str, error: str, context: str = "") -> None:
        entry = {"agent": agent, "error": error[:500], "context": context[:200],
                 "timestamp": datetime.now().isoformat()}
        if self._dedup(entry):
            self.errors.append(entry)

    def to_dict(self) -> dict:
        return {
            "key_findings": self.findings,
            "decisions": self.decisions,
            "errors": self.errors,
        }

    def to_context_string(self, max_chars: int = 2000) -> str:
        """Format memory as a context string for injection into prompts."""
        parts = []
        if self.findings:
            parts.append("Key Findings:")
            for f in self.findings[-5:]:
                parts.append(f"  - [{f['severity']}] {f['name']}: {f['message'][:100]}")
        if self.decisions:
            parts.append("Decisions:")
            for d in self.decisions[-3:]:
                parts.append(f"  - {d['decision']}")
        if self.errors:
            parts.append("Errors:")
            for e in self.errors[-3:]:
                parts.append(f"  - {e['agent']}: {e['error'][:100]}")
        result = "\n".join(parts)
        return result[:max_chars]

    def _dedup(self, entry: dict) -> bool:
        """Return True if this is a new entry."""
        # Hash without timestamp for dedup
        hashable = {k: v for k, v in entry.items() if k != "timestamp"}
        h = hashlib.md5(json.dumps(hashable, sort_keys=True).encode()).hexdigest()
        if h in self._seen_hashes:
            return False
        self._seen_hashes.add(h)
        return True
