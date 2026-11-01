#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
ACTION=install
DRY_RUN=0
SHELL_CHOICE=auto
for arg in "$@"; do
    case "$arg" in
        --uninstall) ACTION=uninstall ;;
        --dry-run) DRY_RUN=1 ;;
        --shell=*) SHELL_CHOICE=${arg#--shell=} ;;
        --help)
            printf 'Usage: %s [--dry-run] [--shell=auto|bash|zsh|both] [--uninstall]\n' "$0"
            exit 0
            ;;
        *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

if [[ $ACTION == install && $DRY_RUN == 0 ]]; then
    if ! python3 -m pip install --user "$ROOT"; then
        CLI_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}/seance
        CLI_VENV=$CLI_HOME/venv
        CLI_BIN=${XDG_BIN_HOME:-"$HOME/.local/bin"}
        CLI_ENTRY=$CLI_BIN/seance
        if [[ -L $CLI_ENTRY && $(readlink "$CLI_ENTRY") == "$CLI_VENV/bin/seance" ]]; then
            :
        elif [[ -e $CLI_ENTRY || -L $CLI_ENTRY ]]; then
            printf 'Refusing to overwrite existing CLI entry point: %s\n' "$CLI_ENTRY" >&2
            exit 1
        fi
        if [[ -e $CLI_VENV/bin/seance ]]; then
            :
        elif [[ -e $CLI_VENV ]]; then
            printf 'Refusing to overwrite existing environment: %s\n' "$CLI_VENV" >&2
            exit 1
        else
            mkdir -p "$CLI_HOME"
            python3 -m venv "$CLI_VENV"
        fi
        "$CLI_VENV/bin/python" -m pip install "$ROOT"
        mkdir -p "$CLI_BIN"
        if [[ ! -e $CLI_ENTRY && ! -L $CLI_ENTRY ]]; then
            ln -s "$CLI_VENV/bin/seance" "$CLI_ENTRY"
        fi
        printf 'Installed isolated CLI at %s\n' "$CLI_ENTRY"
        case ":$PATH:" in
            *":$CLI_BIN:"*) ;;
            *) printf 'Add %s to PATH to use `seance`.\n' "$CLI_BIN" ;;
        esac
    fi
fi

args=(--action "$ACTION" --shell "$SHELL_CHOICE" --root "$ROOT")
(( DRY_RUN )) && args+=(--dry-run)
python3 "$ROOT/scripts/manage_shell_config.py" "${args[@]}"
