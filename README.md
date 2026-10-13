# rtl-ai-regression-triage
An automated, AI-driven log-parsing and failure triage tool designed for hardware verification engineers. This utility scans massive simulation and regression log files, extracts critical error contexts using regular expressions, and leverages LLM APIs to diagnose root causes and generate instant debugging summaries.

## Log parsing

`LogParser` recursively finds `.log` and `.txt` files and extracts lines containing
`FATAL`, `ERROR`, `Assertion Failed`, or `mismatch`, along with up to 10 lines of
surrounding context:

```python
from log_parser import LogParser

parser = LogParser()
for log_path in parser.find_log_files("regression_logs"):
    for error in parser.extract_errors(log_path):
        print(error["filename"], error["error_line"])
        print(error["context_snippet"])
```

## AI failure analysis

`AIAnalyzer` sends a log snippet to an OpenAI-compatible chat-completions API
and returns a JSON-shaped diagnosis. Set the API key and model name when creating
the analyzer; use `base_url` to target a compatible endpoint:

```python
import os

from ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer(
    api_key=os.environ["OPENAI_API_KEY"],
    model_name="gpt-4o-mini",
)
diagnosis = analyzer.analyze_failure(error["context_snippet"])
print(diagnosis["failure_category"])
print(diagnosis["root_cause_summary"])
print(diagnosis["recommended_fix"])
```

## Report generation

Add the source filename to each analysis dictionary, then pass the results to
`ReportGenerator` to write a Markdown summary and per-failure breakdown:

```python
from report_generator import ReportGenerator

results = [
    {"filename": error["filename"], **analyzer.analyze_failure(error["context_snippet"])}
]
ReportGenerator().generate_markdown_report(results, "failure_report.md")
```

## Command-line usage

Set `OPENAI_API_KEY` before running the CLI. Optionally set `OPENAI_MODEL`
(defaults to `gpt-4o-mini`) or `OPENAI_BASE_URL` (defaults to the OpenAI API URL)
to select a model or compatible endpoint:

```console
python cli.py --log-dir regression_logs --output failure_report.md
```
