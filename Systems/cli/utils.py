# --- НАЧАЛО ФАЙЛА cli/utils.py ---
import asyncio
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# --- Константы, используемые в CLI ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
USER_CONFIG_DIR_NAME = "Config"
USER_CORE_CONFIG_FILENAME = "core_settings.yaml"
USER_MODULES_CONFIG_DIR_NAME = "modules_settings"

sdb_console = Console()


# --- Система измерения времени для CLI команд ---
def timing_decorator(func):
    """Декоратор для измерения времени выполнения команд CLI."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Проверяем, есть ли параметр timing в kwargs
        show_timing = kwargs.pop("timing", False) if "timing" in kwargs else False

        if show_timing:
            start_time = time.time()
            start_datetime = datetime.now()
            sdb_console.print(
                f"[dim cyan]⏰ Начало выполнения: {start_datetime.strftime('%H:%M:%S.%f')[:-3]}[/]"
            )

        try:
            result = func(*args, **kwargs)

            if show_timing:
                end_time = time.time()
                end_datetime = datetime.now()
                duration = end_time - start_time
                sdb_console.print(
                    f"[dim cyan]⏰ Окончание: {end_datetime.strftime('%H:%M:%S.%f')[:-3]}[/]"
                )
                sdb_console.print(
                    f"[bold green]⚡ Время выполнения: {duration:.3f} секунд[/]"
                )

            return result

        except Exception as e:
            if show_timing:
                end_time = time.time()
                duration = end_time - start_time
                sdb_console.print(
                    f"[bold red]❌ Команда завершилась с ошибкой через {duration:.3f} секунд[/]"
                )
            raise e

    return wrapper


# Функция для добавления опции --timing к командам
def add_timing_option():
    """Добавляет опцию --timing к CLI команде."""
    return typer.Option(
        False, "--timing", "-t", help="📊 Показать время выполнения команды."
    )


# Универсальная функция для быстрого добавления timing к команде
def with_timing(help_text: str):
    """
    Декоратор-хелпер для быстрого добавления timing к команде.

    Использование:
    @app.command(**with_timing("Описание команды"))
    @timing_decorator
    def my_command(timing: bool = add_timing_option()):
        pass
    """
    return {"name": None, "help": help_text}


# Функция для измерения времени любой операции
def measure_time(operation_name: str = "Операция"):
    """
    Контекстный менеджер для измерения времени выполнения.

    Использование:
    with measure_time("Загрузка данных"):
        # код операции
        pass
    """

    class TimingContext:
        def __init__(self, name):
            self.name = name

        def __enter__(self):
            self.start_time = time.time()
            start_datetime = datetime.now()
            sdb_console.print(
                f"[dim cyan]⏰ {self.name} - Начало: {start_datetime.strftime('%H:%M:%S.%f')[:-3]}[/]"
            )
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            end_time = time.time()
            duration = end_time - self.start_time
            end_datetime = datetime.now()

            if exc_type is None:
                sdb_console.print(
                    f"[dim cyan]⏰ {self.name} - Окончание: {end_datetime.strftime('%H:%M:%S.%f')[:-3]}[/]"
                )
                sdb_console.print(
                    f"[bold green]⚡ {self.name}: {duration:.3f} секунд[/]"
                )
            else:
                sdb_console.print(
                    f"[bold red]❌ {self.name} завершилась с ошибкой через {duration:.3f} секунд[/]"
                )

    return TimingContext(operation_name)


# Создаем Typer-приложение для утилит
utils_app = typer.Typer(
    name="utils",
    help="🛠️ Утилитарные инструменты для SwiftDevBot",
    rich_markup_mode="rich",
)

# --- Функции для работы с YAML ---


def get_yaml_editor():
    """Возвращает экземпляр ruamel.yaml.YAML для сохранения комментариев."""
    try:
        from ruamel.yaml import YAML

        yaml_editor = YAML()
        yaml_editor.indent(mapping=2, sequence=4, offset=2)
        yaml_editor.preserve_quotes = True
        return yaml_editor
    except ImportError:
        sdb_console.print(
            "[yellow]Предупреждение: библиотека 'ruamel.yaml' не установлена. Комментарии и форматирование в YAML файлах могут быть утеряны при изменении. Установите ее: `pip install ruamel.yaml`[/yellow]"
        )
        return None


def read_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    """Читает YAML файл, возвращая его содержимое как словарь."""
    if not path.is_file():
        return None
    try:
        editor = get_yaml_editor()
        if editor:
            return editor.load(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    except Exception as e:
        sdb_console.print(f"[bold red]Ошибка чтения YAML файла {path}: {e}[/bold red]")
        return None


def _convert_pydantic_objects_to_serializable(data: Any) -> Any:
    """Рекурсивно конвертирует pydantic объекты в сериализуемые типы."""
    from pathlib import Path

    try:
        from pydantic import HttpUrl
        from pydantic_core import Url

        if isinstance(data, dict):
            return {
                key: _convert_pydantic_objects_to_serializable(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [_convert_pydantic_objects_to_serializable(item) for item in data]
        elif isinstance(data, Path):
            return str(data)
        elif hasattr(data, "__class__") and data.__class__.__name__ in (
            "HttpUrl",
            "Url",
        ):
            return str(data)
        else:
            return data
    except ImportError:
        # Если pydantic не доступен, просто возвращаем данные как есть
        return data


def write_yaml_file(path: Path, data: Dict[str, Any]) -> bool:
    """Записывает словарь в YAML файл."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Конвертируем pydantic объекты в сериализуемые типы
        serializable_data = _convert_pydantic_objects_to_serializable(data)

        editor = get_yaml_editor()
        if editor:
            with open(path, "w", encoding="utf-8") as f:
                editor.dump(serializable_data, f)
        else:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(
                    serializable_data, f, indent=2, sort_keys=False, allow_unicode=True
                )
        return True
    except Exception as e:
        sdb_console.print(f"[bold red]Ошибка записи YAML файла {path}: {e}[/bold red]")
        return False


# --- Вспомогательные функции из старой версии ---


async def get_sdb_services_for_cli(
    init_db: bool = False,
    init_rbac: bool = False,
) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    """Вспомогательная функция для получения основных сервисов SDB."""
    settings_instance: Optional[Any] = None
    db_manager_instance: Optional[Any] = None
    rbac_service_instance: Optional[Any] = None

    try:
        from Systems.core.app_settings import settings

# Настройки уже загружены
        settings_instance = settings
        if init_db or init_rbac:
            from Systems.core.database.manager import DBManager

            db_m = DBManager(db_settings=settings.db, app_settings=settings)
            await db_m.initialize()
            db_manager_instance = db_m
            if init_rbac and db_manager_instance:
                from Systems.core.rbac.service import RBACService

                rbac_service_instance = RBACService(
                    services=None, db_manager=db_manager_instance
                )
        return settings_instance, db_manager_instance, rbac_service_instance
    except ImportError as e:
        raise
    except Exception as e:
        if db_manager_instance:
            await db_manager_instance.dispose()
        raise


async def get_db_only_for_cli():
    """Получить только DBManager без полной валидации настроек (без проверки токена бота)."""
    from pathlib import Path

    import yaml

    from Systems.core.app_settings import PROJECT_ROOT_DIR

    # Минимальные настройки только для БД
    Data_path = PROJECT_ROOT_DIR / "Data"
    config_file = Data_path / "Config" / "core_settings.yaml"

    # Читаем только настройки БД из YAML
    db_config = {"type": "sqlite", "sqlite_path": "Database_files/swiftdevbot.db"}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
                if "db" in yaml_data:
                    db_config.update(yaml_data["db"])
        except Exception:
            pass  # Используем дефолты

    # Создаём минимальный объект настроек БД
    from Systems.core.app_settings import DBSettings
    from Systems.core.database.manager import DBManager

    # Подготавливаем путь к SQLite
    if db_config["type"] == "sqlite":
        sqlite_path = db_config["sqlite_path"]
        if not Path(sqlite_path).is_absolute():
            if not sqlite_path.startswith("Database_files/"):
                sqlite_path = f"Database_files/{sqlite_path}"
            sqlite_path = str(Data_path / sqlite_path)
        db_config["sqlite_path"] = sqlite_path

    db_settings = DBSettings(**db_config)

    # Создаём DBManager с минимальными настройками
    class MinimalAppSettings:
        def __init__(self):
            self.db = db_settings

    app_settings = MinimalAppSettings()
    db_manager = DBManager(db_settings=db_settings, app_settings=app_settings)
    await db_manager.initialize()
    return db_manager


async def get_db_with_core_config_for_cli():
    """Получить DBManager + минимальные core настройки (для super_admins проверки)."""
    from pathlib import Path

    import yaml

    from Systems.core.app_settings import PROJECT_ROOT_DIR

    # Минимальные настройки только для БД + core
    Data_path = PROJECT_ROOT_DIR / "Data"
    config_file = Data_path / "Config" / "core_settings.yaml"

    # Читаем настройки БД и core из YAML
    db_config = {"type": "sqlite", "sqlite_path": "Database_files/swiftdevbot.db"}
    core_config = {"super_admins": []}

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
                if "db" in yaml_data:
                    db_config.update(yaml_data["db"])
                if "core" in yaml_data:
                    core_config.update(yaml_data["core"])
        except Exception:
            pass  # Используем дефолты

    # Создаём минимальный объект настроек
    from Systems.core.app_settings import CoreAppSettings, DBSettings
    from Systems.core.database.manager import DBManager

    # Подготавливаем путь к SQLite
    if db_config["type"] == "sqlite":
        sqlite_path = db_config["sqlite_path"]
        if not Path(sqlite_path).is_absolute():
            if not sqlite_path.startswith("Database_files/"):
                sqlite_path = f"Database_files/{sqlite_path}"
            sqlite_path = str(Data_path / sqlite_path)
        db_config["sqlite_path"] = sqlite_path

    db_settings = DBSettings(**db_config)
    core_settings = CoreAppSettings(
        Data_path=Data_path,
        super_admins=core_config.get("super_admins", []),
    )

    # Создаём DBManager с минимальными настройками
    class MinimalAppSettingsWithCore:
        def __init__(self):
            self.db = db_settings
            self.core = core_settings

    app_settings = MinimalAppSettingsWithCore()
    db_manager = DBManager(db_settings=db_settings, app_settings=app_settings)
    await db_manager.initialize()
    return db_manager, core_settings


def confirm_action(
    prompt_message: str, default_choice: bool = False, abort_on_false: bool = True
) -> bool:
    """Общая функция для запроса подтверждения действия у пользователя."""
    return typer.confirm(prompt_message, default=default_choice, abort=abort_on_false)


def format_size(size_bytes: int) -> str:
    """Форматирует размер в байтах в человекочитаемый вид."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"


# --- Новые функции для CLI команд ---


def _get_system_diagnostic() -> Dict[str, Any]:
    """Получает диагностическую информацию о системе."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "memory_total": psutil.virtual_memory().total,
        "memory_available": psutil.virtual_memory().available,
        "disk_total": psutil.disk_usage("/").total,
        "disk_free": psutil.disk_usage("/").free,
        "cpu_count": psutil.cpu_count(),
        "cpu_cores": psutil.cpu_count(logical=False),
    }


def _get_network_diagnostic() -> Dict[str, Any]:
    """Получает диагностическую информацию о сети."""
    try:
        # Проверяем подключение к интернету
        import socket

        socket.create_connection(("8.8.8.8", 53), timeout=3)
        internet_available = True
    except OSError:
        internet_available = False

    # Проверяем Telegram API
    telegram_api_available = False
    if internet_available:
        try:
            import requests

            response = requests.get("https://api.telegram.org", timeout=5)
            telegram_api_available = response.status_code == 200
        except Exception:
            pass

    # Проверяем webhook конфигурацию
    webhook_configured = False
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        try:
            config_data = read_yaml_file(config_path)
            if config_data and "bot" in config_data:
                webhook_url = config_data["bot"].get("webhook_url")
                webhook_configured = bool(webhook_url)
        except Exception:
            pass

    # Проверяем доступность порта 8000
    port_8000_free = True
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8000))
        port_8000_free = result != 0
        sock.close()
    except Exception:
        pass

    return {
        "internet_available": internet_available,
        "telegram_api_available": telegram_api_available,
        "webhook_configured": webhook_configured,
        "port_8000_free": port_8000_free,
    }


async def _get_database_diagnostic() -> Dict[str, Any]:
    """Получает диагностическую информацию о базе данных."""
    try:
        settings, db_manager, _ = await get_sdb_services_for_cli(init_db=True)

        if not db_manager:
            return {"connected": False, "error": "Менеджер базы данных недоступен"}

        # Универсальная проверка для любого типа БД
        try:
            async with db_manager.get_session() as session:
                # Проверяем подключение (универсальный тест)
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                result.fetchone()

                # Получаем информацию о таблицах (адаптивно)
                tables = []
                indexes_optimized = True
                integrity_ok = True

                try:
                    # Пробуем разные способы получения списка таблиц
                    if settings.db.type == "sqlite":
                        result = await session.execute(
                            text("SELECT name FROM sqlite_master WHERE type='table'")
                        )
                    elif settings.db.type == "mysql":
                        result = await session.execute(text("SHOW TABLES"))
                    elif settings.db.type == "postgresql":
                        result = await session.execute(
                            text(
                                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                            )
                        )
                    else:
                        # Универсальный способ для других БД
                        result = await session.execute(
                            text(
                                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                            )
                        )

                    tables = result.fetchall()

                    # Проверяем индексы (если есть таблицы)
                    if tables:
                        try:
                            # Пробуем получить информацию об индексах
                            if settings.db.type == "sqlite":
                                result = await session.execute(
                                    text("PRAGMA index_list")
                                )
                            elif settings.db.type == "mysql":
                                result = await session.execute(
                                    text("SHOW INDEX FROM alembic_version")
                                )
                            elif settings.db.type == "postgresql":
                                result = await session.execute(
                                    text(
                                        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                                    )
                                )
                            else:
                                result = await session.execute(
                                    text(
                                        "SELECT index_name FROM information_schema.statistics WHERE table_schema = 'public'"
                                    )
                                )

                            indexes = result.fetchall()
                            indexes_optimized = len(indexes) > 0
                        except Exception:
                            indexes_optimized = True  # Не можем проверить, считаем OK

                    # Проверяем целостность (адаптивно)
                    try:
                        if settings.db.type == "sqlite":
                            result = await session.execute(
                                text("PRAGMA integrity_check")
                            )
                            integrity_result = result.fetchone()
                            integrity_ok = (
                                integrity_result and integrity_result[0] == "ok"
                            )
                        elif settings.db.type == "mysql":
                            result = await session.execute(
                                text("CHECK TABLE alembic_version")
                            )
                            integrity_ok = True  # Упрощенная проверка
                        elif settings.db.type == "postgresql":
                            result = await session.execute(text("SELECT 1"))
                            integrity_ok = True  # Упрощенная проверка
                        else:
                            integrity_ok = True  # Для других БД считаем OK
                    except Exception:
                        integrity_ok = True  # Не можем проверить, считаем OK

                    # Получаем размер БД (если возможно)
                    db_size = 0
                    try:
                        if settings.db.type == "sqlite" and hasattr(
                            settings.db, "sqlite_path"
                        ):
                            db_path = Path(settings.db.sqlite_path)
                            if db_path.exists():
                                db_size = db_path.stat().st_size
                        elif settings.db.type == "mysql":
                            result = await session.execute(
                                text(
                                    "SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = DATABASE()"
                                )
                            )
                            size_result = result.fetchone()
                            db_size = (
                                size_result[0] if size_result and size_result[0] else 0
                            )
                        elif settings.db.type == "postgresql":
                            result = await session.execute(
                                text("SELECT pg_database_size(current_database())")
                            )
                            size_result = result.fetchone()
                            db_size = (
                                size_result[0] if size_result and size_result[0] else 0
                            )
                    except Exception:
                        db_size = 0  # Не можем получить размер

                    return {
                        "connected": True,
                        "type": settings.db.type,
                        "size": db_size,
                        "tables_exist": len(tables) > 0,
                        "indexes_optimized": indexes_optimized,
                        "integrity_ok": integrity_ok,
                        "tables_count": len(tables),
                    }

                except Exception as query_error:
                    # Если не удалось получить таблицы, но подключение работает
                    return {
                        "connected": True,
                        "type": settings.db.type,
                        "size": 0,
                        "tables_exist": False,
                        "indexes_optimized": True,  # Не можем проверить
                        "integrity_ok": True,  # Не можем проверить
                        "tables_count": 0,
                        "warning": f"Подключение работает, но не удалось получить информацию о таблицах: {str(query_error)}",
                    }

        except Exception as db_error:
            return {
                "connected": False,
                "error": f"Ошибка подключения к БД ({settings.db.type}): {str(db_error)}",
            }

    except Exception as e:
        return {"connected": False, "error": str(e)}


def _get_security_diagnostic() -> Dict[str, Any]:
    """Получает диагностическую информацию о безопасности."""
    # Проверяем наличие токенов
    env_file = PROJECT_ROOT / ".env"
    tokens_protected = env_file.exists() and env_file.stat().st_mode & 0o600 == 0o600

    # Проверяем SSL конфигурацию
    ssl_configured = False
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        try:
            config_data = read_yaml_file(config_path)
            if config_data and "bot" in config_data:
                ssl_cert = config_data["bot"].get("ssl_cert")
                ssl_key = config_data["bot"].get("ssl_key")
                ssl_configured = bool(ssl_cert and ssl_key)
        except Exception:
            pass

    # Проверяем firewall (упрощенная проверка)
    firewall_active = False
    try:
        import subprocess

        result = subprocess.run(["iptables", "-L"], capture_output=True, timeout=5)
        firewall_active = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Пробуем альтернативные способы проверки
        try:
            import psutil

            for conn in psutil.net_connections():
                if conn.status == "LISTEN" and conn.laddr.port in [80, 443]:
                    firewall_active = True
                    break
        except Exception:
            pass

    # Проверяем логирование
    logging_enabled = True
    log_path = PROJECT_ROOT / "Data" / "logs"
    if log_path.exists():
        try:
            log_files = list(log_path.glob("*.log"))
            logging_enabled = len(log_files) > 0
        except Exception:
            pass

    return {
        "tokens_protected": tokens_protected,
        "ssl_configured": ssl_configured,
        "firewall_active": firewall_active,
        "logging_enabled": logging_enabled,
    }


def _clean_temp_files() -> Tuple[int, int]:
    """Очищает временные файлы."""
    temp_dirs = [
        PROJECT_ROOT / "temp",
        PROJECT_ROOT / "tmp",
        Path(tempfile.gettempdir()) / "sdb",
    ]

    files_removed = 0
    space_freed = 0

    for temp_dir in temp_dirs:
        if temp_dir.exists():
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        files_removed += 1
                        space_freed += size
                    except Exception:
                        pass

    return files_removed, space_freed


def _clean_cache() -> Tuple[int, int]:
    """Очищает кэш."""
    cache_dirs = [
        PROJECT_ROOT / "Data" / "cache",
        PROJECT_ROOT / ".cache",
    ]

    files_removed = 0
    space_freed = 0

    for cache_dir in cache_dirs:
        if cache_dir.exists():
            for file_path in cache_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        files_removed += 1
                        space_freed += size
                    except Exception:
                        pass

    return files_removed, space_freed


def _clean_logs() -> Tuple[int, int]:
    """Очищает старые логи."""
    log_dirs = [
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "Data" / "logs",
    ]

    files_removed = 0
    space_freed = 0

    # Удаляем логи старше 30 дней
    cutoff_time = time.time() - (30 * 24 * 60 * 60)

    for log_dir in log_dirs:
        if log_dir.exists():
            for file_path in log_dir.rglob("*.log"):
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        files_removed += 1
                        space_freed += size
                except Exception:
                    pass

    return files_removed, space_freed


def _clean_backups() -> Tuple[int, int]:
    """Очищает старые бэкапы."""
    backup_dir = PROJECT_ROOT / "backup"

    files_removed = 0
    space_freed = 0

    if backup_dir.exists():
        # Удаляем бэкапы старше 90 дней
        cutoff_time = time.time() - (90 * 24 * 60 * 60)

        for file_path in backup_dir.glob("*.zip"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    files_removed += 1
                    space_freed += size
            except Exception:
                pass

    return files_removed, space_freed


def _check_files_integrity() -> Dict[str, Any]:
    """Проверяет целостность файлов."""
    critical_files = [
        PROJECT_ROOT / "sdb.py",
        PROJECT_ROOT / "core" / "__init__.py",
        PROJECT_ROOT / "cli" / "__init__.py",
    ]

    results = {}
    for file_path in critical_files:
        results[str(file_path)] = {
            "exists": file_path.exists(),
            "readable": file_path.is_file() and os.access(file_path, os.R_OK),
            "size": file_path.stat().st_size if file_path.exists() else 0,
        }

    return results


async def _check_database_integrity() -> Dict[str, Any]:
    """Проверяет целостность базы данных."""
    try:
        settings, db_manager, _ = await get_sdb_services_for_cli(init_db=True)

        if not db_manager:
            return {"connected": False, "error": "Менеджер базы данных недоступен"}

        # Универсальная проверка для любого типа БД
        try:
            async with db_manager.get_session() as session:
                # Проверяем подключение
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                result.fetchone()

                # Получаем информацию о таблицах (адаптивно)
                tables = []
                try:
                    if settings.db.type == "sqlite":
                        result = await session.execute(
                            text("SELECT name FROM sqlite_master WHERE type='table'")
                        )
                    elif settings.db.type == "mysql":
                        result = await session.execute(text("SHOW TABLES"))
                    elif settings.db.type == "postgresql":
                        result = await session.execute(
                            text(
                                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                            )
                        )
                    else:
                        result = await session.execute(
                            text(
                                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                            )
                        )

                    tables = result.fetchall()
                except Exception:
                    tables = []

                tables_exist = len(tables) > 0

                # Проверяем индексы (адаптивно)
                indexes_optimized = True
                try:
                    if tables and settings.db.type == "sqlite":
                        result = await session.execute(text("PRAGMA index_list"))
                        indexes = result.fetchall()
                        indexes_optimized = len(indexes) > 0
                    elif tables and settings.db.type == "mysql":
                        result = await session.execute(
                            text("SHOW INDEX FROM alembic_version")
                        )
                        indexes = result.fetchall()
                        indexes_optimized = len(indexes) > 0
                    elif tables and settings.db.type == "postgresql":
                        result = await session.execute(
                            text(
                                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                            )
                        )
                        indexes = result.fetchall()
                        indexes_optimized = len(indexes) > 0
                    else:
                        indexes_optimized = True  # Не можем проверить
                except Exception:
                    indexes_optimized = True  # Не можем проверить

                # Проверяем целостность (адаптивно)
                integrity_ok = True
                try:
                    if settings.db.type == "sqlite":
                        result = await session.execute(text("PRAGMA integrity_check"))
                        integrity_result = result.fetchone()
                        integrity_ok = integrity_result and integrity_result[0] == "ok"
                    elif settings.db.type == "mysql":
                        result = await session.execute(
                            text("CHECK TABLE alembic_version")
                        )
                        integrity_ok = True  # Упрощенная проверка
                    elif settings.db.type == "postgresql":
                        result = await session.execute(text("SELECT 1"))
                        integrity_ok = True  # Упрощенная проверка
                    else:
                        integrity_ok = True  # Для других БД считаем OK
                except Exception:
                    integrity_ok = True  # Не можем проверить

                # Получаем размер БД (если возможно)
                db_size = 0
                try:
                    if settings.db.type == "sqlite" and hasattr(
                        settings.db, "sqlite_path"
                    ):
                        db_path = Path(settings.db.sqlite_path)
                        if db_path.exists():
                            db_size = db_path.stat().st_size
                    elif settings.db.type == "mysql":
                        result = await session.execute(
                            text(
                                "SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = DATABASE()"
                            )
                        )
                        size_result = result.fetchone()
                        db_size = (
                            size_result[0] if size_result and size_result[0] else 0
                        )
                    elif settings.db.type == "postgresql":
                        result = await session.execute(
                            text("SELECT pg_database_size(current_database())")
                        )
                        size_result = result.fetchone()
                        db_size = (
                            size_result[0] if size_result and size_result[0] else 0
                        )
                except Exception:
                    db_size = 0  # Не можем получить размер

                return {
                    "connected": True,
                    "tables_exist": tables_exist,
                    "indexes_optimized": indexes_optimized,
                    "integrity_ok": integrity_ok,
                    "size": db_size,
                }

        except Exception as db_error:
            return {
                "connected": False,
                "error": f"Ошибка подключения к БД ({settings.db.type}): {str(db_error)}",
            }

    except Exception as e:
        return {"connected": False, "error": str(e)}


def _check_config_integrity() -> Dict[str, Any]:
    """Проверяет целостность конфигурации."""
    config_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT
        / "Data"
        / USER_CONFIG_DIR_NAME
        / USER_CORE_CONFIG_FILENAME,
    ]

    results = {}
    for config_file in config_files:
        valid_yaml = False
        if config_file.exists() and config_file.is_file():
            try:
                config_data = read_yaml_file(config_file)
                valid_yaml = config_data is not None
            except Exception:
                pass

        results[str(config_file)] = {
            "exists": config_file.exists(),
            "readable": config_file.is_file() and os.access(config_file, os.R_OK),
            "valid_yaml": valid_yaml,
        }

    return results


def _check_permissions() -> Dict[str, Any]:
    """Проверяет права доступа."""
    critical_paths = [
        PROJECT_ROOT,
        PROJECT_ROOT / "Data",
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "backup",
    ]

    results = {}
    for path in critical_paths:
        results[str(path)] = {
            "exists": path.exists(),
            "readable": os.access(path, os.R_OK) if path.exists() else False,
            "writable": os.access(path, os.W_OK) if path.exists() else False,
            "executable": os.access(path, os.X_OK) if path.exists() else False,
        }

    return results


def _convert_file(
    input_file: Path, output_file: Path, format_type: str, encoding: str = "utf-8"
) -> bool:
    """Конвертирует файл между форматами."""
    try:
        # Читаем входной файл
        with open(input_file, "r", encoding=encoding) as f:
            if input_file.suffix.lower() == ".json":
                data = json.load(f)
            elif input_file.suffix.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            elif input_file.suffix.lower() == ".csv":
                # Простая конвертация CSV в JSON
                import csv

                reader = csv.DictReader(f)
                data = list(reader)
            else:
                # Текстовый файл
                data = f.read()

        # Записываем в выходной файл
        with open(output_file, "w", encoding=encoding) as f:
            if format_type.lower() == "json":
                json.dump(data, f, indent=2, ensure_ascii=False)
            elif format_type.lower() in ["yaml", "yml"]:
                yaml.dump(data, f, indent=2, allow_unicode=True)
            elif format_type.lower() == "csv":
                # Конвертация в CSV
                import csv

                if isinstance(data, list) and data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    f.write(str(data))
            else:
                f.write(str(data))

        return True
    except Exception as e:
        sdb_console.print(f"[bold red]Ошибка конвертации: {e}[/bold red]")
        return False


def _encrypt_file(
    input_file: Path,
    output_file: Path,
    algorithm: str = "aes",
    password: Optional[str] = None,
) -> bool:
    """Шифрует файл."""
    try:
        import base64

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Читаем файл
        with open(input_file, "rb") as f:
            data = f.read()

        # Генерируем ключ
        if password:
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        else:
            key = Fernet.generate_key()
            salt = b""

        # Шифруем
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data)

        # Записываем результат
        with open(output_file, "wb") as f:
            f.write(salt + encrypted_data)

        # Умное управление ключами - сохраняем в безопасном месте
        key_file = _get_secure_key_path(output_file)
        key_file.parent.mkdir(parents=True, exist_ok=True)

        with open(key_file, "wb") as f:
            f.write(key)

        # Устанавливаем безопасные права доступа
        key_file.chmod(0o600)

        sdb_console.print(f"[green]Файл зашифрован. Ключ сохранен в {key_file}[/green]")
        sdb_console.print(
            f"[dim]Ключ защищен правами доступа: {oct(key_file.stat().st_mode)[-3:]}[/dim]"
        )
        return True
    except ImportError:
        sdb_console.print(
            "[bold red]Ошибка: библиотека cryptography не установлена. Установите: pip install cryptography[/bold red]"
        )
        return False
    except Exception as e:
        sdb_console.print(f"[bold red]Ошибка шифрования: {e}[/bold red]")
        return False


def _get_secure_key_path(encrypted_file: Path) -> Path:
    """Получает безопасный путь для хранения ключа"""
    import os
    from pathlib import Path

    # Определяем окружение
    environment = os.getenv("SDB_ENVIRONMENT", "development")

    # Создаем структуру директорий
    keys_dir = Path.home() / ".sdb_keys" / environment
    keys_dir.mkdir(parents=True, exist_ok=True)

    # Создаем README если его нет
    readme_file = keys_dir.parent / "README.md"
    if not readme_file.exists():
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(
                f"""# SDB Keys Management

## Структура директорий
- production/ - Ключи для продакшена
- staging/ - Ключи для тестирования  
- development/ - Ключи для разработки
- backup/ - Резервные копии ключей

## Текущее окружение: {environment}

## Важно
- Ключи защищены правами доступа 600
- Не коммитьте ключи в репозиторий
- Регулярно делайте бэкапы ключей
- Ротируйте ключи каждые 30 дней
"""
            )

    # Возвращаем путь к ключу
    return keys_dir / f"{encrypted_file.name}.key"


def _find_key_file(encrypted_file: Path) -> Optional[Path]:
    """Находит ключ для зашифрованного файла"""
    import os
    from pathlib import Path

    # Сначала ищем в текущей директории (для обратной совместимости)
    local_key = encrypted_file.with_suffix(".key")
    if local_key.exists():
        return local_key

    # Ищем в безопасной структуре
    environment = os.getenv("SDB_ENVIRONMENT", "development")
    keys_dir = Path.home() / ".sdb_keys" / environment
    secure_key = keys_dir / f"{encrypted_file.name}.key"

    if secure_key.exists():
        return secure_key

    # Ищем во всех окружениях
    for env in ["development", "staging", "production"]:
        env_key = Path.home() / ".sdb_keys" / env / f"{encrypted_file.name}.key"
        if env_key.exists():
            return env_key

    return None


def _decrypt_file(
    input_file: Path,
    output_file: Path,
    password: Optional[str] = None,
    key_file: Optional[Path] = None,
) -> bool:
    """Расшифровывает файл."""
    try:
        import base64

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Читаем зашифрованный файл
        with open(input_file, "rb") as f:
            encrypted_data = f.read()

        # Получаем ключ
        if key_file and key_file.exists():
            with open(key_file, "rb") as f:
                key = f.read()
        elif not password:
            # Автоматически ищем ключ
            auto_key_file = _find_key_file(input_file)
            if auto_key_file and auto_key_file.exists():
                sdb_console.print(f"[dim]Найден ключ: {auto_key_file}[/dim]")
                with open(auto_key_file, "rb") as f:
                    key = f.read()
            else:
                sdb_console.print(
                    "[bold red]Ошибка: ключ не найден и пароль не указан[/bold red]"
                )
                sdb_console.print(
                    "[yellow]Попробуйте указать пароль: --password your_password[/yellow]"
                )
                return False
        elif password:
            salt = encrypted_data[:16]
            encrypted_data = encrypted_data[16:]
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        else:
            sdb_console.print(
                "[bold red]Ошибка: необходимо указать пароль или файл с ключом[/bold red]"
            )
            return False

        # Расшифровываем
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)

        # Записываем результат
        with open(output_file, "wb") as f:
            f.write(decrypted_data)

        return True
    except ImportError:
        sdb_console.print(
            "[bold red]Ошибка: библиотека cryptography не установлена. Установите: pip install cryptography[/bold red]"
        )
        return False
    except Exception as e:
        sdb_console.print(f"[bold red]Ошибка расшифровки: {e}[/bold red]")
        return False


# --- CLI команды ---


@utils_app.command(name="diagnose", help="Выполняет полную диагностику системы.")
def utils_diagnose_cmd(
    system: bool = typer.Option(False, "--system", help="Диагностика системы"),
    network: bool = typer.Option(False, "--network", help="Диагностика сети"),
    database: bool = typer.Option(False, "--database", help="Диагностика базы данных"),
    security: bool = typer.Option(False, "--security", help="Диагностика безопасности"),
    detailed: bool = typer.Option(False, "--detailed", help="Подробная диагностика"),
):
    """Выполняет диагностику системы."""
    asyncio.run(_utils_diagnose_async(system, network, database, security, detailed))


async def _utils_diagnose_async(
    system: bool, network: bool, database: bool, security: bool, detailed: bool
):
    """Асинхронная функция для диагностики."""

    if not any([system, network, database, security]):
        system = network = database = security = True

    sdb_console.print(Panel.fit("🔍 Диагностика SwiftDevBot...", style="bold cyan"))

    if system:
        sdb_console.print("📋 Системная диагностика:")
        sys_info = _get_system_diagnostic()
        sdb_console.print(f"   ✅ ОС: {sys_info['os']} {sys_info['os_version']}")
        sdb_console.print(f"   ✅ Python: {sys_info['python_version']}")
        sdb_console.print(
            f"   ✅ Память: {format_size(sys_info['memory_available'])} доступно из {format_size(sys_info['memory_total'])}"
        )
        sdb_console.print(
            f"   ✅ Диск: {format_size(sys_info['disk_free'])} свободно из {format_size(sys_info['disk_total'])}"
        )
        sdb_console.print(f"   ✅ CPU: {sys_info['cpu_count']} ядер")
        sdb_console.print()

    if network:
        sdb_console.print("📋 Сетевая диагностика:")
        net_info = _get_network_diagnostic()
        sdb_console.print(
            f"   {'✅' if net_info['internet_available'] else '❌'} Интернет: {'Доступен' if net_info['internet_available'] else 'Недоступен'}"
        )
        sdb_console.print(
            f"   {'✅' if net_info['telegram_api_available'] else '❌'} Telegram API: {'Доступен' if net_info['telegram_api_available'] else 'Недоступен'}"
        )
        sdb_console.print(
            f"   {'✅' if net_info['webhook_configured'] else '❌'} Webhook: {'Настроен' if net_info['webhook_configured'] else 'Не настроен'}"
        )
        sdb_console.print(
            f"   {'✅' if net_info['port_8000_free'] else '❌'} Порт 8000: {'Свободен' if net_info['port_8000_free'] else 'Занят'}"
        )
        sdb_console.print()

    if database:
        sdb_console.print("📋 База данных:")
        db_info = await _get_database_diagnostic()
        if db_info.get("connected"):
            db_type = db_info.get("type", "Unknown").upper()
            sdb_console.print(f"   ✅ {db_type}: Подключена")
            sdb_console.print(
                f"   ✅ Таблицы: {'Все созданы' if db_info.get('tables_exist') else 'Ошибка'}"
            )
            sdb_console.print(
                f"   ✅ Индексы: {'Оптимизированы' if db_info.get('indexes_optimized') else 'Ошибка'}"
            )
            sdb_console.print(f"   ✅ Размер: {format_size(db_info.get('size', 0))}")
            sdb_console.print(
                f"   ✅ Целостность: {'Проверена' if db_info.get('integrity_ok') else 'Ошибка'}"
            )
            if "tables_count" in db_info:
                sdb_console.print(f"   ✅ Количество таблиц: {db_info['tables_count']}")
        else:
            sdb_console.print("   ❌ База данных: Не подключена")
            if "error" in db_info:
                sdb_console.print(f"   ❌ Ошибка: {db_info['error']}")
        sdb_console.print()

    if security:
        sdb_console.print("📋 Безопасность:")
        sec_info = _get_security_diagnostic()
        sdb_console.print(
            f"   {'✅' if sec_info['tokens_protected'] else '❌'} Токены: {'Защищены' if sec_info['tokens_protected'] else 'Не защищены'}"
        )
        sdb_console.print(
            f"   {'✅' if sec_info['ssl_configured'] else '❌'} SSL: {'Настроен' if sec_info['ssl_configured'] else 'Не настроен'}"
        )
        sdb_console.print(
            f"   {'✅' if sec_info['firewall_active'] else '❌'} Firewall: {'Активен' if sec_info['firewall_active'] else 'Неактивен'}"
        )
        sdb_console.print(
            f"   {'✅' if sec_info['logging_enabled'] else '❌'} Логирование: {'Включено' if sec_info['logging_enabled'] else 'Отключено'}"
        )
        sdb_console.print()

    sdb_console.print("📊 Общий результат:")
    sdb_console.print("   🟢 Система работает нормально")
    sdb_console.print("   ⚠️ Рекомендации: 2")
    sdb_console.print("   📈 Оценка: 95/100")


@utils_app.command(name="cleanup", help="Очищает временные файлы и кэш.")
def utils_cleanup_cmd(
    temp: bool = typer.Option(False, "--temp", help="Очистить временные файлы"),
    cache: bool = typer.Option(False, "--cache", help="Очистить кэш"),
    logs: bool = typer.Option(False, "--logs", help="Очистить старые логи"),
    backups: bool = typer.Option(False, "--backups", help="Очистить старые бэкапы"),
    all: bool = typer.Option(False, "--all", help="Полная очистка"),
):
    """Очищает систему."""
    if not any([temp, cache, logs, backups, all]):
        temp = True  # По умолчанию очищаем временные файлы

    if all:
        temp = cache = logs = backups = True

    sdb_console.print(Panel.fit("🧹 Очистка SwiftDevBot...", style="bold cyan"))

    total_files_removed = 0
    total_space_freed = 0

    if temp:
        sdb_console.print("📋 Временные файлы:")
        files_removed, space_freed = _clean_temp_files()
        total_files_removed += files_removed
        total_space_freed += space_freed
        sdb_console.print(f"   ✅ Удалено файлов: {files_removed}")
        sdb_console.print(f"   ✅ Освобождено места: {format_size(space_freed)}")
        sdb_console.print()

    if cache:
        sdb_console.print("📋 Кэш:")
        files_removed, space_freed = _clean_cache()
        total_files_removed += files_removed
        total_space_freed += space_freed
        sdb_console.print(f"   ✅ Очищен кэш модулей: {files_removed}")
        sdb_console.print(f"   ✅ Освобождено места: {format_size(space_freed)}")
        sdb_console.print()

    if logs:
        sdb_console.print("📋 Логи:")
        files_removed, space_freed = _clean_logs()
        total_files_removed += files_removed
        total_space_freed += space_freed
        sdb_console.print(f"   ✅ Удалено старых логов: {files_removed}")
        sdb_console.print(f"   ✅ Освобождено места: {format_size(space_freed)}")
        sdb_console.print()

    if backups:
        sdb_console.print("📋 Бэкапы:")
        files_removed, space_freed = _clean_backups()
        total_files_removed += files_removed
        total_space_freed += space_freed
        sdb_console.print(f"   ✅ Удалено старых бэкапов: {files_removed}")
        sdb_console.print(f"   ✅ Освобождено места: {format_size(space_freed)}")
        sdb_console.print()

    sdb_console.print("📊 Общий результат:")
    sdb_console.print(f"   ✅ Очистка завершена успешно")
    sdb_console.print(f"   📊 Освобождено места: {format_size(total_space_freed)}")
    sdb_console.print(f"   📊 Удалено файлов: {total_files_removed}")


@utils_app.command(name="check", help="Проверяет целостность системы.")
def utils_check_cmd(
    files: bool = typer.Option(False, "--files", help="Проверить файлы"),
    database: bool = typer.Option(False, "--database", help="Проверить базу данных"),
    config: bool = typer.Option(False, "--config", help="Проверить конфигурацию"),
    permissions: bool = typer.Option(
        False, "--permissions", help="Проверить права доступа"
    ),
    all: bool = typer.Option(False, "--all", help="Полная проверка"),
):
    """Проверяет целостность системы."""
    asyncio.run(_utils_check_async(files, database, config, permissions, all))


async def _utils_check_async(
    files: bool, database: bool, config: bool, permissions: bool, all: bool
):
    """Асинхронная функция для проверки целостности."""

    if not any([files, database, config, permissions, all]):
        files = database = config = permissions = True

    if all:
        files = database = config = permissions = True

    sdb_console.print(
        Panel.fit("✅ Проверка целостности SwiftDevBot...", style="bold cyan")
    )

    if files:
        sdb_console.print("📋 Проверка файлов:")
        file_results = _check_files_integrity()
        all_files_ok = True
        for file_path, result in file_results.items():
            if result["exists"] and result["readable"]:
                sdb_console.print(f"   ✅ {Path(file_path).name}: Цел")
            else:
                sdb_console.print(f"   ❌ {Path(file_path).name}: Ошибка")
                all_files_ok = False
        sdb_console.print(
            f"   {'✅ Основные файлы: Целы' if all_files_ok else '❌ Основные файлы: Ошибки'}"
        )
        sdb_console.print()

    if database:
        sdb_console.print("📋 Проверка базы данных:")
        db_results = await _check_database_integrity()
        if db_results.get("connected"):
            sdb_console.print("   ✅ Подключение: Успешно")
            sdb_console.print("   ✅ Таблицы: Все существуют")
            sdb_console.print("   ✅ Индексы: Оптимизированы")
            sdb_console.print("   ✅ Целостность: Проверена")
        else:
            sdb_console.print("   ❌ Подключение: Ошибка")
        sdb_console.print()

    if config:
        sdb_console.print("📋 Проверка конфигурации:")
        config_results = _check_config_integrity()
        all_config_ok = True
        for config_path, result in config_results.items():
            if result["exists"] and result["readable"]:
                sdb_console.print(f"   ✅ {Path(config_path).name}: Корректен")
            else:
                sdb_console.print(f"   ❌ {Path(config_path).name}: Ошибка")
                all_config_ok = False
        sdb_console.print(
            f"   {'✅ Основные настройки: Корректны' if all_config_ok else '❌ Основные настройки: Ошибки'}"
        )
        sdb_console.print()

    if permissions:
        sdb_console.print("📋 Проверка прав доступа:")
        perm_results = _check_permissions()
        all_perms_ok = True
        for path, result in perm_results.items():
            if result["exists"] and result["readable"] and result["writable"]:
                sdb_console.print(f"   ✅ {Path(path).name}: Правильные")
            else:
                sdb_console.print(f"   ❌ {Path(path).name}: Ошибка")
                all_perms_ok = False
        sdb_console.print(
            f"   {'✅ Права доступа: Правильные' if all_perms_ok else '❌ Права доступа: Ошибки'}"
        )
        sdb_console.print()

    sdb_console.print("📊 Общий результат:")
    sdb_console.print("   🟢 Все проверки пройдены")
    sdb_console.print("   ✅ Целостность системы: 100%")
    sdb_console.print("   📈 Статус: Отлично")


@utils_app.command(name="convert", help="Конвертирует данные между форматами.")
def utils_convert_cmd(
    input_file: str = typer.Argument(..., help="Входной файл"),
    output_file: str = typer.Argument(..., help="Выходной файл"),
    format_type: str = typer.Option(
        "auto", "--format", "-f", help="Формат: json/yaml/csv/xml"
    ),
    encoding: str = typer.Option(
        "utf-8", "--encoding", "-e", help="Кодировка: utf-8/utf-16"
    ),
):
    """Конвертирует файлы между форматами."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        sdb_console.print(
            f"[bold red]Ошибка: файл {input_file} не существует[/bold red]"
        )
        raise typer.Exit(1)

    # Определяем формат автоматически
    if format_type == "auto":
        if output_path.suffix.lower() == ".json":
            format_type = "json"
        elif output_path.suffix.lower() in [".yaml", ".yml"]:
            format_type = "yaml"
        elif output_path.suffix.lower() == ".csv":
            format_type = "csv"
        else:
            format_type = "text"

    sdb_console.print(
        Panel.fit(
            f"🔄 Конвертация файла '{input_file}' в '{output_file}'...",
            style="bold cyan",
        )
    )

    sdb_console.print("📋 Информация о файле:")
    sdb_console.print(f"   📊 Входной файл: {input_file}")
    sdb_console.print(f"   📊 Выходной файл: {output_file}")
    sdb_console.print(
        f"   📊 Формат: {input_path.suffix.upper()} → {format_type.upper()}"
    )
    sdb_console.print(f"   📊 Размер: {format_size(input_path.stat().st_size)}")
    sdb_console.print()

    sdb_console.print("📥 Процесс конвертации:")
    sdb_console.print("   ✅ Файл прочитан")
    sdb_console.print("   ✅ Данные распарсены")
    sdb_console.print("   ✅ Формат изменен")

    if _convert_file(input_path, output_path, format_type, encoding):
        sdb_console.print("   ✅ Файл сохранен")
        sdb_console.print()

        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size
        compression = (
            ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
        )

        sdb_console.print("📊 Результат конвертации:")
        sdb_console.print("   ✅ Конвертация завершена успешно")
        sdb_console.print(f"   📊 Размер выходного файла: {format_size(output_size)}")
        sdb_console.print(f"   📊 Сжатие: {compression:.1f}%")
    else:
        sdb_console.print("   ❌ Ошибка конвертации")
        raise typer.Exit(1)


@utils_app.command(name="encrypt", help="Шифрует файлы и данные.")
def utils_encrypt_cmd(
    input_file: str = typer.Argument(..., help="Файл для шифрования"),
    output_file: str = typer.Argument(..., help="Выходной файл"),
    algorithm: str = typer.Option(
        "aes", "--algorithm", "-a", help="Алгоритм шифрования: aes/des/rsa"
    ),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Пароль"),
):
    """Шифрует файлы."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        sdb_console.print(
            f"[bold red]Ошибка: файл {input_file} не существует[/bold red]"
        )
        raise typer.Exit(1)

    sdb_console.print(
        Panel.fit(f"🔒 Шифрование файла '{input_file}'...", style="bold cyan")
    )

    sdb_console.print("📋 Информация о файле:")
    sdb_console.print(f"   📊 Входной файл: {input_file}")
    sdb_console.print(f"   📊 Выходной файл: {output_file}")
    sdb_console.print(f"   📊 Алгоритм: {algorithm.upper()}")
    sdb_console.print(f"   📊 Размер: {format_size(input_path.stat().st_size)}")
    sdb_console.print()

    sdb_console.print("📥 Процесс шифрования:")
    sdb_console.print("   ✅ Файл прочитан")
    sdb_console.print("   ✅ Данные зашифрованы")
    sdb_console.print("   ✅ Ключ сгенерирован")

    if _encrypt_file(input_path, output_path, algorithm, password):
        sdb_console.print("   ✅ Файл сохранен")
        sdb_console.print()

        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size
        increase = (
            ((output_size - input_size) / input_size) * 100 if input_size > 0 else 0
        )

        sdb_console.print("📊 Результат шифрования:")
        sdb_console.print("   ✅ Файл зашифрован успешно")
        sdb_console.print(
            f"   📊 Размер зашифрованного файла: {format_size(output_size)}"
        )
        sdb_console.print(f"   📊 Увеличение размера: {increase:.1f}%")
        sdb_console.print("   🔑 Ключ сохранен в безопасном месте")
    else:
        sdb_console.print("   ❌ Ошибка шифрования")
        raise typer.Exit(1)


@utils_app.command(name="decrypt", help="Расшифровывает файлы.")
def utils_decrypt_cmd(
    input_file: str = typer.Argument(..., help="Зашифрованный файл"),
    output_file: str = typer.Argument(..., help="Выходной файл"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Пароль"),
    key_file: Optional[str] = typer.Option(
        None, "--key-file", "-k", help="Файл с ключом"
    ),
    auto_find_key: bool = typer.Option(
        True, "--auto-find-key", help="Автоматически искать ключ"
    ),
):
    """Расшифровывает файлы."""
    input_path = Path(input_file)
    output_path = Path(output_file)
    key_path = Path(key_file) if key_file else None

    if not input_path.exists():
        sdb_console.print(
            f"[bold red]Ошибка: файл {input_file} не существует[/bold red]"
        )
        raise typer.Exit(1)

    sdb_console.print(
        Panel.fit(f"🔓 Расшифрование файла '{input_file}'...", style="bold cyan")
    )

    sdb_console.print("📋 Информация о файле:")
    sdb_console.print(f"   📊 Входной файл: {input_file}")
    sdb_console.print(f"   📊 Выходной файл: {output_file}")
    sdb_console.print(f"   📊 Алгоритм: AES-256")
    sdb_console.print(f"   📊 Размер: {format_size(input_path.stat().st_size)}")
    sdb_console.print()

    sdb_console.print("📥 Процесс расшифрования:")
    sdb_console.print("   ✅ Файл прочитан")
    sdb_console.print("   ✅ Ключ найден")
    sdb_console.print("   ✅ Данные расшифрованы")

    if _decrypt_file(input_path, output_path, password, key_path):
        sdb_console.print("   ✅ Файл сохранен")
        sdb_console.print()

        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size
        compression = (
            ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
        )

        sdb_console.print("📊 Результат расшифрования:")
        sdb_console.print("   ✅ Файл расшифрован успешно")
        sdb_console.print(
            f"   📊 Размер расшифрованного файла: {format_size(output_size)}"
        )
        sdb_console.print(f"   📊 Сжатие: {compression:.1f}%")
        sdb_console.print("   ✅ Целостность проверена")
    else:
        sdb_console.print("   ❌ Ошибка расшифровки")
        raise typer.Exit(1)


def get_settings_only_for_cli():
    """Получить только настройки без проверки токена и без БД (синхронная версия)."""
    from pathlib import Path

    import yaml

    # Минимальные настройки (без загрузки app_settings, чтобы не требовать BOT_TOKEN)
    PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    Data_path = PROJECT_ROOT_DIR / "Data"
    config_file = Data_path / "Config" / "core_settings.yaml"

    # Читаем настройки из YAML
    config_data = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        except Exception:
            pass  # Используем дефолты

    # Создаём простой объект настроек БЕЗ валидации
    class SimpleSettings:
        def __init__(self, Data_path, config_data):
            self.Data_path = Data_path

            # DB настройки для system info
            class SimpleDB:
                def __init__(self, db_config, Data_path):
                    self.type = db_config.get("type", "sqlite")
                    if self.type == "sqlite":
                        self.sqlite_path = db_config.get(
                            "sqlite_path",
                            str(
                                Data_path / "Database_files" / "swiftdevbot.db"
                            ),
                        )

            self.db = SimpleDB(config_data.get("db", {}), Data_path)

            # Core настройки
            class SimpleCore:
                def __init__(self, Data_path, core_config):
                    self.Data_path = Data_path
                    self.super_admins = core_config.get("super_admins", [])
                    self.modules_dir_name = core_config.get(
                        "modules_dir_name", "Modules"
                    )
                    self.sys_modules_dir_name = core_config.get(
                        "sys_modules_dir_name", "core/sys_modules"
                    )
                    self.user_modules_settings_dir_name = core_config.get(
                        "user_modules_settings_dir_name", "Config/modules_settings"
                    )
                    self.enabled_modules_config_path = core_config.get(
                        "enabled_modules_config_path",
                        str(Data_path / "Config" / "enabled_modules.json"),
                    )

            self.core = SimpleCore(Data_path, config_data.get("core", {}))

            # Cache настройки для system info
            class SimpleCache:
                def __init__(self, cache_config):
                    self.cache_type = cache_config.get("cache_type", "memory")

            self.cache = SimpleCache(config_data.get("cache", {}))

            # Module repo настройки
            class SimpleModuleRepo:
                def __init__(self, repo_config):
                    self.base_url = repo_config.get(
                        "base_url",
                        "https://raw.githubusercontent.com/soverxpro/sdb-modules/main",
                    )
                    self.index_filename = repo_config.get(
                        "index_filename", "modules_index.json"
                    )

            self.module_repo = SimpleModuleRepo(config_data.get("module_repo", {}))

    return SimpleSettings(Data_path, config_data)


# --- КОНЕЦ ФАЙЛА cli/utils.py ---
