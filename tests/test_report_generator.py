from pathlib import Path
import tempfile
import unittest

from report_generator import ReportGenerator


class ReportGeneratorTests(unittest.TestCase):
    def test_generates_category_summary_and_escaped_details(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.md"
            results = [
                {
                    "filename": "run_a.log",
                    "failure_category": "Protocol",
                    "root_cause_summary": "Unexpected **response**.",
                    "recommended_fix": "Check [ready/valid](https://example.test).",
                },
                {
                    "filename": "run_b.log",
                    "failure_category": "Protocol",
                    "root_cause_summary": "Handshake timeout.",
                    "recommended_fix": "Review the driver.",
                },
            ]

            returned_path = ReportGenerator().generate_markdown_report(
                results, output_path
            )
            report = output_path.read_text(encoding="utf-8")

            self.assertEqual(returned_path, output_path)
            self.assertIn("**Total failures:** 2", report)
            self.assertIn("| Protocol | 2 |", report)
            self.assertIn(r"### 1. run\_a\.log", report)
            self.assertIn(r"Unexpected \*\*response\*\*\.", report)
            self.assertIn(r"\[ready/valid\]\(https://example\.test\)", report)

    def test_generates_empty_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "empty.md"

            ReportGenerator().generate_markdown_report([], output_path)

            report = output_path.read_text(encoding="utf-8")
            self.assertIn("| _No failures_ | 0 |", report)
            self.assertIn("No failures to report.", report)


if __name__ == "__main__":
    unittest.main()
