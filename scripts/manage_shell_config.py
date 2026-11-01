#!/usr/bin/env python3
"""Install and remove only Séance Shell's marked shell configuration block."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

START = "# >>> seance-shell >>>"
END = "# <<< seance-shell <<<"
CONFIG_DIR = Path(".config/seance")
INTEGRATIONS = {"bash": ("seance.bash", ".bashrc"), "zsh": ("seance.zsh", ".zshrc")}


def _block(shell: str) -> str:
    integration = "seance.bash" if shell == "bash" else "seance.zsh"
    path = f'$HOME/.config/seance/{integration}'
    return f'{START}\n[[ -f "{path}" ]] && source "{path}"\n{END}'


def _select_shells(requested: str) -> list[str]:
    if requested != "auto":
        return ["bash", "zsh"] if requested == "both" else [requested]
    detected = Path(os.environ.get("SHELL", "")).name
    if detected in INTEGRATIONS:
        return [detected]
    available = [shell for shell, (_, rc) in INTEGRATIONS.items() if (Path.home() / rc).exists()]
    return available or ["bash"]


def _install(home: Path, root: Path, shells: list[str], dry_run: bool) -> int:
    operations: list[tuple[str, Path, Path | None]] = []
    for shell in shells:
        filename, rc_name = INTEGRATIONS[shell]
        rc_path = home / rc_name
        asset_path = home / CONFIG_DIR / filename
        source_asset = root / "shell" / filename
        if not source_asset.is_file():
            print(f"missing integration file: {source_asset}", file=sys.stderr)
            return 1
        if asset_path.exists() and asset_path.read_bytes() != source_asset.read_bytes():
            print(f"refusing to overwrite existing integration file: {asset_path}", file=sys.stderr)
            return 1
        existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
        if START in existing and END in existing:
            if _block(shell) not in existing:
                print(f"existing Séance block differs; leaving {rc_path} unchanged", file=sys.stderr)
                return 1
        operations.append((shell, rc_path, asset_path))

    if dry_run:
        for shell, rc_path, asset_path in operations:
            print(f"would install {asset_path} and update {rc_path}")
        return 0

    for shell, rc_path, asset_path in operations:
        assert asset_path is not None
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        if not asset_path.exists():
            shutil.copy2(root / "shell" / asset_path.name, asset_path)
        existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
        block = _block(shell)
        if block not in existing:
            if rc_path.exists():
                backup = rc_path.with_name(f"{rc_path.name}.seance-backup")
                if backup.exists():
                    backup = rc_path.with_name(f"{rc_path.name}.seance-backup-{os.getpid()}")
                shutil.copy2(rc_path, backup)
                print(f"backed up {rc_path} to {backup}")
            with rc_path.open("a", encoding="utf-8") as config_file:
                if existing and not existing.endswith("\n"):
                    config_file.write("\n")
                config_file.write(f"\n{block}\n")
            print(f"updated {rc_path}")
        else:
            print(f"already configured in {rc_path}")
        print(f"installed integration at {asset_path}")
    return 0


def _uninstall(home: Path, shells: list[str], dry_run: bool) -> int:
    for shell in shells:
        filename, rc_name = INTEGRATIONS[shell]
        rc_path = home / rc_name
        block = _block(shell)
        if rc_path.exists():
            text = rc_path.read_text(encoding="utf-8")
            start_index = text.find(START)
            if start_index >= 0:
                end_index = text.find(END, start_index)
                if end_index < 0:
                    print(f"found an incomplete Séance block in {rc_path}; refusing to edit", file=sys.stderr)
                    return 1
                end_index += len(END)
                updated = text[:start_index] + text[end_index:]
                if updated.startswith("\n\n"):
                    updated = updated[1:]
                if dry_run:
                    print(f"would remove Séance block from {rc_path}")
                else:
                    rc_path.write_text(updated, encoding="utf-8")
                    print(f"removed Séance block from {rc_path}")
            else:
                print(f"no Séance block in {rc_path}")
        asset_path = home / CONFIG_DIR / filename
        if asset_path.exists():
            if dry_run:
                print(f"would remove {asset_path}")
            else:
                asset_path.unlink()
                print(f"removed {asset_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("install", "uninstall"), required=True)
    parser.add_argument("--shell", choices=("auto", "bash", "zsh", "both"), default="auto")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.action == "uninstall" and args.shell == "auto":
        shells = [
            shell for shell, (_, rc_name) in INTEGRATIONS.items()
            if (args.home / rc_name).exists()
            and START in (args.home / rc_name).read_text(encoding="utf-8")
        ]
        if not shells:
            shells = _select_shells(args.shell)
    else:
        shells = _select_shells(args.shell)
    if args.action == "install":
        return _install(args.home, args.root, shells, args.dry_run)
    return _uninstall(args.home, shells, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
