from seance.sanitizer import sanitize_context, sanitize_reflection


def test_secret_patterns_are_redacted():
    value = "token=abc123 Bearer eyJhbGciOi.test https://alice:secret@example.com/api sk-abcdefghijklmnop"
    result = sanitize_context(value)
    assert "abc123" not in result
    assert "eyJhbGciOi.test" not in result
    assert "alice:secret" not in result
    assert "sk-abcdefghijklmnop" not in result


def test_context_is_bounded_and_environment_assignments_are_hidden():
    result = sanitize_context("PRIVATE_KEY=topsecret DEBUG=true " + "x" * 800, limit=60)
    assert len(result) <= 60
    assert "topsecret" not in result
    assert "DEBUG=true" not in result


def test_terminal_controls_are_removed():
    assert sanitize_reflection("\x1b[31mThe hallway remembers you.\x1b[0m") == "The hallway remembers you."
    assert sanitize_reflection("The ghost moves.\nThen vanishes.") is None
    assert sanitize_reflection("A bell rings.\x1b]0;owned title\x07") == "A bell rings."


def test_reflection_word_character_and_sentence_limits():
    assert sanitize_reflection("The old machine dreams in silence.") == "The old machine dreams in silence."
    assert sanitize_reflection(" ".join(["quiet"] * 16) + ".") is None
    assert sanitize_reflection("The " + "x" * 180 + ".") is None
    assert sanitize_reflection("First sentence. Second sentence.") is None
    assert sanitize_reflection("```run this```") is None
    assert sanitize_reflection("") is None
