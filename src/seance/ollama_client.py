"""Small synchronous client for Ollama's local chat API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class OllamaError(RuntimeError):
    """A safe, user-presentable local Ollama failure."""


class OllamaClient:
    def __init__(self, endpoint: str, timeout: float, model: str) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.model = model
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler(),
        )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"num_predict": 48, "temperature": 0.8},
        }
        request = urllib.request.Request(
            f"{self.endpoint}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                body = response.read(256 * 1024)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise OllamaError(f"Ollama could not find model {self.model!r}") from None
            raise OllamaError(f"Ollama returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if isinstance(exc, (TimeoutError,)) or getattr(exc, "reason", None).__class__ is TimeoutError:
                raise OllamaError("Ollama request timed out") from None
            raise OllamaError("Ollama is unavailable at the configured local endpoint") from None

        try:
            data = json.loads(body)
            content = data["message"]["content"]
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError):
            raise OllamaError("Ollama returned an invalid response") from None
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty response")
        return content

    def check(self) -> tuple[bool, str]:
        request = urllib.request.Request(f"{self.endpoint}/api/tags", method="GET")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                data = json.loads(response.read(256 * 1024))
        except urllib.error.HTTPError as exc:
            return False, f"Ollama returned HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError):
            return False, "Ollama is unavailable at the configured local endpoint"
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, "Ollama returned invalid JSON"
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list):
            return False, "Ollama returned an invalid model list"
        names = {
            item.get("name")
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        if self.model not in names:
            return False, f"model {self.model!r} is not installed; run: ollama pull {self.model}"
        return True, f"Ollama is reachable and {self.model!r} is installed"
