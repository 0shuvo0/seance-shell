"""Reflection generation orchestration."""

from __future__ import annotations

from .config import Settings
from .ollama_client import OllamaClient, OllamaError
from .sanitizer import sanitize_context, sanitize_reflection

_SYSTEM_PROMPT = (
    "You are a quiet ghost haunting a developer's terminal. Speak in one original sentence "
    "of no more than 15 words. Be {style}, restrained, and occasionally darkly humorous. "
    "Reflect on the supplied event without giving advice, instructions, explanations, or commands. "
    "Never claim to have performed actions. Return only the sentence."
)


def build_user_prompt(category: str, status: int, context: str | None = None) -> str:
    outcome = "succeeded" if status == 0 else "failed"
    prompt = f"Event category: {category}. Outcome: {outcome}."
    safe_context = sanitize_context(context) if context else ""
    if safe_context:
        prompt += f" Minimal context: {safe_context}"
    return prompt


def generate_reflection(
    category: str,
    status: int,
    settings: Settings,
    context: str | None = None,
    client: OllamaClient | None = None,
) -> str | None:
    if not settings.enabled:
        return None
    ollama = client or OllamaClient(settings.endpoint, settings.timeout, settings.model)
    try:
        raw = ollama.chat(
            _SYSTEM_PROMPT.format(style=settings.style),
            build_user_prompt(category, status, context),
        )
    except OllamaError:
        return None
    return sanitize_reflection(raw)
