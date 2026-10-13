import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cli


class FakeAnalyzer:
    def __init__(self, api_key, model_name, base_url):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    def analyze_failure(self, error_snippet):
        return {
            "failure_category": "Protocol",
            "root_cause_summary": "Handshake timed out.",
            "recommended_fix": "Check ready/valid timing.",
        }


class CLITests(unittest.TestCase):
    def test_scans_analyzes_and_reports_nested_log_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            logs = root / "logs"
            (logs / "first").mkdir(parents=True)
            (logs / "second").mkdir()
            for folder in ("first", "second"):
                (logs / folder / "run.log").write_text(
                    "ERROR: handshake timeout\n", encoding="utf-8"
                )
            output_path = root / "report.md"
            environment = {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "OPENAI_BASE_URL": "https://llm.test/v1",
            }

            with patch.dict(os.environ, environment), patch.object(
                cli, "AIAnalyzer", FakeAnalyzer
            ):
                result = cli.main(
                    ["--log-dir", str(logs), "--output", str(output_path)]
                )

            report = output_path.read_text(encoding="utf-8")
            self.assertEqual(result, 0)
            self.assertIn("**Total failures:** 2", report)
            self.assertIn(r"first/run\.log", report)
            self.assertIn(r"second/run\.log", report)

    def test_requires_existing_log_directory_and_api_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing_dir = root / "missing"
            with patch.dict(os.environ, {"OPENAI_API_KEY": "key"}):
                self.assertEqual(
                    cli.main(
                        [
                            "--log-dir",
                            str(missing_dir),
                            "--output",
                            str(root / "report.md"),
                        ]
                    ),
                    2,
                )

            logs = root / "logs"
            logs.mkdir()
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    cli.main(
                        [
                            "--log-dir",
                            str(logs),
                            "--output",
                            str(root / "report.md"),
                        ]
                    ),
                    2,
                )


if __name__ == "__main__":
    unittest.main()
