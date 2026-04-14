import json
import shutil
import subprocess

from langchain_core.tools import tool

MAX_OUTPUT = 4000


@tool
def run_nuclei(target_url: str, templates: str = "", extra_args: str = "") -> str:
    """Run Nuclei vulnerability scanner against a target URL. Returns JSON findings."""
    if not shutil.which("nuclei"):
        return json.dumps({"error": "nuclei not found on PATH"})

    cmd = ["nuclei", "-u", target_url, "-jsonl", "-silent"]
    if templates:
        cmd.extend(["-t", templates])
    if extra_args:
        cmd.extend(extra_args.split())

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "nuclei timed out after 180s"})

    findings = []
    for line in proc.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            f = json.loads(line)
            findings.append({
                "template_id": f.get("template-id", ""),
                "name": f.get("info", {}).get("name", ""),
                "severity": f.get("info", {}).get("severity", ""),
                "matched_at": f.get("matched-at", ""),
                "description": f.get("info", {}).get("description", "")[:500],
            })
        except json.JSONDecodeError:
            continue

    return json.dumps({
        "exit_code": proc.returncode,
        "findings": findings[:50],
        "total_findings": len(findings),
        "stderr": proc.stderr[:MAX_OUTPUT],
    }, indent=2)
