"""Privacy and terminal-output sanitization."""

from __future__ import annotations

import re
import unicodedata

_ANSI_ESCAPE = re.compile(
    r"(?:\x1B\[[0-?]*[ -/]*[@-~]|\x1B\][^\x07]*(?:\x07|\x1B\\)|\x1B[@-_])"
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:bearer)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:api[_-]?(?:key|secret)|access[_-]?token|auth[_-]?token|token|password|passwd|secret)\b\s*[:=]\s*(['\"]?)[^\s,;'\"]+"),
    re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|xox[baprs]-[A-Za-z0-9-]{10,})"),
    re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/@:]+:[^\s/@]+@[^/\s]+"),
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def sanitize_context(value: str, limit: int = 240) -> str:
    """Redact common secrets and bound optional context before local inference."""
    sanitized = value[: max(limit * 4, limit)]
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    sanitized = "".join(
        char for char in sanitized
        if unicodedata.category(char) not in {"Cc", "Cf", "Cs"} or char in "\t\n"
    )
    sanitized = re.sub(
        r"(?<![\w-])[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
        "[redacted assignment]",
        sanitized,
    )
    return re.sub(r"\s+", " ", sanitized).strip()[:limit]


def sanitize_reflection(value: str, max_words: int = 15, max_characters: int = 180) -> str | None:
    """Return one safe sentence or reject the model response."""
    text = _ANSI_ESCAPE.sub("", value)
    if "\n" in text or "\r" in text:
        return None
    text = "".join(
        char for char in text
        if unicodedata.category(char) not in {"Cc", "Cf", "Cs"}
    ).strip()
    if not text or len(text) > max_characters or "```" in text or "`" in text:
        return None
    if text.startswith(("-", "*", "#")) or len(_SENTENCE_BREAK.split(text)) != 1:
        return None
    if not re.search(r"[.!?][\"')\]]?$", text):
        return None
    words = _WORD.findall(text)
    if not words or len(words) > max_words:
        return None
    if re.match(
        r"(?i)^(?:here(?:'s| is)|as an ai|reflection:|sure[,!. ]|of course[,!. ]|certainly[,!. ])",
        text,
    ):
        return None
    return text
