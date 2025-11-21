# cli_commands/system_cmd.py

import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel

# Импортируем функции для возможности моканья в тестах
try:
    from Systems.cli.utils import get_settings_only_for_cli
    from Systems.core.app_settings import PROJECT_ROOT_DIR, settings
except ImportError:
    # Fallback для тестов
    settings = None
    get_settings_only_for_cli = None
    PROJECT_ROOT_DIR = Path.cwd()

# Создаем приложение для системных команд
system_app = typer.Typer(help="Системные команды для SwiftDevBot.")
console = Console()


def _show_basic_system_info(settings):
    """Показывает базовую информацию о системе без асинхронных вызовов."""
    console.print("\n[bold cyan]Системная информация:[/bold cyan]")

    # Информация о БД
    console.print(f"[bold]База данных:[/bold] {settings.db.type}")
    if settings.db.type == "sqlite":
        db_path = settings.core.project_data_path / (
            settings.db.sqlite_path or "Database_files/swiftdevbot.db"
        )
        db_exists = db_path.exists()
        console.print(f"[bold]Файл БД:[/bold] {db_path} {'✅' if db_exists else '❌'}")

    # Информация о директориях
    dirs_to_check = [
        ("Логи", settings.core.project_data_path / "Logs"),
        ("Кэш", settings.core.project_data_path / "Cache_data"),
        ("Бэкапы", settings.core.project_data_path / "core_backups"),
        ("Конфиг", settings.core.project_data_path / "Config"),
    ]

    for name, path in dirs_to_check:
        exists = path.exists()
        console.print(f"[bold]{name}:[/bold] {path} {'✅' if exists else '❌'}")

    # Информация о кэше
    cache_type = getattr(settings.cache, "type", "memory")
    console.print(f"[bold]Тип кэша:[/bold] {cache_type}")

    # Информация о модулях (попытка загрузить список)
    try:
        enabled_modules_path = (
            settings.core.project_data_path / settings.core.enabled_modules_config_path
        )
        if enabled_modules_path.exists():
            with open(enabled_modules_path, "r") as f:
                enabled_modules = json.load(f)
            console.print(
                f"[bold]Конфигурация модулей:[/bold] {len(enabled_modules)} записей"
            )
        else:
            console.print(f"[bold]Конфигурация модулей:[/bold] файл не найден")
    except Exception as e:
        console.print(f"[bold]Конфигурация модулей:[/bold] ошибка чтения ({e})")


@system_app.command(name="info", help="Показать системную информацию о SwiftDevBot.")
def info_cmd():
    """
    Команда для отображения системной информации.
    Использует минимальную загрузку настроек без BOT_TOKEN.
    """
    try:
        settings = get_settings_only_for_cli()  # Оптимизированная загрузка без токена
        _show_basic_system_info(settings)
    except Exception as e:
        console.print(f"[red]Ошибка получения системной информации: {e}[/red]")
        raise typer.Exit(1)


@system_app.command(name="update", help="Обновить SwiftDevBot до последней версии.")
def update_cmd(
    branch: str = typer.Option("main", "--branch", "-b", help="Ветка для обновления."),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Создать резервную копию перед обновлением."
    ),
    restart: bool = typer.Option(
        False, "--restart", "-r", help="Перезапустить бота после обновления."
    ),
):
    """Обновление системы до последней версии."""
    try:
        settings = settings  # Настройки уже загружены
        root_dir = PROJECT_ROOT_DIR

        console.print(
            f"[bold blue]Обновление SwiftDevBot с ветки '{branch}'...[/bold blue]"
        )

        # Создание резервной копии если требуется
        if backup:
            console.print("[yellow]Создание резервной копии...[/yellow]")
            backup_name = (
                f"backup_before_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            backup_path = (
                settings.core.project_data_path
                / "core_backups"
                / f"{backup_name}.tar.gz"
            )
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Создаем архив с исключениями
            with tarfile.open(backup_path, "w:gz") as tar:

                def filter_func(tarinfo):
                    # Исключаем временные файлы и директории
                    if any(
                        exclude in tarinfo.name
                        for exclude in [
                            ".git",
                            "__pycache__",
                            ".pytest_cache",
                            "node_modules",
                            "venv",
                            ".env",
                        ]
                    ):
                        return None
                    return tarinfo

                tar.add(root_dir, arcname=".", filter=filter_func)

            console.print(f"[green]Резервная копия создана: {backup_path}[/green]")

        # Git pull для обновления
        console.print("[blue]Загрузка обновлений...[/blue]")
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=root_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"[red]Ошибка при обновлении: {result.stderr}[/red]")
            raise typer.Exit(1)

        console.print("[green]Код успешно обновлен![/green]")

        # Проверка и установка зависимостей
        requirements_path = root_dir / "requirements.txt"
        if requirements_path.exists():
            console.print("[blue]Обновление зависимостей...[/blue]")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_path),
                    "--upgrade",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                console.print("[green]Зависимости обновлены![/green]")
            else:
                console.print(
                    f"[yellow]Предупреждение при обновлении зависимостей: {result.stderr}[/yellow]"
                )

        # Применение миграций БД
        console.print("[blue]Применение миграций БД...[/blue]")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=root_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                console.print("[green]Миграции применены![/green]")
            else:
                console.print(
                    f"[yellow]Предупреждение при применении миграций: {result.stderr}[/yellow]"
                )
        except Exception as e:
            console.print(f"[yellow]Не удалось применить миграции: {e}[/yellow]")

        console.print("[bold green]✅ Обновление завершено успешно![/bold green]")

        if restart:
            console.print("[blue]Перезапуск бота...[/blue]")
            try:
                # Проверяем, запущен ли бот
                import signal
                import subprocess
                import time

                # Ищем процесс бота
                result = subprocess.run(
                    ["pgrep", "-f", "run_bot.py"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    pid = int(result.stdout.strip())
                    console.print(f"[yellow]Останавливаем бот (PID: {pid})...[/yellow]")

                    # Отправляем SIGTERM для корректного завершения
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(3)

                    # Проверяем, завершился ли процесс
                    try:
                        os.kill(pid, 0)  # Проверка существования процесса
                        console.print(
                            "[yellow]Процесс не завершился, принудительное завершение...[/yellow]"
                        )
                        os.kill(pid, signal.SIGKILL)
                        time.sleep(1)
                    except ProcessLookupError:
                        pass  # Процесс уже завершился

                # Запускаем бот заново
                console.print("[green]Запускаем бот...[/green]")
                subprocess.Popen(
                    [sys.executable, "run_bot.py"],
                    cwd=settings.core.project_root_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                console.print("[bold green]✅ Бот успешно перезапущен![/bold green]")

            except Exception as restart_error:
                console.print(f"[red]Ошибка при перезапуске: {restart_error}[/red]")
                console.print(
                    "[yellow]Пожалуйста, перезапустите бот вручную: python run_bot.py[/yellow]"
                )

    except Exception as e:
        console.print(f"[red]Ошибка при обновлении: {e}[/red]")
        raise typer.Exit(1)


@system_app.command(name="rollback", help="Откатить SwiftDevBot к предыдущей версии.")
def rollback_cmd(
    backup_name: str = typer.Argument(
        ..., help="Имя резервной копии для восстановления."
    ),
    confirm: bool = typer.Option(
        False, "--confirm", "-y", help="Подтвердить откат без дополнительных вопросов."
    ),
):
    """Откат системы к предыдущей версии из резервной копии."""
    try:
        settings = settings  # Настройки уже загружены
        root_dir = PROJECT_ROOT_DIR

        # Поиск резервной копии
        backup_path = (
            settings.core.project_data_path / "core_backups" / f"{backup_name}.tar.gz"
        )
        if not backup_path.exists():
            # Попробуем найти без расширения
            backup_path = settings.core.project_data_path / "core_backups" / backup_name
            if not backup_path.exists():
                console.print(f"[red]Резервная копия '{backup_name}' не найдена![/red]")
                console.print("\n[blue]Доступные резервные копии:[/blue]")
                backup_dir = settings.core.project_data_path / "core_backups"
                if backup_dir.exists():
                    for backup in backup_dir.glob("*.tar.gz"):
                        console.print(f"  • {backup.stem}")
                raise typer.Exit(1)

        console.print(f"[yellow]Найдена резервная копия: {backup_path}[/yellow]")

        # Подтверждение операции
        if not confirm:
            confirm_rollback = typer.confirm(
                "⚠️  ВНИМАНИЕ! Откат перезапишет все текущие файлы. Продолжить?"
            )
            if not confirm_rollback:
                console.print("[blue]Откат отменен пользователем.[/blue]")
                raise typer.Exit(0)

        console.print("[bold red]🔄 Выполняется откат системы...[/bold red]")

        # Создание временной резервной копии текущего состояния
        temp_backup_name = (
            f"temp_before_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        temp_backup_path = (
            settings.core.project_data_path
            / "core_backups"
            / f"{temp_backup_name}.tar.gz"
        )

        console.print("[blue]Создание временной копии текущего состояния...[/blue]")
        with tarfile.open(temp_backup_path, "w:gz") as tar:
            tar.add(
                root_dir,
                arcname=".",
                exclude=lambda path: any(ex in path for ex in [".git", "__pycache__"]),
            )

        # Восстановление из резервной копии
        console.print("[blue]Восстановление файлов из резервной копии...[/blue]")
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=root_dir, filter="data")

        console.print("[green]✅ Файлы восстановлены из резервной копии![/green]")
        console.print(f"[blue]Временная копия сохранена: {temp_backup_path}[/blue]")
        console.print(
            "[bold yellow]Не забудьте также откатить миграции БД (`sdb db downgrade ...`) и Python-зависимости, если это необходимо![/bold yellow]"
        )

    except Exception as e:
        console.print(f"[red]Ошибка при откате: {e}[/red]")
        raise typer.Exit(1)


@system_app.command(
    name="status", help="Показать статус системы и запущенных процессов."
)
def status_cmd():
    """Показывает статус системы."""
    try:
        # Настройки уже загружены из импорта

        console.print("\n[bold cyan]Статус SwiftDevBot:[/bold cyan]")

        # Проверка основных файлов
        root_dir = PROJECT_ROOT_DIR

        main_files = [
            ("Основной файл", root_dir / "sdb.py"),
            ("Файл запуска", root_dir / "run_bot.py"),
            (
                "Конфигурация",
                settings.core.project_data_path / "Config" / "core_settings.yaml",
            ),
        ]

        for name, path in main_files:
            exists = path.exists()
            console.print(f"[bold]{name}:[/bold] {'✅' if exists else '❌'} {path}")

        # Информация о системе
        console.print(
            f"\n[bold]Операционная система:[/bold] {platform.system()} {platform.release()}"
        )
        console.print(f"[bold]Python версия:[/bold] {platform.python_version()}")
        console.print(f"[bold]Архитектура:[/bold] {platform.machine()}")

        # Проверка Git статуса
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=root_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                commit_hash = result.stdout.strip()
                console.print(f"[bold]Git коммит:[/bold] {commit_hash}")

                # Проверка на изменения
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=root_dir,
                    capture_output=True,
                    text=True,
                )

                if result.stdout.strip():
                    console.print("[yellow]⚠️ Есть незафиксированные изменения[/yellow]")
                else:
                    console.print("[green]✅ Рабочая директория чистая[/green]")
        except:
            console.print("[yellow]Git информация недоступна[/yellow]")

        # Проверка VPN статуса
        console.print(f"\n[bold cyan]VPN Статус:[/bold cyan]")
        try:
            # Проверяем systemd сервис
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", "swiftdevbot-vpn.service"],
                capture_output=True,
            )

            if result.returncode == 0:
                console.print("[green]✅ VPN сервис активен[/green]")

                # Проверяем VPN интерфейс
                result = subprocess.run(
                    ["ip", "addr", "show", "tun1"], capture_output=True, text=True
                )

                if result.returncode == 0:
                    console.print("[green]✅ VPN интерфейс активен[/green]")

                    # Получаем внешний IP
                    try:
                        result = subprocess.run(
                            [
                                "curl",
                                "-s",
                                "--connect-timeout",
                                "5",
                                "https://icanhazip.com",
                            ],
                            capture_output=True,
                            text=True,
                        )

                        if result.returncode == 0 and result.stdout.strip():
                            external_ip = result.stdout.strip()
                            console.print(f"[bold]Внешний IP:[/bold] {external_ip}")

                            if external_ip == "31.202.91.112":
                                console.print(
                                    "[green]🎉 Подключение через ASUS роутер подтверждено![/green]"
                                )
                            else:
                                console.print(
                                    "[yellow]⚠️ IP не соответствует ожидаемому[/yellow]"
                                )
                    except:
                        console.print("[yellow]Не удалось получить внешний IP[/yellow]")
                else:
                    console.print("[red]❌ VPN интерфейс недоступен[/red]")
            else:
                console.print("[red]❌ VPN сервис неактивен[/red]")
        except Exception as vpn_error:
            console.print(
                f"[yellow]Не удалось проверить VPN статус: {vpn_error}[/yellow]"
            )

        _show_basic_system_info(settings)

    except Exception as e:
        console.print(f"[red]Ошибка получения статуса: {e}[/red]")
        raise typer.Exit(1)


@system_app.command(name="vpn", help="Проверить статус VPN подключения.")
def vpn_status_cmd():
    """Проверка статуса VPN подключения."""
    try:
        # Запускаем наш скрипт проверки VPN
        result = subprocess.run(
            [str(PROJECT_ROOT_DIR / "scripts" / "check_vpn_status.sh")],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print(f"[red]Ошибка при проверке VPN: {result.stderr}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Ошибка при проверке VPN статуса: {e}[/red]")
        raise typer.Exit(1)
