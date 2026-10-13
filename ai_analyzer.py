import json
from urllib.error import URLError
from urllib.request import Request, urlopen


class AIAnalyzer:
    """Analyze simulation failures using an OpenAI-compatible chat API."""

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
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
            return self._fallback()

    @classmethod
    def _fallback(cls):
        return cls._FALLBACK_RESULT.copy()
