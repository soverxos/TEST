#!/usr/bin/env python3

import sys
from pathlib import Path

# Гарантируем, что корень проекта в sys.path
current_script_path = Path(__file__).resolve()
project_root = current_script_path.parent
systems_path = project_root / "Systems"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(systems_path) not in sys.path:
    sys.path.insert(0, str(systems_path))

try:
    import typer
    from rich.console import Console
except ImportError as e:
    print(f"Критическая ошибка: Typer или Rich не установлены. {e}", file=sys.stderr)
    print(f"Пожалуйста, установите зависимости: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

# Создаем главный CLI-объект
# Включаем режим CLI, чтобы загрузка настроек не требовала BOT_TOKEN
import os as _os
import sys as _sys
_os.environ.setdefault("SDB_CLI_MODE", "true")

# Проверяем флаг -v/--verbose ДО импорта модулей, чтобы установить формат логирования
_argv = _sys.argv[1:]
_verbose_flag = "-v" in _argv or "--verbose" in _argv
if _verbose_flag:
    _os.environ["SDB_VERBOSE"] = "true"
else:
    _os.environ["SDB_VERBOSE"] = "false"
    # Настраиваем простой формат логирования ДО импорта модулей
    # чтобы логи при загрузке настроек не были подробными
    try:
        from loguru import logger as _early_logger
        _early_logger.remove()  # Удаляем стандартный handler
        # Простой формат: только время и сообщение
        _early_logger.add(
            _sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> <level>{message}</level>",
            colorize=True
        )
    except ImportError:
        pass  # Если loguru не доступен, пропускаем

# Гарантируем, что CLI-режим не мешает загрузке токена при старте бота
_bot_commands = {"start", "run", "bot"}
if _argv and _argv[0] in _bot_commands:
    if _os.environ.get("SDB_CLI_MODE") == "true":
        del _os.environ["SDB_CLI_MODE"]
cli_main_app = typer.Typer(
    name="sdb",
    help="🚀 [bold cyan]SwiftDevBot CLI[/] - Утилита для управления вашим SDB!",
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)

# Импортируем и регистрируем все команды и группы
try:
    # Группы команд (Typer-приложения)
    from Systems.cli.config import config_app
    from Systems.cli.db import db_app
    from Systems.cli.module import module_app
    from Systems.cli.user import user_app
    from Systems.cli.backup import backup_app
    from Systems.cli.system import system_app
    from Systems.cli.bot import bot_app
    from Systems.cli.monitor import monitor_app
    from Systems.cli.utils import utils_app
    from Systems.cli.security import security_app
    from Systems.cli.notifications import notifications_app
    
    # Добавляем недостающие модули
    from Systems.cli.dev import dev_app
    from Systems.cli.api import api_app
    from Systems.cli.cache import cache_app
    from Systems.cli.tasks import tasks_app
    
    cli_main_app.add_typer(config_app, name="config", help="🔧 Управление конфигурацией.")
    cli_main_app.add_typer(db_app, name="db", help="🗄️ Управление базой данных.")
    cli_main_app.add_typer(module_app, name="module", help="🧩 Управление модулями.")
    cli_main_app.add_typer(user_app, name="user", help="👤 Управление пользователями.")
    cli_main_app.add_typer(backup_app, name="backup", help="💾 Управление бэкапами.")
    cli_main_app.add_typer(system_app, name="system", help="🛠️ Системные команды.")
    cli_main_app.add_typer(bot_app, name="bot", help="🤖 Взаимодействие с Bot API.")
    cli_main_app.add_typer(monitor_app, name="monitor", help="📊 Мониторинг и аналитика.")
    cli_main_app.add_typer(utils_app, name="utils", help="🛠️ Утилитарные инструменты.")
    cli_main_app.add_typer(security_app, name="security", help="🔒 Управление безопасностью.")
    cli_main_app.add_typer(notifications_app, name="notifications", help="🔔 Управление уведомлениями.")
    
    # Добавляем новые модули
    cli_main_app.add_typer(dev_app, name="dev", help="🔧 Инструменты разработки.")
    cli_main_app.add_typer(api_app, name="api", help="🌐 Управление API.")
    cli_main_app.add_typer(cache_app, name="cache", help="💾 Управление кэшем системы.")
    cli_main_app.add_typer(tasks_app, name="tasks", help="📋 Управление задачами системы.")
    
    # Добавляем веб-панель
    try:
        from Systems.cli.web import web_app
        cli_main_app.add_typer(web_app, name="web", help="🌐 Управление веб-панелью.")
    except Exception as web_error:
        # Веб-панель опциональна, не критично если не импортируется
        # Логируем ошибку для отладки
        import os
        import traceback
        if os.environ.get("SDB_DEBUG"):
            console = Console()
            console.print(f"[yellow]Предупреждение: Веб-панель не доступна: {web_error}[/]")
            console.print(f"[dim]{traceback.format_exc()}[/]")
        # В любом случае продолжаем выполнение без веб-панели
        pass

    # Отдельные команды
    from Systems.cli.run import run_command
    from Systems.cli.process import stop_command, status_command, restart_command

    # Регистрируем команды верхнего уровня
    cli_main_app.command("run")(run_command)
    cli_main_app.command("start", help="🚀 Псевдоним для 'run'.")(run_command)
    cli_main_app.command("stop", help="🚦 Остановить процесс бота.")(stop_command)
    cli_main_app.command("status", help="🚦 Показать статус процесса.")(status_command)
    cli_main_app.command("restart", help="🚦 Перезапустить процесс бота.")(restart_command)

except ImportError as e:
    console = Console()
    console.print(f"[bold red]Ошибка импорта CLI компонентов:[/]\n {e}")
    console.print("Убедитесь, что структура папки 'cli/' корректна и все файлы на месте.")
    sys.exit(1)


if __name__ == "__main__":
    cli_main_app()
# --- КОНЕЦ ФАЙЛА sdb.py (и sdb) ---