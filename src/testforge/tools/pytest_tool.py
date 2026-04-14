import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool

MAX_OUTPUT = 4000


@tool
def run_pytest(test_path: str, markers: str = "", extra_args: str = "") -> str:
    """Run pytest on a path. Returns JSON with exit_code, stdout, stderr, and parsed results."""
    if not shutil.which("pytest"):
        return json.dumps({"error": "pytest not found on PATH"})

    report_file = Path(tempfile.mktemp(suffix=".json"))
    cmd = ["pytest", test_path, "-q", "--tb=short", "--json-report", f"--json-report-file={report_file}"]
    if markers:
        cmd.extend(["-m", markers])
    if extra_args:
        cmd.extend(extra_args.split())

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "pytest timed out after 120s"})

    result = {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[:MAX_OUTPUT],
        "stderr": proc.stderr[:MAX_OUTPUT],
    }

    if report_file.exists():
        try:
            report = json.loads(report_file.read_text())
            tests = []
            for t in report.get("tests", []):
                tests.append({
                    "name": t.get("nodeid", ""),
                    "outcome": t.get("outcome", ""),
                    "duration": t.get("duration", 0),
                    "message": t.get("call", {}).get("longrepr", "")[:1000] if t.get("call") else "",
                })
            result["tests"] = tests
            result["summary"] = report.get("summary", {})
        except json.JSONDecodeError:
            pass
        report_file.unlink(missing_ok=True)

    return json.dumps(result, indent=2)
