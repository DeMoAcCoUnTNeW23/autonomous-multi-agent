"""Python execution tool: runs a snippet and captures stdout.

Used by the Executor for computation / data analysis tasks.
Runs in-process with a restricted namespace — local-first, no sandbox
dependency needed for v1.
"""
import io
import traceback
from contextlib import redirect_stdout


def run_python(code: str, timeout_note: str = "") -> str:
    buf = io.StringIO()
    safe_builtins = {
        "print": print, "len": len, "range": range, "sum": sum,
        "min": min, "max": max, "sorted": sorted, "abs": abs,
        "round": round, "enumerate": enumerate, "zip": zip,
        "str": str, "int": int, "float": float, "list": list,
        "dict": dict, "set": set, "tuple": tuple,
    }
    namespace = {"__builtins__": safe_builtins}
    # Allow common data libs if installed
    for lib in ("math", "statistics", "json", "re", "collections"):
        try:
            namespace[lib] = __import__(lib)
        except Exception:
            pass
    try:
        import numpy  # noqa
        namespace["np"] = numpy
    except Exception:
        pass
    try:
        with redirect_stdout(buf):
            exec(code, namespace)
        out = buf.getvalue().strip()
        return out or "(code ran with no printed output)"
    except Exception:
        return "ERROR:\n" + traceback.format_exc(limit=3)
