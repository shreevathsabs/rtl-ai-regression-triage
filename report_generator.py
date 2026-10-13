from collections import Counter
from pathlib import Path


class ReportGenerator:
    """Compile analyzed failures into a Markdown report."""

    def generate_markdown_report(self, analysis_results, output_path):
        """Write a category summary and per-failure details to a Markdown file.

        Each result may contain the fields ``filename``, ``failure_category``,
        ``root_cause_summary``, and ``recommended_fix``.
        """
        results = list(analysis_results)
        category_counts = Counter(
            self._field(result, "failure_category", "Uncategorized")
            for result in results
        )

        lines = [
            "# Failure Analysis Report",
            "",
            f"**Total failures:** {len(results)}",
            "",
            "## Summary by Category",
            "",
            "| Failure category | Count |",
            "| --- | ---: |",
        ]
        if category_counts:
            lines.extend(
                f"| {self._escape_table(category)} | {count} |"
                for category, count in sorted(category_counts.items())
            )
        else:
            lines.append("| _No failures_ | 0 |")

        lines.extend(["", "## Failure Details", ""])
        if not results:
            lines.append("No failures to report.")
        else:
            for index, result in enumerate(results, start=1):
                filename = self._field(result, "filename", "Unknown file")
                category = self._field(result, "failure_category", "Uncategorized")
                root_cause = self._field(
                    result, "root_cause_summary", "Not provided"
                )
                recommended_fix = self._field(
                    result, "recommended_fix", "Not provided"
                )
                lines.extend(
                    [
                        f"### {index}. {self._escape_heading(filename)}",
                        "",
                        f"**Category:** {category}",
                        "",
                        "**Root cause analysis**",
                        "",
                        root_cause,
                        "",
                        "**Recommended fix**",
                        "",
                        recommended_fix,
                        "",
                    ]
                )

        path = Path(output_path)
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path

    @staticmethod
    def _field(result, key, default):
        value = result.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else default

    @staticmethod
    def _escape_table(value):
        return value.replace("|", r"\|").replace("\n", " ")

    @staticmethod
    def _escape_heading(value):
        return value.replace("\n", " ").replace("\r", " ")
