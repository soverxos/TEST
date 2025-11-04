# cli_commands/bot_cmd.py
import asyncio
from pathlib import Path

import typer
from aiogram import Bot
from aiogram.types import BotCommand
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from Systems.core.module_loader import ModuleLoader
from Systems.core.services_provider import BotServicesProvider

from .utils import get_sdb_services_for_cli

console = Console()
bot_app = typer.Typer(
    name="bot", help="🤖 Управление настройками Telegram-бота.", rich_markup_mode="rich"
)


@bot_app.command(
    name="delete-commands", help="Удалить все команды из меню команд Telegram."
)
def delete_commands():
    """Удаляет все команды из меню команд Telegram."""

    async def _delete_commands_async():
        settings_obj, _, _ = await get_sdb_services_for_cli(
            init_db=False, init_rbac=False
        )
        if not settings_obj:
            console.print("[bold red]Ошибка: Не удалось загрузить настройки бота.[/]")
            logger.error("Не удалось загрузить настройки для команды delete-commands")
            raise typer.Exit(code=1)

        try:
            bot_token = settings_obj.telegram.token
            # <-- ИЗМЕНЕНИЕ: Добавляем проверку на наличие токена
            if not bot_token:
                console.print(
                    "[bold red]Ошибка: Токен бота не найден. Невозможно выполнить команду.[/bold red]"
                )
                console.print("Пожалуйста, настройте токен в .env файле.")
                raise typer.Exit(code=1)

            bot = Bot(token=bot_token)
            await bot.delete_my_commands()
            await bot.session.close()
            console.print(
                Panel(
                    "[bold green]Все команды успешно удалены из меню Telegram![/]",
                    expand=False,
                    border_style="green",
                )
            )
            logger.success("Все команды удалены из меню Telegram")
        except AttributeError as e:
            console.print(
                f"[bold red]Ошибка: Неправильная структура настроек CoreAppSettings: {e}[/]"
            )
            logger.error(f"Ошибка структуры настроек CoreAppSettings: {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red]Ошибка при удалении команд: {e}[/]")
            logger.error(f"Ошибка при удалении команд: {e}")
            raise typer.Exit(code=1)

    try:
        asyncio.run(_delete_commands_async())
    except (
        typer.Exit
    ):  # <-- ИЗМЕНЕНИЕ: Пропускаем typer.Exit, чтобы не показывать лишний traceback
        pass
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка: {e}[/]")
        logger.error(f"Неожиданная ошибка в delete-commands: {e}")
        raise typer.Exit(code=1)


@bot_app.command(
    name="set-commands",
    help="Установить команды в меню Telegram из модулей и настроек.",
)
def set_commands():
    """Устанавливает команды в меню Telegram."""

    async def _set_commands_async():
        settings_obj, _, _ = await get_sdb_services_for_cli(
            init_db=False, init_rbac=False
        )
        if not settings_obj:
            console.print("[bold red]Ошибка: Не удалось загрузить настройки бота.[/]")
            logger.error("Не удалось загрузить настройки для команды set-commands")
            raise typer.Exit(code=1)

        try:
            bot_token = settings_obj.telegram.token
            # <-- ИЗМЕНЕНИЕ: Добавляем проверку на наличие токена
            if not bot_token:
                console.print(
                    "[bold red]Ошибка: Токен бота не найден. Невозможно выполнить команду.[/bold red]"
                )
                console.print("Пожалуйста, настройте токен в .env файле.")
                raise typer.Exit(code=1)

            # Инициализируем ModuleLoader
            temp_bsp = BotServicesProvider(settings=settings_obj)
            loader = ModuleLoader(settings=settings_obj, services_provider=temp_bsp)
            loader.scan_all_available_modules()
            if hasattr(loader, "_load_enabled_plugin_names"):
                loader._load_enabled_plugin_names()

            # Собираем команды из модулей
            commands = []
            for module_info in loader.available_modules.values():
                if (
                    module_info.manifest
                    and module_info.name in loader.enabled_plugin_names
                ):
                    for cmd in module_info.manifest.commands or []:
                        # Проверяем, что cmd - это словарь
                        if (
                            isinstance(cmd, dict)
                            and cmd.get("command")
                            and cmd.get("description")
                        ):
                            commands.append(
                                BotCommand(
                                    command=cmd["command"].lstrip("/"),
                                    description=cmd["description"],
                                )
                            )

            # Добавляем команды из bot_commands.yaml (если есть)
            core_commands_path = (
                settings_obj.core.project_data_path / "Config" / "bot_commands.yaml"
            )
            if core_commands_path.exists():
                import yaml

                with core_commands_path.open("r", encoding="utf-8") as f:
                    core_commands = yaml.safe_load(f) or []
                for cmd in core_commands:
                    if (
                        isinstance(cmd, dict)
                        and cmd.get("command")
                        and cmd.get("description")
                    ):
                        commands.append(
                            BotCommand(
                                command=cmd["command"].lstrip("/"),
                                description=cmd["description"],
                            )
                        )

            if not commands:
                console.print("[yellow]Не найдено команд для установки.[/]")
                logger.warning("Нет команд для установки в меню Telegram")
                return

            # Устанавливаем команды
            bot = Bot(token=bot_token)
            await bot.set_my_commands(commands)
            await bot.session.close()

            # Выводим таблицу установленных команд
            table = Table(
                title="[bold cyan]Установленные команды[/]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Команда", style="cyan")
            table.add_column("Описание", style="green")
            for cmd in commands:
                table.add_row(f"/{cmd.command}", cmd.description)
            console.print(table)
            console.print(
                Panel(
                    "[bold green]Команды успешно установлены в меню Telegram![/]",
                    expand=False,
                    border_style="green",
                )
            )
            logger.success(f"Установлено {len(commands)} команд в меню Telegram")
        except AttributeError as e:
            console.print(
                f"[bold red]Ошибка: Неправильная структура настроек CoreAppSettings: {e}[/]"
            )
            logger.error(f"Ошибка структуры настроек CoreAppSettings: {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red]Ошибка при установке команд: {e}[/]")
            logger.error(f"Ошибка при установке команд: {e}")
            raise typer.Exit(code=1)

    try:
        asyncio.run(_set_commands_async())
    except typer.Exit:  # <-- ИЗМЕНЕНИЕ: Пропускаем typer.Exit
        pass
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка: {e}[/]")
        logger.error(f"Неожиданная ошибка в set-commands: {e}")
        raise typer.Exit(code=1)


@bot_app.command(name="status", help="Проверить статус бота.")
def status():
    """Проверяет, доступен ли бот."""

    async def _status_async():
        settings_obj, _, _ = await get_sdb_services_for_cli(
            init_db=False, init_rbac=False
        )
        if not settings_obj:
            console.print("[bold red]Ошибка: Не удалось загрузить настройки бота.[/]")
            logger.error("Не удалось загрузить настройки для команды status")
            raise typer.Exit(code=1)

        try:
            bot_token = settings_obj.telegram.token
            # <-- ИЗМЕНЕНИЕ: Добавляем проверку на наличие токена
            if not bot_token:
                console.print(
                    "[bold yellow]Проверка статуса невозможна: токен бота не настроен.[/bold yellow]"
                )
                console.print(
                    "Пожалуйста, настройте токен в .env файле и повторите попытку."
                )
                raise typer.Exit()  # Завершаем команду без ошибки

            bot = Bot(token=bot_token)
            bot_info = await bot.get_me()
            await bot.session.close()
            console.print(
                Panel(
                    f"[bold green]Бот активен! ID: {bot_info.id}, Имя: @{bot_info.username}[/]",
                    expand=False,
                    border_style="green",
                )
            )
            logger.success(f"Бот активен: @{bot_info.username}")
        except AttributeError as e:
            console.print(
                f"[bold red]Ошибка: Неправильная структура настроек CoreAppSettings: {e}[/]"
            )
            logger.error(f"Ошибка структуры настроек CoreAppSettings: {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red]Ошибка при проверке статуса: {e}[/]")
            logger.error(f"Ошибка при проверке статуса: {e}")
            raise typer.Exit(code=1)

    try:
        asyncio.run(_status_async())
    except typer.Exit:  # <-- ИЗМЕНЕНИЕ: Пропускаем typer.Exit
        pass
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка: {e}[/]")
        logger.error(f"Неожиданная ошибка в status: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    bot_app()
