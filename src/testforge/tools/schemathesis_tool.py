import json
import shutil
import subprocess

from langchain_core.tools import tool

MAX_OUTPUT = 4000


@tool
def run_schemathesis(openapi_url: str, base_url: str = "", extra_args: str = "") -> str:
    """Run Schemathesis API fuzzing against an OpenAPI spec. Returns JSON with results."""
    if not shutil.which("st"):
        return json.dumps({"error": "schemathesis (st) not found on PATH"})

    cmd = ["st", "run", openapi_url, "--dry-run"]
    if base_url:
        cmd.extend(["--base-url", base_url])
    if extra_args:
        cmd.extend(extra_args.split())

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "schemathesis timed out after 120s"})

    return json.dumps({
        "exit_code": proc.returncode,
        "stdout": proc.stdout[:MAX_OUTPUT],
        "stderr": proc.stderr[:MAX_OUTPUT],
    }, indent=2)
