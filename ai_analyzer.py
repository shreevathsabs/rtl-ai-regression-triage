import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIAnalyzer:
    """Analyze simulation failures using an OpenAI-compatible chat API."""

    _MAX_ATTEMPTS = 3
    _INITIAL_RETRY_DELAY = 1
    _MAX_RETRY_DELAY = 30
    _SYSTEM_PROMPT = (
        "You are an expert RTL verification engineer. Analyze the supplied "
        "simulation log snippet, diagnose the most likely root cause, and "
        "recommend a concrete fix. Return only a valid JSON object with exactly "
        "these string keys: 'failure_category' (for example Protocol, "
        "Testbench, or RTL Bug), 'root_cause_summary', and 'recommended_fix'. "
        "Do not include Markdown or text outside the JSON object."
    )
    _FALLBACK_RESULT = {
        "failure_category": "Analysis Error",
        "root_cause_summary": "Failure analysis could not be completed.",
        "recommended_fix": (
            "Verify the API key, endpoint, model name, and network connection, "
            "then retry."
        ),
    }

    def __init__(self, api_key, model_name, base_url="https://api.openai.com/v1"):
        if not api_key:
            raise ValueError("api_key must not be empty")
        if not model_name:
            raise ValueError("model_name must not be empty")

        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def analyze_failure(self, error_snippet):
        """Return a structured diagnosis, or a fallback result if analysis fails."""
        if not isinstance(error_snippet, str):
            raise TypeError("error_snippet must be a string")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": error_snippet},
            ],
        }

        try:
            request = Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
        except ValueError:
            return self._fallback()

        for attempt in range(self._MAX_ATTEMPTS):
            try:
                with urlopen(request, timeout=30) as response:
                    api_response = json.loads(response.read().decode("utf-8"))
                content = api_response["choices"][0]["message"]["content"]
                result = json.loads(content)
                if not isinstance(result, dict) or any(
                    not isinstance(result.get(key), str)
                    for key in (
                        "failure_category",
                        "root_cause_summary",
                        "recommended_fix",
                    )
                ):
                    return self._fallback()

                return {
                    "failure_category": result["failure_category"],
                    "root_cause_summary": result["root_cause_summary"],
                    "recommended_fix": result["recommended_fix"],
                }
            except HTTPError as error:
                error.close()
                if error.code != 429 and not 500 <= error.code < 600:
                    return self._fallback()
                retry_after = (
                    error.headers.get("Retry-After") if error.headers else None
                )
                delay = self._retry_delay(attempt, retry_after)
            except (URLError, TimeoutError, OSError):
                delay = self._retry_delay(attempt)
            except (ValueError, KeyError, TypeError):
                return self._fallback()

            if attempt + 1 == self._MAX_ATTEMPTS:
                break
            time.sleep(delay)

        return self._fallback()

    @classmethod
    def _retry_delay(cls, attempt, retry_after=None):
        try:
            delay = float(retry_after)
        except (TypeError, ValueError):
            delay = cls._INITIAL_RETRY_DELAY * (2 ** attempt)
        return max(0, min(delay, cls._MAX_RETRY_DELAY))

    @classmethod
    def _fallback(cls):
        return cls._FALLBACK_RESULT.copy()
