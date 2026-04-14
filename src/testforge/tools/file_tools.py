import glob as globmod
from pathlib import Path

from langchain_core.tools import tool

MAX_READ = 8000


@tool
def read_file(file_path: str) -> str:
    """Read a file and return its contents (truncated to 8000 chars)."""
    p = Path(file_path)
    if not p.exists():
        return f"Error: {file_path} does not exist"
    if not p.is_file():
        return f"Error: {file_path} is not a file"
    text = p.read_text(errors="replace")
    if len(text) > MAX_READ:
        return text[:MAX_READ] + f"\n... [truncated, {len(text)} total chars]"
    return text


@tool
def list_files(directory: str, pattern: str = "**/*") -> str:
    """List files in a directory matching a glob pattern. Returns newline-separated paths."""
    base = Path(directory)
    if not base.is_dir():
        return f"Error: {directory} is not a directory"
    matches = sorted(globmod.glob(str(base / pattern), recursive=True))
    files = [m for m in matches if Path(m).is_file()]
    if not files:
        return "No files matched"
    if len(files) > 200:
        return "\n".join(files[:200]) + f"\n... [{len(files)} total files]"
    return "\n".join(files)
