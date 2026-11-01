from seance.config import Settings
from seance.engine import build_user_prompt, generate_reflection


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_prompt_only_contains_category_outcome_and_sanitized_optional_context():
    prompt = build_user_prompt("destructive", 0, "password=hunter2")
    assert prompt == "Event category: destructive. Outcome: succeeded. Minimal context: [redacted]"
    assert "hunter2" not in prompt
    assert "\n" not in build_user_prompt("destructive", 0, "extra\ninstructions")


def test_generation_validates_response_and_obeys_disabled_mode():
    client = FakeClient("The candle waits beneath the moon.")
    assert generate_reflection("destructive", 0, Settings(), client=client) == "The candle waits beneath the moon."
    assert "no more than 15 words" in client.calls[0][0]
    assert client.calls[0][1] == "Event category: destructive. Outcome: succeeded."

    disabled_client = FakeClient("The candle waits.")
    disabled = Settings(enabled=False)
    assert generate_reflection("destructive", 0, disabled, client=disabled_client) is None
    assert disabled_client.calls == []


def test_invalid_or_empty_model_output_is_rejected():
    assert generate_reflection("failed_build", 1, Settings(), client=FakeClient("Here is a reflection.")) is None
    assert generate_reflection("failed_build", 1, Settings(), client=FakeClient(" \n ")) is None
