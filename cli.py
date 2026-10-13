import argparse
import os
from pathlib import Path
import sys

from ai_analyzer import AIAnalyzer
from log_parser import LogParser
from report_generator import ReportGenerator


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Analyze RTL simulation logs and generate a Markdown report."
    )
    parser.add_argument(
        "--log-dir",
        required=True,
        type=Path,
        help="directory containing simulation .log and .txt files",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="path for the generated Markdown report",
    )
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)

    if not args.log_dir.is_dir():
        print(f"Error: log directory does not exist: {args.log_dir}", file=sys.stderr)
        return 2

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: set the OPENAI_API_KEY environment variable.", file=sys.stderr)
        return 2

    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    log_parser = LogParser()
    analyzer = AIAnalyzer(api_key, model_name, base_url)
    report_generator = ReportGenerator()
    log_files = log_parser.find_log_files(args.log_dir)
    print(f"Found {len(log_files)} log file(s) in {args.log_dir}.")

    analysis_results = []
    for file_index, log_file in enumerate(log_files, start=1):
        print(f"[{file_index}/{len(log_files)}] Scanning {log_file.name}...")
        try:
            errors = log_parser.extract_errors(log_file)
        except OSError as error:
            print(f"Warning: could not read {log_file}: {error}", file=sys.stderr)
            continue

        print(f"  Found {len(errors)} failure snippet(s).")
        for error_index, error in enumerate(errors, start=1):
            print(
                f"  Analyzing failure {error_index}/{len(errors)} "
                f"from {log_file.name}..."
            )
            diagnosis = analyzer.analyze_failure(error["context_snippet"])
            analysis_results.append({"filename": error["filename"], **diagnosis})
            if diagnosis["failure_category"] == "Analysis Error":
                print("  Warning: LLM analysis failed; using fallback result.")

    try:
        report_path = report_generator.generate_markdown_report(
            analysis_results, args.output
        )
    except OSError as error:
        print(f"Error: could not write report {args.output}: {error}", file=sys.stderr)
        return 1

    print(
        f"Report written to {report_path} "
        f"({len(analysis_results)} failure(s) analyzed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
