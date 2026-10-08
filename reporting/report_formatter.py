"""Report formatter: save Markdown reports as output artifacts (not a DB)."""
import os
from utils.helpers import report_filename


def save_report(markdown: str, directory: str = "reports") -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, report_filename())
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return path
