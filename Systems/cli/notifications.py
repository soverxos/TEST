# cli/notifications.py
import asyncio
import json
import logging
import smtplib
import subprocess
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
notifications_app = typer.Typer(
    name="notifications", help="🔔 Управление уведомлениями"
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для уведомлений
NOTIFICATIONS_DIR = Path("Data/notifications")
NOTIFICATIONS_CONFIG_FILE = NOTIFICATIONS_DIR / "notifications_config.json"
NOTIFICATIONS_LOG_FILE = NOTIFICATIONS_DIR / "notifications.log"


def _ensure_notifications_directory():
    """Создать директорию для уведомлений если её нет"""
    NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTIFICATIONS_CONFIG_FILE.exists():
        default_config = {
            "channels": {
                "telegram_admin": {
                    "type": "telegram",
                    "status": "active",
                    "description": "Уведомления администраторам",
                    "config": {"chat_id": None, "bot_token": None},
                },
                "email_support": {
                    "type": "email",
                    "status": "inactive",
                    "description": "Email уведомления",
                    "config": {
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "username": None,
                        "password": None,
                        "from_email": None,
                        "to_email": None,
                    },
                },
                "webhook_monitoring": {
                    "type": "webhook",
                    "status": "active",
                    "description": "Webhook для мониторинга",
                    "config": {"url": None, "method": "POST", "headers": {}},
                },
                "slack_alerts": {
                    "type": "slack",
                    "status": "configured",
                    "description": "Slack уведомления",
                    "config": {"webhook_url": None, "channel": "#alerts"},
                },
            },
            "templates": {
                "system_alert": {
                    "subject": "🚨 Системное уведомление",
                    "body": "Сообщение: {message}\nВремя: {timestamp}\nПриоритет: {priority}",
                },
                "backup_complete": {
                    "subject": "✅ Резервное копирование завершено",
                    "body": "Резервное копирование успешно завершено в {timestamp}",
                },
                "error_report": {
                    "subject": "❌ Ошибка системы",
                    "body": "Произошла ошибка: {error}\nВремя: {timestamp}\nКомпонент: {component}",
                },
            },
        }
        with open(NOTIFICATIONS_CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)


def _load_notifications_config() -> Dict[str, Any]:
    """Загрузить конфигурацию уведомлений"""
    _ensure_notifications_directory()
    try:
        with open(NOTIFICATIONS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"channels": {}, "templates": {}}


def _save_notifications_config(config: Dict[str, Any]):
    """Сохранить конфигурацию уведомлений"""
    _ensure_notifications_directory()
    with open(NOTIFICATIONS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _log_notification_event(channel: str, event: str, details: str = ""):
    """Записать событие уведомления в лог"""
    _ensure_notifications_directory()
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {channel}: {event}"
    if details:
        log_entry += f" - {details}"

    with open(NOTIFICATIONS_LOG_FILE, "a") as f:
        f.write(log_entry + "\n")


@notifications_app.command(name="list", help="Показать список каналов уведомлений.")
def notifications_list_cmd(
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Фильтр по статусу: active, inactive, configured"
    ),
    format: str = typer.Option(
        "table", "--format", "-f", help="Формат вывода: table, json"
    ),
):
    """Показать список каналов уведомлений"""
    try:
        asyncio.run(_notifications_list_async(status, format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'notifications list': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _notifications_list_async(status: Optional[str], format: str):
    """Показать список каналов уведомлений"""
    console.print(
        Panel("[bold blue]КАНАЛЫ УВЕДОМЛЕНИЙ[/]", expand=False, border_style="blue")
    )

    config = _load_notifications_config()
    channels = config.get("channels", {})

    if not channels:
        console.print("[yellow]Каналы уведомлений не найдены[/]")
        return

    # Фильтруем каналы по статусу
    filtered_channels = []
    for channel_name, channel_info in channels.items():
        if status is None or channel_info.get("status") == status:
            filtered_channels.append((channel_name, channel_info))

    if not filtered_channels:
        console.print(f"[yellow]Каналы со статусом '{status}' не найдены[/]")
        return

    if format == "json":
        console.print(json.dumps(channels, indent=2, ensure_ascii=False))
        return

    # Табличный формат
    table = Table(title=f"Каналы уведомлений (показано: {len(filtered_channels)})")
    table.add_column("Канал", style="cyan")
    table.add_column("Тип", style="blue")
    table.add_column("Статус", style="green")
    table.add_column("Описание", style="white")
    table.add_column("Конфигурация", style="yellow")

    for channel_name, channel_info in filtered_channels:
        status = channel_info.get("status", "unknown")
        status_color = {
            "active": "green",
            "inactive": "red",
            "configured": "yellow",
            "error": "red",
        }.get(status, "white")

        # Проверяем конфигурацию
        config_status = (
            "✅ Настроен" if _is_channel_configured(channel_info) else "❌ Не настроен"
        )

        table.add_row(
            channel_name,
            channel_info.get("type", "unknown"),
            f"[{status_color}]{status}[/{status_color}]",
            channel_info.get("description", "Без описания"),
            config_status,
        )

    console.print(table)


def _is_channel_configured(channel_info: Dict[str, Any]) -> bool:
    """Проверить, настроен ли канал"""
    config = channel_info.get("config", {})
    channel_type = channel_info.get("type", "")

    if channel_type == "telegram":
        return bool(config.get("chat_id") and config.get("bot_token"))
    elif channel_type == "email":
        return bool(
            config.get("username") and config.get("password") and config.get("to_email")
        )
    elif channel_type == "webhook":
        return bool(config.get("url"))
    elif channel_type == "slack":
        return bool(config.get("webhook_url"))
    else:
        return False


@notifications_app.command(name="send", help="Отправить уведомление.")
def notifications_send_cmd(
    channel: str = typer.Argument(..., help="Канал для отправки"),
    message: str = typer.Argument(..., help="Текст сообщения"),
    priority: str = typer.Option(
        "normal", "--priority", "-p", help="Приоритет: low, normal, high, urgent"
    ),
    template: Optional[str] = typer.Option(
        None, "--template", "-t", help="Шаблон уведомления"
    ),
    subject: Optional[str] = typer.Option(
        None, "--subject", "-s", help="Тема сообщения"
    ),
):
    """Отправить уведомление"""
    try:
        asyncio.run(
            _notifications_send_async(channel, message, priority, template, subject)
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'notifications send': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _notifications_send_async(
    channel: str,
    message: str,
    priority: str,
    template: Optional[str],
    subject: Optional[str],
):
    """Отправить уведомление"""
    console.print(
        Panel("[bold blue]ОТПРАВКА УВЕДОМЛЕНИЯ[/]", expand=False, border_style="blue")
    )

    config = _load_notifications_config()
    channels = config.get("channels", {})

    if channel not in channels:
        console.print(f"[bold red]Канал '{channel}' не найден[/]")
        raise typer.Exit(code=1)

    channel_info = channels[channel]
    channel_type = channel_info.get("type", "")
    channel_status = channel_info.get("status", "inactive")

    if channel_status != "active":
        console.print(
            f"[yellow]Канал '{channel}' неактивен (статус: {channel_status})[/]"
        )
        return

    # Подготавливаем сообщение
    final_message = message
    final_subject = subject or "Уведомление системы"

    if template:
        templates = config.get("templates", {})
        if template in templates:
            template_info = templates[template]
            template_body = template_info.get("body", message)
            template_subject = template_info.get("subject", final_subject)

            # Заменяем плейсхолдеры
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            template_body = template_body.format(
                message=message,
                timestamp=timestamp,
                priority=priority,
                error=message,
                component="CLI",
            )
            template_subject = template_subject.format(
                message=message, timestamp=timestamp, priority=priority
            )

            final_message = template_body
            final_subject = template_subject
        else:
            console.print(
                f"[yellow]Шаблон '{template}' не найден, используется обычное сообщение[/]"
            )

    console.print(f"[cyan]Канал:[/] {channel}")
    console.print(f"[cyan]Тип:[/] {channel_type}")
    console.print(f"[cyan]Приоритет:[/] {priority}")
    console.print(f"[cyan]Тема:[/] {final_subject}")
    console.print(f"[cyan]Сообщение:[/] {final_message}")

    # Отправляем уведомление
    success = False
    try:
        if channel_type == "telegram":
            success = await _send_telegram_notification(
                channel_info, final_message, priority
            )
        elif channel_type == "email":
            success = await _send_email_notification(
                channel_info, final_subject, final_message, priority
            )
        elif channel_type == "webhook":
            success = await _send_webhook_notification(
                channel_info, final_message, priority
            )
        elif channel_type == "slack":
            success = await _send_slack_notification(
                channel_info, final_message, priority
            )
        else:
            console.print(f"[yellow]Неподдерживаемый тип канала: {channel_type}[/]")
            return
    except Exception as e:
        console.print(f"[bold red]Ошибка при отправке уведомления: {e}[/]")
        _log_notification_event(channel, "send_failed", str(e))
        return

    if success:
        console.print(
            f"[green]✅ Уведомление успешно отправлено через канал '{channel}'[/]"
        )
        _log_notification_event(channel, "send_success", f"priority={priority}")
    else:
        console.print(
            f"[red]❌ Не удалось отправить уведомление через канал '{channel}'[/]"
        )
        _log_notification_event(channel, "send_failed", f"priority={priority}")


async def _send_telegram_notification(
    channel_info: Dict[str, Any], message: str, priority: str
) -> bool:
    """Отправить уведомление в Telegram с реальной интеграцией"""
    config = channel_info.get("config", {})
    chat_id = config.get("chat_id")
    bot_token = config.get("bot_token")

    if not chat_id or not bot_token:
        console.print(
            "[yellow]Telegram не настроен (отсутствует chat_id или bot_token)[/]"
        )
        logger.warning(
            f"Telegram notification failed: missing config - chat_id: {bool(chat_id)}, bot_token: {bool(bot_token)}"
        )
        return False

    try:
        # Формируем сообщение с приоритетом и временной меткой
        priority_emoji = {"low": "🔵", "normal": "⚪", "high": "🟡", "urgent": "🔴"}
        emoji = priority_emoji.get(priority, "⚪")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted_message = f"""
{emoji} **{priority.upper()} УВЕДОМЛЕНИЕ**
⏰ {timestamp}

{message}

---
🤖 SwiftDevBot
        """.strip()

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": formatted_message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        console.print(
            f"[cyan]Отправка уведомления в Telegram (chat_id: {chat_id})...[/]"
        )

        response = requests.post(url, json=data, timeout=15)

        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                console.print("[green]✅ Уведомление отправлено в Telegram[/]")
                logger.info(
                    f"Telegram notification sent successfully to chat_id: {chat_id}"
                )
                return True
            else:
                error_msg = result.get("description", "Unknown error")
                console.print(f"[red]❌ Ошибка Telegram API: {error_msg}[/]")
                logger.error(f"Telegram API error: {error_msg}")
                return False
        else:
            console.print(f"[red]❌ HTTP ошибка: {response.status_code}[/]")
            logger.error(f"Telegram HTTP error: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        console.print("[red]❌ Таймаут при отправке в Telegram[/]")
        logger.error("Telegram notification timeout")
        return False
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Ошибка сети: {e}[/]")
        logger.error(f"Telegram network error: {e}")
        return False
    except Exception as e:
        console.print(f"[red]❌ Неожиданная ошибка: {e}[/]")
        logger.error(f"Telegram unexpected error: {e}")
        return False


async def _send_email_notification(
    channel_info: Dict[str, Any], subject: str, message: str, priority: str
) -> bool:
    """Отправить уведомление по email с улучшенной обработкой ошибок"""
    config = channel_info.get("config", {})

    smtp_server = config.get("smtp_server")
    smtp_port = config.get("smtp_port", 587)
    username = config.get("username")
    password = config.get("password")
    from_email = config.get("from_email")
    to_email = config.get("to_email")

    if not all([smtp_server, username, password, from_email, to_email]):
        console.print(
            "[yellow]Email не настроен (отсутствуют необходимые параметры)[/]"
        )
        logger.warning("Email notification failed: missing configuration")
        return False

    try:
        # Формируем сообщение с улучшенным форматированием
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        priority_emoji = {"low": "🔵", "normal": "⚪", "high": "🟡", "urgent": "🔴"}
        emoji = priority_emoji.get(priority, "⚪")

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = f"{emoji} [{priority.upper()}] {subject}"

        body = f"""
🤖 SwiftDevBot - Уведомление

Приоритет: {priority.upper()}
Время: {timestamp}

{message}

Это автоматическое уведомление от системы SwiftDevBot.
        """

        msg.attach(MIMEText(body, "plain", "utf-8"))

        console.print(f"[cyan]Отправка email уведомления на {to_email}...[/]")

        # Подключение к SMTP серверу
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()

        console.print("[green]✅ Email уведомление отправлено[/]")
        logger.info(f"Email notification sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        console.print("[red]❌ Ошибка аутентификации SMTP[/]")
        logger.error("Email SMTP authentication error")
        return False
    except smtplib.SMTPRecipientsRefused:
        console.print("[red]❌ Неверный адрес получателя[/]")
        logger.error(f"Email recipient refused: {to_email}")
        return False
    except smtplib.SMTPServerDisconnected:
        console.print("[red]❌ Соединение с SMTP сервером разорвано[/]")
        logger.error("Email SMTP server disconnected")
        return False
    except Exception as e:
        console.print(f"[red]❌ Ошибка отправки email: {e}[/]")
        logger.error(f"Email sending error: {e}")
        return False


async def _send_webhook_notification(
    channel_info: Dict[str, Any], message: str, priority: str
) -> bool:
    """Отправить уведомление через webhook с улучшенной обработкой"""
    config = channel_info.get("config", {})
    url = config.get("url")
    method = config.get("method", "POST")
    headers = config.get("headers", {})

    if not url:
        console.print("[yellow]Webhook не настроен (отсутствует URL)[/]")
        logger.warning("Webhook notification failed: missing URL")
        return False

    try:
        timestamp = datetime.now().isoformat()
        data = {
            "message": message,
            "priority": priority,
            "timestamp": timestamp,
            "source": "swiftdevbot",
            "version": "1.0",
        }

        console.print(f"[cyan]Отправка webhook уведомления на {url}...[/]")

        response = requests.request(method, url, json=data, headers=headers, timeout=15)

        if response.status_code in [200, 201, 202]:
            console.print("[green]✅ Webhook уведомление отправлено[/]")
            logger.info(f"Webhook notification sent successfully to {url}")
            return True
        else:
            console.print(f"[red]❌ Webhook ошибка: HTTP {response.status_code}[/]")
            logger.error(f"Webhook HTTP error: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        console.print("[red]❌ Таймаут при отправке webhook[/]")
        logger.error("Webhook notification timeout")
        return False
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Ошибка сети webhook: {e}[/]")
        logger.error(f"Webhook network error: {e}")
        return False
    except Exception as e:
        console.print(f"[red]❌ Неожиданная ошибка webhook: {e}[/]")
        logger.error(f"Webhook unexpected error: {e}")
        return False


async def _send_slack_notification(
    channel_info: Dict[str, Any], message: str, priority: str
) -> bool:
    """Отправить уведомление в Slack с улучшенной интеграцией"""
    config = channel_info.get("config", {})
    webhook_url = config.get("webhook_url")
    channel = config.get("channel", "#alerts")

    if not webhook_url:
        console.print("[yellow]Slack не настроен (отсутствует webhook_url)[/]")
        logger.warning("Slack notification failed: missing webhook_url")
        return False

    try:
        # Формируем Slack сообщение с приоритетом
        priority_emoji = {"low": "🔵", "normal": "⚪", "high": "🟡", "urgent": "🔴"}
        emoji = priority_emoji.get(priority, "⚪")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        slack_data = {
            "channel": channel,
            "text": f"{emoji} *{priority.upper()} УВЕДОМЛЕНИЕ*",
            "attachments": [
                {
                    "color": {
                        "low": "#3498db",
                        "normal": "#95a5a6",
                        "high": "#f39c12",
                        "urgent": "#e74c3c",
                    }.get(priority, "#95a5a6"),
                    "text": message,
                    "fields": [
                        {
                            "title": "Приоритет",
                            "value": priority.upper(),
                            "short": True,
                        },
                        {"title": "Время", "value": timestamp, "short": True},
                        {"title": "Источник", "value": "SwiftDevBot", "short": True},
                    ],
                    "footer": "SwiftDevBot",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
        }

        console.print(f"[cyan]Отправка Slack уведомления в канал {channel}...[/]")

        response = requests.post(webhook_url, json=slack_data, timeout=15)

        if response.status_code == 200:
            console.print("[green]✅ Slack уведомление отправлено[/]")
            logger.info(f"Slack notification sent successfully to channel {channel}")
            return True
        else:
            console.print(f"[red]❌ Slack ошибка: HTTP {response.status_code}[/]")
            logger.error(f"Slack HTTP error: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        console.print("[red]❌ Таймаут при отправке в Slack[/]")
        logger.error("Slack notification timeout")
        return False
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Ошибка сети Slack: {e}[/]")
        logger.error(f"Slack network error: {e}")
        return False
    except Exception as e:
        console.print(f"[red]❌ Неожиданная ошибка Slack: {e}[/]")
        logger.error(f"Slack unexpected error: {e}")
        return False


@notifications_app.command(name="configure", help="Настроить канал уведомлений.")
def notifications_configure_cmd(
    channel: str = typer.Argument(..., help="Канал для настройки"),
    config_file: Optional[str] = typer.Option(
        None, "--config", "-c", help="Файл конфигурации"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Интерактивная настройка"
    ),
):
    """Настроить канал уведомлений"""
    try:
        asyncio.run(_notifications_configure_async(channel, config_file, interactive))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'notifications configure': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _notifications_configure_async(
    channel: str, config_file: Optional[str], interactive: bool
):
    """Настроить канал уведомлений"""
    from Systems.cli.utils import confirm_action

    console.print(
        Panel(
            f"[bold blue]НАСТРОЙКА КАНАЛА: {channel}[/]",
            expand=False,
            border_style="blue",
        )
    )

    config = _load_notifications_config()
    channels = config.get("channels", {})

    if channel not in channels:
        console.print(f"[bold red]Канал '{channel}' не найден[/]")
        raise typer.Exit(code=1)

    channel_info = channels[channel]
    channel_type = channel_info.get("type", "")

    console.print(f"[cyan]Канал:[/] {channel}")
    console.print(f"[cyan]Тип:[/] {channel_type}")
    console.print(f"[cyan]Текущий статус:[/] {channel_info.get('status', 'unknown')}")

    if config_file:
        console.print(f"[cyan]Файл конфигурации:[/] {config_file}")

        # Загружаем конфигурацию из файла
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                console.print(
                    f"[bold red]Файл конфигурации не найден: {config_file}[/]"
                )
                raise typer.Exit(code=1)

            # Читаем файл конфигурации
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    import yaml

                    file_config = yaml.safe_load(f)
                elif config_path.suffix.lower() == ".json":
                    import json

                    file_config = json.load(f)
                else:
                    console.print(
                        f"[bold red]Неподдерживаемый формат файла: {config_path.suffix}[/]"
                    )
                    raise typer.Exit(code=1)

            # Применяем конфигурацию к каналу
            if channel in file_config:
                channel_config = file_config[channel]
                channels[channel].update(channel_config)
                _save_notifications_config(config)
                console.print(
                    f"[green]Конфигурация для канала '{channel}' успешно загружена из файла![/]"
                )
            else:
                console.print(
                    f"[yellow]Канал '{channel}' не найден в файле конфигурации.[/]"
                )
                console.print(
                    f"[cyan]Доступные каналы в файле: {', '.join(file_config.keys())}[/]"
                )

        except Exception as e:
            console.print(f"[bold red]Ошибка при загрузке конфигурации: {e}[/]")
            raise typer.Exit(code=1)
    elif interactive:
        await _configure_channel_interactive(channel, channel_info, config)
    else:
        console.print(
            "[yellow]Используйте --interactive для интерактивной настройки[/]"
        )
        console.print("[dim]Или укажите файл конфигурации с --config[/]")


@notifications_app.command(name="test", help="Протестировать отправку уведомления.")
def notifications_test_cmd(
    channel: str = typer.Argument(..., help="Канал для тестирования"),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Тестовое сообщение"
    ),
    priority: str = typer.Option(
        "normal", "--priority", "-p", help="Приоритет: low, normal, high, urgent"
    ),
):
    """Протестировать отправку уведомления в указанный канал"""
    try:
        asyncio.run(_notifications_test_async(channel, message, priority))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'notifications test': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _notifications_test_async(
    channel: str, message: Optional[str], priority: str
):
    """Протестировать отправку уведомления"""
    console.print(
        Panel(
            f"[bold blue]ТЕСТИРОВАНИЕ УВЕДОМЛЕНИЙ: {channel}[/]",
            expand=False,
            border_style="blue",
        )
    )

    config = _load_notifications_config()
    channels = config.get("channels", {})

    if channel not in channels:
        console.print(f"[bold red]❌ Канал '{channel}' не найден[/]")
        console.print(f"[cyan]Доступные каналы: {', '.join(channels.keys())}[/]")
        raise typer.Exit(code=1)

    channel_info = channels[channel]
    if channel_info.get("status") != "active":
        console.print(
            f"[yellow]⚠️ Канал '{channel}' неактивен (статус: {channel_info.get('status')})[/]"
        )
        if not typer.confirm("Продолжить тестирование?"):
            raise typer.Exit(code=1)

    # Формируем тестовое сообщение
    if not message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Это тестовое уведомление от SwiftDevBot\nВремя отправки: {timestamp}\nПриоритет: {priority.upper()}"

    console.print(f"[cyan]Отправка тестового уведомления в канал '{channel}'...[/]")
    console.print(
        f"[dim]Сообщение: {message[:100]}{'...' if len(message) > 100 else ''}[/]"
    )

    # Отправляем уведомление
    success = await _send_notification_by_type(channel_info, message, priority)

    if success:
        console.print("[bold green]✅ Тест уведомления прошел успешно![/]")
        logger.info(f"Notification test successful for channel: {channel}")
    else:
        console.print("[bold red]❌ Тест уведомления не удался[/]")
        logger.error(f"Notification test failed for channel: {channel}")
        raise typer.Exit(code=1)


async def _send_notification_by_type(
    channel_info: Dict[str, Any], message: str, priority: str
) -> bool:
    """Отправить уведомление по типу канала"""
    channel_type = channel_info.get("type")

    if channel_type == "telegram":
        return await _send_telegram_notification(channel_info, message, priority)
    elif channel_type == "email":
        subject = "Тестовое уведомление"
        return await _send_email_notification(channel_info, subject, message, priority)
    elif channel_type == "webhook":
        return await _send_webhook_notification(channel_info, message, priority)
    elif channel_type == "slack":
        return await _send_slack_notification(channel_info, message, priority)
    else:
        console.print(f"[yellow]Неподдерживаемый тип канала: {channel_type}[/]")
        return False


async def _configure_channel_interactive(
    channel: str, channel_info: Dict[str, Any], config: Dict[str, Any]
):
    """Интерактивная настройка канала уведомлений"""
    channel_type = channel_info.get("type")

    console.print(f"[cyan]Настройка канала '{channel}' (тип: {channel_type})[/]")

    if channel_type == "telegram":
        await _configure_telegram_interactive(channel, channel_info, config)
    elif channel_type == "email":
        await _configure_email_interactive(channel, channel_info, config)
    elif channel_type == "webhook":
        await _configure_webhook_interactive(channel, channel_info, config)
    elif channel_type == "slack":
        await _configure_slack_interactive(channel, channel_info, config)
    else:
        console.print(
            f"[yellow]Интерактивная настройка для типа '{channel_type}' не поддерживается[/]"
        )


async def _configure_telegram_interactive(
    channel: str, channel_info: Dict[str, Any], config: Dict[str, Any]
):
    """Интерактивная настройка Telegram канала"""
    console.print("[cyan]Настройка Telegram канала:[/]")

    # Получаем текущие значения
    current_config = channel_info.get("config", {})
    current_chat_id = current_config.get("chat_id")
    current_bot_token = current_config.get("bot_token")

    # Chat ID
    if current_chat_id:
        console.print(f"[dim]Текущий chat_id: {current_chat_id}[/]")
    chat_id = input("Chat ID (или Enter для пропуска): ").strip()
    if not chat_id and current_chat_id:
        chat_id = current_chat_id

    # Bot Token
    if current_bot_token:
        console.print(f"[dim]Текущий bot_token: {'*' * len(current_bot_token)}[/]")
    bot_token = input("Bot Token (или Enter для пропуска): ").strip()
    if not bot_token and current_bot_token:
        bot_token = current_bot_token

    # Обновляем конфигурацию
    if chat_id and bot_token:
        config["channels"][channel]["config"]["chat_id"] = chat_id
        config["channels"][channel]["config"]["bot_token"] = bot_token
        config["channels"][channel]["status"] = "active"

        _save_notifications_config(config)
        console.print("[green]✅ Telegram канал настроен[/]")

        # Тестируем подключение
        if typer.confirm("Протестировать подключение?"):
            test_message = "Тестовое уведомление от SwiftDevBot"
            success = await _send_telegram_notification(
                config["channels"][channel], test_message, "normal"
            )
            if success:
                console.print("[green]✅ Тест подключения прошел успешно![/]")
            else:
                console.print("[red]❌ Тест подключения не удался[/]")
    else:
        console.print("[yellow]Недостаточно данных для настройки Telegram[/]")


async def _configure_email_interactive(
    channel: str, channel_info: Dict[str, Any], config: Dict[str, Any]
):
    """Интерактивная настройка Email канала"""
    console.print("[cyan]Настройка Email канала:[/]")

    current_config = channel_info.get("config", {})

    # SMTP сервер
    smtp_server = input(
        f"SMTP сервер (по умолчанию: {current_config.get('smtp_server', 'smtp.gmail.com')}): "
    ).strip()
    if not smtp_server:
        smtp_server = current_config.get("smtp_server", "smtp.gmail.com")

    # SMTP порт
    smtp_port_input = input(
        f"SMTP порт (по умолчанию: {current_config.get('smtp_port', 587)}): "
    ).strip()
    smtp_port = (
        int(smtp_port_input)
        if smtp_port_input
        else current_config.get("smtp_port", 587)
    )

    # Учетные данные
    username = input("Email пользователь: ").strip()
    password = input("Email пароль: ").strip()
    from_email = input("Email отправителя: ").strip()
    to_email = input("Email получателя: ").strip()

    if all([username, password, from_email, to_email]):
        config["channels"][channel]["config"].update(
            {
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "username": username,
                "password": password,
                "from_email": from_email,
                "to_email": to_email,
            }
        )
        config["channels"][channel]["status"] = "active"

        _save_notifications_config(config)
        console.print("[green]✅ Email канал настроен[/]")

        # Тестируем подключение
        if typer.confirm("Протестировать подключение?"):
            test_message = "Тестовое уведомление от SwiftDevBot"
            success = await _send_email_notification(
                config["channels"][channel], "Тест", test_message, "normal"
            )
            if success:
                console.print("[green]✅ Тест подключения прошел успешно![/]")
            else:
                console.print("[red]❌ Тест подключения не удался[/]")
    else:
        console.print("[yellow]Недостаточно данных для настройки Email[/]")


async def _configure_webhook_interactive(
    channel: str, channel_info: Dict[str, Any], config: Dict[str, Any]
):
    """Интерактивная настройка Webhook канала"""
    console.print("[cyan]Настройка Webhook канала:[/]")

    current_config = channel_info.get("config", {})
    current_url = current_config.get("url")

    if current_url:
        console.print(f"[dim]Текущий URL: {current_url}[/]")

    url = input("Webhook URL: ").strip()
    if not url and current_url:
        url = current_url

    if url:
        config["channels"][channel]["config"]["url"] = url
        config["channels"][channel]["status"] = "active"

        _save_notifications_config(config)
        console.print("[green]✅ Webhook канал настроен[/]")

        # Тестируем подключение
        if typer.confirm("Протестировать подключение?"):
            test_message = "Тестовое уведомление от SwiftDevBot"
            success = await _send_webhook_notification(
                config["channels"][channel], test_message, "normal"
            )
            if success:
                console.print("[green]✅ Тест подключения прошел успешно![/]")
            else:
                console.print("[red]❌ Тест подключения не удался[/]")
    else:
        console.print("[yellow]URL не указан[/]")


async def _configure_slack_interactive(
    channel: str, channel_info: Dict[str, Any], config: Dict[str, Any]
):
    """Интерактивная настройка Slack канала"""
    console.print("[cyan]Настройка Slack канала:[/]")

    current_config = channel_info.get("config", {})
    current_webhook_url = current_config.get("webhook_url")
    current_channel = current_config.get("channel", "#alerts")

    if current_webhook_url:
        console.print(f"[dim]Текущий webhook_url: {'*' * len(current_webhook_url)}[/]")

    webhook_url = input("Slack Webhook URL: ").strip()
    if not webhook_url and current_webhook_url:
        webhook_url = current_webhook_url

    channel_name = input(f"Slack канал (по умолчанию: {current_channel}): ").strip()
    if not channel_name:
        channel_name = current_channel

    if webhook_url:
        config["channels"][channel]["config"].update(
            {"webhook_url": webhook_url, "channel": channel_name}
        )
        config["channels"][channel]["status"] = "active"

        _save_notifications_config(config)
        console.print("[green]✅ Slack канал настроен[/]")

        # Тестируем подключение
        if typer.confirm("Протестировать подключение?"):
            test_message = "Тестовое уведомление от SwiftDevBot"
            success = await _send_slack_notification(
                config["channels"][channel], test_message, "normal"
            )
            if success:
                console.print("[green]✅ Тест подключения прошел успешно![/]")
            else:
                console.print("[red]❌ Тест подключения не удался[/]")
    else:
        console.print("[yellow]Webhook URL не указан[/]")


if __name__ == "__main__":
    notifications_app()
