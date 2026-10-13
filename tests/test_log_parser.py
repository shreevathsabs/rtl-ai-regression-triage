from pathlib import Path
import tempfile
import unittest

from log_parser import LogParser


class LogParserTests(unittest.TestCase):
    def test_finds_log_and_text_files_recursively_case_insensitively(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()
            (root / "top.LOG").write_text("", encoding="utf-8")
            (nested / "details.Txt").write_text("", encoding="utf-8")
            (nested / "ignored.md").write_text("", encoding="utf-8")

            files = LogParser().find_log_files(root)

            self.assertEqual([path.name for path in files], ["details.Txt", "top.LOG"])

    def test_extracts_error_with_ten_lines_of_context_at_file_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "run.log"
            log_file.write_text(
                "".join(f"before {index}\n" for index in range(12))
                + "FATAL: simulation stopped\n"
                + "after 1\n",
                encoding="utf-8",
            )

            errors = LogParser().extract_errors(log_file)

            self.assertEqual(len(errors), 1)
            self.assertEqual(
                errors[0],
                {
                    "filename": "run.log",
                    "error_line": "FATAL: simulation stopped",
                    "context_snippet": "\n".join(
                        [*(f"before {index}" for index in range(2, 12)),
                         "FATAL: simulation stopped", "after 1"]
                    ),
                },
            )


if __name__ == "__main__":
    unittest.main()
