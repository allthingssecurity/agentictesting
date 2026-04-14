"""Structured JSON logging for TestForge agent actions and tool invocations."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_LOG_FILE: Path | None = None
_LOG_LEVEL: str = "INFO"

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


def configure(log_file: Path | None = None, level: str = "INFO") -> None:
    global _LOG_FILE, _LOG_LEVEL
    _LOG_FILE = log_file
    _LOG_LEVEL = level.upper()


def _emit(record: dict) -> None:
    line = json.dumps(record, default=str)
    if _LOG_FILE:
        with open(_LOG_FILE, "a") as f:
            f.write(line + "\n")
    else:
        print(line, file=sys.stderr)


def _should_log(level: str) -> bool:
    return LEVELS.get(level, 20) >= LEVELS.get(_LOG_LEVEL, 20)


def log(level: str, event: str, **kwargs) -> None:
    if not _should_log(level):
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **kwargs,
    }
    _emit(record)


def log_tool_call(agent: str, tool_name: str, args: dict, result: str, duration_ms: float) -> None:
    log("INFO", "tool_call", agent=agent, tool=tool_name, args=args,
        result_length=len(result), duration_ms=round(duration_ms, 1))


def log_agent_start(agent: str, node: str) -> None:
    log("INFO", "agent_start", agent=agent, node=node)


def log_agent_end(agent: str, node: str, results_count: int) -> None:
    log("INFO", "agent_end", agent=agent, node=node, results_count=results_count)


def log_error(agent: str, error: str, **kwargs) -> None:
    log("ERROR", "error", agent=agent, error=error, **kwargs)


class TimingContext:
    """Context manager for timing operations."""

    def __init__(self):
        self.start = 0.0
        self.duration_ms = 0.0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.duration_ms = (time.monotonic() - self.start) * 1000
