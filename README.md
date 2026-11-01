# Séance Shell 👻

A quiet, local-AI terminal companion that offers one short reflection after selected commands. The ghost is atmospheric, not an assistant: it gives no advice, runs no generated text, and never retries a command.

```text
$ git reset --hard HEAD~1
ghost: the past has accepted your changes, and forgotten your future.
```

Reflections are generated independently by Ollama on your machine with `gemma3:latest`. Model output is validated before display. If the local model is unavailable, the reflection is skipped.

## What it does

- Notices selected destructive-looking commands and failed build/test commands.
- Reflects only after the shell has already completed a command; it never re-runs it.
- Sends Ollama a category, outcome, and—only for an explicit `seance reflect --context` request—short sanitized context. Shell hooks do not send the command text to the model.
- Requires one sentence, at most 15 words and 180 characters; malformed output is discarded.
- Uses dim terminal text when appropriate, respects `NO_COLOR`, and does not print model errors from hooks.
- Supports Bash and Zsh using separate shell-native hooks.

This is an experimental companion, not a coding assistant or an autonomous agent.

## Requirements

- macOS or Linux, Python 3.10+, and Bash or Zsh.
- Ollama installed and running locally for generated reflections.
- `gemma3:latest` installed for generated reflections.

Install Ollama using its official instructions, start it, and explicitly install the model:

```bash
ollama pull gemma3:latest
```

Séance Shell never starts Ollama or downloads a model for you. The software remains usable without the model; hooks simply skip reflections.

## Install

From a checkout of this project:

```bash
python3 scripts/manage_shell_config.py --action install --shell auto
```

Or use the convenience installer, which installs the Python package for the current user and adds the detected shell integration:

```bash
./scripts/install.sh
```

Choose a shell explicitly or install both:

```bash
./scripts/install.sh --shell=bash
./scripts/install.sh --shell=zsh
./scripts/install.sh --shell=both
./scripts/install.sh --dry-run --shell=both
```

The installer copies the selected integration into `~/.config/seance/`, appends a marked source block to `~/.bashrc` or `~/.zshrc`, and backs up an existing rc file before changing it. Re-running it is idempotent. It refuses to overwrite an existing integration file that differs from the packaged one. Review the printed paths; then open a new interactive shell.

The installer first uses `python3 -m pip install --user`. If the Python distribution blocks user installs (for example, Homebrew Python under PEP 668), it falls back to a dedicated virtual environment in `~/.local/share/seance/venv` and exposes its CLI through `~/.local/bin/seance`. Ensure the user-level script directory is on `PATH` (`~/.local/bin` on many Linux and macOS installations). Check with `command -v seance`.

### Manual installation

Install the CLI and copy the matching integration yourself:

```bash
python3 -m pip install --user .
mkdir -p ~/.config/seance
cp shell/seance.bash ~/.config/seance/
```

Add this line to `~/.bashrc`:

```bash
[[ -f "$HOME/.config/seance/seance.bash" ]] && source "$HOME/.config/seance/seance.bash"
```

For Zsh, copy `shell/seance.zsh` and add the equivalent `source` line to `~/.zshrc`. Do not add Bash integration to Zsh or vice versa.

## Use the CLI

```bash
seance --help
seance doctor
seance config
seance test
seance reflect --category destructive --status 0
seance reflect --category failed-build --status 1
seance disable
seance enable
```

`seance test` creates a harmless sample reflection; it does not run a shell command. `reflect --context` accepts optional text, which is heuristically redacted and bounded before it is sent to local Ollama. The supplied text is never executed. `doctor` returns nonzero if Ollama is unreachable or the configured model is missing. Hook errors are intentionally silent so they cannot interfere with normal shell use.

## Triggers and conservative matching

By default, the following command forms are classified:

- Destructive-looking: `rm` with arguments, `git reset --hard`, `git clean -fd`, `git checkout --`, and `git restore`.
- Failed development commands: `npm run build`, `npm test`, `pytest`, `cargo build`, and `make`, only when their exit status is nonzero.

The hook passes the typed command and the shell-captured status to the CLI through standard input. The Python classifier tokenizes with shell-like quoting, but does not interpret shell syntax. It skips pipelines, command separators, expansions, leading assignments, wrappers, and other ambiguous forms. This intentionally creates false negatives rather than guessing. Successful build/test commands do not trigger. Destructive-looking commands may trigger regardless of exit status.

Additional exact command prefixes can be configured with `SEANCE_DESTRUCTIVE_COMMANDS` and `SEANCE_BUILD_COMMANDS`, as comma-separated values. For example:

```bash
export SEANCE_BUILD_COMMANDS="npm run build,pytest,just verify"
```

Configured destructive commands trigger regardless of status; configured build commands trigger only on failure. Keep custom values simple and avoid shell operators.

## Configuration

Environment variables override values in `~/.config/seance/config.ini` (or the path in `SEANCE_CONFIG`):

| Setting | Default | Description |
|---|---|---|
| `SEANCE_ENABLED` | `true` | Set to `0`/`false` to disable hooks, or `1`/`true` to enable them |
| `SEANCE_ENDPOINT` | `http://localhost:11434` | Local Ollama base URL; non-loopback hosts are rejected |
| `SEANCE_MODEL` | `gemma3:latest` | Local model tag |
| `SEANCE_TIMEOUT` | `2.5` | Request timeout in seconds; accepted range is 0.2–15 |
| `SEANCE_STYLE` | `eerie` | `eerie`, `poetic`, `darkly humorous`, or `restrained` |
| `SEANCE_COLOR` | `auto` | `auto`, `always`, or `never`; `NO_COLOR` always disables ANSI color |
| `SEANCE_DESTRUCTIVE_COMMANDS` | built-in list | Comma-separated custom destructive command prefixes |
| `SEANCE_BUILD_COMMANDS` | built-in list | Comma-separated build/test command prefixes |
| `SEANCE_CONFIG` | `~/.config/seance/config.ini` | Optional config file location |

`seance enable` and `seance disable` persist the enabled state in the config file. An explicit `SEANCE_ENABLED` environment setting takes precedence over that file. Set `SEANCE_SHELL_DISABLED=1` before sourcing the integration to prevent hook registration in that shell. Set `SEANCE_ENABLED=0` to disable reflections while keeping the integration loaded.

Example config:

```ini
[seance]
enabled = true
endpoint = http://localhost:11434
model = gemma3:latest
timeout = 2.5
style = eerie
color = auto
```

## Shell behavior and compatibility

Both integrations install hooks only for interactive shells and preserve existing prompt hooks rather than replacing them.

- **Bash:** `PROMPT_COMMAND` captures the previous status before running the reflection hook. The integration keeps existing `PROMPT_COMMAND` entries and restores the captured status after them. Bash's history interface supplies the previous command; ambiguous input is skipped. A prompt hook that is later replaced or reordered by another shell plugin can affect this behavior.
- **Zsh:** `preexec` captures the command text and `precmd` observes the command status. Séance's handlers are arranged around existing hook functions and restore the status before the prompt. Plugins that later rewrite hook arrays may change the ordering.
- The candidate prefilter avoids starting Python for most prompts. Eligible-looking input is checked again by Python. The model request runs synchronously, with a default 2.5-second upper bound; this is not instant, and actual local inference latency varies by model, hardware, and Ollama state.
- Non-interactive shells do not register hooks. Pipelines, background jobs, shell syntax with ambiguous interpretation, and commands the classifier cannot parse are skipped. Aliases, functions, wrappers, and arbitrary user shell customizations are not guaranteed to be recognized.

These integrations have not been verified against every shell version or plugin configuration. If preserving your personal shell behavior is uncertain, use the manual `seance` CLI or leave the integration disabled. The shell's own command output and standard error are never captured or redirected.

## Privacy and safety

The application calls only a loopback Ollama endpoint (`localhost`, `127.0.0.1`, or `::1`). It does not use cloud AI APIs, API keys, telemetry, shell history uploads, or a background daemon. Ollama receives only the configured model request. The shell hook sends category and outcome, not the command string. Optional `--context` text is limited and checked against common patterns such as bearer tokens, API keys, passwords, credential-bearing URLs, and secret assignments.

Secret detection is heuristic, not a guarantee. A secret in an unusual format may not be recognized, and local Ollama may retain request details according to its own behavior. Avoid providing sensitive `--context`; disable the companion for sensitive work. Model output is treated as untrusted display text: terminal escape/control characters are stripped, strict length and sentence checks are applied, and output is never evaluated or executed.

## Troubleshooting

- `seance: command not found`: add Python's user-level script directory to `PATH`, or reinstall with `python3 -m pip install --user .`.
- `seance doctor` reports Ollama unavailable: start Ollama yourself, check `SEANCE_ENDPOINT`, then retry. Séance does not start services.
- Model missing: run `ollama pull gemma3:latest` yourself, or set `SEANCE_MODEL` to an already installed local model.
- No reflection: confirm the trigger category/status, run `seance test`, and check `seance doctor`. Complex command syntax is intentionally ignored.
- Disable immediately: `export SEANCE_ENABLED=0`. Remove it with `unset SEANCE_ENABLED` when ready to use the config-file setting again.
- Shell hook problems: set `SEANCE_SHELL_DISABLED=1` before sourcing, or remove the marked block from your shell rc file.

## Remove Séance Shell

```bash
./scripts/uninstall.sh
```

To select shells explicitly, pass `--shell=bash`, `--shell=zsh`, or `--shell=both`. Uninstall removes only the marked Séance block and the dedicated integration copy from `~/.config/seance/`; it preserves other rc-file content and does not uninstall the Python package. Remove the package separately with:

```bash
python3 -m pip uninstall seance-shell
```

If the installer used its isolated fallback, uninstall with `~/.local/share/seance/venv/bin/python -m pip uninstall seance-shell`; remove `~/.local/bin/seance` only if it still points to this installation.

## Tests

Install pytest if needed, then run:

```bash
python3 -m pytest
```

Unit tests mock all Ollama HTTP calls and use safe fixture command strings. No test requires a running server or executes a destructive fixture. Shell tests check status restoration and installer idempotence. Optional manual integration check, with Ollama and the model already running:

```bash
seance doctor
seance test
```

## Contributing

Contributions should preserve the central guarantees: no command replay, no execution of model output, loopback-only inference, conservative classification, bounded requests, and unchanged shell status/output. Add unit tests for behavior changes; do not make automated tests depend on an installed model or real destructive commands.

## License

MIT. See [LICENSE](LICENSE).
