import pytest

from seance.config import ConfigError, DEFAULT_MODEL, load_settings


def test_missing_config_uses_documented_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("SEANCE_CONFIG", str(tmp_path / "missing.ini"))
    for key in ("SEANCE_ENABLED", "SEANCE_ENDPOINT", "SEANCE_MODEL", "SEANCE_TIMEOUT",
                "SEANCE_STYLE", "SEANCE_COLOR", "SEANCE_BUILD_COMMANDS", "SEANCE_DESTRUCTIVE_COMMANDS"):
        monkeypatch.delenv(key, raising=False)
    settings = load_settings()
    assert settings.enabled is True
    assert settings.endpoint == "http://localhost:11434"
    assert settings.model == DEFAULT_MODEL == "gemma3:latest"
    assert settings.timeout == 2.5


def test_environment_values_override_config_file(tmp_path, monkeypatch):
    path = tmp_path / "config.ini"
    path.write_text("[seance]\nenabled = false\nmodel = old-model\n", encoding="utf-8")
    monkeypatch.setenv("SEANCE_CONFIG", str(path))
    monkeypatch.setenv("SEANCE_ENABLED", "true")
    monkeypatch.setenv("SEANCE_MODEL", "gemma3:latest")
    settings = load_settings()
    assert settings.enabled is True
    assert settings.model == "gemma3:latest"


def test_remote_endpoint_and_invalid_timeout_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("SEANCE_CONFIG", str(tmp_path / "missing.ini"))
    monkeypatch.setenv("SEANCE_ENDPOINT", "https://example.com")
    with pytest.raises(ConfigError, match="only permits a local"):
        load_settings()
    monkeypatch.setenv("SEANCE_ENDPOINT", "http://localhost:11434")
    monkeypatch.setenv("SEANCE_TIMEOUT", "0")
    with pytest.raises(ConfigError, match="between 0.2 and 15"):
        load_settings()
