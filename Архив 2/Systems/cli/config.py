# --- НАЧАЛО ФАЙЛА cli/config.py ---
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, Tuple

import typer
import yaml
from dotenv import find_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .utils import (PROJECT_ROOT, USER_CONFIG_DIR_NAME,
                    USER_CORE_CONFIG_FILENAME, USER_MODULES_CONFIG_DIR_NAME,
                    confirm_action, read_yaml_file, sdb_console,
                    write_yaml_file)

# --- Typer App для группы команд 'config' ---
config_app = typer.Typer(
    name="config",
    help="🔧 Управление конфигурацией SwiftDevBot (инициализация, просмотр, изменение).",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

storage_app = typer.Typer(
    name="storage",
    help="🔁 Управление backendом FSM storage и переключением cache type.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

db_config_app = typer.Typer(
    name="db",
    help="🗄️ Управление конфигурацией базы данных.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

ENV_FILENAME = ".env"


# --- Вспомогательные функции ---
def _update_env_file(key: str, value: str) -> bool:
    """Безопасно находит и обновляет .env файл."""
    env_path = find_dotenv(
        filename=ENV_FILENAME, usecwd=True, raise_error_if_not_found=False
    )
    if not env_path:
        env_path = PROJECT_ROOT / ENV_FILENAME
        sdb_console.print(
            f"[dim]Файл .env не найден, будет создан новый: {env_path}[/dim]"
        )
        env_path.touch()
    try:
        set_key(
            dotenv_path=env_path,
            key_to_set=key,
            value_to_set=value,
            quote_mode="always",
        )
        sdb_console.print(
            f"[green]✓[/] Переменная [cyan]{key}[/] сохранена в [yellow]{env_path}[/yellow]"
        )
        return True
    except Exception as e:
        sdb_console.print(
            f"[bold red]Ошибка при записи в .env файл ({env_path}): {e}[/bold red]"
        )
        return False


def _get_project_data_path() -> Path:
    """Получает путь к Data (было project_data), даже если настройки еще не загружены."""
    from Systems.core.app_settings import CoreAppSettings

    default_path = CoreAppSettings.model_fields["project_data_path"].default
    return (PROJECT_ROOT / default_path).resolve()


# --- Команды CLI ---


@config_app.command(
    name="init", help="Интерактивная настройка бота и создание файлов конфигурации."
)
def init_command(
    force: bool = typer.Option(
        False, "--force", "-f", help="Принудительно перезаписать существующие конфиги."
    )
):
    """Запускает интерактивный визард для первоначальной настройки бота."""
    sdb_console.print(
        Panel("🤖 [bold cyan]Интерактивный настройщик SwiftDevBot[/]", expand=False)
    )

    # Шаг 1: Токен Бота
    sdb_console.print("\n--- [bold]Шаг 1: Токен Telegram Бота[/bold] ---")
    bot_token = typer.prompt(
        "🔑 Введите ваш BOT_TOKEN (получить у @BotFather)", hide_input=True
    )
    if not bot_token or len(bot_token.split(":")) != 2:
        sdb_console.print(
            "[bold red]Ошибка: Токен выглядит некорректно. Настройка прервана.[/bold red]"
        )
        raise typer.Exit(1)
    _update_env_file("BOT_TOKEN", bot_token)

    # Шаг 2: База Данных
    sdb_console.print("\n--- [bold]Шаг 2: База Данных[/bold] ---")
    db_type_choice = typer.prompt(
        "🗄️ Тип БД: [1] sqlite, [2] postgresql, [3] mysql", default="1"
    )

    env_vars_to_set: Dict[str, str] = {}
    if db_type_choice == "1":
        env_vars_to_set["SDB_DB_TYPE"] = "sqlite"
        env_vars_to_set["SDB_DB_SQLITE_PATH"] = "Database_files/swiftdevbot.db"
    elif db_type_choice in ["2", "3"]:
        db_type = "postgresql" if db_type_choice == "2" else "mysql"
        sdb_console.print(f"--- [bold]Настройка {db_type.capitalize()}[/bold] ---")
        host = typer.prompt("  🌐 Хост", default="localhost")
        port = typer.prompt(
            "  🚪 Порт", default="5432" if db_type == "postgresql" else "3306"
        )
        user = typer.prompt("  👤 Пользователь")
        password = typer.prompt("  🔒 Пароль", hide_input=True)
        dbname = typer.prompt("  💾 Имя БД")
        driver = "psycopg" if db_type == "postgresql" else "aiomysql"
        dsn = f"{db_type}+{driver}://{user}:{password}@{host}:{port}/{dbname}"
        if db_type == "mysql":
            dsn += "?charset=utf8mb4"
        env_vars_to_set["SDB_DB_TYPE"] = db_type
        env_key = "SDB_DB_PG_DSN" if db_type == "postgresql" else "SDB_DB_MYSQL_DSN"
        env_vars_to_set[env_key] = dsn
    else:
        sdb_console.print("[bold red]Неверный выбор. Настройка прервана.[/bold red]")
        raise typer.Exit(1)

    for key, value in env_vars_to_set.items():
        _update_env_file(key, value)

    # Шаг 3: Супер-Администратор
    sdb_console.print("\n--- [bold]Шаг 3: Супер-Администратор[/bold] ---")
    super_admin_id = typer.prompt("👑 Введите ваш Telegram ID (числовой)")
    if not super_admin_id.isdigit():
        sdb_console.print(
            "[bold red]Ошибка: Telegram ID должен быть числом.[/bold red]"
        )
        raise typer.Exit(1)
    _update_env_file("SDB_CORE_SUPER_ADMINS", super_admin_id)

    # Шаг 4: Создание core_settings.yaml
    sdb_console.print("\n--- [bold]Шаг 4: Файл базовых настроек[/bold] ---")
    project_data_path = _get_project_data_path()
    user_config_file = (
        project_data_path / USER_CONFIG_DIR_NAME / USER_CORE_CONFIG_FILENAME
    )

    if (
        user_config_file.exists()
        and not force
        and not confirm_action(
            f"Файл {user_config_file} уже существует. Перезаписать его?",
            default_choice=False,
            abort_on_false=False,
        )
    ):
        sdb_console.print("[yellow]Создание core_settings.yaml пропущено.[/yellow]")
    else:
        from Systems.core.app_settings import AppSettings

        default_settings = AppSettings(telegram={"token": "dummy"}).model_dump(
            exclude_defaults=False
        )
        # Удаляем ключи, которые хранятся в .env
        del default_settings["telegram"]
        del default_settings["db"]
        del default_settings["core"]["super_admins"]

        if write_yaml_file(user_config_file, default_settings):
            sdb_console.print(
                f"[green]✓[/] Файл [yellow]{user_config_file}[/yellow] успешно создан/обновлен."
            )

    sdb_console.print(
        Panel("✅ [bold green]Настройка успешно завершена![/]", expand=False)
    )
    sdb_console.print("💡 [bold]Следующий шаг:[/bold] [cyan]sdb db upgrade head[/cyan]")


@config_app.command(
    "get", help="Показать всю конфигурацию или значение конкретного ключа."
)
def get_command(
    key: Optional[str] = typer.Argument(None, help="Ключ (напр. 'db.type')"),
    show_defaults: bool = typer.Option(False, "--show-defaults"),
):
    """Отображает текущую активную конфигурацию SDB."""
    try:
        from Systems.core.app_settings import settings

        # Настройки уже загружены в app_settings
    except Exception as e:
        sdb_console.print(f"[bold red]Ошибка загрузки настроек: {e}[/bold red]")
        raise typer.Exit(1)

    if key is None:
        config_dict = settings.model_dump(
            mode="json", exclude_defaults=not show_defaults
        )
        yaml_output = yaml.dump(config_dict, indent=2, sort_keys=False)
        sdb_console.print(
            Panel("[bold cyan]Активная конфигурация SwiftDevBot[/]", expand=False)
        )
        sdb_console.print(
            Syntax(yaml_output, "yaml", theme="native", line_numbers=True)
        )
    else:
        try:
            value = settings
            for part in key.split("."):
                value = getattr(value, part) if hasattr(value, part) else value[part]  # type: ignore

            if hasattr(value, "model_dump"):
                value = value.model_dump(mode="json")

            # Красивое отображение значения
            sdb_console.print(Panel(f"[bold cyan]Конфигурация: {key}[/]", expand=False))

            if isinstance(value, dict):
                yaml_output = yaml.dump(value, indent=2, sort_keys=False)
                sdb_console.print(Syntax(yaml_output, "yaml", theme="native"))
            else:
                sdb_console.print(f"   [green]Значение:[/green] {value}")
                sdb_console.print(f"   [blue]Тип:[/blue] {type(value).__name__}")

        except (AttributeError, KeyError):
            sdb_console.print(f"[bold red]Ошибка: Ключ '{key}' не найден.[/bold red]")
            raise typer.Exit(1)


@config_app.command("set", help="Установить значение в core_settings.yaml или .env.")
def set_command(
    key: str = typer.Argument(..., help="Ключ для установки (напр. 'core.log_level')"),
    value: str = typer.Argument(..., help="Новое значение."),
):
    """Изменяет значение конфигурации ядра или переменной окружения."""
    sdb_console.print(
        f"Попытка установить [cyan]{key}[/] = [green]'{value}'[/green]..."
    )

    # Сначала проверяем, не является ли это переменной окружения
    env_map = {
        "telegram.token": "BOT_TOKEN",
        "db.pg_dsn": "SDB_DB_PG_DSN",
        "db.mysql_dsn": "SDB_DB_MYSQL_DSN",
        "core.super_admins": "SDB_CORE_SUPER_ADMINS",
    }
    if key.lower() in env_map:
        _update_env_file(env_map[key.lower()], value)
        return

    # Если нет, работаем с core_settings.yaml
    project_data_path = _get_project_data_path()
    config_file = project_data_path / USER_CONFIG_DIR_NAME / USER_CORE_CONFIG_FILENAME
    config_data = read_yaml_file(config_file)
    if config_data is None:
        sdb_console.print(
            f"[bold red]Ошибка: Не удалось прочитать файл {config_file}.[/bold red]\nЗапустите 'sdb config init', чтобы создать его."
        )
        raise typer.Exit(1)

    keys = key.split(".")
    current_level = config_data
    for i, k in enumerate(keys[:-1]):
        if k not in current_level or not isinstance(current_level[k], dict):
            current_level[k] = {}
        current_level = current_level[k]

    # Преобразуем значение в правильный тип, если возможно
    final_value: Any = value
    if value.lower() in ["true", "false"]:
        final_value = value.lower() == "true"
    elif value.isdigit():
        final_value = int(value)
    else:
        try:
            final_value = float(value)
        except ValueError:
            pass

    current_level[keys[-1]] = final_value

    if write_yaml_file(config_file, config_data):
        sdb_console.print(
            f"[green]✓[/] Ключ [cyan]{key}[/] обновлен в [yellow]{config_file}[/yellow]."
        )
        sdb_console.print(
            "[yellow]Изменения вступят в силу после перезапуска бота.[/yellow]"
        )


def _write_cache_config(cache_type: Literal["memory", "redis"], redis_url: Optional[str]) -> None:
    project_data_path = _get_project_data_path()
    config_file = project_data_path / USER_CONFIG_DIR_NAME / USER_CORE_CONFIG_FILENAME
    config_data = read_yaml_file(config_file) or {}
    cache_section = config_data.get("cache", {})
    cache_section["type"] = cache_type
    if cache_type == "redis":
        cache_section["redis_url"] = redis_url or cache_section.get("redis_url", "redis://localhost:6379/0")
    else:
        cache_section.pop("redis_url", None)
    config_data["cache"] = cache_section

    if write_yaml_file(config_file, config_data):
        sdb_console.print(
            f"[green]✓[/] Настройки кэша обновлены в {config_file} (cache.type={cache_type})."
        )
        if cache_type == "redis":
            sdb_console.print(f"[dim]redis_url={cache_section.get('redis_url')}[/]")
        sdb_console.print("[yellow]Перезапустите бот, чтобы изменения вступили в силу.[/yellow]")


@storage_app.command("set", help="Установить тип кэша/хранилища FSM.")
def storage_set(
    cache_type: Literal["memory", "redis"] = typer.Argument(
        ...,
        help="Тип кэша/хранилища: memory или redis.",
    ),
    redis_url: Optional[str] = typer.Option(
        None,
        "--redis-url",
        "-r",
        help="URL Redis (только для redis).",
    ),
):
    if cache_type == "redis" and not redis_url:
        sdb_console.print("[bold red]Для redis нужно указать --redis-url.[/bold red]")
        raise typer.Exit(code=1)
    _write_cache_config(cache_type, redis_url)


@storage_app.command("status", help="Показать текущий cache backend.")
def storage_status():
    try:
        from Systems.core.app_settings import settings
        cache_cfg = settings.cache
        cache_status = f"cache.type = {cache_cfg.type}"
        if cache_cfg.type == "redis":
            cache_status += f", redis_url = {cache_cfg.redis_url}"
        sdb_console.print(Panel(f"[bold cyan]Текущий cache backend[/]\n{cache_status}", expand=False))
    except Exception as e_status:
        sdb_console.print(f"[bold red]Не удалось получить настройки кэша: {e_status}[/bold red]")


def _normalize_db_type(db_type: str) -> str:
    normalized = db_type.lower()
    if normalized == "postgres":
        normalized = "postgresql"
    if normalized not in {"sqlite", "postgresql", "mysql"}:
        raise ValueError(f"Неподдерживаемый тип БД '{db_type}'. Поддерживаемые: sqlite, postgresql, mysql.")
    return normalized


def _write_db_config(
    db_type: Literal["sqlite", "postgresql", "mysql"],
    sqlite_path: Optional[str],
    dsn: Optional[str]
) -> None:
    project_data_path = _get_project_data_path()
    config_file = project_data_path / USER_CONFIG_DIR_NAME / USER_CORE_CONFIG_FILENAME
    config_data = read_yaml_file(config_file) or {}
    db_section = config_data.get("db", {})
    db_section["type"] = db_type
    if db_type == "sqlite":
        db_section["sqlite_path"] = sqlite_path or "Database_files/swiftdevbot.db"
        db_section.pop("pg_dsn", None)
        db_section.pop("mysql_dsn", None)
    elif db_type == "postgresql":
        db_section["pg_dsn"] = dsn or db_section.get("pg_dsn")
        db_section.pop("mysql_dsn", None)
    elif db_type == "mysql":
        db_section["mysql_dsn"] = dsn or db_section.get("mysql_dsn")
        db_section.pop("pg_dsn", None)
    config_data["db"] = db_section

    if write_yaml_file(config_file, config_data):
        sdb_console.print(
            f"[green]✓[/] Конфиг БД обновлён: {config_file} (db.type={db_type})."
        )
        if db_type == "postgresql":
            sdb_console.print(f"[dim]pg_dsn={db_section.get('pg_dsn')}[/]")
        elif db_type == "mysql":
            sdb_console.print(f"[dim]mysql_dsn={db_section.get('mysql_dsn')}[/]")
        elif db_type == "sqlite":
            sdb_console.print(f"[dim]sqlite_path={db_section.get('sqlite_path')}[/]")
        sdb_console.print("[yellow]Перезапустите SDB и выполните 'sdb db upgrade head' для миграций.[/yellow]")


def _build_pg_dsn(host: str, port: int, user: str, password: str, database: str) -> str:
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def _build_mysql_dsn(host: str, port: int, user: str, password: str, database: str) -> str:
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


@db_config_app.command("set", help="Настроить подключение к базе данных.")
def db_config_set(
    db_type: Literal["sqlite", "postgresql", "mysql"] = typer.Argument(
        ..., help="Тип базы данных."
    ),
    sqlite_path: Optional[str] = typer.Option(
        None, "--sqlite-path", help="Путь к файлу SQLite (для sqlite)."
    ),
    host: Optional[str] = typer.Option(
        None, "--host", "-H", help="Хост базы данных (для postgresql/mysql)."
    ),
    port: Optional[int] = typer.Option(
        None, "--port", "-P", help="Порт базы данных."
    ),
    user: Optional[str] = typer.Option(
        None, "--user", "-u", help="Пользователь базы данных."
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Пароль для базы данных."
    ),
    database: Optional[str] = typer.Option(
        None, "--database", "-d", help="Имя базы данных."
    ),
):
    if db_type == "sqlite":
        if sqlite_path is None:
            typer.echo("[bold yellow]Путь sqlite необязателен — используется значение по умолчанию.[/]")
        _write_db_config("sqlite", sqlite_path, None)
        return

    if not all([host, port, user, password, database]):
        raise typer.Exit(
            code=1,
            message="[bold red]Для PostgreSQL/MySQL требуется host, port, user, password и database.[/bold red]",
        )

    if db_type == "postgresql":
        dsn = _build_pg_dsn(host, port, user, password, database)
    else:
        dsn = _build_mysql_dsn(host, port, user, password, database)

    _write_db_config(db_type, None, dsn)


@db_config_app.command("status", help="Показать текущую конфигурацию БД.")
def db_config_status():
    try:
        from Systems.core.app_settings import settings

        db_cfg = settings.db
        status_lines = [f"db.type = {db_cfg.type}"]
        if db_cfg.type == "sqlite":
            status_lines.append(f"sqlite_path = {db_cfg.sqlite_path}")
        elif db_cfg.type == "postgresql":
            status_lines.append(f"pg_dsn = {db_cfg.pg_dsn}")
        elif db_cfg.type == "mysql":
            status_lines.append(f"mysql_dsn = {db_cfg.mysql_dsn}")

        sdb_console.print(
            Panel(
                "[bold cyan]Текущая конфигурация БД[/]\n" + "\n".join(status_lines),
                expand=False,
            )
        )
    except Exception as e_db_status:
        sdb_console.print(f"[bold red]Не удалось прочитать конфигурацию БД: {e_db_status}[/bold red]")


config_app.add_typer(storage_app, name="storage")
config_app.add_typer(db_config_app, name="db")
config_app.add_typer(storage_app, name="storage")


@config_app.command("notifications", help="Управление уведомлениями о запуске/остановке.")
def notifications_command(
    enable: bool = typer.Option(True, "--enable/--disable", help="Включить или отключить уведомления.")
):
    """Управляет отправкой уведомлений администраторам о запуске/остановке бота."""
    sdb_console.print(
        f"🔕 Управление уведомлениями: {'включены' if enable else 'отключены'}"
    )
    
    # Устанавливаем настройку через set_command
    set_command("core.enable_startup_shutdown_notifications", str(enable).lower())


@config_app.command("set-module", help="Установить настройку для конкретного модуля.")
def set_module_command(
    module_name: str = typer.Argument(..., help="Имя модуля (из manifest.name)."),
    key: str = typer.Argument(..., help="Ключ настройки в модуле."),
    value: str = typer.Argument(..., help="Новое значение."),
):
    """Изменяет значение конфигурации для указанного модуля."""
    sdb_console.print(
        f"Установка настройки для модуля [magenta]{module_name}[/]: [cyan]{key}[/] = [green]'{value}'[/green]"
    )

    project_data_path = _get_project_data_path()
    module_config_file = (
        project_data_path
        / USER_CONFIG_DIR_NAME
        / USER_MODULES_CONFIG_DIR_NAME
        / f"{module_name}.yaml"
    )

    config_data = read_yaml_file(module_config_file) or {}

    # Преобразуем значение
    final_value: Any = value
    if value.lower() in ["true", "false"]:
        final_value = value.lower() == "true"
    elif value.isdigit():
        final_value = int(value)
    else:
        try:
            final_value = float(value)
        except ValueError:
            pass

    config_data[key] = final_value

    if write_yaml_file(module_config_file, config_data):
        sdb_console.print(
            f"[green]✓[/] Настройка модуля [magenta]{module_name}[/] обновлена в [yellow]{module_config_file}[/yellow]."
        )
        sdb_console.print(
            "[yellow]Изменения вступят в силу после перезапуска бота.[/yellow]"
        )


if __name__ == "__main__":
    config_app()  # --- КОНЕЦ ФАЙЛА cli/config.py ---
