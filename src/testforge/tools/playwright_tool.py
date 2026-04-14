import json
import shutil
import subprocess

from langchain_core.tools import tool

MAX_OUTPUT = 4000


@tool
def run_playwright(test_path: str, headed: bool = False) -> str:
    """Run Playwright tests. Returns JSON with exit_code, stdout, stderr."""
    if not shutil.which("npx"):
        return json.dumps({"error": "npx not found on PATH"})

    cmd = ["npx", "playwright", "test", test_path, "--reporter=json"]
    if headed:
        cmd.append("--headed")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "playwright timed out after 180s"})

    result = {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[:MAX_OUTPUT],
        "stderr": proc.stderr[:MAX_OUTPUT],
    }

    # Try to parse the JSON reporter output
    try:
        report = json.loads(proc.stdout)
        suites = report.get("suites", [])
        tests = []
        for suite in suites:
            for spec in suite.get("specs", []):
                for t in spec.get("tests", []):
                    for r in t.get("results", []):
                        tests.append({
                            "name": spec.get("title", ""),
                            "status": r.get("status", ""),
                            "duration": r.get("duration", 0),
                        })
        result["tests"] = tests
    except (json.JSONDecodeError, KeyError):
        pass

    return json.dumps(result, indent=2)
