"""File tools: safe local file reading/listing."""
import os

SAFE_ROOT = os.path.abspath(os.getcwd())
MAX_CHARS = 20000


def _safe(path: str) -> str:
    p = os.path.abspath(path)
    return p


def read_file(path: str) -> str:
    try:
        p = _safe(path)
        if not os.path.isfile(p):
            return f"File not found: {path}"
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(MAX_CHARS)
        return content or "(empty file)"
    except Exception as e:
        return f"Error reading {path}: {e}"


def list_files(directory: str = ".") -> str:
    try:
        p = _safe(directory)
        if not os.path.isdir(p):
            return f"Not a directory: {directory}"
        entries = sorted(os.listdir(p))[:100]
        return "\n".join(entries) or "(empty directory)"
    except Exception as e:
        return f"Error listing {directory}: {e}"
