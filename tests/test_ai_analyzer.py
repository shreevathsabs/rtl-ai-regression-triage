import json
from email.message import Message
from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from ai_analyzer import AIAnalyzer


class MockResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class AIAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = AIAnalyzer("test-key", "test-model", "https://llm.test/v1")
        self.result = {
            "failure_category": "Protocol",
            "root_cause_summary": "Unexpected response order.",
            "recommended_fix": "Check the handshake sequence.",
        }

    def response_body(self, result=None):
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(result or self.result),
                        }
                    }
                ]
            }
        ).encode("utf-8")

    @patch("ai_analyzer.urlopen")
    def test_sends_authenticated_request_and_parses_result(self, urlopen):
        urlopen.return_value = MockResponse(self.response_body())

        result = self.analyzer.analyze_failure("ERROR: response out of order")

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(result, self.result)
        self.assertEqual(request.full_url, "https://llm.test/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(payload["model"], "test-model")
        self.assertIn("expert RTL verification engineer", payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1]["content"], "ERROR: response out of order")

    @patch("ai_analyzer.time.sleep")
    @patch("ai_analyzer.urlopen")
    def test_retries_rate_limit_then_succeeds(self, urlopen, sleep):
        headers = Message()
        headers["Retry-After"] = "0"
        rate_limit = HTTPError(
            "https://llm.test/v1/chat/completions",
            429,
            "Rate limited",
            headers,
            BytesIO(b""),
        )
        urlopen.side_effect = [rate_limit, MockResponse(self.response_body())]

        result = self.analyzer.analyze_failure("FATAL: timeout")

        self.assertEqual(result, self.result)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0)

    @patch("ai_analyzer.time.sleep")
    @patch("ai_analyzer.urlopen")
    def test_returns_fallback_after_transient_failures(self, urlopen, sleep):
        urlopen.side_effect = TimeoutError("timed out")

        result = self.analyzer.analyze_failure("ERROR: timeout")

        self.assertEqual(result["failure_category"], "Analysis Error")
        self.assertEqual(urlopen.call_count, self.analyzer._MAX_ATTEMPTS)
        self.assertEqual(sleep.call_count, self.analyzer._MAX_ATTEMPTS - 1)

    @patch("ai_analyzer.urlopen")
    def test_returns_fallback_for_invalid_model_json(self, urlopen):
        urlopen.return_value = MockResponse(
            json.dumps(
                {"choices": [{"message": {"content": "not valid json"}}]}
            ).encode("utf-8")
        )

        self.assertEqual(
            self.analyzer.analyze_failure("ERROR"),
            self.analyzer._fallback(),
        )


if __name__ == "__main__":
    unittest.main()
