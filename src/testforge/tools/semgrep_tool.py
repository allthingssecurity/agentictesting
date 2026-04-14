import json
import shutil
import subprocess

from langchain_core.tools import tool

MAX_OUTPUT = 4000


@tool
def run_semgrep(target_path: str, rules: str = "auto") -> str:
    """Run Semgrep static analysis. Returns JSON findings."""
    if not shutil.which("semgrep"):
        return json.dumps({"error": "semgrep not found on PATH"})

    cmd = ["semgrep", "scan", "--json", "--config", rules, target_path]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "semgrep timed out after 120s"})

    result = {
        "exit_code": proc.returncode,
        "stderr": proc.stderr[:MAX_OUTPUT],
    }

    try:
        findings = json.loads(proc.stdout)
        results = findings.get("results", [])
        result["findings"] = [
            {
                "check_id": f.get("check_id", ""),
                "path": f.get("path", ""),
                "line": f.get("start", {}).get("line", 0),
                "message": f.get("extra", {}).get("message", "")[:500],
                "severity": f.get("extra", {}).get("severity", ""),
            }
            for f in results[:50]
        ]
        result["total_findings"] = len(results)
    except json.JSONDecodeError:
        result["stdout"] = proc.stdout[:MAX_OUTPUT]

    return json.dumps(result, indent=2)
