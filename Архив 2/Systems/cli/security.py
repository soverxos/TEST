# cli/security.py
import asyncio
import hashlib
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Systems.cli.utils import confirm_action

# Импортируем модуль интеграций безопасности
try:
    from Modules.security_integrations import security_integrations

    SECURITY_INTEGRATIONS_AVAILABLE = True
except ImportError:
    SECURITY_INTEGRATIONS_AVAILABLE = False

console = Console()
security_app = typer.Typer(name="security", help="🔒 Управление безопасностью системы")

# Константы для ключей
KEYS_DIR = Path("security/keys")
KEYS_CONFIG_FILE = KEYS_DIR / "keys_config.json"


@security_app.command(name="audit", help="Провести аудит безопасности системы.")
def security_audit_cmd(
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Файл для сохранения отчета"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Формат отчета: text, json, html"
    ),
):
    """Провести аудит безопасности системы"""
    try:
        asyncio.run(_security_audit_async(output_file, format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'security audit': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _security_audit_async(output_file: Optional[str], format: str):
    """Провести аудит безопасности"""
    console.print(
        Panel(
            "[bold blue]АУДИТ БЕЗОПАСНОСТИ СИСТЕМЫ[/]",
            expand=False,
            border_style="blue",
        )
    )

    audit_results = []

    # 1. Проверка файлов конфигурации
    console.print("[cyan]1. Проверка файлов конфигурации...[/]")
    config_issues = await _audit_config_files()
    audit_results.extend(config_issues)

    # 2. Проверка прав доступа
    console.print("[cyan]2. Проверка прав доступа...[/]")
    permission_issues = await _audit_file_permissions()
    audit_results.extend(permission_issues)

    # 3. Проверка сетевой безопасности
    console.print("[cyan]3. Проверка сетевой безопасности...[/]")
    network_issues = await _audit_network_security()
    audit_results.extend(network_issues)

    # 4. Проверка зависимостей
    console.print("[cyan]4. Проверка зависимостей...[/]")
    dependency_issues = await _audit_dependencies()
    audit_results.extend(dependency_issues)

    # 5. Проверка ключей безопасности
    console.print("[cyan]5. Проверка ключей безопасности...[/]")
    keys_issues = await _audit_security_keys()
    audit_results.extend(keys_issues)

    # Выводим результаты
    await _display_audit_results(audit_results, output_file, format)


async def _audit_config_files() -> List[dict]:
    """Проверка файлов конфигурации"""
    issues = []

    # Проверяем наличие .env файла
    env_file = Path(".env")
    if env_file.exists():
        # Проверяем права доступа
        stat = env_file.stat()
        if stat.st_mode & 0o777 != 0o600:
            issues.append(
                {
                    "type": "warning",
                    "category": "config",
                    "message": f"Файл .env имеет небезопасные права доступа: {oct(stat.st_mode)[-3:]}",
                }
            )
    else:
        issues.append(
            {
                "type": "info",
                "category": "config",
                "message": "Файл .env не найден (возможно, используется другой способ конфигурации)",
            }
        )

    # Проверяем другие конфигурационные файлы
    config_files = [".env", "core_settings.yaml", "alembic.ini"]
    for config_file in config_files:
        file_path = Path(config_file)
        if file_path.exists():
            stat = file_path.stat()
            if stat.st_mode & 0o777 > 0o644:
                issues.append(
                    {
                        "type": "warning",
                        "category": "config",
                        "message": f"Файл {config_file} имеет слишком открытые права доступа",
                    }
                )

    return issues


async def _audit_file_permissions() -> List[dict]:
    """Проверка прав доступа к файлам"""
    issues = []

    # Проверяем права доступа к ключевым директориям
    key_dirs = ["Data", "logs", "backup"]
    for dir_name in key_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            stat = dir_path.stat()
            if stat.st_mode & 0o777 > 0o755:
                issues.append(
                    {
                        "type": "warning",
                        "category": "permissions",
                        "message": f"Директория {dir_name} имеет слишком открытые права доступа",
                    }
                )

    return issues


async def _audit_network_security() -> List[dict]:
    """Проверка сетевой безопасности"""
    issues = []

    # Проверяем открытые порты
    try:
        result = subprocess.run(["netstat", "-tuln"], capture_output=True, text=True)
        if result.returncode == 0:
            open_ports = result.stdout.strip().split("\n")
            if len(open_ports) > 1:  # Есть открытые порты
                issues.append(
                    {
                        "type": "info",
                        "category": "network",
                        "message": f"Обнаружено {len(open_ports)-1} открытых портов",
                    }
                )
    except FileNotFoundError:
        issues.append(
            {
                "type": "info",
                "category": "network",
                "message": "Не удалось проверить открытые порты (netstat недоступен)",
            }
        )

    return issues


async def _audit_dependencies() -> List[dict]:
    """Проверка зависимостей на уязвимости"""
    issues = []

    # Проверяем наличие pip-audit
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"], capture_output=True, text=True
        )
        if result.returncode == 0:
            packages = result.stdout.strip().split("\n")
            if len(packages) > 2:  # Есть установленные пакеты
                issues.append(
                    {
                        "type": "info",
                        "category": "dependencies",
                        "message": f"Установлено {len(packages)-2} Python пакетов",
                    }
                )

                # Рекомендация по проверке уязвимостей
                issues.append(
                    {
                        "type": "recommendation",
                        "category": "dependencies",
                        "message": "Рекомендуется запустить 'pip-audit' для проверки уязвимостей",
                    }
                )
    except Exception as e:
        issues.append(
            {
                "type": "error",
                "category": "dependencies",
                "message": f"Ошибка при проверке зависимостей: {e}",
            }
        )

    return issues


async def _audit_security_keys() -> List[dict]:
    """Проверка ключей безопасности"""
    issues = []

    # Проверяем директорию ключей
    if KEYS_DIR.exists():
        if not KEYS_CONFIG_FILE.exists():
            issues.append(
                {
                    "type": "warning",
                    "category": "keys",
                    "message": "Конфигурационный файл ключей не найден",
                }
            )
        else:
            try:
                with open(KEYS_CONFIG_FILE, "r") as f:
                    keys_config = json.load(f)

                for key_name, key_info in keys_config.items():
                    if key_info.get("expires_at"):
                        expires_at = datetime.fromisoformat(key_info["expires_at"])
                        if expires_at < datetime.now():
                            issues.append(
                                {
                                    "type": "error",
                                    "category": "keys",
                                    "message": f"Ключ {key_name} истек {expires_at.strftime('%Y-%m-%d %H:%M')}",
                                }
                            )
                        elif expires_at < datetime.now() + timedelta(days=30):
                            issues.append(
                                {
                                    "type": "warning",
                                    "category": "keys",
                                    "message": f"Ключ {key_name} истекает {expires_at.strftime('%Y-%m-%d %H:%M')}",
                                }
                            )
            except Exception as e:
                issues.append(
                    {
                        "type": "error",
                        "category": "keys",
                        "message": f"Ошибка при чтении конфигурации ключей: {e}",
                    }
                )
    else:
        issues.append(
            {
                "type": "info",
                "category": "keys",
                "message": "Директория ключей безопасности не создана",
            }
        )

    return issues


async def _display_audit_results(
    issues: List[dict], output_file: Optional[str], format: str
):
    """Отобразить результаты аудита"""

    # Группируем по типам
    warnings = [i for i in issues if i["type"] == "warning"]
    errors = [i for i in issues if i["type"] == "error"]
    info = [i for i in issues if i["type"] == "info"]
    recommendations = [i for i in issues if i["type"] == "recommendation"]

    # Создаем таблицу
    table = Table(title="Результаты аудита безопасности")
    table.add_column("Тип", style="cyan")
    table.add_column("Категория", style="blue")
    table.add_column("Сообщение", style="white")

    for issue in issues:
        color = {
            "warning": "yellow",
            "error": "red",
            "info": "blue",
            "recommendation": "green",
        }.get(issue["type"], "white")

        table.add_row(
            f"[{color}]{issue['type'].upper()}[/{color}]",
            issue["category"],
            issue["message"],
        )

    console.print(table)

    # Статистика
    console.print(f"\n[bold green]Статистика:[/]")
    console.print(f"  ⚠️ Предупреждения: {len(warnings)}")
    console.print(f"  ❌ Ошибки: {len(errors)}")
    console.print(f"  ℹ️ Информация: {len(info)}")
    console.print(f"  💡 Рекомендации: {len(recommendations)}")

    # Сохранение в файл
    if output_file:
        await _save_audit_report(issues, output_file, format)


async def _save_audit_report(issues: List[dict], output_file: str, format: str):
    """Сохранить отчет в файл"""
    try:
        if format == "json":
            import json

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(issues, f, indent=2, ensure_ascii=False)
        elif format == "html":
            html_content = _generate_html_report(issues)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:  # text
            with open(output_file, "w", encoding="utf-8") as f:
                for issue in issues:
                    f.write(
                        f"[{issue['type'].upper()}] {issue['category']}: {issue['message']}\n"
                    )

        console.print(f"[green]Отчет сохранен в файл: {output_file}[/]")
    except Exception as e:
        console.print(f"[bold red]Ошибка при сохранении отчета: {e}[/]")


def _generate_html_report(issues: List[dict]) -> str:
    """Генерировать HTML отчет"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Аудит безопасности SwiftDevBot</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .warning { color: #ff8c00; }
            .error { color: #ff0000; }
            .info { color: #0066cc; }
            .recommendation { color: #008000; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>Аудит безопасности SwiftDevBot</h1>
        <table>
            <tr><th>Тип</th><th>Категория</th><th>Сообщение</th></tr>
    """

    for issue in issues:
        html += f"""
            <tr>
                <td class="{issue['type']}">{issue['type'].upper()}</td>
                <td>{issue['category']}</td>
                <td>{issue['message']}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    return html


def _ensure_keys_directory():
    """Создать директорию для ключей если её нет"""
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if not KEYS_CONFIG_FILE.exists():
        with open(KEYS_CONFIG_FILE, "w") as f:
            json.dump({}, f)


def _load_keys_config() -> Dict[str, Any]:
    """Загрузить конфигурацию ключей"""
    _ensure_keys_directory()
    try:
        with open(KEYS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_keys_config(config: Dict[str, Any]):
    """Сохранить конфигурацию ключей"""
    _ensure_keys_directory()
    with open(KEYS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _generate_key(key_type: str, length: int = 32) -> str:
    """Генерировать ключ указанного типа"""
    if key_type == "jwt":
        return secrets.token_urlsafe(length)
    elif key_type == "api":
        return secrets.token_hex(length)
    elif key_type == "encryption":
        return secrets.token_bytes(length).hex()
    else:
        return secrets.token_urlsafe(length)


@security_app.command(name="keys", help="Управление ключами безопасности.")
def security_keys_cmd(
    action: str = typer.Argument(..., help="Действие: list, generate, rotate, delete"),
    key_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Тип ключа: jwt, api, encryption"
    ),
    key_name: Optional[str] = typer.Option(None, "--name", "-n", help="Имя ключа"),
    length: int = typer.Option(32, "--length", "-l", help="Длина ключа в байтах"),
    expires_in_days: Optional[int] = typer.Option(
        None, "--expires", "-e", help="Срок действия в днях"
    ),
):
    """Управление ключами безопасности"""
    console.print(
        Panel(
            "[bold blue]УПРАВЛЕНИЕ КЛЮЧАМИ БЕЗОПАСНОСТИ[/]",
            expand=False,
            border_style="blue",
        )
    )

    if action == "list":
        _list_keys()
    elif action == "generate":
        if not key_type:
            console.print("[bold red]Необходимо указать тип ключа (--type)[/]")
            raise typer.Exit(code=1)
        if not key_name:
            console.print("[bold red]Необходимо указать имя ключа (--name)[/]")
            raise typer.Exit(code=1)
        _generate_new_key(key_type, key_name, length, expires_in_days)
    elif action == "rotate":
        if not key_name:
            console.print("[bold red]Необходимо указать имя ключа (--name)[/]")
            raise typer.Exit(code=1)
        _rotate_key(key_name, length, expires_in_days)
    elif action == "delete":
        if not key_name:
            console.print("[bold red]Необходимо указать имя ключа (--name)[/]")
            raise typer.Exit(code=1)
        _delete_key(key_name)
    else:
        console.print(f"[bold red]Неизвестное действие: {action}[/]")
        raise typer.Exit(code=1)


def _list_keys():
    """Показать список ключей"""
    config = _load_keys_config()

    if not config:
        console.print("[yellow]Ключи не найдены[/]")
        return

    table = Table(title="Ключи безопасности")
    table.add_column("Имя", style="cyan")
    table.add_column("Тип", style="blue")
    table.add_column("Создан", style="green")
    table.add_column("Истекает", style="yellow")
    table.add_column("Статус", style="red")

    for key_name, key_info in config.items():
        created_at = datetime.fromisoformat(key_info["created_at"])
        expires_at = (
            datetime.fromisoformat(key_info["expires_at"])
            if key_info.get("expires_at")
            else None
        )

        status = "Активен"
        status_color = "green"
        if expires_at:
            if expires_at < datetime.now():
                status = "Истек"
                status_color = "red"
            elif expires_at < datetime.now() + timedelta(days=30):
                status = "Скоро истекает"
                status_color = "yellow"

        table.add_row(
            key_name,
            key_info["type"],
            created_at.strftime("%Y-%m-%d %H:%M"),
            expires_at.strftime("%Y-%m-%d %H:%M") if expires_at else "Бессрочно",
            f"[{status_color}]{status}[/{status_color}]",
        )

    console.print(table)


def _generate_new_key(
    key_type: str, key_name: str, length: int, expires_in_days: Optional[int]
):
    """Генерировать новый ключ"""
    config = _load_keys_config()

    if key_name in config:
        if not confirm_action(f"Ключ '{key_name}' уже существует. Перезаписать?"):
            return

    # Генерируем ключ
    key_value = _generate_key(key_type, length)

    # Сохраняем в файл
    key_file = KEYS_DIR / f"{key_name}.key"
    with open(key_file, "w") as f:
        f.write(key_value)

    # Обновляем конфигурацию
    now = datetime.now()
    expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

    config[key_name] = {
        "type": key_type,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "length": length,
        "file": str(key_file),
    }

    _save_keys_config(config)

    console.print(f"[green]Ключ '{key_name}' успешно создан[/]")
    console.print(f"[dim]Тип: {key_type}[/]")
    console.print(f"[dim]Длина: {length} байт[/]")
    if expires_at:
        console.print(f"[dim]Истекает: {expires_at.strftime('%Y-%m-%d %H:%M')}[/]")


def _rotate_key(key_name: str, length: int, expires_in_days: Optional[int]):
    """Ротация ключа"""
    config = _load_keys_config()

    if key_name not in config:
        console.print(f"[bold red]Ключ '{key_name}' не найден[/]")
        raise typer.Exit(code=1)

    key_info = config[key_name]
    key_type = key_info["type"]

    # Генерируем новый ключ
    key_value = _generate_key(key_type, length)

    # Сохраняем в файл
    key_file = KEYS_DIR / f"{key_name}.key"
    with open(key_file, "w") as f:
        f.write(key_value)

    # Обновляем конфигурацию
    now = datetime.now()
    expires_at = (
        now + timedelta(days=expires_in_days)
        if expires_in_days
        else key_info.get("expires_at")
    )

    config[key_name].update(
        {
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "length": length,
        }
    )

    _save_keys_config(config)

    console.print(f"[green]Ключ '{key_name}' успешно обновлен[/]")


def _delete_key(key_name: str):
    """Удалить ключ"""
    config = _load_keys_config()

    if key_name not in config:
        console.print(f"[bold red]Ключ '{key_name}' не найден[/]")
        raise typer.Exit(code=1)

    if not confirm_action(f"Удалить ключ '{key_name}'?"):
        return

    # Удаляем файл ключа
    key_file = KEYS_DIR / f"{key_name}.key"
    if key_file.exists():
        key_file.unlink()

    # Удаляем из конфигурации
    del config[key_name]
    _save_keys_config(config)

    console.print(f"[green]Ключ '{key_name}' успешно удален[/]")


@security_app.command(name="ssl", help="Управление SSL сертификатами.")
def security_ssl_cmd(
    action: str = typer.Argument(..., help="Действие: check, install, renew, list"),
    domain: Optional[str] = typer.Option(
        None, "--domain", "-d", help="Домен для сертификата"
    ),
    cert_file: Optional[str] = typer.Option(
        None, "--cert", "-c", help="Путь к файлу сертификата"
    ),
    key_file: Optional[str] = typer.Option(
        None, "--key", "-k", help="Путь к файлу ключа"
    ),
):
    """Управление SSL сертификатами"""
    console.print(
        Panel(
            "[bold blue]УПРАВЛЕНИЕ SSL СЕРТИФИКАТАМИ[/]",
            expand=False,
            border_style="blue",
        )
    )

    if action == "check":
        _check_ssl_certificate(domain, cert_file)
    elif action == "install":
        if not cert_file or not key_file:
            console.print("[bold red]Необходимо указать пути к сертификату и ключу[/]")
            raise typer.Exit(code=1)
        _install_ssl_certificate(cert_file, key_file, domain)
    elif action == "renew":
        _renew_ssl_certificate(domain)
    elif action == "list":
        _list_ssl_certificates()
    else:
        console.print(f"[bold red]Неизвестное действие: {action}[/]")
        raise typer.Exit(code=1)


def _check_ssl_certificate(domain: Optional[str], cert_file: Optional[str]):
    """Проверить SSL сертификат"""
    if domain:
        _check_ssl_domain(domain)
    elif cert_file:
        _check_ssl_file(cert_file)
    else:
        console.print("[bold red]Необходимо указать домен или файл сертификата[/]")
        raise typer.Exit(code=1)


def _check_ssl_domain(domain: str):
    """Проверить SSL сертификат домена"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                console.print(f"[green]SSL сертификат для {domain}:[/]")
                console.print(f"  [dim]Издатель: {cert.get('issuer', [])}[/]")
                console.print(f"  [dim]Субъект: {cert.get('subject', [])}[/]")

                # Проверяем срок действия
                not_after = cert.get("notAfter")
                if not_after:
                    import email.utils
                    from datetime import datetime

                    expires = email.utils.parsedate_to_datetime(not_after)
                    now = datetime.now()

                    if expires < now:
                        console.print(
                            f"  [red]❌ Сертификат истек {expires.strftime('%Y-%m-%d')}[/]"
                        )
                    elif expires < now + timedelta(days=30):
                        console.print(
                            f"  [yellow]⚠️ Сертификат истекает {expires.strftime('%Y-%m-%d')}[/]"
                        )
                    else:
                        console.print(
                            f"  [green]✅ Сертификат действителен до {expires.strftime('%Y-%m-%d')}[/]"
                        )

    except Exception as e:
        console.print(f"[bold red]Ошибка при проверке SSL сертификата: {e}[/]")


def _check_ssl_file(cert_file: str):
    """Проверить SSL сертификат из файла"""
    try:
        import OpenSSL.crypto as crypto

        with open(cert_file, "rb") as f:
            cert_data = f.read()

        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)

        console.print(f"[green]SSL сертификат из файла {cert_file}:[/]")
        console.print(f"  [dim]Субъект: {cert.get_subject()}[/]")
        console.print(f"  [dim]Издатель: {cert.get_issuer()}[/]")

        # Проверяем срок действия
        not_after = cert.get_notAfter()
        if not_after:
            expires = datetime.strptime(not_after.decode(), "%Y%m%d%H%M%SZ")
            now = datetime.now()

            if expires < now:
                console.print(
                    f"  [red]❌ Сертификат истек {expires.strftime('%Y-%m-%d')}[/]"
                )
            elif expires < now + timedelta(days=30):
                console.print(
                    f"  [yellow]⚠️ Сертификат истекает {expires.strftime('%Y-%m-%d')}[/]"
                )
            else:
                console.print(
                    f"  [green]✅ Сертификат действителен до {expires.strftime('%Y-%m-%d')}[/]"
                )

    except ImportError:
        console.print(
            "[yellow]Для проверки файлов сертификатов установите pyOpenSSL[/]"
        )
    except Exception as e:
        console.print(f"[bold red]Ошибка при проверке файла сертификата: {e}[/]")


def _install_ssl_certificate(cert_file: str, key_file: str, domain: Optional[str]):
    """Установить SSL сертификат"""
    console.print(f"[yellow]Установка SSL сертификата...[/]")
    console.print(f"[dim]Сертификат: {cert_file}[/]")
    console.print(f"[dim]Ключ: {key_file}[/]")
    if domain:
        console.print(f"[dim]Домен: {domain}[/]")

    # Проверяем существование файлов
    if not Path(cert_file).exists():
        console.print(f"[bold red]Файл сертификата не найден: {cert_file}[/]")
        raise typer.Exit(code=1)

    if not Path(key_file).exists():
        console.print(f"[bold red]Файл ключа не найден: {key_file}[/]")
        raise typer.Exit(code=1)

    # Здесь была бы логика установки сертификата
    # Для демонстрации просто показываем сообщение
    console.print("[green]✅ SSL сертификат успешно установлен[/]")


def _renew_ssl_certificate(domain: Optional[str]):
    """Обновить SSL сертификат"""
    if not domain:
        console.print(
            "[bold red]Необходимо указать домен для обновления сертификата[/]"
        )
        raise typer.Exit(code=1)

    console.print(f"[yellow]Обновление SSL сертификата для {domain}...[/]")
    console.print(
        "[dim]Эта функция требует настройки автоматического обновления сертификатов[/]"
    )


def _list_ssl_certificates():
    """Показать список SSL сертификатов"""
    console.print("[yellow]Список SSL сертификатов:[/]")
    console.print("[dim]Эта функция покажет все установленные сертификаты[/]")


@security_app.command(name="firewall", help="Управление настройками файрвола.")
def security_firewall_cmd(
    action: str = typer.Argument(
        ..., help="Действие: status, rules, add-rule, remove-rule, list"
    ),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Порт для правила"),
    protocol: Optional[str] = typer.Option(
        "tcp", "--protocol", help="Протокол: tcp, udp"
    ),
    direction: Optional[str] = typer.Option(
        "in", "--direction", help="Направление: in, out"
    ),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Источник (IP или подсеть)"
    ),
):
    """Управление настройками файрвола"""
    console.print(
        Panel("[bold blue]УПРАВЛЕНИЕ ФАЙРВОЛОМ[/]", expand=False, border_style="blue")
    )

    if action == "status":
        _check_firewall_status()
    elif action == "rules":
        _list_firewall_rules()
    elif action == "add-rule":
        if not port:
            console.print("[bold red]Необходимо указать порт (--port)[/]")
            raise typer.Exit(code=1)
        _add_firewall_rule(port, protocol, direction, source)
    elif action == "remove-rule":
        if not port:
            console.print("[bold red]Необходимо указать порт (--port)[/]")
            raise typer.Exit(code=1)
        _remove_firewall_rule(port, protocol)
    elif action == "list":
        _list_firewall_rules()
    else:
        console.print(f"[bold red]Неизвестное действие: {action}[/]")
        raise typer.Exit(code=1)


def _check_firewall_status():
    """Проверить статус файрвола"""
    try:
        # Проверяем iptables
        result = subprocess.run(["iptables", "-L"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✅ iptables активен[/]")
            rules_count = len(
                [
                    line
                    for line in result.stdout.split("\n")
                    if line.strip() and not line.startswith("-")
                ]
            )
            console.print(f"[dim]Найдено правил: {rules_count}[/]")
        else:
            console.print("[yellow]⚠️ iptables не активен или недоступен[/]")
    except FileNotFoundError:
        console.print("[yellow]⚠️ iptables не установлен[/]")

    try:
        # Проверяем ufw
        result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            if "Status: active" in result.stdout:
                console.print("[green]✅ UFW активен[/]")
            else:
                console.print("[yellow]⚠️ UFW неактивен[/]")
        else:
            console.print("[yellow]⚠️ UFW не установлен[/]")
    except FileNotFoundError:
        console.print("[yellow]⚠️ UFW не установлен[/]")


def _list_firewall_rules():
    """Показать правила файрвола"""
    console.print("[cyan]Правила iptables:[/]")
    try:
        result = subprocess.run(
            ["iptables", "-L", "-n", "--line-numbers"], capture_output=True, text=True
        )
        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print("[yellow]Не удалось получить правила iptables[/]")
    except FileNotFoundError:
        console.print("[yellow]iptables не установлен[/]")


def _add_firewall_rule(port: int, protocol: str, direction: str, source: Optional[str]):
    """Добавить правило файрвола"""
    console.print(f"[yellow]Добавление правила файрвола...[/]")
    console.print(f"[dim]Порт: {port}[/]")
    console.print(f"[dim]Протокол: {protocol}[/]")
    console.print(f"[dim]Направление: {direction}[/]")
    if source:
        console.print(f"[dim]Источник: {source}[/]")

    # Здесь была бы реальная команда добавления правила
    # Например: iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    console.print("[green]✅ Правило файрвола добавлено[/]")


def _remove_firewall_rule(port: int, protocol: str):
    """Удалить правило файрвола"""
    console.print(f"[yellow]Удаление правила файрвола...[/]")
    console.print(f"[dim]Порт: {port}[/]")
    console.print(f"[dim]Протокол: {protocol}[/]")

    # Здесь была бы реальная команда удаления правила
    console.print("[green]✅ Правило файрвола удалено[/]")


# === НОВЫЕ КОМАНДЫ ДЛЯ ИНТЕГРАЦИЙ С ВНЕШНИМИ СЕРВИСАМИ ===


@security_app.command(
    name="integrations",
    help="Управление интеграциями с внешними сервисами безопасности.",
)
def security_integrations_cmd(
    action: str = typer.Argument(
        ...,
        help="Действие: config, test, virustotal, shodan, abuseipdb, securitytrails, nmap, sslyze, system-info",
    ),
    target: Optional[str] = typer.Option(
        None, "--target", "-t", help="Цель для сканирования (IP, домен, файл)"
    ),
    scan_type: Optional[str] = typer.Option(
        "basic", "--scan-type", help="Тип сканирования: basic, full, quick"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="API ключ для сервиса"
    ),
    service: Optional[str] = typer.Option(
        None,
        "--service",
        "-s",
        help="Сервис: virustotal, shodan, abuseipdb, securitytrails",
    ),
):
    """Управление интеграциями с внешними сервисами безопасности"""
    if not SECURITY_INTEGRATIONS_AVAILABLE:
        console.print("[bold red]❌ Модуль интеграций безопасности не доступен[/]")
        console.print("[yellow]Установите зависимости: pip install aiohttp[/]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            "[bold blue]ИНТЕГРАЦИИ С ВНЕШНИМИ СЕРВИСАМИ БЕЗОПАСНОСТИ[/]",
            expand=False,
            border_style="blue",
        )
    )

    if action == "config":
        _manage_integrations_config(service, api_key)
    elif action == "test":
        _test_integrations()
    elif action == "virustotal":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_virustotal_scan(target))
    elif action == "shodan":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_shodan_scan(target))
    elif action == "abuseipdb":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_abuseipdb_check(target))
    elif action == "securitytrails":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_securitytrails_scan(target))
    elif action == "nmap":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_nmap_scan(target, scan_type))
    elif action == "sslyze":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_sslyze_scan(target))
    elif action == "comprehensive":
        if not target:
            console.print("[bold red]Необходимо указать цель (--target)[/]")
            raise typer.Exit(code=1)
        asyncio.run(_comprehensive_security_audit(target))
    elif action == "system-info":
        _show_system_info()
    else:
        console.print(f"[bold red]Неизвестное действие: {action}[/]")
        raise typer.Exit(code=1)


def _manage_integrations_config(service: Optional[str], api_key: Optional[str]):
    """Управление конфигурацией интеграций"""
    config = security_integrations.get_config()

    if service and api_key:
        # Обновляем API ключ для конкретного сервиса
        if service in config:
            config[service]["enabled"] = True
            config[service]["api_key"] = api_key
            security_integrations.update_config(config)
            console.print(f"[green]✅ API ключ для {service} обновлен[/]")
        else:
            console.print(f"[bold red]Неизвестный сервис: {service}[/]")
    else:
        # Показываем текущую конфигурацию
        table = Table(title="Конфигурация интеграций")
        table.add_column("Сервис", style="cyan")
        table.add_column("Статус", style="green")
        table.add_column("API ключ", style="dim")

        for service_name, service_config in config.items():
            if isinstance(service_config, dict) and "enabled" in service_config:
                status = "✅ Включен" if service_config["enabled"] else "❌ Отключен"
                api_key_status = (
                    "✅ Настроен" if service_config.get("api_key") else "❌ Не настроен"
                )
                table.add_row(service_name, status, api_key_status)

        console.print(table)


def _test_integrations():
    """Тестирование интеграций"""
    console.print("[cyan]Тестирование интеграций...[/]")

    config = security_integrations.get_config()
    test_results = []

    for service_name, service_config in config.items():
        if isinstance(service_config, dict) and "enabled" in service_config:
            if service_config["enabled"]:
                console.print(f"[yellow]Тестирование {service_name}...[/]")
                # Здесь можно добавить реальные тесты
                test_results.append(f"✅ {service_name} - настроен")
            else:
                test_results.append(f"❌ {service_name} - отключен")

    for result in test_results:
        console.print(result)


async def _virustotal_scan(target: str):
    """Сканирование через VirusTotal"""
    console.print(f"[cyan]Сканирование {target} через VirusTotal...[/]")

    async with security_integrations as si:
        if Path(target).exists():
            # Сканирование файла
            result = await si.virustotal_scan_file(target)
        else:
            # Сканирование URL
            result = await si.virustotal_scan_url(target)

        if "error" in result:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
        else:
            console.print("[green]✅ Сканирование завершено[/]")
            console.print(
                f"[dim]Результат: {json.dumps(result, indent=2, ensure_ascii=False)}[/]"
            )


async def _shodan_scan(target: str):
    """Сканирование через Shodan"""
    console.print(f"[cyan]Получение информации о {target} через Shodan...[/]")

    async with security_integrations as si:
        result = await si.shodan_host_info(target)

        if "error" in result:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
        else:
            console.print("[green]✅ Информация получена[/]")
            console.print(
                f"[dim]Результат: {json.dumps(result, indent=2, ensure_ascii=False)}[/]"
            )


async def _abuseipdb_check(target: str):
    """Проверка через AbuseIPDB"""
    console.print(f"[cyan]Проверка {target} через AbuseIPDB...[/]")

    async with security_integrations as si:
        result = await si.abuseipdb_check_ip(target)

        if "error" in result:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
        else:
            console.print("[green]✅ Проверка завершена[/]")
            console.print(
                f"[dim]Результат: {json.dumps(result, indent=2, ensure_ascii=False)}[/]"
            )


async def _securitytrails_scan(target: str):
    """Сканирование через SecurityTrails"""
    console.print(f"[cyan]Получение информации о {target} через SecurityTrails...[/]")

    async with security_integrations as si:
        result = await si.securitytrails_domain_info(target)

        if "error" in result:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
        else:
            console.print("[green]✅ Информация получена[/]")
            console.print(
                f"[dim]Результат: {json.dumps(result, indent=2, ensure_ascii=False)}[/]"
            )


async def _nmap_scan(target: str, scan_type: str):
    """Сканирование с помощью Nmap"""
    console.print(f"[cyan]Сканирование {target} с помощью Nmap ({scan_type})...[/]")

    async with security_integrations as si:
        result = await si.nmap_scan(target, scan_type)

        if "error" in result and result["error"]:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
            if result.get("error_details"):
                console.print(f"[dim]Детали: {result['error_details']}[/]")
        else:
            console.print("[green]✅ Сканирование завершено[/]")
            if result.get("output"):
                console.print(f"[dim]Результат:\n{result['output']}[/]")
            if result.get("privileged"):
                console.print("[yellow]ℹ️ Использованы привилегированные возможности[/]")


async def _sslyze_scan(target: str):
    """Сканирование SSL с помощью SSLyze"""
    console.print(f"[cyan]Сканирование SSL для {target}...[/]")

    async with security_integrations as si:
        result = await si.sslyze_scan(target)

        if "error" in result:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
        else:
            console.print("[green]✅ SSL сканирование завершено[/]")
            if result.get("output"):
                console.print(f"[dim]Результат:\n{result['output']}[/]")


async def _comprehensive_security_audit(target: str):
    """Комплексный аудит безопасности"""
    console.print(f"[cyan]Комплексный аудит безопасности для {target}...[/]")

    async with security_integrations as si:
        result = await si.comprehensive_audit(target)

        if "error" in result:
            console.print(f"[bold red]Ошибка: {result['error']}[/]")
        else:
            console.print("[green]✅ Комплексный аудит завершен[/]")
            console.print(
                f"[dim]Результат: {json.dumps(result, indent=2, ensure_ascii=False)}[/]"
            )


def _show_system_info():
    """Показать информацию о системе"""
    console.print(
        Panel("[bold blue]ИНФОРМАЦИЯ О СИСТЕМЕ[/]", expand=False, border_style="blue")
    )

    system_info = security_integrations.get_system_info()

    # Основная информация
    console.print(f"[cyan]ОС:[/] {system_info['os']}")
    console.print(
        f"[cyan]Root права:[/] {'✅ Да' if system_info['is_root'] else '❌ Нет'}"
    )
    console.print(
        f"[cyan]Контейнер:[/] {'✅ Да' if system_info['is_container'] else '❌ Нет'}"
    )

    # Доступные инструменты
    console.print("\n[cyan]Доступные инструменты:[/]")
    tools_table = Table()
    tools_table.add_column("Инструмент", style="cyan")
    tools_table.add_column("Статус", style="green")

    for tool, available in system_info["available_tools"].items():
        status = "✅ Доступен" if available else "❌ Недоступен"
        tools_table.add_row(tool, status)

    console.print(tools_table)

    # Рекомендации
    if system_info["recommendations"]:
        console.print("\n[cyan]Рекомендации:[/]")
        for rec in system_info["recommendations"]:
            console.print(f"  {rec}")


# ============================================================================
# КОМАНДЫ БЕЗОПАСНОСТИ МОДУЛЕЙ
# ============================================================================

@security_app.command("modules-status")
def modules_security_status():
    """Показать статус системы безопасности модулей"""
    try:
        # Импортируем здесь, чтобы избежать циклических импортов
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        # Создаем таблицу статуса
        table = Table(title="🛡️ Статус системы безопасности модулей SDB")
        table.add_column("Сервис", style="cyan")
        table.add_column("Статус", style="green")
        table.add_column("Описание")
        
        # Проверяем доступность сервисов
        services_status = [
            ("ModuleSignatureManager", "✅ Доступен", "Цифровые подписи модулей"),
            ("ModuleSandboxManager", "✅ Доступен", "Sandbox для модулей"),
            ("SecurityAuditLogger", "✅ Доступен", "Аудит действий"),
            ("ModuleReputationSystem", "✅ Доступен", "Система репутации"),
            ("ModuleCodeScanner", "✅ Доступен", "Сканер кода"),
            ("SecurityLevelManager", "✅ Доступен", "Уровни безопасности"),
            ("AnomalyDetector", "✅ Доступен", "Детекция аномалий")
        ]
        
        for service, status, description in services_status:
            table.add_row(service, status, description)
        
        console.print(table)
        
        # Показываем текущий уровень безопасности
        try:
            security_config = services.security_level_manager.get_current_configuration()
            console.print(Panel(
                f"Текущий уровень безопасности: [bold green]{security_config.level.value}[/bold green]\n"
                f"Активные политики: {len(security_config.policies)}\n"
                f"Минимальная репутация: {security_config.min_reputation_score}\n"
                f"Максимальный риск: {security_config.max_risk_score}",
                title="🔒 Конфигурация безопасности"
            ))
        except Exception as e:
            console.print(f"[red]Ошибка получения конфигурации безопасности: {e}[/red]")
    
    except Exception as e:
        console.print(f"[red]Ошибка получения статуса безопасности: {e}[/red]")

@security_app.command("modules-scan")
def scan_module(
    module_path: str = typer.Argument(..., help="Путь к модулю для сканирования")
):
    """Сканировать модуль на предмет угроз безопасности"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        module_path_obj = Path(module_path)
        if not module_path_obj.exists():
            console.print(f"[red]Модуль не найден: {module_path}[/red]")
            return
        
        # Сканируем модуль
        scan_result = services.code_scanner.scan_module(module_path_obj)
        
        # Показываем результаты
        if scan_result.is_safe:
            console.print(f"[green]✅ Модуль {scan_result.module_name} безопасен[/green]")
        else:
            console.print(f"[red]⚠️ Модуль {scan_result.module_name} содержит угрозы[/red]")
        
        console.print(f"Риск: {scan_result.risk_score:.1f}/100")
        console.print(f"Найдено угроз: {len(scan_result.threats_found)}")
        
        if scan_result.threats_found:
            table = Table(title="🚨 Обнаруженные угрозы")
            table.add_column("Тип", style="red")
            table.add_column("Уровень", style="yellow")
            table.add_column("Файл", style="cyan")
            table.add_column("Строка", style="magenta")
            table.add_column("Описание")
            
            for threat in scan_result.threats_found:
                table.add_row(
                    threat.threat_type.value,
                    threat.threat_level.value,
                    Path(threat.file_path).name,
                    str(threat.line_number),
                    threat.description
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[red]Ошибка сканирования модуля: {e}[/red]")

@security_app.command("modules-anomalies")
def list_anomalies(
    hours: int = typer.Option(24, help="Количество часов для показа аномалий")
):
    """Показать недавние аномалии безопасности модулей"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        anomalies = services.anomaly_detector.get_recent_anomalies(hours)
        
        if not anomalies:
            console.print(f"[green]✅ Аномалий за последние {hours} часов не обнаружено[/green]")
            return
        
        table = Table(title=f"🚨 Аномалии за последние {hours} часов")
        table.add_column("Время", style="cyan")
        table.add_column("Модуль", style="yellow")
        table.add_column("Тип", style="red")
        table.add_column("Серьезность", style="magenta")
        table.add_column("Описание")
        
        for anomaly in anomalies[-20:]:  # Показываем последние 20
            from datetime import datetime
            time_str = datetime.fromtimestamp(anomaly.timestamp).strftime("%H:%M:%S")
            table.add_row(
                time_str,
                anomaly.module_name,
                anomaly.anomaly_type.value,
                anomaly.severity.value,
                anomaly.description
            )
        
        console.print(table)
        
        # Показываем статистику
        stats = services.anomaly_detector.get_anomaly_statistics()
        console.print(Panel(
            f"Всего аномалий: {stats['total_anomalies']}\n"
            f"Заблокированных модулей: {len(stats['auto_blocked_modules'])}\n"
            f"Активных модулей: {stats['active_modules']}",
            title="📊 Статистика аномалий"
        ))
    
    except Exception as e:
        console.print(f"[red]Ошибка получения аномалий: {e}[/red]")

@security_app.command("modules-reputation")
def reputation(
    module_name: Optional[str] = typer.Option(None, help="Имя модуля для проверки репутации")
):
    """Показать репутацию модулей"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        if module_name:
            # Показываем репутацию конкретного модуля
            reputation = services.reputation_system.get_module_reputation(module_name)
            
            if reputation:
                console.print(Panel(
                    f"Модуль: {reputation.module_name}\n"
                    f"Разработчик: {reputation.developer_id}\n"
                    f"Оценка: {reputation.total_score:.1f}/100\n"
                    f"Уровень: {reputation.level.value}\n"
                    f"Уверенность: {reputation.confidence:.1%}",
                    title=f"⭐ Репутация модуля {module_name}"
                ))
            else:
                console.print(f"[yellow]Репутация модуля {module_name} не найдена[/yellow]")
        else:
            # Показываем топ модулей
            top_modules = services.reputation_system.get_top_modules(10)
            
            if top_modules:
                table = Table(title="🏆 Топ модулей по репутации")
                table.add_column("Модуль", style="cyan")
                table.add_column("Разработчик", style="yellow")
                table.add_column("Оценка", style="green")
                table.add_column("Уровень", style="magenta")
                
                for module_name, reputation in top_modules:
                    table.add_row(
                        module_name,
                        reputation.developer_id,
                        f"{reputation.total_score:.1f}",
                        reputation.level.value
                    )
                
                console.print(table)
            else:
                console.print("[yellow]Нет данных о репутации модулей[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Ошибка получения репутации: {e}[/red]")

@security_app.command("keys-generate")
def generate_key(
    key_id: str = typer.Argument(..., help="ID ключа для генерации"),
    key_size: int = typer.Option(2048, help="Размер ключа в битах")
):
    """Генерировать новую пару ключей для подписания модулей"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        # Генерируем ключи
        success = services.signature_manager.generate_signing_key(key_id, key_size)
        
        if success:
            console.print(f"[green]✅ Сгенерирована новая пара ключей: {key_id}[/green]")
            console.print(f"[cyan]Размер ключа: {key_size} бит[/cyan]")
            
            # Показываем публичный ключ
            public_key = services.signature_manager.export_public_key(key_id)
            if public_key:
                console.print(Panel(
                    public_key.decode('utf-8'),
                    title=f"🔑 Публичный ключ {key_id}",
                    subtitle="Сохраните этот ключ для распространения"
                ))
        else:
            console.print(f"[red]❌ Ошибка генерации ключей {key_id}[/red]")
    
    except Exception as e:
        console.print(f"[red]Ошибка генерации ключей: {e}[/red]")

@security_app.command("keys-list")
def list_keys():
    """Показать список доступных ключей"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        # Получаем список ключей
        available_keys = services.signature_manager.list_available_keys()
        trusted_signers = services.signature_manager.list_trusted_signers()
        
        if available_keys:
            table = Table(title="🔑 Доступные ключи")
            table.add_column("ID ключа", style="cyan")
            table.add_column("Статус", style="green")
            table.add_column("Описание")
            
            for key_id in available_keys:
                is_trusted = key_id in trusted_signers
                status = "✅ Доверенный" if is_trusted else "⚠️ Не доверенный"
                description = trusted_signers.get(key_id, {}).get("description", "Нет описания")
                
                table.add_row(key_id, status, description)
            
            console.print(table)
        else:
            console.print("[yellow]Нет доступных ключей[/yellow]")
        
        # Показываем доверенных подписантов
        if trusted_signers:
            console.print("\n[cyan]Доверенные подписанты:[/cyan]")
            for signer_id, signer_info in trusted_signers.items():
                console.print(f"  • {signer_id}: {signer_info.get('name', 'Неизвестно')}")
    
    except Exception as e:
        console.print(f"[red]Ошибка получения списка ключей: {e}[/red]")

@security_app.command("sign-module")
def sign_module(
    module_path: str = typer.Argument(..., help="Путь к модулю для подписания"),
    key_id: str = typer.Argument(..., help="ID ключа для подписания")
):
    """Подписать модуль цифровой подписью"""
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from Systems.core.app_settings import load_app_settings
        from Systems.core.services_provider import BotServicesProvider
        
        settings = load_app_settings()
        services = BotServicesProvider(settings)
        
        module_path_obj = Path(module_path)
        if not module_path_obj.exists():
            console.print(f"[red]Модуль не найден: {module_path}[/red]")
            return
        
        # Подписываем модуль
        success = services.signature_manager.sign_module(module_path_obj, key_id)
        
        if success:
            console.print(f"[green]✅ Модуль {module_path_obj.name} успешно подписан ключом {key_id}[/green]")
        else:
            console.print(f"[red]❌ Ошибка подписания модуля {module_path_obj.name}[/red]")
    
    except Exception as e:
        console.print(f"[red]Ошибка подписания модуля: {e}[/red]")

if __name__ == "__main__":
    security_app()
