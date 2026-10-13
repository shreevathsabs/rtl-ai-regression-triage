from collections import deque
from pathlib import Path
import re


class LogParser:
    """Find log files and extract error lines with surrounding context."""

    _ERROR_PATTERN = re.compile(
        r"FATAL|ERROR|Assertion Failed|mismatch",
        re.IGNORECASE,
    )
    _CONTEXT_LINES = 10

    def find_log_files(self, directory_path):
        """Return all .log and .txt files below a directory, in sorted order."""
        directory = Path(directory_path)
        return sorted(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in {".log", ".txt"}
        )

    def extract_errors(self, file_path):
        """Return matching lines and up to ten lines of context on each side."""
        path = Path(file_path)
        preceding_lines = deque(maxlen=self._CONTEXT_LINES)
        pending_errors = []
        errors = []

        with path.open(encoding="utf-8", errors="replace") as log_file:
            for line_number, raw_line in enumerate(log_file, start=1):
                line = raw_line.rstrip("\r\n")

                for pending in pending_errors:
                    pending["context_lines"].append(line)

                if self._ERROR_PATTERN.search(line):
                    pending_errors.append(
                        {
                            "line_number": line_number,
                            "error_line": line,
                            "context_lines": [*preceding_lines, line],
                        }
                    )

                ready_errors = [
                    pending
                    for pending in pending_errors
                    if line_number >= pending["line_number"] + self._CONTEXT_LINES
                ]
                for pending in ready_errors:
                    errors.append(
                        {
                            "filename": path.name,
                            "error_line": pending["error_line"],
                            "context_snippet": "\n".join(pending["context_lines"]),
                        }
                    )
                    pending_errors.remove(pending)

                preceding_lines.append(line)

        for pending in pending_errors:
            errors.append(
                {
                    "filename": path.name,
                    "error_line": pending["error_line"],
                    "context_snippet": "\n".join(pending["context_lines"]),
                }
            )

        return errors
