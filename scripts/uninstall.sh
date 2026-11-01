#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$ROOT/scripts/manage_shell_config.py" --action uninstall "$@"
