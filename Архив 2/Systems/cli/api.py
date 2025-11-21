# cli/api.py
import asyncio
import hashlib
import json
import secrets
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
api_app = typer.Typer(name="api", help="🌐 Управление API")

# Константы для API
API_DIR = Path("Data/api")
API_CONFIG_FILE = API_DIR / "api_config.json"
API_KEYS_FILE = API_DIR / "api_keys.json"
API_RATE_LIMITS_FILE = API_DIR / "rate_limits.json"
API_DOCS_DIR = API_DIR / "docs"


@dataclass
class APIEndpoint:
    path: str
    method: str
    description: str
    status: str
    rate_limit: Optional[int] = None
    auth_required: bool = True


# Определяем стандартные API endpoints
DEFAULT_ENDPOINTS = [
    APIEndpoint(
        "/api/v1/health", "GET", "Проверка здоровья системы", "active", 100, False
    ),
    APIEndpoint("/api/v1/status", "GET", "Статус системы", "active", 60),
    APIEndpoint("/api/v1/users", "GET", "Список пользователей", "active", 30),
    APIEndpoint("/api/v1/users", "POST", "Создание пользователя", "active", 10),
    APIEndpoint("/api/v1/users/{id}", "GET", "Получение пользователя", "active", 60),
    APIEndpoint("/api/v1/users/{id}", "PUT", "Обновление пользователя", "active", 30),
    APIEndpoint("/api/v1/users/{id}", "DELETE", "Удаление пользователя", "active", 10),
    APIEndpoint("/api/v1/modules", "GET", "Список модулей", "active", 60),
    APIEndpoint("/api/v1/modules", "POST", "Установка модуля", "active", 10),
    APIEndpoint("/api/v1/modules/{id}", "GET", "Информация о модуле", "active", 60),
    APIEndpoint("/api/v1/modules/{id}", "DELETE", "Удаление модуля", "active", 10),
    APIEndpoint("/api/v1/system", "GET", "Системная информация", "active", 30),
    APIEndpoint("/api/v1/logs", "GET", "Логи системы", "active", 20),
    APIEndpoint("/api/v1/backup", "POST", "Создание резервной копии", "active", 5),
    APIEndpoint(
        "/api/v1/restore", "POST", "Восстановление из резервной копии", "active", 5
    ),
]


def _ensure_api_directory():
    """Создать директорию для API если её нет"""
    API_DIR.mkdir(parents=True, exist_ok=True)
    API_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if not API_CONFIG_FILE.exists():
        default_config = {
            "server": {
                "host": "localhost",
                "port": 8000,
                "debug": False,
                "ssl_enabled": False,
            },
            "endpoints": {
                f"{ep.method}:{ep.path}": {
                    "path": ep.path,
                    "method": ep.method,
                    "description": ep.description,
                    "status": ep.status,
                    "rate_limit": ep.rate_limit,
                    "auth_required": ep.auth_required,
                }
                for ep in DEFAULT_ENDPOINTS
            },
            "rate_limits": {"default": 60, "authenticated": 120, "admin": 300},
        }
        with open(API_CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)

    if not API_KEYS_FILE.exists():
        with open(API_KEYS_FILE, "w") as f:
            json.dump({"keys": {}}, f, indent=2)

    if not API_RATE_LIMITS_FILE.exists():
        with open(API_RATE_LIMITS_FILE, "w") as f:
            json.dump({"limits": {}, "usage": {}}, f, indent=2)


def _load_api_config() -> Dict[str, Any]:
    """Загрузить конфигурацию API"""
    _ensure_api_directory()
    try:
        with open(API_CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"server": {}, "endpoints": {}, "rate_limits": {}}


def _save_api_config(config: Dict[str, Any]):
    """Сохранить конфигурацию API"""
    _ensure_api_directory()
    with open(API_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _load_api_keys() -> Dict[str, Any]:
    """Загрузить API ключи"""
    _ensure_api_directory()
    try:
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"keys": {}}


def _save_api_keys(keys_data: Dict[str, Any]):
    """Сохранить API ключи"""
    _ensure_api_directory()
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys_data, f, indent=2)


def _load_rate_limits() -> Dict[str, Any]:
    """Загрузить лимиты запросов"""
    _ensure_api_directory()
    try:
        with open(API_RATE_LIMITS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"limits": {}, "usage": {}}


def _save_rate_limits(rate_data: Dict[str, Any]):
    """Сохранить лимиты запросов"""
    _ensure_api_directory()
    with open(API_RATE_LIMITS_FILE, "w") as f:
        json.dump(rate_data, f, indent=2)


def _generate_api_key() -> str:
    """Генерировать API ключ"""
    return f"sk-{secrets.token_urlsafe(32)}"


def _check_api_server_status() -> Dict[str, Any]:
    """Проверить статус API сервера"""
    config = _load_api_config()
    server_config = config.get("server", {})

    host = server_config.get("host", "localhost")
    port = server_config.get("port", 8000)

    status_info = {
        "host": host,
        "port": port,
        "ssl_enabled": server_config.get("ssl_enabled", False),
        "debug": server_config.get("debug", False),
        "status": "unknown",
        "uptime": None,
        "memory_usage": None,
        "cpu_usage": None,
    }

    try:
        # Проверяем, слушает ли порт
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            status_info["status"] = "running"

            # Пытаемся получить информацию о процессе
            try:
                for proc in psutil.process_iter(
                    ["pid", "name", "cmdline", "create_time"]
                ):
                    try:
                        cmdline = proc.info["cmdline"]
                        if cmdline and any(
                            "uvicorn" in cmd or "gunicorn" in cmd for cmd in cmdline
                        ):
                            status_info["uptime"] = (
                                datetime.now().timestamp() - proc.info["create_time"]
                            )
                            status_info["memory_usage"] = (
                                proc.memory_info().rss / 1024 / 1024
                            )  # MB
                            status_info["cpu_usage"] = proc.cpu_percent()
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception:
                pass
        else:
            status_info["status"] = "stopped"

    except Exception as e:
        status_info["status"] = "error"
        status_info["error"] = str(e)

    return status_info


@api_app.command(name="status", help="Показать статус API.")
def api_status_cmd(
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Подробная информация"
    ),
    format: str = typer.Option(
        "table", "--format", "-f", help="Формат вывода: table, json"
    ),
):
    """Показать статус API"""
    try:
        asyncio.run(_api_status_async(detailed, format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'api status': {e}[/]")
        raise typer.Exit(code=1)


async def _api_status_async(detailed: bool, format: str):
    """Показать статус API"""
    console.print(Panel("[bold blue]СТАТУС API[/]", expand=False, border_style="blue"))

    config = _load_api_config()
    server_status = _check_api_server_status()

    if format == "json":
        status_data = {
            "server": server_status,
            "endpoints": config.get("endpoints", {}),
            "rate_limits": config.get("rate_limits", {}),
        }
        console.print(json.dumps(status_data, indent=2, ensure_ascii=False))
        return

    # Основная информация о сервере
    console.print(f"[cyan]Сервер:[/] {server_status['host']}:{server_status['port']}")
    console.print(f"[cyan]Статус:[/] {server_status['status']}")
    console.print(
        f"[cyan]SSL:[/] {'Включен' if server_status['ssl_enabled'] else 'Отключен'}"
    )
    console.print(
        f"[cyan]Debug:[/] {'Включен' if server_status['debug'] else 'Отключен'}"
    )

    if server_status["uptime"]:
        uptime_seconds = int(server_status["uptime"])
        uptime_str = str(timedelta(seconds=uptime_seconds))
        console.print(f"[cyan]Время работы:[/] {uptime_str}")

    if server_status["memory_usage"]:
        console.print(
            f"[cyan]Использование памяти:[/] {server_status['memory_usage']:.1f} MB"
        )

    if server_status["cpu_usage"]:
        console.print(f"[cyan]Использование CPU:[/] {server_status['cpu_usage']:.1f}%")

    # Статус endpoints
    endpoints = config.get("endpoints", {})
    if endpoints:
        console.print(f"\n[bold cyan]API Endpoints ({len(endpoints)}):[/]")

        table = Table()
        table.add_column("Endpoint", style="cyan")
        table.add_column("Метод", style="blue")
        table.add_column("Статус", style="green")
        table.add_column("Лимит", style="yellow")
        table.add_column("Описание", style="white")

        for endpoint_key, endpoint_info in endpoints.items():
            status = endpoint_info.get("status", "unknown")
            status_color = {
                "active": "green",
                "planned": "yellow",
                "deprecated": "red",
                "maintenance": "orange",
            }.get(status, "white")

            rate_limit = endpoint_info.get("rate_limit", "N/A")
            if rate_limit:
                rate_limit = f"{rate_limit}/min"

            table.add_row(
                endpoint_info.get("path", "N/A"),
                endpoint_info.get("method", "N/A"),
                f"[{status_color}]{status}[/{status_color}]",
                str(rate_limit),
                endpoint_info.get("description", "Без описания"),
            )

        console.print(table)

    # Подробная информация
    if detailed:
        console.print(f"\n[bold cyan]Подробная информация:[/]")
        console.print(f"[dim]Конфигурационный файл:[/] {API_CONFIG_FILE}")
        console.print(f"[dim]Файл ключей:[/] {API_KEYS_FILE}")
        console.print(f"[dim]Файл лимитов:[/] {API_RATE_LIMITS_FILE}")


@api_app.command(name="keys", help="Управление API ключами.")
def api_keys_cmd(
    action: str = typer.Argument(..., help="Действие: list, generate, revoke, info"),
    key_name: Optional[str] = typer.Option(None, "--name", "-n", help="Имя ключа"),
    permissions: Optional[str] = typer.Option(
        None, "--permissions", "-p", help="Права доступа (read,write,admin)"
    ),
    expires_in_days: Optional[int] = typer.Option(
        None, "--expires", "-e", help="Срок действия в днях"
    ),
):
    """Управление API ключами"""
    try:
        asyncio.run(_api_keys_async(action, key_name, permissions, expires_in_days))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'api keys': {e}[/]")
        raise typer.Exit(code=1)


async def _api_keys_async(
    action: str,
    key_name: Optional[str],
    permissions: Optional[str],
    expires_in_days: Optional[int],
):
    """Асинхронная обработка команд управления API ключами"""
    console.print(
        Panel("[bold blue]УПРАВЛЕНИЕ API КЛЮЧАМИ[/]", expand=False, border_style="blue")
    )

    keys_data = _load_api_keys()
    keys = keys_data.get("keys", {})

    if action == "list":
        _list_api_keys(keys)
    elif action == "generate":
        if not key_name:
            console.print(
                "[bold red]Для действия 'generate' необходимо указать имя ключа (--name).[/]"
            )
            raise typer.Exit(code=1)
        _generate_api_key_cmd(key_name, permissions, expires_in_days, keys_data)
    elif action == "revoke":
        if not key_name:
            console.print(
                "[bold red]Для действия 'revoke' необходимо указать имя ключа (--name).[/]"
            )
            raise typer.Exit(code=1)
        _revoke_api_key(key_name, keys_data)
    elif action == "info":
        if not key_name:
            console.print(
                "[bold red]Для действия 'info' необходимо указать имя ключа (--name).[/]"
            )
            raise typer.Exit(code=1)
        _show_api_key_info(key_name, keys)
    else:
        console.print(f"[bold red]Неизвестное действие: {action}[/]")
        raise typer.Exit(code=1)


def _list_api_keys(keys: Dict[str, Any]):
    """Показать список API ключей"""
    if not keys:
        console.print("[yellow]API ключи не найдены[/]")
        return

    table = Table(title="API Ключи")
    table.add_column("Имя", style="cyan")
    table.add_column("Создан", style="blue")
    table.add_column("Права", style="green")
    table.add_column("Истекает", style="yellow")
    table.add_column("Статус", style="red")

    for key_name, key_info in keys.items():
        created_at = key_info.get("created_at", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                created_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                created_str = created_at
        else:
            created_str = "N/A"

        expires_at = key_info.get("expires_at")
        if expires_at:
            try:
                dt = datetime.fromisoformat(expires_at)
                if dt < datetime.now():
                    expires_str = "Истек"
                    status = "expired"
                    status_color = "red"
                else:
                    expires_str = dt.strftime("%Y-%m-%d %H:%M")
                    status = "active"
                    status_color = "green"
            except:
                expires_str = "N/A"
                status = "unknown"
                status_color = "white"
        else:
            expires_str = "Бессрочно"
            status = "active"
            status_color = "green"

        permissions = key_info.get("permissions", "read")

        table.add_row(
            key_name,
            created_str,
            permissions,
            expires_str,
            f"[{status_color}]{status}[/{status_color}]",
        )

    console.print(table)


def _generate_api_key_cmd(
    key_name: str,
    permissions: Optional[str],
    expires_in_days: Optional[int],
    keys_data: Dict[str, Any],
):
    """Генерировать новый API ключ"""
    keys = keys_data.get("keys", {})

    if key_name in keys:
        from Systems.cli.utils import confirm_action

        if not confirm_action(f"API ключ '{key_name}' уже существует. Перезаписать?"):
            return

    # Генерируем ключ
    api_key = _generate_api_key()

    # Создаем информацию о ключе
    now = datetime.now()
    expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

    keys[key_name] = {
        "key": api_key,
        "permissions": permissions or "read",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "last_used": None,
        "usage_count": 0,
    }

    _save_api_keys(keys_data)

    console.print(f"[green]✅ API ключ '{key_name}' успешно создан[/]")
    console.print(f"[dim]Ключ:[/] {api_key}")
    console.print(f"[dim]Права:[/] {permissions or 'read'}")
    if expires_at:
        console.print(f"[dim]Истекает:[/] {expires_at.strftime('%Y-%m-%d %H:%M')}")


def _revoke_api_key(key_name: str, keys_data: Dict[str, Any]):
    """Отозвать API ключ"""
    keys = keys_data.get("keys", {})

    if key_name not in keys:
        console.print(f"[bold red]API ключ '{key_name}' не найден[/]")
        raise typer.Exit(code=1)

    from Systems.cli.utils import confirm_action

    if not confirm_action(f"Отозвать API ключ '{key_name}'?"):
        return

    del keys[key_name]
    _save_api_keys(keys_data)

    console.print(f"[green]✅ API ключ '{key_name}' успешно отозван[/]")


def _show_api_key_info(key_name: str, keys: Dict[str, Any]):
    """Показать информацию об API ключе"""
    if key_name not in keys:
        console.print(f"[bold red]API ключ '{key_name}' не найден[/]")
        raise typer.Exit(code=1)

    key_info = keys[key_name]

    console.print(f"[cyan]Имя:[/] {key_name}")
    console.print(f"[cyan]Ключ:[/] {key_info.get('key', 'N/A')}")
    console.print(f"[cyan]Права:[/] {key_info.get('permissions', 'N/A')}")
    console.print(f"[cyan]Создан:[/] {key_info.get('created_at', 'N/A')}")
    console.print(
        f"[cyan]Последнее использование:[/] {key_info.get('last_used', 'Никогда')}"
    )
    console.print(
        f"[cyan]Количество использований:[/] {key_info.get('usage_count', 0)}"
    )

    expires_at = key_info.get("expires_at")
    if expires_at:
        try:
            dt = datetime.fromisoformat(expires_at)
            if dt < datetime.now():
                console.print(
                    f"[cyan]Истекает:[/] [red]Истек {dt.strftime('%Y-%m-%d %H:%M')}[/red]"
                )
            else:
                console.print(f"[cyan]Истекает:[/] {dt.strftime('%Y-%m-%d %H:%M')}")
        except:
            console.print(f"[cyan]Истекает:[/] {expires_at}")


@api_app.command(name="rate-limit", help="Управление лимитами запросов.")
def api_rate_limit_cmd(
    action: str = typer.Argument(..., help="Действие: show, set, reset, stats"),
    endpoint: Optional[str] = typer.Option(
        None, "--endpoint", "-e", help="Endpoint для настройки"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Лимит запросов в минуту"
    ),
    window: Optional[int] = typer.Option(
        None, "--window", "-w", help="Окно времени в секундах"
    ),
):
    """Управление лимитами запросов"""
    try:
        asyncio.run(_api_rate_limit_async(action, endpoint, limit, window))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'api rate-limit': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _api_rate_limit_async(
    action: str, endpoint: Optional[str], limit: Optional[int], window: Optional[int]
):
    """Асинхронная обработка команд управления лимитами"""
    console.print(
        Panel(
            "[bold blue]УПРАВЛЕНИЕ ЛИМИТАМИ ЗАПРОСОВ[/]",
            expand=False,
            border_style="blue",
        )
    )

    rate_data = _load_rate_limits()
    limits = rate_data.get("limits", {})
    usage = rate_data.get("usage", {})

    if action == "show":
        _show_rate_limits(limits, usage)
    elif action == "set":
        if not endpoint or limit is None:
            console.print(
                "[bold red]Для действия 'set' необходимо указать endpoint и limit.[/]"
            )
            raise typer.Exit(code=1)
        _set_rate_limit(endpoint, limit, window, rate_data)
    elif action == "reset":
        _reset_rate_limits(rate_data)
    elif action == "stats":
        _show_rate_limit_stats(usage)
    else:
        console.print(f"[bold red]Неизвестное действие: {action}[/]")
        raise typer.Exit(code=1)


def _show_rate_limits(limits: Dict[str, Any], usage: Dict[str, Any]):
    """Показать лимиты запросов"""
    if not limits:
        console.print("[yellow]Лимиты запросов не настроены[/]")
        return

    table = Table(title="Лимиты запросов")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Лимит", style="blue")
    table.add_column("Окно", style="green")
    table.add_column("Использовано", style="yellow")
    table.add_column("Осталось", style="red")

    for endpoint, limit_info in limits.items():
        limit_value = limit_info.get("limit", 0)
        window_value = limit_info.get("window", 60)

        # Получаем текущее использование
        current_usage = usage.get(endpoint, {}).get("count", 0)
        remaining = max(0, limit_value - current_usage)

        usage_color = "green" if remaining > 0 else "red"

        table.add_row(
            endpoint,
            f"{limit_value}/min",
            f"{window_value}s",
            str(current_usage),
            f"[{usage_color}]{remaining}[/{usage_color}]",
        )

    console.print(table)


def _set_rate_limit(
    endpoint: str, limit: int, window: Optional[int], rate_data: Dict[str, Any]
):
    """Установить лимит запросов"""
    limits = rate_data.get("limits", {})

    limits[endpoint] = {
        "limit": limit,
        "window": window or 60,
        "created_at": datetime.now().isoformat(),
    }

    _save_rate_limits(rate_data)

    console.print(f"[green]✅ Лимит для '{endpoint}' установлен: {limit}/min[/]")


def _reset_rate_limits(rate_data: Dict[str, Any]):
    """Сбросить все лимиты запросов"""
    from Systems.cli.utils import confirm_action

    if not confirm_action("Сбросить все лимиты запросов?"):
        return

    rate_data["limits"] = {}
    rate_data["usage"] = {}
    _save_rate_limits(rate_data)

    console.print("[green]✅ Все лимиты запросов сброшены[/]")


def _show_rate_limit_stats(usage: Dict[str, Any]):
    """Показать статистику использования лимитов"""
    if not usage:
        console.print("[yellow]Статистика использования пуста[/]")
        return

    table = Table(title="Статистика использования лимитов")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Запросов", style="blue")
    table.add_column("Последний запрос", style="green")
    table.add_column("Среднее время", style="yellow")

    for endpoint, usage_info in usage.items():
        count = usage_info.get("count", 0)
        last_request = usage_info.get("last_request")
        avg_time = usage_info.get("avg_response_time", "N/A")

        if last_request:
            try:
                dt = datetime.fromisoformat(last_request)
                last_str = dt.strftime("%H:%M:%S")
            except:
                last_str = last_request
        else:
            last_str = "Никогда"

        table.add_row(endpoint, str(count), last_str, str(avg_time))

    console.print(table)


@api_app.command(name="docs", help="Генерировать документацию API.")
def api_docs_cmd(
    format: str = typer.Option(
        "html", "--format", "-f", help="Формат документации: html, json, yaml"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Файл для сохранения документации"
    ),
    include_examples: bool = typer.Option(
        True, "--examples", help="Включить примеры запросов"
    ),
):
    """Генерировать документацию API"""
    try:
        asyncio.run(_api_docs_async(format, output_file, include_examples))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'api docs': {e}[/]")
        raise typer.Exit(code=1)


async def _api_docs_async(
    format: str, output_file: Optional[str], include_examples: bool
):
    """Генерировать документацию API"""
    console.print(
        Panel(
            "[bold blue]ГЕНЕРАЦИЯ ДОКУМЕНТАЦИИ API[/]",
            expand=False,
            border_style="blue",
        )
    )

    config = _load_api_config()
    endpoints = config.get("endpoints", {})

    if not endpoints:
        console.print("[yellow]API endpoints не найдены[/]")
        return

    console.print(f"[cyan]Формат:[/] {format}")
    console.print(f"[cyan]Включить примеры:[/] {'Да' if include_examples else 'Нет'}")

    if format == "html":
        _generate_html_docs(endpoints, output_file, include_examples)
    elif format == "json":
        _generate_json_docs(endpoints, output_file)
    elif format == "yaml":
        _generate_yaml_docs(endpoints, output_file)
    else:
        console.print(f"[bold red]Неподдерживаемый формат: {format}[/]")
        raise typer.Exit(code=1)


def _generate_html_docs(
    endpoints: Dict[str, Any], output_file: Optional[str], include_examples: bool
):
    """Генерировать HTML документацию"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SwiftDevBot API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .endpoint { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .method { font-weight: bold; color: #fff; padding: 3px 8px; border-radius: 3px; }
            .get { background-color: #61affe; }
            .post { background-color: #49cc90; }
            .put { background-color: #fca130; }
            .delete { background-color: #f93e3e; }
            .path { font-family: monospace; background-color: #f5f5f5; padding: 5px; }
            .description { margin: 10px 0; }
            .example { background-color: #f8f9fa; padding: 10px; border-left: 4px solid #007bff; margin: 10px 0; }
            .rate-limit { color: #6c757d; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>SwiftDevBot API Documentation</h1>
        <p>Документация API для SwiftDevBot системы.</p>
    """

    for endpoint_key, endpoint_info in endpoints.items():
        method = endpoint_info.get("method", "GET")
        path = endpoint_info.get("path", "")
        description = endpoint_info.get("description", "")
        rate_limit = endpoint_info.get("rate_limit", "N/A")
        auth_required = endpoint_info.get("auth_required", True)

        html_content += f"""
        <div class="endpoint">
            <div>
                <span class="method {method.lower()}">{method}</span>
                <span class="path">{path}</span>
            </div>
            <div class="description">{description}</div>
            <div class="rate-limit">Лимит: {rate_limit}/min | Аутентификация: {'Требуется' if auth_required else 'Не требуется'}</div>
        """

        if include_examples:
            html_content += f"""
            <div class="example">
                <strong>Пример запроса:</strong><br>
                <code>curl -X {method} "http://localhost:8000{path}"</code>
            </div>
            """

        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        console.print(f"[green]✅ HTML документация сохранена в: {output_file}[/]")
    else:
        default_file = API_DOCS_DIR / "api_docs.html"
        with open(default_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        console.print(f"[green]✅ HTML документация сохранена в: {default_file}[/]")


def _generate_json_docs(endpoints: Dict[str, Any], output_file: Optional[str]):
    """Генерировать JSON документацию"""
    docs_data = {
        "info": {
            "title": "SwiftDevBot API",
            "version": "1.0.0",
            "description": "API для управления системой SwiftDevBot",
        },
        "endpoints": endpoints,
    }

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(docs_data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✅ JSON документация сохранена в: {output_file}[/]")
    else:
        default_file = API_DOCS_DIR / "api_docs.json"
        with open(default_file, "w", encoding="utf-8") as f:
            json.dump(docs_data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✅ JSON документация сохранена в: {default_file}[/]")


def _generate_yaml_docs(endpoints: Dict[str, Any], output_file: Optional[str]):
    """Генерировать YAML документацию"""
    try:
        import yaml
    except ImportError:
        console.print("[yellow]Для генерации YAML документации установите PyYAML[/]")
        return

    docs_data = {
        "info": {
            "title": "SwiftDevBot API",
            "version": "1.0.0",
            "description": "API для управления системой SwiftDevBot",
        },
        "endpoints": endpoints,
    }

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(docs_data, f, default_flow_style=False, allow_unicode=True)
        console.print(f"[green]✅ YAML документация сохранена в: {output_file}[/]")
    else:
        default_file = API_DOCS_DIR / "api_docs.yaml"
        with open(default_file, "w", encoding="utf-8") as f:
            yaml.dump(docs_data, f, default_flow_style=False, allow_unicode=True)
        console.print(f"[green]✅ YAML документация сохранена в: {default_file}[/]")


if __name__ == "__main__":
    api_app()
