import pytest
from typer.testing import CliRunner

from sdb import cli_main_app


@pytest.fixture(autouse=True)
def set_cli_mode_env(monkeypatch):
    """Запускаем CLI в безопасном режиме без настоящего токена."""
    monkeypatch.setenv("SDB_CLI_MODE", "true")
    monkeypatch.setenv("SDB_VERBOSE", "false")


def _collect_cli_command_paths():
    """Возвращает все доступные пути команд CLI (включая группы и подгруппы)."""
    command_paths = []

    for cmd in cli_main_app.registered_commands:
        command_paths.append((cmd.name,))

    def _traverse(prefix, typer_app):
        for cmd in typer_app.registered_commands:
            command_paths.append(tuple(prefix + [cmd.name]))
        for group in typer_app.registered_groups:
            _traverse(prefix + [group.name], group.typer_instance)

    for group in cli_main_app.registered_groups:
        _traverse([group.name], group.typer_instance)

    return command_paths


ALL_CLI_COMMAND_PATHS = _collect_cli_command_paths()


@pytest.mark.parametrize("command_path", ALL_CLI_COMMAND_PATHS)
def test_cli_command_help(command_path):
    command_args = list(command_path) + ["--help"]
    runner = CliRunner()
    result = runner.invoke(cli_main_app, command_args)
    assert result.exit_code == 0, f"'{' '.join(command_args)}' failed: {result.output}"
    assert "Usage:" in result.output

