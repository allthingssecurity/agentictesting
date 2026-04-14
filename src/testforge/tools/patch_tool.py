from pathlib import Path

from langchain_core.tools import tool


@tool
def apply_patch(file_path: str, original: str, replacement: str) -> str:
    """Replace exact text in a file. Returns success/failure message."""
    p = Path(file_path)
    if not p.exists():
        return f"Error: {file_path} does not exist"
    content = p.read_text()
    if original not in content:
        return f"Error: original text not found in {file_path}"
    count = content.count(original)
    new_content = content.replace(original, replacement, 1)
    p.write_text(new_content)
    return f"Patched {file_path} (replaced 1 of {count} occurrences)"
