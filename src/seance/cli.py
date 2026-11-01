"""Command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from . import __version__
from .config import ConfigError, Settings, load_settings, set_enabled
from .engine import generate_reflection
from .ollama_client import OllamaClient
from .triggers import classify_command


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seance", description="A quiet terminal companion powered by local Ollama.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="action", required=True)

    reflect = commands.add_parser("reflect", help="generate a reflection without executing a command")
    reflect.add_argument("--category", choices=("destructive", "failed-build"), required=True)
    reflect.add_argument("--status", type=int, default=0)
    reflect.add_argument("--context", help="optional minimal context; never executed")

    hook = commands.add_parser("hook", help=argparse.SUPPRESS)
    hook.add_argument("--status", type=int, required=True)

    commands.add_parser("doctor", help="check the local Ollama endpoint and configured model")
    commands.add_parser("config", help="list effective configuration")
    commands.add_parser("enable", help="enable reflections in the config file")
    commands.add_parser("disable", help="disable reflections in the config file")
    commands.add_parser("test", help="generate a sample reflection without running a command")
    return parser


def _color_enabled(settings: Settings) -> bool:
    if settings.color == "never" or os.environ.get("NO_COLOR") is not None:
        return False
    if settings.color == "always":
        return True
    return sys.stdout.isatty()


def _display(text: str, settings: Settings) -> None:
    line = f"ghost: {text}"
    if _color_enabled(settings):
        line = f"\033[2m{line}\033[0m"
    print(line, flush=True)


def _hook(settings: Settings, status: int) -> int:
    if not settings.enabled:
        return 0
    command = sys.stdin.read(4097)
    trigger = classify_command(command, status, settings)
    if trigger is None:
        return 0
    reflection = generate_reflection(trigger.category, status, settings)
    if reflection:
        _display(reflection, settings)
    return 0


def _run(args: argparse.Namespace) -> int:
    settings = load_settings()
    if args.action == "hook":
        return _hook(settings, args.status)
    if args.action == "config":
        print(f"enabled: {str(settings.enabled).lower()}")
        print(f"endpoint: {settings.endpoint}")
        print(f"model: {settings.model}")
        print(f"timeout: {settings.timeout:g}s")
        print(f"style: {settings.style}")
        print(f"color: {settings.color}")
        print(f"build_commands: {', '.join(settings.build_commands)}")
        print(f"destructive_commands: {', '.join(settings.destructive_commands)}")
        print(f"config_file: {settings.config_path}")
        return 0
    if args.action in {"enable", "disable"}:
        path = set_enabled(args.action == "enable", settings.config_path)
        print(f"Séance Shell {args.action}d in {path}")
        return 0
    if args.action == "doctor":
        client = OllamaClient(settings.endpoint, settings.timeout, settings.model)
        healthy, message = client.check()
        print(message)
        return 0 if healthy else 1
    if args.action == "test":
        category, status, context = "destructive", 0, None
    elif args.action == "reflect":
        category = args.category
        status = args.status
        context = args.context
    else:
        return 2
    if not settings.enabled:
        print("Séance Shell is disabled; run `seance enable` to enable it.", file=sys.stderr)
        return 1
    reflection = generate_reflection(category, status, settings, context)
    if not reflection:
        print("No reflection was generated; check `seance doctor` and the model response.", file=sys.stderr)
        return 1
    _display(reflection, settings)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _run(args)
    except ConfigError as exc:
        if args.action == "hook":
            return 0
        print(f"seance: configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
