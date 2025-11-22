# --- НАЧАЛО ФАЙЛА cli/run.py ---
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import typer
from loguru import logger as global_logger
from rich.panel import Panel

from .process import (PID_FILENAME,  # Импортируем из соседнего файла
                      _is_process_running)

sdb_console = None  # Будет инициализирована в sdb.py


def _load_runtime_dependencies():
    """Загружает настройки и точку входа бота с дружелюбными подсказками."""
    global sdb_console
    if sdb_console is None:
        from rich.console import Console

        sdb_console = Console()

    try:
        os.environ.setdefault("SDB_SKIP_APP_SETTINGS_AUTOLOAD", "true")
        import Systems.core.app_settings as app_settings

        settings = app_settings.load_app_settings()
        app_settings.settings = settings
        from Systems.core.bot_entrypoint import run_sdb_bot
    except ValueError as settings_error:
        project_root = Path(__file__).resolve().parent.parent.parent
        env_path = project_root / ".env"
        env_example_path = project_root / "env.example"

        help_lines = [
            "BOT_TOKEN не найден. Заполните .env или core_settings.yaml перед запуском.",
            f"Ожидался файл: [cyan]{env_path}[/cyan]",
        ]

        if env_example_path.exists():
            help_lines.append(
                f"Скопируйте пример: [cyan]cp {env_example_path} {env_path}[/cyan] и установите BOT_TOKEN."
            )

        help_lines.append(
            "Или используйте визард настройки: [cyan]sdb config init[/cyan]"
        )

        sdb_console.print(
            Panel(
                "\n".join(help_lines),
                title="Настройте окружение перед запуском",
                border_style="red",
                expand=False,
            )
        )

        global_logger.error(
            "Ошибка загрузки настроек перед запуском бота: {}", settings_error
        )
        raise typer.Exit(code=1)

    return settings, run_sdb_bot


def run_command(
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Запустить бота в режиме отладки (увеличит уровень логирования до DEBUG).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Подробный вывод логов с информацией о модуле, функции и строке.",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Запустить бота в фоновом режиме (демонизировать).",
    ),
):
    """
    🚀 Запускает основной процесс Telegram бота SDB.
    """
    # Импортируем здесь, чтобы избежать циклических зависимостей и ускорить запуск CLI
    settings, run_sdb_bot = _load_runtime_dependencies()

    global sdb_console
    if sdb_console is None:
        from rich.console import Console

        sdb_console = Console()

    project_root = Path(__file__).resolve().parent.parent
    # Настройки уже загружены
    pid_file_path = settings.core.project_data_path / PID_FILENAME

    if pid_file_path.exists():
        try:
            with open(pid_file_path, "r") as f:
                pid = int(f.read().strip())
            if _is_process_running(pid):
                sdb_console.print(
                    f"[yellow]⚡ SDB Core уже активен (PID: {pid}). Используйте 'sdb stop' для остановки.[/yellow]"
                )
                raise typer.Exit(code=1)
        except (OSError, ValueError):
            sdb_console.print(
                f"[yellow]🔄 Обнаружен устаревший PID-файл ({pid_file_path}). Очистка...[/yellow]"
            )
            pid_file_path.unlink(missing_ok=True)
        except Exception as e_pid_check:
            sdb_console.print(
                f"[red]Ошибка при проверке PID-файла: {e_pid_check}[/red]"
            )

    if debug:
        sdb_console.print(
            Panel(
                f"[bold yellow]Запрос на запуск бота в режиме DEBUG.[/]",
                title="SDB Run (Debug Mode Requested)",
                expand=False,
                border_style="yellow",
            )
        )
        os.environ["SDB_LAUNCH_DEBUG_MODE"] = "true"
    else:
        os.environ["SDB_LAUNCH_DEBUG_MODE"] = "false"
    
    # Устанавливаем флаг verbose для логирования
    if verbose:
        os.environ["SDB_VERBOSE"] = "true"
    else:
        os.environ["SDB_VERBOSE"] = "false"

    if background:
        if sys.platform == "win32":
            sdb_console.print(
                "[bold red]Фоновый режим (-b/--background) пока не поддерживается на Windows через эту команду.[/bold red]"
            )
            sdb_console.print(
                "Пожалуйста, запустите бота без флага -b или используйте другие средства для демонизации."
            )
            raise typer.Exit(code=1)

        sdb_console.print(
            Panel(
                "[bold blue]🚀 Запуск SDB Core в фоновом режиме...[/]",
                title="SDB Core (Background)",
                expand=False,
                border_style="blue",
            )
        )

        run_bot_script_path = project_root / "run_bot.py"

        env_for_subprocess = os.environ.copy()
        env_for_subprocess["SDB_SHOULD_WRITE_PID"] = "true"
        # Передаем флаг verbose в фоновый процесс
        env_for_subprocess["SDB_VERBOSE"] = "true" if verbose else "false"

        try:
            process = subprocess.Popen(
                [sys.executable, str(run_bot_script_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env_for_subprocess,
            )
            sdb_console.print(
                f"⚡ SDB Core запущен в фоне (системный PID: {process.pid})."
            )
            sdb_console.print(
                f"Ожидание создания PID-файла '{PID_FILENAME}' (до 10 секунд)..."
            )

            pid_file_created_successfully = False
            for i in range(10):
                time.sleep(1)
                if pid_file_path.exists():
                    try:
                        actual_pid_from_file_str = pid_file_path.read_text().strip()
                        if actual_pid_from_file_str.isdigit():
                            actual_pid_from_file = int(actual_pid_from_file_str)
                            sdb_console.print(
                                f"[green]PID-файл {pid_file_path} создан. PID бота: {actual_pid_from_file}.[/green]"
                            )
                            sdb_console.print(
                                "Для просмотра статуса используйте: [cyan]sdb status[/cyan]"
                            )
                            sdb_console.print(
                                "Для остановки используйте: [cyan]sdb stop[/cyan]"
                            )
                            pid_file_created_successfully = True
                            break
                    except (ValueError, IOError) as e_read_pid:
                        sdb_console.print(
                            f"[yellow]Ошибка чтения PID из файла ({e_read_pid}). Попытка {i+1}/10.[/yellow]"
                        )

            if not pid_file_created_successfully:
                sdb_console.print(
                    f"[yellow]Предупреждение: PID-файл не был корректно создан/прочитан в течение 10 секунд.[/yellow]"
                )
                sdb_console.print(
                    f"  Возможно, бот не запустился корректно. Проверьте логи."
                )
                sdb_console.print(
                    f"  Системный PID: {process.pid}. Проверьте его статус вручную."
                )

        except Exception as e_popen:
            sdb_console.print(
                f"[bold red]Ошибка при запуске бота в фоновом режиме: {e_popen}[/bold red]"
            )
            raise typer.Exit(code=1)
    else:
        if not debug:
            sdb_console.print(
                Panel(
                    "[bold green]Запуск Telegram бота SDB...[/]",
                    title="SDB Run",
                    expand=False,
                    border_style="green",
                )
            )
        try:
            os.environ["SDB_SHOULD_WRITE_PID"] = "false"

            bot_coroutine = run_sdb_bot()
            exit_code = asyncio.run(bot_coroutine)

            if exit_code != 0:
                sdb_console.print(
                    f"[bold red]Бот завершил работу с кодом ошибки: {exit_code}[/]"
                )
                sys.exit(exit_code)
            else:
                sdb_console.print("[bold green]Бот успешно завершил свою работу.[/]")

        except KeyboardInterrupt:
            sdb_console.print(
                "\n[bold orange_red1]🤖 Бот остановлен пользователем (Ctrl+C).[/]"
            )
            sys.exit(0)
        except Exception as e:
            sdb_console.print(
                Panel(
                    f"[bold red]КРИТИЧЕСКАЯ ОШИБКА:[/]\n{e}",
                    title="SDB Runtime Error",
                    border_style="red",
                    expand=True,
                )
            )
            global_logger.opt(exception=e).critical(
                "Необработанное исключение в cli/run.py"
            )
            sys.exit(1)


# --- КОНЕЦ ФАЙЛА cli/run.py ---
