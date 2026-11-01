"""Conservative command classification for shell hooks."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True)
class Trigger:
    category: str


_PUNCTUATION = set(";&|<>")
_EXPANSION_MARKERS = ("$", "`", "\x00")


def _tokens(command: str) -> list[str] | None:
    if not command or len(command) > 4096 or any(marker in command for marker in _EXPANSION_MARKERS):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    if not tokens or any(token and all(char in _PUNCTUATION for char in token) for token in tokens):
        return None
    tokens[0] = os.path.basename(tokens[0])
    if "=" in tokens[0]:
        return None
    return tokens


def _configured_match(tokens: list[str], configured: tuple[str, ...]) -> bool:
    for expression in configured:
        pattern = _tokens(expression)
        if pattern and tokens[:len(pattern)] == pattern:
            return True
    return False


def classify_command(command: str, status: int, settings: Settings) -> Trigger | None:
    """Classify a simple command; ambiguous shell syntax is deliberately ignored."""
    tokens = _tokens(command)
    if not tokens:
        return None

    if _configured_match(tokens, settings.destructive_commands):
        return Trigger("destructive")

    executable = tokens[0]
    if executable == "rm" and len(tokens) > 1:
        return Trigger("destructive")
    if executable == "git" and len(tokens) >= 3:
        if tokens[1:3] == ["reset", "--hard"]:
            return Trigger("destructive")
        if tokens[1:3] == ["clean", "-fd"]:
            return Trigger("destructive")
        if tokens[1:3] == ["checkout", "--"]:
            return Trigger("destructive")
        if tokens[1] == "restore":
            return Trigger("destructive")

    if status != 0 and _configured_match(tokens, settings.build_commands):
        return Trigger("failed_build")
    return None
