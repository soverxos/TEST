# --- НАЧАЛО ФАЙЛА cli/process.py ---
import asyncio
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from typing import Tuple as TypingTuple

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    import psutil
except ImportError:
    psutil = None

from .utils import get_sdb_services_for_cli

# Эта консоль будет инициализирована в главном файле sdb
sdb_console: Console = Console()

PID_FILENAME = "sdb_bot.pid"


def _get_pid_file_path() -> Path:
    from Systems.core.app_settings import settings

    # Настройки уже загружены
    return settings.core.project_data_path / PID_FILENAME


def _read_pid_from_file(pid_file: Path) -> Optional[int]:
    if not pid_file.is_file():
        return None
    try:
        pid_str = pid_file.read_text().strip()
        if not pid_str.isdigit():
            sys.stderr.write(
                f"Предупреждение: PID-файл содержит нечисловое значение: '{pid_str}'.\n"
            )
            return None
        return int(pid_str)
    except Exception as e:
        sys.stderr.write(f"Ошибка чтения PID из файла {pid_file}: {e}\n")
        return None


def _is_process_running(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if psutil:
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    else:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return str(pid) in result.stdout
        except (FileNotFoundError, Exception):
            return False


async def _get_total_users_count_cli() -> Optional[int]:
    db_m = None
    try:
        _, db_m, _ = await get_sdb_services_for_cli(init_db=True)
        if not db_m:
            return None
        from sqlalchemy import func as sql_func
        from sqlalchemy import select

        from Systems.core.database.core_models import User

        async with db_m.get_session() as session:
            stmt = select(sql_func.count(User.id))
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0
    except Exception:
        return None
    finally:
        if db_m:
            await db_m.dispose()


def status_command():
    """Показывает текущий статус и информацию о SDB боте."""
    from aiogram import __version__ as aiogram_version

    from Systems.core.app_settings import settings

    # Настройки уже загружены
    pid_file = _get_pid_file_path()
    pid = _read_pid_from_file(pid_file)

    status_text_elements: List[Text] = []
    process_info_data: Optional[List[TypingTuple[str, str]]] = None

    is_running_flag = False
    if pid and _is_process_running(pid):
        is_running_flag = True
        status_text_elements.append(
            Text.assemble(
                ("✅ БОТ ЗАПУЩЕН ", "bold green"), 
                ("● SDB Core активен ", "green"), 
                (f"(PID: {pid})", "green bold")
            )
        )
        if psutil:
            try:
                p = psutil.Process(pid)
                process_info_data = []
                with p.oneshot():
                    create_time = datetime.fromtimestamp(p.create_time())
                    uptime_delta = datetime.now() - create_time
                    days, remainder = divmod(uptime_delta.total_seconds(), 86400)
                    hours, remainder = divmod(remainder, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    uptime_str_parts = []
                    if days > 0:
                        uptime_str_parts.append(f"{int(days)}д")
                    if hours > 0:
                        uptime_str_parts.append(f"{int(hours)}ч")
                    if minutes > 0:
                        uptime_str_parts.append(f"{int(minutes)}м")
                    uptime_str_parts.append(f"{int(seconds)}с")

                    process_info_data.append(
                        ("Запущен:", create_time.strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    process_info_data.append(
                        ("Время работы:", " ".join(uptime_str_parts) or "0с")
                    )
                    process_info_data.append(
                        ("CPU нагрузка:", f"{p.cpu_percent(interval=0.1):.1f}%")
                    )
                    rss_mb = p.memory_info().rss / (1024 * 1024)
                    process_info_data.append(("Память (RSS):", f"{rss_mb:.2f} MB"))
                    try:
                        process_info_data.append(
                            ("Кол-во потоков:", str(p.num_threads()))
                        )
                    except (psutil.Error, AttributeError, NotImplementedError):
                        pass
                    process_info_data.append(("Статус процесса:", str(p.status())))
                    try:
                        process_info_data.append(("Запущен от:", str(p.username())))
                    except (psutil.Error, AttributeError, NotImplementedError):
                        pass
            except psutil.NoSuchProcess:
                is_running_flag = False
                status_text_elements.clear()
                status_text_elements.append(
                    Text("❌ БОТ НЕ ЗАПУЩЕН", style="bold red")
                )
                status_text_elements.append(
                    Text(
                        f"⚠ PID-файл ({pid_file}) для PID {pid} существует, но процесс уже не найден (устарел).",
                        style="yellow",
                    )
                )
                # Автоматически удаляем устаревший PID-файл
                if pid_file.is_file():
                    try:
                        pid_file.unlink()
                        status_text_elements.append(
                            Text(f"✓ Устаревший PID-файл автоматически удален.", style="green")
                        )
                    except Exception as e_unlink:
                        status_text_elements.append(
                            Text(
                                f"  Не удалось удалить PID-файл: rm {pid_file}",
                                style="cyan",
                            )
                        )
            except psutil.AccessDenied:
                status_text_elements.append(
                    Text(
                        f"✗ Отказано в доступе к информации о процессе PID {pid}.",
                        style="red",
                    )
                )
            except Exception as e_psutil:
                status_text_elements.append(
                    Text(f"✗ Ошибка psutil для PID {pid}: {e_psutil}", style="red")
                )
        else:
            status_text_elements.append(
                Text(
                    "(Установите 'psutil' для детальной информации о процессе)",
                    style="dim",
                )
            )
    elif pid:
        status_text_elements.append(
            Text("❌ БОТ НЕ ЗАПУЩЕН", style="bold red")
        )
        status_text_elements.append(
            Text(
                f"⚠ SDB Core не активен (PID-файл {pid_file} (PID {pid}) устарел).",
                style="yellow",
            )
        )
        # Автоматически удаляем устаревший PID-файл
        if pid_file.is_file():
            try:
                pid_file.unlink()
                status_text_elements.append(
                    Text(f"✓ Устаревший PID-файл автоматически удален.", style="green")
                )
            except Exception as e_unlink:
                status_text_elements.append(
                    Text(f"  Рекомендуется удалить PID-файл: rm {pid_file}", style="cyan")
                )
    else:
        status_text_elements.append(
            Text("❌ БОТ НЕ ЗАПУЩЕН", style="bold red")
        )
        status_text_elements.append(
            Text("◎ SDB Core не активен (PID-файл не найден).", style="red")
        )

    status_panel_content = Text("\n").join(status_text_elements)
    # Меняем цвет рамки в зависимости от статуса
    border_color = "green" if is_running_flag else "red"
    title_color = "green" if is_running_flag else "red"
    status_panel = Panel(
        status_panel_content,
        title=f"[bold {title_color}]Статус SDB Core[/bold {title_color}]",
        border_style=border_color,
        expand=False,
        padding=(1, 2),
    )

    process_panel_renderable = None
    if process_info_data and is_running_flag:
        proc_table = Table(show_header=False, box=None, padding=(0, 1), show_edge=False)
        proc_table.add_column(
            style="dim blue", justify="right", min_width=18, max_width=20
        )
        proc_table.add_column(min_width=20)
        for key, value in process_info_data:
            proc_table.add_row(key, value)
        process_panel_renderable = Panel(
            proc_table,
            title="[bold blue]Процесс SDB[/bold blue]",
            border_style="blue",
            expand=False,
            padding=1,
        )

    sdb_info_data_list: List[TypingTuple[str, Any]] = []
    sdb_info_data_list.append(("Версия SDB Core:", settings.core.sdb_version))
    sdb_info_data_list.append(("Версия Aiogram:", aiogram_version))
    sdb_info_data_list.append(("Тип БД:", settings.db.type.upper()))
    sdb_info_data_list.append(("Тип кэша:", settings.cache.type.capitalize()))

    try:
        from Systems.core.module_loader import ModuleLoader
        from Systems.core.services_provider import BotServicesProvider

        temp_bsp = BotServicesProvider(settings=settings)
        loader = ModuleLoader(settings=settings, services_provider=temp_bsp)
        loader.scan_all_available_modules()
        loader._load_enabled_plugin_names()
        sdb_info_data_list.append(
            ("Найдено модулей:", str(len(loader.available_modules)))
        )
        sdb_info_data_list.append(
            ("Активных модулей:", str(len(loader.enabled_plugin_names)))
        )
    except Exception:
        sdb_info_data_list.append(("Модули:", Text("Ошибка подсчета", style="yellow")))

    total_users = asyncio.run(_get_total_users_count_cli())
    user_count_text_val = (
        str(total_users)
        if total_users is not None
        else Text("Не удалось получить", style="yellow")
    )
    sdb_info_data_list.append(("Всего пользователей в БД:", user_count_text_val))

    sdb_info_table = Table(show_header=False, box=None, padding=(0, 1), show_edge=False)
    sdb_info_table.add_column(style="dim magenta", justify="right", min_width=26)
    sdb_info_table.add_column(min_width=25)
    for key, value in sdb_info_data_list:
        sdb_info_table.add_row(key, value)
    sdb_info_panel = Panel(
        sdb_info_table,
                    title="[bold magenta]Конфигурация SDB Core[/bold magenta]",
        border_style="magenta",
        expand=False,
        padding=1,
    )

    sdb_console.print(status_panel)

    columns_content = []
    if process_panel_renderable:
        columns_content.append(process_panel_renderable)
    columns_content.append(sdb_info_panel)

    if columns_content:
        sdb_console.print(
            Columns(
                columns_content,
                expand=True,
                equal=False,
                padding=(0, 2),
                column_first=False,
            )
        )


def stop_command(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Принудительно остановить (SIGKILL), если SIGTERM не сработал (ОПАСНО).",
    ),
    timeout: int = typer.Option(
        5,
        "--timeout",
        "-t",
        help="Время ожидания (сек) после SIGTERM перед SIGKILL (если --force).",
        min=1,
        max=60,
    ),
):
    """Останавливает процесс SDB бота."""
    pid_file = _get_pid_file_path()
    pid = _read_pid_from_file(pid_file)

    if not pid:
        sdb_console.print("[yellow]SDB Core не активен (PID-файл не найден).[/yellow]")
        return

    if not _is_process_running(pid):
        sdb_console.print(
            f"[yellow]SDB бот (PID: {pid} из файла) уже не запущен.[/yellow]"
        )
        if pid_file.is_file():
            try:
                pid_file.unlink()
                sdb_console.print(f"Устаревший PID-файл {pid_file} удален.")
            except Exception as e_unlink:
                sdb_console.print(
                    f"[red]Не удалось удалить устаревший PID-файл {pid_file}: {e_unlink}[/red]"
                )
        return

    sdb_console.print(f"Попытка остановить SDB бота (PID: {pid})...")

    if sys.platform == "win32":
        sdb_console.print(
            "[yellow]Автоматическая остановка для Windows не реализована. Пожалуйста, остановите процесс вручную (taskkill /F /PID {pid}).[/yellow]"
        )
        raise typer.Exit(code=1)

    try:
        os.kill(pid, signal.SIGTERM)
        sdb_console.print(f"Отправлен сигнал SIGTERM процессу {pid}.")

        for i in range(timeout):
            time.sleep(1)
            if not _is_process_running(pid):
                sdb_console.print(
                    f"[green]SDB бот (PID: {pid}) успешно остановлен (через {i+1} сек).[/green]"
                )
                if pid_file.is_file():
                    pid_file.unlink(missing_ok=True)
                return

        if _is_process_running(pid):
            if force:
                sdb_console.print(
                    f"[yellow]Процесс {pid} все еще активен после {timeout} сек. Принудительная остановка (SIGKILL)...[/yellow]"
                )
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.1)
                if not _is_process_running(pid):
                    sdb_console.print(
                        f"[green]SDB бот (PID: {pid}) принудительно остановлен (SIGKILL).[/green]"
                    )
                else:
                    sdb_console.print(
                        f"[red]✗ SDB бот (PID: {pid}) не остановился даже после SIGKILL. Проверьте вручную.[/red]"
                    )
                    raise typer.Exit(code=1)
                if pid_file.is_file():
                    pid_file.unlink(missing_ok=True)
            else:
                sdb_console.print(
                    f"[red]✗ SDB бот (PID: {pid}) не остановился после SIGTERM ({timeout} сек).[/red]"
                )
                sdb_console.print(
                    f"  Попробуйте 'sdb stop --force' или остановите процесс вручную (kill {pid})."
                )
                raise typer.Exit(code=1)
        else:
            sdb_console.print(
                f"[green]SDB бот (PID: {pid}) успешно остановлен.[/green]"
            )
            if pid_file.is_file():
                pid_file.unlink(missing_ok=True)
    except ProcessLookupError:
        sdb_console.print(f"[green]SDB бот (PID: {pid}) уже был остановлен.[/green]")
        if pid_file.is_file():
            pid_file.unlink(missing_ok=True)
    except typer.Exit:
        raise
    except Exception as e:
        sdb_console.print(f"[red]Ошибка при остановке бота: {e}[/red]")
        raise typer.Exit(code=1)


def restart_command(
    force_stop: bool = typer.Option(
        False,
        "--force-stop",
        help="Использовать --force при остановке перед перезапуском.",
    ),
    stop_timeout: int = typer.Option(
        5,
        "--stop-timeout",
        help="Время ожидания (сек) для команды stop.",
        min=1,
        max=60,
    ),
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: default=False ---
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Запустить бота в фоновом режиме после перезапуска.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Запустить бота в режиме отладки после перезапуска.",
    ),
):
    """Перезапускает SDB бота: останавливает (если запущен) и затем запускает."""
    sdb_console.print(Panel("[blue]Перезапуск SDB бота...[/blue]", expand=False))

    sdb_console.print(
        "\n[cyan]Шаг 1: Остановка текущего экземпляра бота (если запущен)...[/cyan]"
    )
    stop_failed = False

    sdb_executable_str: Optional[str] = None
    project_root = Path(sys.argv[0]).parent.resolve()

    # Ищем sdb (исполняемый) или sdb.py
    sdb_path = project_root / "sdb"
    sdb_py_path = project_root / "sdb.py"

    if sdb_path.exists() and os.access(sdb_path, os.X_OK):
        sdb_executable_str = str(sdb_path)
    elif sdb_py_path.exists():
        sdb_executable_str = str(sdb_py_path)

    if not sdb_executable_str:
        sdb_console.print(
            f"[bold red]Не удалось определить исполняемый файл SDB CLI.[/bold red]"
        )
        raise typer.Exit(1)

    try:
        # Вызываем команду stop через subprocess, чтобы она работала в своем контексте
        stop_command_args = [sdb_executable_str, "stop", f"--timeout={stop_timeout}"]
        if force_stop:
            stop_command_args.append("--force")

        sdb_console.print(
            f"[dim]Вызов команды остановки: {' '.join(stop_command_args)}[/dim]"
        )
        stop_process_result = subprocess.run(
            stop_command_args, capture_output=True, text=True, encoding="utf-8"
        )

        if stop_process_result.stdout:
            sdb_console.print(
                f"[dim cyan]Вывод 'stop':[/]\n{stop_process_result.stdout.strip()}"
            )
        if stop_process_result.stderr:
            sdb_console.print(
                f"[dim yellow]Ошибки от 'stop':[/]\n{stop_process_result.stderr.strip()}"
            )
        if stop_process_result.returncode != 0:
            sdb_console.print(
                f"[bold red]Ошибка на фазе остановки (код: {stop_process_result.returncode}).[/bold red]"
            )
            if not typer.confirm("Продолжить попытку запуска?", default=False):
                raise typer.Exit(code=1)
            stop_failed = True
    except Exception as e_stop_wrapper:
        sdb_console.print(
            Text.assemble(
                ("[bold red]Ошибка при вызове 'stop': ", "bold red"),
                Text(str(e_stop_wrapper)),
            )
        )
        if not typer.confirm("Продолжить попытку запуска?", default=False):
            raise typer.Exit(code=1)
        stop_failed = True

    if not stop_failed:
        time.sleep(1)

    sdb_console.print("\n[cyan]Шаг 2: Запуск нового экземпляра бота...[/cyan]")
    try:
        start_command_args = [sdb_executable_str, "run"]
        if background:
            start_command_args.append("--background")
        if debug:
            start_command_args.append("--debug")

        sdb_console.print(
            f"[dim]Вызов команды запуска: {' '.join(start_command_args)}[/dim]"
        )

        if background:
            # Запускаем и "забываем" - это и есть фоновый режим
            subprocess.Popen(
                start_command_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            sdb_console.print(
                "[green]Команда запуска бота в фоновом режиме успешно отправлена.[/green]"
            )
        else:
            # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Запускаем процесс в интерактивном режиме ---
            # Просто вызываем команду, и ее вывод пойдет в текущий терминал.
            # Не используем capture_output=True
            subprocess.run(start_command_args)
            # Код здесь будет ждать завершения процесса бота
            sdb_console.print(
                "[bold green]Интерактивный сеанс бота завершен.[/bold green]"
            )

    except Exception as e_start_wrapper:
        sdb_console.print(
            Text.assemble(
                ("[bold red]Ошибка на этапе запуска: ", "bold red"),
                Text(str(e_start_wrapper)),
            )
        )
        raise typer.Exit(code=1)

    sdb_console.print("\n[bold green]Команда перезапуска завершена.[/bold green]")
    if background:
        sdb_console.print("  Проверьте статус бота через: [cyan]sdb status[/cyan]")


# --- КОНЕЦ ФАЙЛА cli/process.py ---
