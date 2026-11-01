import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_bash_hook_preserves_last_status_and_does_not_run_noninteractive():
    result = _run([
        "bash", "-c",
        f"source '{ROOT / 'shell/seance.bash'}'; false; seance_prompt_hook; printf '%s' \"$?\"",
    ])
    assert result.returncode == 0
    assert result.stdout == "1"
    assert result.stderr == ""


def test_interactive_bash_registration_preserves_existing_prompt_command():
    result = _run([
        "bash", "--noprofile", "--norc", "-ic",
        f"PROMPT_COMMAND='existing_prompt'; source '{ROOT / 'shell/seance.bash'}'; "
        f"source '{ROOT / 'shell/seance.bash'}'; declare -p PROMPT_COMMAND",
    ])
    assert result.returncode == 0
    assert "seance_prompt_hook; existing_prompt; seance_prompt_restore_status" in result.stdout
    assert result.stdout.count("seance_prompt_hook") == 1


def test_zsh_hook_preserves_last_status_and_does_not_run_noninteractive():
    if not shutil_which("zsh"):
        return
    result = _run([
        "zsh", "-c",
        f"source '{ROOT / 'shell/seance.zsh'}'; false; seance_precmd; print -r -- $?",
    ])
    assert result.returncode == 0
    assert result.stdout.strip() == "1"


def test_interactive_zsh_registration_preserves_existing_hooks():
    if not shutil_which("zsh"):
        return
    result = _run([
        "zsh", "-f", "-ic",
        f"precmd_functions=(existing_precmd); preexec_functions=(existing_preexec); "
        f"source '{ROOT / 'shell/seance.zsh'}'; source '{ROOT / 'shell/seance.zsh'}'; "
        "print -r -- \"precmd=$precmd_functions\"; print -r -- \"preexec=$preexec_functions\"",
    ])
    assert result.returncode == 0
    assert "precmd=seance_precmd existing_precmd seance_precmd_restore_status" in result.stdout
    assert "preexec=seance_preexec existing_preexec" in result.stdout


def test_zsh_hook_skips_recursive_preexec_and_classifies_after_status_capture(tmp_path):
    if not shutil_which("zsh"):
        return
    fake_cli = tmp_path / "seance"
    fake_cli.write_text("#!/bin/sh\nprintf 'hook-called\\n'\n", encoding="utf-8")
    fake_cli.chmod(0o755)
    env = {"PATH": f"{tmp_path}:{__import__('os').environ['PATH']}", "SEANCE_ENABLED": "1"}
    recursive = _run([
        "zsh", "-c",
        f"source '{ROOT / 'shell/seance.zsh'}'; SEANCE_LAST_COMMAND=keep; SEANCE_HOOK_RUNNING=1; "
        "seance_preexec 'rm harmless'; print -r -- $SEANCE_LAST_COMMAND",
    ])
    assert recursive.stdout.strip() == "keep"

    result = subprocess.run(
        [
            "zsh", "-c",
            f"source '{ROOT / 'shell/seance.zsh'}'; SEANCE_LAST_COMMAND='rm harmless'; "
            "false; seance_precmd; print -r -- \"status=$?\"",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["hook-called", "status=1"]


def test_installer_is_idempotent_and_uninstaller_preserves_other_config(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".bashrc"
    rc.write_text("export EXISTING=1\n", encoding="utf-8")
    manager = ROOT / "scripts/manage_shell_config.py"
    base = [sys.executable, str(manager), "--shell", "bash", "--home", str(home), "--root", str(ROOT)]
    for _ in range(2):
        result = _run(base + ["--action", "install"])
        assert result.returncode == 0, result.stderr
    contents = rc.read_text(encoding="utf-8")
    assert contents.count("# >>> seance-shell >>>") == 1
    assert "export EXISTING=1" in contents
    assert (home / ".bashrc.seance-backup").exists()

    result = _run(base + ["--action", "uninstall"])
    assert result.returncode == 0, result.stderr
    assert rc.read_text(encoding="utf-8").strip() == "export EXISTING=1"
    assert not (home / ".config/seance/seance.bash").exists()


def shutil_which(program):
    from shutil import which
    return which(program)
