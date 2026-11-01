"""Configuration loading and validation."""

from __future__ import annotations

import configparser
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class ConfigError(ValueError):
    """Raised when a setting is invalid or the config file cannot be read."""


DEFAULT_BUILD_COMMANDS = ("npm run build", "npm test", "pytest", "cargo build", "make")
DEFAULT_DESTRUCTIVE_COMMANDS = ("rm", "git reset --hard", "git clean -fd", "git checkout --", "git restore")
DEFAULT_ENDPOINT = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:latest"


@dataclass(frozen=True)
class Settings:
    enabled: bool = True
    endpoint: str = DEFAULT_ENDPOINT
    model: str = DEFAULT_MODEL
    timeout: float = 2.5
    style: str = "eerie"
    color: str = "auto"
    build_commands: tuple[str, ...] = DEFAULT_BUILD_COMMANDS
    destructive_commands: tuple[str, ...] = DEFAULT_DESTRUCTIVE_COMMANDS
    config_path: Path = Path("~/.config/seance/config.ini")


def default_config_path() -> Path:
    return Path(os.environ.get("SEANCE_CONFIG", "~/.config/seance/config.ini")).expanduser()


def _read_file(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    if not path.exists():
        return parser
    try:
        with path.open(encoding="utf-8") as config_file:
            parser.read_file(config_file)
    except (OSError, configparser.Error) as exc:
        raise ConfigError(f"cannot read configuration at {path}: {exc}") from exc
    return parser


def _bool_value(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be one of: 1, 0, true, false, yes, no, on, off")


def _csv(value: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    commands = tuple(part.strip() for part in value.split(",") if part.strip())
    return commands or fallback


def _validate_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigError("Ollama endpoint must be an http(s) URL on this machine")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConfigError("Ollama endpoint cannot contain credentials, a query, or a fragment")
    hostname = parsed.hostname.lower()
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ConfigError("Séance Shell only permits a local Ollama endpoint")
    return endpoint.rstrip("/")


def load_settings() -> Settings:
    path = default_config_path()
    parser = _read_file(path)
    section = parser["seance"] if parser.has_section("seance") else {}

    def value(env_name: str, key: str, fallback: str) -> str:
        return os.environ.get(env_name, section.get(key, fallback))

    enabled = _bool_value(value("SEANCE_ENABLED", "enabled", "true"), "SEANCE_ENABLED")
    endpoint = _validate_endpoint(value("SEANCE_ENDPOINT", "endpoint", DEFAULT_ENDPOINT))
    model = value("SEANCE_MODEL", "model", DEFAULT_MODEL).strip()
    if not model or len(model) > 120 or any(ord(char) < 32 for char in model):
        raise ConfigError("model name must be between 1 and 120 printable characters")

    try:
        timeout = float(value("SEANCE_TIMEOUT", "timeout", "2.5"))
    except ValueError as exc:
        raise ConfigError("SEANCE_TIMEOUT must be a number between 0.2 and 15 seconds") from exc
    if not 0.2 <= timeout <= 15:
        raise ConfigError("SEANCE_TIMEOUT must be between 0.2 and 15 seconds")

    style = value("SEANCE_STYLE", "style", "eerie").strip().lower()
    if style not in {"eerie", "poetic", "darkly humorous", "restrained"}:
        raise ConfigError("SEANCE_STYLE must be eerie, poetic, darkly humorous, or restrained")
    color = value("SEANCE_COLOR", "color", "auto").strip().lower()
    if color not in {"auto", "always", "never"}:
        raise ConfigError("SEANCE_COLOR must be auto, always, or never")

    return Settings(
        enabled=enabled,
        endpoint=endpoint,
        model=model,
        timeout=timeout,
        style=style,
        color=color,
        build_commands=_csv(value("SEANCE_BUILD_COMMANDS", "build_commands", ",".join(DEFAULT_BUILD_COMMANDS)),
                            DEFAULT_BUILD_COMMANDS),
        destructive_commands=_csv(
            value("SEANCE_DESTRUCTIVE_COMMANDS", "destructive_commands", ",".join(DEFAULT_DESTRUCTIVE_COMMANDS)),
            DEFAULT_DESTRUCTIVE_COMMANDS,
        ),
        config_path=path,
    )


def set_enabled(enabled: bool, path: Path | None = None) -> Path:
    config_path = path or default_config_path()
    parser = _read_file(config_path)
    if not parser.has_section("seance"):
        parser.add_section("seance")
    parser.set("seance", "enabled", "true" if enabled else "false")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=config_path.parent, delete=False
        ) as config_file:
            temporary_path = config_file.name
            parser.write(config_file)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, config_path)
    except OSError as exc:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise ConfigError(f"cannot write configuration at {config_path}: {exc}") from exc
    return config_path
