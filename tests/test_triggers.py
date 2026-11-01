from seance.config import Settings
from seance.triggers import classify_command


def test_destructive_commands_match_only_command_positions():
    settings = Settings()
    assert classify_command("rm -rf old-build", 0, settings).category == "destructive"
    assert classify_command("git reset --hard HEAD~1", 0, settings).category == "destructive"
    assert classify_command("git clean -fd", 0, settings).category == "destructive"
    assert classify_command("git checkout -- file.txt", 0, settings).category == "destructive"
    assert classify_command("git restore file.txt", 0, settings).category == "destructive"


def test_mentions_and_complex_commands_do_not_trigger():
    settings = Settings()
    assert classify_command("printf '%s\\n' rm", 0, settings) is None
    assert classify_command("echo 'git reset --hard'", 0, settings) is None
    assert classify_command("rm file; echo done", 0, settings) is None
    assert classify_command("rm $(printf file)", 0, settings) is None
    assert classify_command("FOO=bar rm file", 0, settings) is None


def test_build_commands_trigger_only_on_failure():
    settings = Settings()
    for command in ("npm run build", "npm test", "pytest", "cargo build", "make"):
        assert classify_command(command, 1, settings).category == "failed_build"
        assert classify_command(command, 0, settings) is None
    assert classify_command("echo pytest", 1, settings) is None


def test_custom_command_categories_are_supported():
    settings = Settings(destructive_commands=("purge cache",), build_commands=("just verify",))
    assert classify_command("purge cache all", 0, settings).category == "destructive"
    assert classify_command("just verify", 2, settings).category == "failed_build"
