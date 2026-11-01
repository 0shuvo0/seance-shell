import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from seance.ollama_client import OllamaClient, OllamaError


def _response(body):
    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    return Response(body)


def test_chat_formats_independent_bounded_request():
    payload = {"message": {"content": "The clock forgets your name."}}
    opener = type("FakeOpener", (), {"open": lambda self, request, timeout: _response(json.dumps(payload).encode())})()
    with patch("urllib.request.build_opener", return_value=opener), patch.object(opener, "open", wraps=opener.open) as open_url:
        client = OllamaClient("http://localhost:11434", 1.25, "gemma3:latest")
        assert client.chat("system", "category only") == payload["message"]["content"]
    request = open_url.call_args.args[0]
    body = json.loads(request.data)
    assert request.full_url == "http://localhost:11434/api/chat"
    assert body["model"] == "gemma3:latest"
    assert body["stream"] is False
    assert body["options"]["num_predict"] == 48
    assert body["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "category only"},
    ]
    assert open_url.call_args.kwargs["timeout"] == 1.25


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (urllib.error.URLError("offline"), "unavailable"),
        (TimeoutError(), "timed out"),
        (urllib.error.HTTPError("url", 404, "missing", {}, None), "could not find model"),
    ],
)
def test_connection_timeout_and_missing_model_errors(failure, message):
    opener = type("FakeOpener", (), {"open": lambda self, request, timeout: None})()
    with patch("urllib.request.build_opener", return_value=opener), patch.object(opener, "open", side_effect=failure):
        with pytest.raises(OllamaError, match=message):
            OllamaClient("http://localhost:11434", 1, "gemma3:latest").chat("sys", "user")


@pytest.mark.parametrize("body", [b"not json", b'{"message":{"content":""}}', b'{"message":{}}'])
def test_invalid_and_empty_responses_are_rejected(body):
    opener = type("FakeOpener", (), {"open": lambda self, request, timeout: _response(body)})()
    with patch("urllib.request.build_opener", return_value=opener):
        with pytest.raises(OllamaError):
            OllamaClient("http://localhost:11434", 1, "gemma3:latest").chat("sys", "user")


def test_client_disables_proxies_and_redirects():
    with patch("urllib.request.build_opener", wraps=__import__("urllib.request").request.build_opener) as builder:
        OllamaClient("http://localhost:11434", 1, "gemma3:latest")
    handlers = builder.call_args.args
    proxy_handler = next(item for item in handlers if isinstance(item, __import__("urllib.request").request.ProxyHandler))
    assert proxy_handler.proxies == {}
    assert any(type(handler).__name__ == "_NoRedirectHandler" for handler in handlers)
