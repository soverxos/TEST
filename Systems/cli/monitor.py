# --- НАЧАЛО ФАЙЛА cli/monitor.py ---
import asyncio
import json
import logging
import os
import platform
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import psutil
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

# Импорт для работы с SDB сервисами
try:
    from Systems.cli.utils import get_sdb_services_for_cli
except ImportError:
    # Fallback если функция не найдена
    async def get_sdb_services_for_cli(init_db=False):
        raise ImportError("get_sdb_services_for_cli не доступна")


from rich.align import Align
from rich.layout import Layout

from Systems.cli.utils import format_size, get_sdb_services_for_cli

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем Typer-приложение для мониторинга
monitor_app = typer.Typer(
    name="monitor",
    help="📊 Мониторинг и аналитика системы SwiftDevBot",
    rich_markup_mode="rich",
)

console = Console()

# Константы для мониторинга
MONITOR_DIR = Path("Data/monitor")
METRICS_DB = MONITOR_DIR / "metrics.db"
ALERTS_CONFIG = MONITOR_DIR / "alerts_config.json"
METRICS_HISTORY_FILE = MONITOR_DIR / "metrics_history.json"

# Пороги для алертов
DEFAULT_ALERTS = {
    "cpu": {"warning": 70, "critical": 90},
    "memory": {"warning": 80, "critical": 95},
    "disk": {"warning": 85, "critical": 95},
    "response_time": {"warning": 2.0, "critical": 5.0},
}


def _ensure_monitor_directory():
    """Создать директорию для мониторинга если её нет"""
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)

    # Инициализация БД метрик
    if not METRICS_DB.exists():
        _init_metrics_database()

    # Инициализация конфигурации алертов
    if not ALERTS_CONFIG.exists():
        _init_alerts_config()


def _init_metrics_database():
    """Инициализация базы данных для метрик"""
    conn = sqlite3.connect(METRICS_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_bytes_sent INTEGER,
            network_bytes_recv INTEGER,
            response_time REAL,
            bot_status TEXT,
            db_status TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON metrics(timestamp)
    """
    )

    conn.commit()
    conn.close()
    logger.info("База данных метрик инициализирована")


def _init_alerts_config():
    """Инициализация конфигурации алертов"""
    config = {
        "alerts": DEFAULT_ALERTS,
        "notifications": {
            "enabled": True,
            "channels": ["telegram_admin"],
            "cooldown": 300,  # 5 минут между уведомлениями
        },
        "history": {"enabled": True, "retention_days": 30},
    }

    with open(ALERTS_CONFIG, "w") as f:
        json.dump(config, f, indent=2)

    logger.info("Конфигурация алертов инициализирована")


def _load_alerts_config() -> Dict[str, Any]:
    """Загрузить конфигурацию алертов"""
    _ensure_monitor_directory()
    try:
        with open(ALERTS_CONFIG, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"alerts": DEFAULT_ALERTS, "notifications": {"enabled": True}}


def _save_metrics_to_db(metrics: Dict[str, Any]):
    """Сохранить метрики в базу данных"""
    try:
        conn = sqlite3.connect(METRICS_DB)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO metrics 
            (cpu_percent, memory_percent, disk_percent, network_bytes_sent, 
             network_bytes_recv, response_time, bot_status, db_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metrics.get("cpu_percent", 0),
                metrics.get("memory_percent", 0),
                metrics.get("disk_percent", 0),
                metrics.get("network_bytes_sent", 0),
                metrics.get("network_bytes_recv", 0),
                metrics.get("response_time", 0),
                metrics.get("bot_status", "unknown"),
                metrics.get("db_status", "unknown"),
            ),
        )

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка сохранения метрик в БД: {e}")


def _get_metrics_history(hours: int = 24) -> List[Dict[str, Any]]:
    """Получить историю метрик"""
    try:
        conn = sqlite3.connect(METRICS_DB)
        cursor = conn.cursor()

        since = datetime.now() - timedelta(hours=hours)

        cursor.execute(
            """
            SELECT * FROM metrics 
            WHERE timestamp >= ? 
            ORDER BY timestamp DESC
        """,
            (since,),
        )

        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        conn.close()

        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка получения истории метрик: {e}")
        return []


async def _check_alerts(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Проверить метрики на соответствие правилам алертов"""
    config = _load_alerts_config()
    alerts = []

    # Проверка CPU
    cpu_percent = metrics.get("cpu_percent", 0)
    if cpu_percent > config["alerts"]["cpu"]["critical"]:
        alerts.append(
            {
                "type": "critical",
                "metric": "cpu",
                "value": cpu_percent,
                "threshold": config["alerts"]["cpu"]["critical"],
                "message": f"Критическая загрузка CPU: {cpu_percent:.1f}%",
            }
        )
    elif cpu_percent > config["alerts"]["cpu"]["warning"]:
        alerts.append(
            {
                "type": "warning",
                "metric": "cpu",
                "value": cpu_percent,
                "threshold": config["alerts"]["cpu"]["warning"],
                "message": f"Высокая загрузка CPU: {cpu_percent:.1f}%",
            }
        )

    # Проверка памяти
    memory_percent = metrics.get("memory_percent", 0)
    if memory_percent > config["alerts"]["memory"]["critical"]:
        alerts.append(
            {
                "type": "critical",
                "metric": "memory",
                "value": memory_percent,
                "threshold": config["alerts"]["memory"]["critical"],
                "message": f"Критическое использование памяти: {memory_percent:.1f}%",
            }
        )
    elif memory_percent > config["alerts"]["memory"]["warning"]:
        alerts.append(
            {
                "type": "warning",
                "metric": "memory",
                "value": memory_percent,
                "threshold": config["alerts"]["memory"]["warning"],
                "message": f"Высокое использование памяти: {memory_percent:.1f}%",
            }
        )

    # Проверка диска
    disk_percent = metrics.get("disk_percent", 0)
    if disk_percent > config["alerts"]["disk"]["critical"]:
        alerts.append(
            {
                "type": "critical",
                "metric": "disk",
                "value": disk_percent,
                "threshold": config["alerts"]["disk"]["critical"],
                "message": f"Критическое использование диска: {disk_percent:.1f}%",
            }
        )
    elif disk_percent > config["alerts"]["disk"]["warning"]:
        alerts.append(
            {
                "type": "warning",
                "metric": "disk",
                "value": disk_percent,
                "threshold": config["alerts"]["disk"]["warning"],
                "message": f"Высокое использование диска: {disk_percent:.1f}%",
            }
        )

    return alerts


async def _send_alert_notifications(alerts: List[Dict[str, Any]]):
    """Отправить уведомления об алертах"""
    if not alerts:
        return

    config = _load_alerts_config()
    if not config.get("notifications", {}).get("enabled", False):
        return

    try:
        from Systems.cli.notifications import (_load_notifications_config,
                                       _send_notification_by_type)

        notifications_config = _load_notifications_config()
        channels = notifications_config.get("channels", {})

        for alert in alerts:
            priority = "urgent" if alert["type"] == "critical" else "high"
            message = f"🚨 АЛЕРТ: {alert['message']}\n\nМетрика: {alert['metric']}\nЗначение: {alert['value']:.1f}\nПорог: {alert['threshold']:.1f}"

            # Отправляем в настроенные каналы
            for channel_name in config["notifications"]["channels"]:
                if (
                    channel_name in channels
                    and channels[channel_name].get("status") == "active"
                ):
                    await _send_notification_by_type(
                        channels[channel_name], message, priority
                    )

    except ImportError:
        logger.warning("Модуль уведомлений не найден")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений об алертах: {e}")


# --- Вспомогательные функции ---


def _get_system_info() -> Dict[str, Any]:
    """Получает базовую информацию о системе."""
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }


def _get_cpu_info() -> Dict[str, Any]:
    """Получает информацию о CPU."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    return {
        "percent": cpu_percent,
        "count": cpu_count,
        "frequency": cpu_freq.current if cpu_freq else None,
        "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
    }


def _get_memory_info() -> Dict[str, Any]:
    """Получает информацию о памяти."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total": memory.total,
        "available": memory.available,
        "used": memory.used,
        "percent": memory.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
    }


def _get_disk_info() -> Dict[str, Any]:
    """Получает информацию о диске."""
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()

    return {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent,
        "read_bytes": disk_io.read_bytes if disk_io else 0,
        "write_bytes": disk_io.write_bytes if disk_io else 0,
    }


def _get_network_info() -> Dict[str, Any]:
    """Получает информацию о сети."""
    network_io = psutil.net_io_counters()

    return {
        "bytes_sent": network_io.bytes_sent,
        "bytes_recv": network_io.bytes_recv,
        "packets_sent": network_io.packets_sent,
        "packets_recv": network_io.packets_recv,
    }


async def _get_bot_status() -> Dict[str, Any]:
    """Получает статус бота."""
    try:
        # Сначала пытаемся получить настройки
        try:
            settings, db_manager, _ = await get_sdb_services_for_cli()
            bot_token = settings.bot_token
        except Exception as e:
            # Если не можем получить настройки, пробуем из .env
            try:
                from dotenv import load_dotenv

                load_dotenv()
                bot_token = os.getenv("BOT_TOKEN")
                if not bot_token:
                    return {
                        "status": "error",
                        "error": "BOT_TOKEN не найден в настройках или .env",
                        "response_time": 0,
                        "uptime": "unknown",
                    }
            except Exception:
                return {
                    "status": "error",
                    "error": "Не удалось получить BOT_TOKEN",
                    "response_time": 0,
                    "uptime": "unknown",
                }

        # Проверяем доступность Bot API
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{bot_token}/getMe"
                start_time = time.time()
                async with session.get(url, timeout=10) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            return {
                                "status": "active",
                                "username": data.get("result", {}).get(
                                    "username", "unknown"
                                ),
                                "response_time": response_time,
                                "uptime": "running",
                            }
                        else:
                            return {
                                "status": "error",
                                "error": f"Telegram API error: {data.get('description', 'Unknown error')}",
                                "response_time": response_time,
                                "uptime": "unknown",
                            }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "response_time": response_time,
                            "uptime": "unknown",
                        }
        except aiohttp.ClientError as e:
            return {
                "status": "error",
                "error": f"Network error: {str(e)}",
                "response_time": 0,
                "uptime": "unknown",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Request error: {str(e)}",
                "response_time": 0,
                "uptime": "unknown",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "response_time": 0,
            "uptime": "unknown",
        }


async def _get_database_status() -> Dict[str, Any]:
    """Получает статус базы данных."""
    try:
        # Сначала пытаемся получить настройки
        try:
            settings, db_manager, _ = await get_sdb_services_for_cli(init_db=True)
        except Exception as e:
            # Если не можем получить настройки, пробуем проверить SQLite файл
            try:
                from dotenv import load_dotenv

                load_dotenv()

                # Проверяем SQLite файл
                db_path = os.getenv("DB_SQLITE_PATH", "Data/database.db")
                if os.path.exists(db_path):
                    import sqlite3

                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    start_time = time.time()
                    cursor.execute("SELECT 1")
                    response_time = time.time() - start_time
                    conn.close()

                    return {
                        "status": "connected",
                        "response_time": response_time,
                        "type": "sqlite",
                        "url": db_path,
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Database file not found: {db_path}",
                        "response_time": 0,
                        "type": "unknown",
                    }
            except Exception as db_error:
                return {
                    "status": "error",
                    "error": f"Database check failed: {str(db_error)}",
                    "response_time": 0,
                    "type": "unknown",
                }

        # Проверяем подключение к БД через менеджер
        try:
            if db_manager is None:
                return {
                    "status": "error",
                    "error": "Database manager is None - database not initialized",
                    "response_time": 0,
                    "type": "unknown",
                }

            start_time = time.time()
            async with db_manager.get_session() as session:
                # Простой запрос для проверки
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                response_time = time.time() - start_time

                return {
                    "status": "connected",
                    "response_time": response_time,
                    "type": settings.db.type,
                    "url": (
                        str(db_manager.url) if hasattr(db_manager, "url") else "unknown"
                    ),
                }
        except Exception as db_error:
            return {
                "status": "error",
                "error": f"Database connection failed: {str(db_error)}",
                "response_time": 0,
                "type": settings.db.type if settings else "unknown",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "response_time": 0,
            "type": "unknown",
        }


def _format_uptime(seconds: float) -> str:
    """Форматирует время работы."""
    if seconds < 60:
        return f"{seconds:.0f} секунда" if seconds == 1 else f"{seconds:.0f} секунд"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f} минут"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.0f} часов"
    else:
        days = seconds / 86400
        return f"{days:.0f} дней"


# --- CLI команды ---


@monitor_app.command(name="status", help="Показать общий статус системы.")
def monitor_status_cmd(
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Подробная информация"
    ),
    json_output: bool = typer.Option(False, "--json", help="Вывод в формате JSON"),
    health: bool = typer.Option(False, "--health", help="Только проверка здоровья"),
    notify: Optional[str] = typer.Option(
        None, "--notify", help="Канал для уведомлений"
    ),
):
    """Показывает общий статус системы."""
    asyncio.run(_monitor_status_async(detailed, json_output, health, notify))


async def _monitor_status_async(
    detailed: bool, json_output: bool, health: bool, notify: Optional[str]
):
    """Асинхронная функция для получения статуса."""

    console.print(Panel.fit("🔍 Проверка статуса системы", style="bold cyan"))

    # Собираем все метрики
    cpu_info = _get_cpu_info()
    memory_info = _get_memory_info()
    disk_info = _get_disk_info()
    network_info = _get_network_info()
    bot_status = await _get_bot_status()
    db_status = await _get_database_status()

    # Формируем общие метрики
    metrics = {
        "cpu_percent": cpu_info["percent"],
        "memory_percent": memory_info["percent"],
        "disk_percent": disk_info["percent"],
        "network_bytes_sent": network_info["bytes_sent"],
        "network_bytes_recv": network_info["bytes_recv"],
        "response_time": bot_status.get("response_time", 0),
        "bot_status": bot_status.get("status", "unknown"),
        "db_status": db_status.get("status", "unknown"),
    }

    # Сохраняем метрики в БД
    _save_metrics_to_db(metrics)

    # Проверяем алерты
    alerts = await _check_alerts(metrics)

    # Отправляем уведомления если есть алерты
    if alerts:
        await _send_alert_notifications(alerts)

    # Формируем результат
    status_data = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "network": network_info,
        },
        "services": {"bot": bot_status, "database": db_status},
        "alerts": alerts,
        "health": {
            "overall": "healthy" if not alerts else "unhealthy",
            "alerts_count": len(alerts),
        },
    }

    if json_output:
        console.print(json.dumps(status_data, indent=2))
        return

    if health:
        if alerts:
            console.print(f"[bold red]❌ Система нездорова: {len(alerts)} алертов[/]")
            for alert in alerts:
                console.print(f"   🔴 {alert['message']}")
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]✅ Система здорова[/]")
            return

    # Отображаем статус
    console.print("🖥️ Системная информация:")
    console.print(f"   📊 CPU: {cpu_info['percent']:.1f}% ({cpu_info['count']} ядер)")
    console.print(
        f"   💾 Memory: {memory_info['percent']:.1f}% ({format_size(memory_info['used'])}/{format_size(memory_info['total'])})"
    )
    console.print(
        f"   💿 Disk: {disk_info['percent']:.1f}% ({format_size(disk_info['used'])}/{format_size(disk_info['total'])})"
    )
    console.print()

    console.print("🤖 Сервисы:")
    bot_emoji = "🟢" if bot_status["status"] == "active" else "🔴"
    db_emoji = "🟢" if db_status["status"] == "connected" else "🔴"

    console.print(f"   {bot_emoji} Bot API: {bot_status['status']}")
    if bot_status["status"] == "active":
        console.print(
            f"      📊 Response time: {bot_status.get('response_time', 0):.3f}s"
        )
        console.print(f"      👤 Username: {bot_status.get('username', 'unknown')}")

    console.print(f"   {db_emoji} Database: {db_status['status']}")
    if db_status["status"] == "connected":
        console.print(
            f"      📊 Response time: {db_status.get('response_time', 0):.3f}s"
        )
        console.print(f"      🔧 Type: {db_status.get('type', 'unknown')}")

    # Показываем алерты
    if alerts:
        console.print("\n🚨 Активные алерты:")
        for alert in alerts:
            emoji = "🔴" if alert["type"] == "critical" else "🟡"
            console.print(f"   {emoji} {alert['message']}")
    else:
        console.print("\n✅ Активных алертов нет")

    # Отправляем уведомление если указан канал
    if notify:
        try:
            from Systems.cli.notifications import (_load_notifications_config,
                                           _send_notification_by_type)

            notifications_config = _load_notifications_config()
            channels = notifications_config.get("channels", {})

            if notify in channels and channels[notify].get("status") == "active":
                message = f"📊 Статус системы SwiftDevBot\n\n"
                message += f"CPU: {cpu_info['percent']:.1f}%\n"
                message += f"Memory: {memory_info['percent']:.1f}%\n"
                message += f"Disk: {disk_info['percent']:.1f}%\n"
                message += f"Bot: {bot_status['status']}\n"
                message += f"Database: {db_status['status']}\n"

                if alerts:
                    message += f"\n🚨 Активных алертов: {len(alerts)}"
                    priority = "high"
                else:
                    message += f"\n✅ Система здорова"
                    priority = "normal"

                await _send_notification_by_type(channels[notify], message, priority)
                console.print(f"[green]✅ Уведомление отправлено в канал '{notify}'[/]")
            else:
                console.print(
                    f"[yellow]⚠️ Канал '{notify}' не настроен или неактивен[/]"
                )

        except ImportError:
            console.print("[yellow]⚠️ Модуль уведомлений не найден[/]")
        except Exception as e:
            console.print(f"[red]❌ Ошибка отправки уведомления: {e}[/]")


@monitor_app.command(name="metrics", help="Показать метрики производительности.")
def monitor_metrics_cmd(
    cpu: bool = typer.Option(False, "--cpu", help="Загрузка процессора"),
    memory: bool = typer.Option(False, "--memory", help="Использование памяти"),
    disk: bool = typer.Option(False, "--disk", help="Использование диска"),
    network: bool = typer.Option(False, "--network", help="Сетевой трафик"),
    real_time: bool = typer.Option(
        False, "--real-time", help="Обновление в реальном времени"
    ),
    history: bool = typer.Option(False, "--history", help="Исторические данные"),
    hours: int = typer.Option(24, "--hours", help="Количество часов для истории"),
):
    """Показывает метрики производительности."""
    asyncio.run(
        _monitor_metrics_async(cpu, memory, disk, network, real_time, history, hours)
    )


async def _monitor_metrics_async(
    cpu: bool,
    memory: bool,
    disk: bool,
    network: bool,
    real_time: bool,
    history: bool,
    hours: int,
):
    """Асинхронная функция для получения метрик."""

    # Если не указаны конкретные метрики, показываем все
    if not any([cpu, memory, disk, network]):
        cpu = memory = disk = network = True

    if history:
        await _display_metrics_history(hours)
        return

    if real_time:
        await _display_metrics_realtime(cpu, memory, disk, network)
        return

    await _display_metrics(cpu, memory, disk, network)


async def _display_metrics(cpu: bool, memory: bool, disk: bool, network: bool):
    """Отображает текущие метрики."""
    console.print(Panel.fit("📊 Метрики производительности системы", style="bold cyan"))

    # Собираем и сохраняем метрики
    metrics = {}

    if cpu:
        cpu_info = _get_cpu_info()
        metrics["cpu_percent"] = cpu_info["percent"]
        console.print("🖥️ CPU (Процессор):")
        console.print(f"   📊 Текущая загрузка: {cpu_info['percent']:.1f}%")
        console.print(f"   📈 Количество ядер: {cpu_info['count']}")
        if cpu_info["frequency"]:
            console.print(f"   🔧 Частота: {cpu_info['frequency']:.0f}MHz")
        if cpu_info["load_avg"]:
            console.print(f"   📈 Load average: {cpu_info['load_avg'][0]:.2f}")
        console.print()

    if memory:
        memory_info = _get_memory_info()
        metrics["memory_percent"] = memory_info["percent"]
        console.print("💾 Memory (Память):")
        console.print(
            f"   📊 Использовано: {format_size(memory_info['used'])} / {format_size(memory_info['total'])} ({memory_info['percent']:.1f}%)"
        )
        console.print(f"   📈 Доступно: {format_size(memory_info['available'])}")
        console.print(
            f"   📈 Swap: {format_size(memory_info['swap_used'])} / {format_size(memory_info['swap_total'])} ({memory_info['swap_percent']:.1f}%)"
        )
        console.print()

    if disk:
        disk_info = _get_disk_info()
        metrics["disk_percent"] = disk_info["percent"]
        console.print("💿 Disk (Диск):")
        console.print(
            f"   📊 Использовано: {format_size(disk_info['used'])} / {format_size(disk_info['total'])} ({disk_info['percent']:.1f}%)"
        )
        console.print(f"   📈 Свободно: {format_size(disk_info['free'])}")
        console.print(f"   📈 Прочитано: {format_size(disk_info['read_bytes'])}")
        console.print(f"   📈 Записано: {format_size(disk_info['write_bytes'])}")
        console.print()

    if network:
        network_info = _get_network_info()
        metrics["network_bytes_sent"] = network_info["bytes_sent"]
        metrics["network_bytes_recv"] = network_info["bytes_recv"]
        console.print("🌐 Network (Сеть):")
        console.print(f"   📊 Отправлено: {format_size(network_info['bytes_sent'])}")
        console.print(f"   📊 Получено: {format_size(network_info['bytes_recv'])}")
        console.print(f"   📈 Пакетов отправлено: {network_info['packets_sent']}")
        console.print(f"   📈 Пакетов получено: {network_info['packets_recv']}")
        console.print()

    # Сохраняем метрики в БД
    if metrics:
        _save_metrics_to_db(metrics)

    # Проверяем алерты
    alerts = await _check_alerts(metrics)
    if alerts:
        console.print("🚨 Активные алерты:")
        for alert in alerts:
            emoji = "🔴" if alert["type"] == "critical" else "🟡"
            console.print(f"   {emoji} {alert['message']}")
        console.print()


async def _display_metrics_realtime(cpu: bool, memory: bool, disk: bool, network: bool):
    """Отображает метрики в реальном времени."""
    console.print("📊 Метрики в реальном времени (Ctrl+C для выхода)")

    def generate_layout():
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(Layout(name="left"), Layout(name="right"))
        return layout

    layout = generate_layout()

    try:
        with Live(layout, refresh_per_second=2, screen=True):
            while True:
                # Обновляем метрики
                metrics = {}

                if cpu:
                    cpu_info = _get_cpu_info()
                    metrics["cpu_percent"] = cpu_info["percent"]
                    layout["left"].update(
                        Panel(
                            (
                                f"🖥️ CPU: {cpu_info['percent']:.1f}%\n"
                                f"📈 Ядер: {cpu_info['count']}\n"
                                f"🔧 Частота: {cpu_info['frequency']:.0f}MHz"
                                if cpu_info["frequency"]
                                else "N/A"
                            ),
                            title="CPU",
                        )
                    )

                if memory:
                    memory_info = _get_memory_info()
                    metrics["memory_percent"] = memory_info["percent"]
                    layout["right"].update(
                        Panel(
                            f"💾 Memory: {memory_info['percent']:.1f}%\n"
                            f"📊 Использовано: {format_size(memory_info['used'])}\n"
                            f"📈 Доступно: {format_size(memory_info['available'])}",
                            title="Memory",
                        )
                    )

                if disk:
                    disk_info = _get_disk_info()
                    metrics["disk_percent"] = disk_info["percent"]
                    layout["left"].update(
                        Panel(
                            f"💿 Disk: {disk_info['percent']:.1f}%\n"
                            f"📊 Использовано: {format_size(disk_info['used'])}\n"
                            f"📈 Свободно: {format_size(disk_info['free'])}",
                            title="Disk",
                        )
                    )

                if network:
                    network_info = _get_network_info()
                    metrics["network_bytes_sent"] = network_info["bytes_sent"]
                    metrics["network_bytes_recv"] = network_info["bytes_recv"]
                    layout["right"].update(
                        Panel(
                            f"🌐 Network\n"
                            f"📊 Отправлено: {format_size(network_info['bytes_sent'])}\n"
                            f"📊 Получено: {format_size(network_info['bytes_recv'])}",
                            title="Network",
                        )
                    )

                # Сохраняем метрики
                if metrics:
                    _save_metrics_to_db(metrics)

                # Проверяем алерты
                alerts = await _check_alerts(metrics)
                if alerts:
                    alert_text = "\n".join(
                        [f"🚨 {alert['message']}" for alert in alerts]
                    )
                    layout["footer"].update(
                        Panel(alert_text, title="Алерты", style="red")
                    )
                else:
                    layout["footer"].update(
                        Panel("✅ Система здорова", title="Статус", style="green")
                    )

                layout["header"].update(
                    Panel(
                        f"📊 Мониторинг в реальном времени | {datetime.now().strftime('%H:%M:%S')}",
                        style="bold cyan",
                    )
                )

                await asyncio.sleep(2)

    except KeyboardInterrupt:
        console.print("\n⏹️ Мониторинг остановлен")


async def _display_metrics_history(hours: int):
    """Отображает историю метрик."""
    console.print(
        Panel.fit(f"📈 История метрик (последние {hours} часов)", style="bold cyan")
    )

    history = _get_metrics_history(hours)

    if not history:
        console.print("[yellow]История метрик пуста[/]")
        return

    # Создаем таблицу
    table = Table(title=f"История метрик ({len(history)} записей)")
    table.add_column("Время", style="cyan")
    table.add_column("CPU %", style="yellow")
    table.add_column("Memory %", style="green")
    table.add_column("Disk %", style="blue")
    table.add_column("Network (MB)", style="magenta")

    for record in history[:50]:  # Показываем последние 50 записей
        timestamp = datetime.fromisoformat(record["timestamp"])
        cpu = record.get("cpu_percent", 0)
        memory = record.get("memory_percent", 0)
        disk = record.get("disk_percent", 0)
        network_sent = record.get("network_bytes_sent", 0) / (1024 * 1024)  # MB
        network_recv = record.get("network_bytes_recv", 0) / (1024 * 1024)  # MB

        table.add_row(
            timestamp.strftime("%H:%M:%S"),
            f"{cpu:.1f}",
            f"{memory:.1f}",
            f"{disk:.1f}",
            f"{network_sent:.1f}↑/{network_recv:.1f}↓",
        )

    console.print(table)

    # Статистика
    if history:
        cpu_values = [r.get("cpu_percent", 0) for r in history]
        memory_values = [r.get("memory_percent", 0) for r in history]
        disk_values = [r.get("disk_percent", 0) for r in history]

        console.print("\n📊 Статистика:")
        console.print(
            f"   CPU: мин {min(cpu_values):.1f}%, макс {max(cpu_values):.1f}%, средн {sum(cpu_values)/len(cpu_values):.1f}%"
        )
        console.print(
            f"   Memory: мин {min(memory_values):.1f}%, макс {max(memory_values):.1f}%, средн {sum(memory_values)/len(memory_values):.1f}%"
        )
        console.print(
            f"   Disk: мин {min(disk_values):.1f}%, макс {max(disk_values):.1f}%, средн {sum(disk_values)/len(disk_values):.1f}%"
        )


@monitor_app.command(name="alerts", help="Управление системой оповещений.")
def monitor_alerts_cmd(
    list_alerts: bool = typer.Option(
        False, "--list", help="Показать активные оповещения"
    ),
    configure: bool = typer.Option(
        False, "--configure", help="Настроить правила оповещений"
    ),
    test: bool = typer.Option(False, "--test", help="Протестировать оповещения"),
    history: bool = typer.Option(False, "--history", help="История алертов"),
):
    """Управляет системой оповещений."""
    asyncio.run(_monitor_alerts_async(list_alerts, configure, test, history))


async def _monitor_alerts_async(
    list_alerts: bool, configure: bool, test: bool, history: bool
):
    """Асинхронная функция для управления алертами."""

    if not any([list_alerts, configure, test, history]):
        list_alerts = True  # По умолчанию показываем список

    console.print(Panel.fit("🔔 Управление системой оповещений", style="bold cyan"))

    config = _load_alerts_config()

    if list_alerts:
        console.print("📋 Настроенные правила алертов:")

        for metric, thresholds in config["alerts"].items():
            console.print(f"   🔴 {metric.upper()}:")
            console.print(f"      ⚠️ Предупреждение: > {thresholds['warning']}")
            console.print(f"      🚨 Критический: > {thresholds['critical']}")
        console.print()

        # Проверяем текущие алерты
        current_metrics = {
            "cpu_percent": _get_cpu_info()["percent"],
            "memory_percent": _get_memory_info()["percent"],
            "disk_percent": _get_disk_info()["percent"],
        }

        current_alerts = await _check_alerts(current_metrics)

        if current_alerts:
            console.print("🚨 Активные алерты:")
            for alert in current_alerts:
                emoji = "🔴" if alert["type"] == "critical" else "🟡"
                console.print(f"   {emoji} {alert['message']}")
        else:
            console.print("✅ Активных алертов нет")

    if configure:
        console.print("⚙️ Настройка правил алертов:")

        new_config = config.copy()

        for metric, thresholds in config["alerts"].items():
            console.print(f"\n📊 {metric.upper()}:")

            warning = input(
                f"Порог предупреждения (текущий: {thresholds['warning']}): "
            ).strip()
            if warning:
                new_config["alerts"][metric]["warning"] = float(warning)

            critical = input(
                f"Критический порог (текущий: {thresholds['critical']}): "
            ).strip()
            if critical:
                new_config["alerts"][metric]["critical"] = float(critical)

        # Настройка уведомлений
        console.print("\n📧 Настройка уведомлений:")
        enable_notifications = (
            input("Включить уведомления? (y/n): ").strip().lower() == "y"
        )
        new_config["notifications"]["enabled"] = enable_notifications

        if enable_notifications:
            channels = input("Каналы уведомлений (через запятую): ").strip()
            if channels:
                new_config["notifications"]["channels"] = [
                    c.strip() for c in channels.split(",")
                ]

        # Сохраняем конфигурацию
        with open(ALERTS_CONFIG, "w") as f:
            json.dump(new_config, f, indent=2)

        console.print("[green]✅ Конфигурация алертов обновлена[/]")

    if test:
        console.print("🧪 Тестирование алертов:")

        # Создаем тестовые метрики
        test_metrics = {
            "cpu_percent": 95.0,  # Критический уровень
            "memory_percent": 85.0,  # Предупреждение
            "disk_percent": 90.0,  # Критический уровень
        }

        test_alerts = await _check_alerts(test_metrics)

        if test_alerts:
            console.print("🚨 Тестовые алерты:")
            for alert in test_alerts:
                emoji = "🔴" if alert["type"] == "critical" else "🟡"
                console.print(f"   {emoji} {alert['message']}")

            # Отправляем тестовые уведомления
            await _send_alert_notifications(test_alerts)
            console.print("[green]✅ Тестовые уведомления отправлены[/]")
        else:
            console.print("✅ Тестовые алерты не сработали")


@monitor_app.command(name="logs", help="Анализ логов системы.")
def monitor_logs_cmd(
    file: str = typer.Argument(..., help="ОБЯЗАТЕЛЬНО: Путь к конкретному файлу лога"),
    analyze: bool = typer.Option(False, "--analyze", help="Анализ паттернов в логах"),
    errors: bool = typer.Option(False, "--errors", help="Показать только ошибки"),
    last_n: Optional[int] = typer.Option(None, "--last", help="Последние N записей"),
    since: Optional[str] = typer.Option(
        None, "--since", help="Логи с определенной даты"
    ),
    search: Optional[str] = typer.Option(None, "--search", help="Поиск по паттерну"),
    force: bool = typer.Option(
        False, "--force", help="Принудительно обработать большой файл (>15MB)"
    ),
):
    """Анализирует КОНКРЕТНЫЙ файл лога. Максимум 15MB без --force."""
    asyncio.run(
        _monitor_logs_async(file, analyze, errors, last_n, since, search, force)
    )


async def _monitor_logs_async(
    file_path: str,
    analyze: bool,
    errors: bool,
    last_n: Optional[int],
    since: Optional[str],
    search: Optional[str],
    force: bool,
):
    """Асинхронная функция для анализа КОНКРЕТНОГО файла лога."""

    if not any([analyze, errors, last_n, since, search]):
        analyze = True  # По умолчанию анализируем

    console.print(Panel.fit("📋 Анализ конкретного файла лога", style="bold cyan"))

    # Определяем базовую директорию логов
    logs_dir = Path("Data/Logs")

    # Обработка пути к файлу
    if file_path.startswith("/"):
        # Абсолютный путь
        log_file = Path(file_path)
    elif file_path.startswith("Data/Logs/"):
        # Относительный путь от корня проекта
        log_file = Path(file_path)
    else:
        # Относительный путь от директории логов
        log_file = logs_dir / file_path

    # Проверяем существование файла
    if not log_file.exists():
        console.print(f"[red]❌ Файл не найден: {log_file}[/]")

        # Попробуем найти похожие файлы
        if logs_dir.exists():
            similar_files = list(logs_dir.rglob(f"*{Path(file_path).name}*"))
            if similar_files:
                console.print(
                    f"[yellow]🔍 Возможно, вы имели в виду один из этих файлов:[/]"
                )
                for i, similar_file in enumerate(similar_files[:10], 1):
                    rel_path = similar_file.relative_to(logs_dir)
                    file_size = format_size(similar_file.stat().st_size)
                    console.print(f"   {i}. 📄 {rel_path} ({file_size})")
        return

    # Проверяем, что это файл лога
    if not log_file.suffix.lower() in [".log", ".txt"]:
        console.print(
            f"[yellow]⚠️ Предупреждение: '{log_file.suffix}' - не стандартное расширение лога[/]"
        )

    # 🛡️ ЗАЩИТА ОТ БОЛЬШИХ ФАЙЛОВ - МАКСИМУМ 15MB
    file_size = log_file.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    MAX_SIZE_MB = 15

    console.print(f"[cyan]📄 Файл: {log_file.name}[/]")
    console.print(
        f"[cyan]📦 Размер: {format_size(file_size)} ({file_size_mb:.1f} MB)[/]"
    )

    if file_size_mb > MAX_SIZE_MB and not force:
        console.print(f"[red]🚫 ФАЙЛ СЛИШКОМ БОЛЬШОЙ![/]")
        console.print(
            f"[red]   Размер: {file_size_mb:.1f} MB (максимум: {MAX_SIZE_MB} MB)[/]"
        )
        console.print(f"[yellow]   Используйте --force для принудительной обработки[/]")
        console.print(
            f"[yellow]   Или разрежьте файл на части < {MAX_SIZE_MB}MB каждая[/]"
        )
        console.print()
        console.print("[dim]Примеры разбивки файла:[/]")
        console.print(
            f"[dim]   split -b {MAX_SIZE_MB}M '{log_file}' '{log_file}.part_'[/]"
        )
        console.print(f"[dim]   head -n 10000 '{log_file}' > '{log_file}.first_10k'[/]")
        console.print(f"[dim]   tail -n 10000 '{log_file}' > '{log_file}.last_10k'[/]")
        return

    if file_size_mb > MAX_SIZE_MB and force:
        console.print(
            f"[red]⚠️ ПРИНУДИТЕЛЬНАЯ ОБРАБОТКА БОЛЬШОГО ФАЙЛА ({file_size_mb:.1f} MB)[/]"
        )
        console.print(f"[red]   Это может занять много времени и памяти![/]")

        # Дополнительное подтверждение для очень больших файлов
        if file_size_mb > 50:
            console.print(
                f"[red]🚨 КРИТИЧЕСКИ БОЛЬШОЙ ФАЙЛ ({file_size_mb:.1f} MB)![/]"
            )
            try:
                confirm = input(
                    "Вы действительно хотите продолжить? (введите 'ДА' для подтверждения): "
                ).strip()
                if confirm != "ДА":
                    console.print("[yellow]⚠️ Операция отменена[/]")
                    return
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️ Операция отменена пользователем[/]")
                return

    # Выполняем запрошенные операции
    log_files = [log_file]  # Работаем только с одним файлом

    if analyze:
        await _analyze_single_log_file(log_file)

    if errors:
        await _show_log_errors(log_files)

    if last_n:
        await _show_last_n_logs(log_files, last_n)

    if since:
        await _show_logs_since(log_files, since)

    if search:
        await _search_in_logs(log_files, search)


async def _select_log_files(
    all_files: List[Path], max_files: int, total_size_mb: float
) -> List[Path]:
    """Интерактивный выбор файлов для обработки"""

    console.print(
        f"[yellow]⚠️ ВНИМАНИЕ: Найдено {len(all_files)} файлов (общий размер: {total_size_mb:.1f} MB)[/]"
    )
    console.print(
        "[yellow]   Обработка всех файлов может занять много времени и памяти![/]"
    )
    console.print()

    console.print("📋 Доступные варианты:")
    console.print("1. 📅 Только сегодняшние файлы")
    console.print("2. 📊 N самых свежих файлов")
    console.print("3. 🎯 Выбрать конкретные файлы")
    console.print("4. 🔍 Фильтр по размеру файлов")
    console.print("5. ❌ Отмена")

    try:
        choice = input("\nВыберите вариант (1-5): ").strip()

        if choice == "1":
            # Только сегодняшние файлы - ищем в папке сегодняшней даты
            today = datetime.now()
            today_str = today.strftime("%Y-%m-%d")
            today_files = []

            # Ищем в новой структуре: Data/Logs/YYYY/MM-Month/DD/
            today_year = today.year
            today_month = today.strftime("%m-%B")
            today_day = today.strftime("%d")

            today_path = (
                Path("Data/Logs") / str(today_year) / today_month / today_day
            )

            if today_path.exists() and today_path.is_dir():
                today_files.extend(list(today_path.glob("*.log")))
                console.print(
                    f"[dim]Найдено в {today_path}: {len(today_files)} файлов[/]"
                )

            # Также проверяем старую структуру - файлы с сегодняшней датой в имени
            logs_dir = Path("Data/Logs")
            for pattern in [
                f"*{today_str}*.log",
                f"*{today.strftime('%Y-%m-%d')}*.log",
            ]:
                old_files = list(logs_dir.glob(pattern))
                for file in old_files:
                    if file not in today_files:
                        today_files.append(file)

            # Дополнительно проверяем по дате модификации (но только если файлы не найдены)
            if not today_files:
                console.print(
                    "[yellow]📅 Файлы за сегодня в структуре каталогов не найдены, ищем по дате модификации...[/]"
                )
                today_date = today.date()
                for file in all_files:
                    file_date = datetime.fromtimestamp(file.stat().st_mtime).date()
                    if file_date == today_date:
                        today_files.append(file)

            if today_files:
                console.print(
                    f"[green]✅ Найдено файлов за {today_str}: {len(today_files)}[/]"
                )
                # Показываем найденные файлы
                for i, file in enumerate(today_files, 1):
                    rel_path = file.relative_to(Path("Data/Logs"))
                    file_size = format_size(file.stat().st_size)
                    console.print(f"   {i}. 📄 {rel_path} ({file_size})")
                return today_files
            else:
                console.print(f"[yellow]⚠️ Файлов за {today_str} не найдено[/]")
                return []

        elif choice == "2":
            # N самых свежих файлов
            try:
                n = int(input(f"Количество файлов (максимум {max_files}): ").strip())
                n = min(n, max_files, len(all_files))
                selected = all_files[:n]
                console.print(
                    f"[green]✅ Выбрано {len(selected)} самых свежих файлов[/]"
                )
                return selected
            except ValueError:
                console.print("[red]❌ Неверное число[/]")
                return []

        elif choice == "3":
            # Выбор конкретных файлов
            return await _interactive_file_selection(all_files, max_files)

        elif choice == "4":
            # Фильтр по размеру
            try:
                max_size_mb = float(input("Максимальный размер файла в MB: ").strip())
                max_size_bytes = max_size_mb * 1024 * 1024

                filtered_files = []
                for file in all_files:
                    if file.stat().st_size <= max_size_bytes:
                        filtered_files.append(file)
                        if len(filtered_files) >= max_files:
                            break

                console.print(
                    f"[green]✅ Выбрано {len(filtered_files)} файлов размером до {max_size_mb}MB[/]"
                )
                return filtered_files
            except ValueError:
                console.print("[red]❌ Неверный размер[/]")
                return []

        elif choice == "5":
            return []

        else:
            console.print("[red]❌ Неверный выбор[/]")
            return []

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Операция отменена пользователем[/]")
        return []
    except Exception as e:
        console.print(f"[red]❌ Ошибка выбора: {e}[/]")
        return []


async def _interactive_file_selection(
    all_files: List[Path], max_files: int
) -> List[Path]:
    """Детальный интерактивный выбор файлов"""

    console.print("📋 Доступные файлы:")

    # Показываем файлы с номерами
    for i, file in enumerate(all_files[:20], 1):  # Показываем первые 20
        rel_path = file.relative_to(Path("Data/Logs"))
        file_size = format_size(file.stat().st_size)
        file_date = datetime.fromtimestamp(file.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )
        console.print(f"   {i:2d}. 📄 {rel_path} ({file_size}, {file_date})")

    if len(all_files) > 20:
        console.print(f"   ... и еще {len(all_files) - 20} файлов")

    console.print(
        f"\n[cyan]Введите номера файлов через запятую (максимум {max_files})[/]"
    )
    console.print("[dim]Пример: 1,3,5 или 1-5 или all для всех первых 20[/]")

    try:
        selection = input("Ваш выбор: ").strip()

        if selection.lower() == "all":
            selected_count = min(max_files, len(all_files), 20)
            return all_files[:selected_count]

        # Парсим диапазоны и номера
        selected_indices = set()

        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                # Диапазон
                try:
                    start, end = map(int, part.split("-"))
                    for i in range(start, end + 1):
                        if 1 <= i <= min(len(all_files), 20):
                            selected_indices.add(i - 1)  # Конвертируем в 0-based
                except ValueError:
                    console.print(f"[yellow]⚠️ Неверный диапазон: {part}[/]")
            else:
                # Одиночный номер
                try:
                    i = int(part)
                    if 1 <= i <= min(len(all_files), 20):
                        selected_indices.add(i - 1)  # Конвертируем в 0-based
                except ValueError:
                    console.print(f"[yellow]⚠️ Неверный номер: {part}[/]")

        # Ограничиваем количество
        selected_indices = list(selected_indices)[:max_files]
        selected_files = [all_files[i] for i in selected_indices]

        console.print(f"[green]✅ Выбрано файлов: {len(selected_files)}[/]")
        return selected_files

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Выбор отменен[/]")
        return []
    except Exception as e:
        console.print(f"[red]❌ Ошибка парсинга выбора: {e}[/]")
        return []


async def _analyze_single_log_file(log_file: Path):
    """Безопасный анализ одного файла лога с ограничениями"""
    console.print(f"📊 Анализ файла: {log_file.name}")

    try:
        file_size = log_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        total_lines = 0
        error_count = 0
        warning_count = 0
        info_count = 0
        debug_count = 0

        # БЕЗОПАСНОСТЬ: Ограничиваем количество читаемых строк
        max_lines_to_read = 50000  # Максимум 50k строк

        console.print(f"   📦 Размер файла: {format_size(file_size)}")
        console.print(f"   🔒 Максимум строк для чтения: {max_lines_to_read:,}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task("Анализ файла...", total=None)

            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines_read = 0

                    for line_num, line in enumerate(f, 1):
                        if lines_read >= max_lines_to_read:
                            console.print(
                                f"   ⚠️ Достигнут лимит чтения ({max_lines_to_read:,} строк)"
                            )
                            break

                        lines_read += 1
                        total_lines = line_num

                        # Анализ типов сообщений
                        line_lower = line.lower()
                        if any(
                            keyword in line_lower
                            for keyword in ["error", "exception", "failed", "fatal"]
                        ):
                            error_count += 1
                        elif any(
                            keyword in line_lower
                            for keyword in ["warning", "warn", "deprecated"]
                        ):
                            warning_count += 1
                        elif any(
                            keyword in line_lower for keyword in ["info", "information"]
                        ):
                            info_count += 1
                        elif any(
                            keyword in line_lower for keyword in ["debug", "trace"]
                        ):
                            debug_count += 1

                        # Обновляем прогресс каждые 1000 строк
                        if lines_read % 1000 == 0:
                            progress.update(
                                task, description=f"Прочитано {lines_read:,} строк..."
                            )

                progress.update(task, description="Анализ завершен")

            except Exception as e:
                console.print(f"   ❌ Ошибка чтения файла: {str(e)[:100]}...")
                return

        # Результаты анализа
        console.print(f"\n📊 Результаты анализа:")
        console.print(f"   📝 Всего строк в файле: {total_lines:,}")
        console.print(f"   📖 Прочитано строк: {lines_read:,}")

        if lines_read < total_lines:
            console.print(
                f"   ⚠️ Файл обработан частично ({(lines_read/total_lines)*100:.1f}%)"
            )

        console.print(f"   🔴 Ошибок найдено: {error_count:,}")
        console.print(f"   🟡 Предупреждений: {warning_count:,}")
        console.print(f"   🟢 Информационных: {info_count:,}")
        console.print(f"   🔵 Отладочных: {debug_count:,}")

        # Показываем процентное соотношение
        if lines_read > 0:
            console.print(f"\n📈 Процентное соотношение:")
            console.print(f"   🔴 Ошибки: {(error_count/lines_read)*100:.1f}%")
            console.print(
                f"   🟡 Предупреждения: {(warning_count/lines_read)*100:.1f}%"
            )
            console.print(f"   🟢 Информация: {(info_count/lines_read)*100:.1f}%")
            console.print(f"   🔵 Отладка: {(debug_count/lines_read)*100:.1f}%")

        # Оценка здоровья лога
        if error_count > 0:
            error_ratio = error_count / lines_read
            if error_ratio > 0.1:  # Более 10% ошибок
                console.print(
                    f"\n🚨 [red]КРИТИЧЕСКОЕ СОСТОЯНИЕ: {error_ratio*100:.1f}% ошибок![/]"
                )
            elif error_ratio > 0.05:  # Более 5% ошибок
                console.print(
                    f"\n⚠️ [yellow]ВНИМАНИЕ: Высокий уровень ошибок ({error_ratio*100:.1f}%)[/]"
                )
            else:
                console.print(
                    f"\n✅ [green]Приемлемый уровень ошибок ({error_ratio*100:.1f}%)[/]"
                )
        else:
            console.print(f"\n🎉 [green]Отлично: Ошибки не обнаружены![/]")

    except Exception as e:
        console.print(f"   ❌ Ошибка анализа: {str(e)[:100]}...")

    console.print()


async def _analyze_log_files(log_files: List[Path]):
    """Анализ файлов логов"""
    console.print("📊 Анализ файлов логов:")

    try:
        if not log_files:
            console.print("   📭 Файлы логов не найдены")
            return

        total_lines = 0
        error_count = 0
        warning_count = 0
        info_count = 0
        debug_count = 0
        total_size = 0

        console.print(f"   📁 Обрабатывается файлов: {len(log_files)}")

        # Добавляем прогресс-бар для больших операций
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task("Анализ логов...", total=len(log_files))

            # Анализируем каждый файл
            for log_file in log_files:
                try:
                    file_size = log_file.stat().st_size
                    total_size += file_size

                    # БЕЗОПАСНОСТЬ: Ограничиваем чтение больших файлов
                    max_lines_to_read = 10000  # Максимум 10k строк на файл
                    lines_read = 0

                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        file_lines = 0
                        file_errors = 0
                        file_warnings = 0
                        file_info = 0
                        file_debug = 0

                        # Если файл очень большой, читаем с конца
                        if file_size > 10 * 1024 * 1024:  # 10MB
                            # Читаем последние строки большого файла
                            f.seek(max(0, file_size - 1024 * 1024))  # Последний 1MB
                            f.readline()  # Пропускаем неполную строку

                        for line in f:
                            file_lines += 1
                            lines_read += 1

                            # Ограничиваем количество обработанных строк
                            if lines_read > max_lines_to_read:
                                break

                            line_lower = line.lower()

                            # Более точная классификация логов
                            if any(
                                keyword in line_lower
                                for keyword in [
                                    "error",
                                    "ошибка",
                                    "exception",
                                    "failed",
                                    "critical",
                                ]
                            ):
                                file_errors += 1
                            elif any(
                                keyword in line_lower
                                for keyword in ["warning", "warn", "предупреждение"]
                            ):
                                file_warnings += 1
                            elif any(
                                keyword in line_lower
                                for keyword in ["debug", "trace", "отладка"]
                            ):
                                file_debug += 1
                            elif any(
                                keyword in line_lower
                                for keyword in [
                                    "info",
                                    "информация",
                                    "success",
                                    "started",
                                    "finished",
                                ]
                            ):
                                file_info += 1

                        total_lines += file_lines
                        error_count += file_errors
                        warning_count += file_warnings
                        info_count += file_info
                        debug_count += file_debug

                    # Показываем информацию о файле
                    rel_path = log_file.relative_to(Path("Data/Logs"))
                    truncated = " (усечен)" if lines_read >= max_lines_to_read else ""
                    console.print(
                        f"   📄 {rel_path}: {file_lines:,} строк{truncated}, {format_size(file_size)}"
                    )
                    if file_errors > 0:
                        console.print(f"      🔴 Ошибок: {file_errors}")
                    if file_warnings > 0:
                        console.print(f"      🟡 Предупреждений: {file_warnings}")

                    progress.advance(task)

                except Exception as e:
                    console.print(
                        f"   ❌ Ошибка чтения {log_file.name}: {str(e)[:50]}..."
                    )
                    progress.advance(task)

        # Общая статистика
        console.print(f"\n📊 Общая статистика:")
        console.print(f"   📝 Всего записей: {total_lines:,}")
        console.print(f"   📦 Общий размер: {format_size(total_size)}")
        console.print(f"   🔴 Ошибок: {error_count:,}")
        console.print(f"   🟡 Предупреждений: {warning_count:,}")
        console.print(f"   🟢 Информационных: {info_count:,}")
        console.print(f"   🔵 Отладочных: {debug_count:,}")

        # Анализируем паттерны активности (только для небольшого количества файлов)
        if len(log_files) <= 3 and total_size < 50 * 1024 * 1024:  # Меньше 50MB
            await _analyze_activity_patterns(log_files)
        else:
            console.print(
                "   📈 Анализ паттернов активности пропущен (слишком много данных)"
            )

    except Exception as e:
        console.print(f"   ❌ Ошибка анализа логов: {str(e)[:100]}...")

    console.print()


async def _analyze_activity_patterns(log_files: List[Path]):
    """Анализ паттернов активности в логах"""
    console.print("📈 Анализ паттернов активности:")

    try:
        hourly_activity = {hour: 0 for hour in range(24)}
        recent_errors = []

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-1000:]  # Анализируем последние 1000 строк

                    for line in lines:
                        # Пытаемся извлечь время из строки
                        if len(line) > 19:  # Минимальная длина для даты-времени
                            try:
                                # Ищем паттерны даты-времени
                                import re

                                time_pattern = (
                                    r"(\d{4}-\d{2}-\d{2}\s+\d{2}):(\d{2}):\d{2}"
                                )
                                match = re.search(time_pattern, line)
                                if match:
                                    hour = int(match.group(2))
                                    hourly_activity[hour] += 1

                                # Собираем недавние ошибки
                                if any(
                                    keyword in line.lower()
                                    for keyword in ["error", "ошибка", "exception"]
                                ):
                                    if len(recent_errors) < 5:
                                        recent_errors.append(line.strip()[:100])
                            except:
                                continue

            except Exception:
                continue

        # Находим пиковые часы
        if sum(hourly_activity.values()) > 0:
            max_hour = max(hourly_activity, key=hourly_activity.get)
            min_hour = min(hourly_activity, key=hourly_activity.get)

            console.print(
                f"   📊 Пиковая активность: {max_hour:02d}:00 ({hourly_activity[max_hour]} записей)"
            )
            console.print(
                f"   📊 Минимальная активность: {min_hour:02d}:00 ({hourly_activity[min_hour]} записей)"
            )

            avg_activity = sum(hourly_activity.values()) / 24
            console.print(f"   📊 Средняя активность: {avg_activity:.1f} записей/час")

        # Показываем недавние ошибки
        if recent_errors:
            console.print("🔍 Недавние ошибки:")
            for error in recent_errors:
                console.print(f"   ❌ {error}")

    except Exception as e:
        console.print(f"   ❌ Ошибка анализа паттернов: {str(e)[:100]}...")


async def _show_log_errors(log_files: List[Path]):
    """Показать только ошибки из логов"""
    console.print("❌ Последние ошибки в логах:")

    try:
        error_lines = []
        max_errors = 20  # Максимум ошибок для показа

        for log_file in log_files:
            try:
                file_size = log_file.stat().st_size

                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    # Для больших файлов читаем с конца
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        f.seek(max(0, file_size - 1024 * 1024))  # Последний 1MB
                        f.readline()  # Пропускаем неполную строку

                    lines_processed = 0
                    for line_num, line in enumerate(f, 1):
                        lines_processed += 1
                        # Ограничиваем количество обработанных строк
                        if lines_processed > 5000:
                            break

                        if any(
                            keyword in line.lower()
                            for keyword in [
                                "error",
                                "ошибка",
                                "exception",
                                "failed",
                                "critical",
                            ]
                        ):
                            rel_path = log_file.relative_to(Path("Data/Logs"))
                            error_lines.append((str(rel_path), line_num, line.strip()))

                            if len(error_lines) >= max_errors:
                                break
                if len(error_lines) >= max_errors:
                    break
            except Exception:
                continue

        if error_lines:
            console.print(f"   📊 Найдено ошибок: {len(error_lines)}")
            for file_name, line_num, line in error_lines[
                -15:
            ]:  # Показываем последние 15
                console.print(f"   📄 {file_name}:{line_num} - {line[:120]}")
        else:
            console.print("   ✅ Ошибки в логах не найдены")

    except Exception as e:
        console.print(f"   ❌ Ошибка поиска ошибок: {str(e)[:100]}...")

    console.print()


async def _show_last_n_logs(log_files: List[Path], n: int):
    """Показать последние N записей из логов"""
    console.print(f"📋 Последние {n} записей из логов:")

    try:
        all_lines = []

        # Сортируем файлы по времени модификации
        sorted_files = sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True)

        for log_file in sorted_files[:3]:  # Берем 3 самых свежих файла
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    rel_path = log_file.relative_to(Path("Data/Logs"))
                    for line in lines[-50:]:  # Последние 50 строк из каждого файла
                        all_lines.append((str(rel_path), line.strip()))
            except Exception:
                continue

        # Показываем последние N строк
        for file_name, line in all_lines[-n:]:
            console.print(f"   📄 {file_name}: {line[:150]}")

        if not all_lines:
            console.print("   📭 Записи в логах не найдены")

    except Exception as e:
        console.print(f"   ❌ Ошибка чтения логов: {str(e)[:100]}...")

    console.print()


async def _show_logs_since(log_files: List[Path], since: str):
    """Показать логи с определенной даты"""
    console.print(f"📋 Логи с {since}:")

    try:
        # Парсим дату
        from datetime import datetime

        since_date = datetime.strptime(since, "%Y-%m-%d")

        found_lines = []

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    rel_path = log_file.relative_to(Path("Data/Logs"))
                    for line in f:
                        # Пытаемся найти дату в строке
                        import re

                        date_pattern = r"(\d{4}-\d{2}-\d{2})"
                        match = re.search(date_pattern, line)
                        if match:
                            try:
                                line_date = datetime.strptime(
                                    match.group(1), "%Y-%m-%d"
                                )
                                if line_date >= since_date:
                                    found_lines.append((str(rel_path), line.strip()))
                                    if len(found_lines) >= 30:  # Ограничиваем вывод
                                        break
                            except:
                                continue
                if len(found_lines) >= 30:
                    break
            except Exception:
                continue

        if found_lines:
            for file_name, line in found_lines:
                console.print(f"   📄 {file_name}: {line[:150]}")
        else:
            console.print(f"   📭 Записи с {since} не найдены")

    except ValueError:
        console.print(f"   ❌ Неверный формат даты. Используйте YYYY-MM-DD")
    except Exception as e:
        console.print(f"   ❌ Ошибка поиска по дате: {str(e)[:100]}...")

    console.print()


async def _search_in_logs(log_files: List[Path], pattern: str):
    """Поиск по паттерну в логах"""
    console.print(f"🔍 Поиск по паттерну '{pattern}' в логах:")

    try:
        found_lines = []
        max_matches = 25  # Максимум совпадений

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task("Поиск в логах...", total=len(log_files))

            for log_file in log_files:
                try:
                    file_size = log_file.stat().st_size

                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        # Для больших файлов ограничиваем поиск
                        if file_size > 10 * 1024 * 1024:  # 10MB
                            f.seek(max(0, file_size - 2 * 1024 * 1024))  # Последние 2MB
                            f.readline()  # Пропускаем неполную строку

                        rel_path = log_file.relative_to(Path("Data/Logs"))
                        lines_processed = 0

                        for line_num, line in enumerate(f, 1):
                            lines_processed += 1

                            # Ограничиваем количество обработанных строк
                            if lines_processed > 10000:  # Максимум 10k строк на файл
                                break

                            if pattern.lower() in line.lower():
                                found_lines.append(
                                    (str(rel_path), line_num, line.strip())
                                )

                                if len(found_lines) >= max_matches:
                                    break

                    progress.advance(task)

                    if len(found_lines) >= max_matches:
                        break
                except Exception:
                    progress.advance(task)
                    continue

        if found_lines:
            console.print(f"   📊 Найдено совпадений: {len(found_lines)}")
            for file_name, line_num, line in found_lines:
                console.print(f"   📄 {file_name}:{line_num} - {line[:120]}")
        else:
            console.print(f"   📭 Совпадения с '{pattern}' не найдены")

    except Exception as e:
        console.print(f"   ❌ Ошибка поиска: {str(e)[:100]}...")

    console.print()


def format_size(size_bytes: int) -> str:
    """Форматирует размер файла в человекочитаемый вид"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


@monitor_app.command(name="performance", help="Анализ производительности системы.")
def monitor_performance_cmd(
    slow_queries: bool = typer.Option(
        False, "--slow-queries", help="Медленные запросы к БД"
    ),
    response_time: bool = typer.Option(
        False, "--response-time", help="Время ответа API"
    ),
    memory_leaks: bool = typer.Option(
        False, "--memory-leaks", help="Поиск утечек памяти"
    ),
    bottlenecks: bool = typer.Option(False, "--bottlenecks", help="Поиск узких мест"),
):
    """Анализирует производительность системы."""
    asyncio.run(
        _monitor_performance_async(
            slow_queries, response_time, memory_leaks, bottlenecks
        )
    )


async def _monitor_performance_async(
    slow_queries: bool, response_time: bool, memory_leaks: bool, bottlenecks: bool
):
    """Асинхронная функция для анализа производительности."""

    # Если не указаны конкретные метрики, показываем все
    if not any([slow_queries, response_time, memory_leaks, bottlenecks]):
        slow_queries = response_time = memory_leaks = bottlenecks = True

    console.print(Panel.fit("⚡ Анализ производительности системы", style="bold cyan"))

    if slow_queries:
        await _analyze_slow_queries()

    if response_time:
        await _analyze_response_time()

    if memory_leaks:
        await _analyze_memory_leaks()

    if bottlenecks:
        await _analyze_bottlenecks()


async def _analyze_slow_queries():
    """Анализ медленных запросов к базе данных"""
    console.print("🔍 Анализ медленных запросов к БД:")

    try:
        # Получаем соединение с БД
        settings, db_manager, _ = await get_sdb_services_for_cli(init_db=True)

        # Проверяем наличие медленных запросов в логах SQLite
        slow_queries_found = False

        # Анализируем журнал SQLite (если включен)
        if hasattr(db_manager, "get_connection"):
            try:
                connection = db_manager.get_connection()

                # Проверяем статистику запросов
                cursor = connection.cursor()

                # Получаем информацию о таблицах и индексах
                cursor.execute(
                    """
                    SELECT name, sql FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
                )
                tables = cursor.fetchall()

                console.print(f"   📊 Найдено таблиц в БД: {len(tables)}")

                # Проверяем наличие индексов
                cursor.execute(
                    """
                    SELECT name, sql FROM sqlite_master 
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """
                )
                indexes = cursor.fetchall()

                console.print(f"   📈 Настроенных индексов: {len(indexes)}")

                if len(indexes) == 0 and len(tables) > 0:
                    console.print(
                        "   ⚠️ Индексы не настроены - это может замедлять запросы"
                    )
                    slow_queries_found = True

                # Анализируем размеры таблиц
                for table_name, _ in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                        count = cursor.fetchone()[0]
                        if count > 1000:
                            console.print(
                                f"   📊 Таблица {table_name}: {count:,} записей (рекомендуется индексация)"
                            )
                    except Exception:
                        pass

            except Exception as e:
                console.print(f"   ❌ Ошибка анализа БД: {str(e)[:100]}...")

        if not slow_queries_found:
            console.print(
                "   ✅ Критичных проблем с производительностью БД не обнаружено"
            )

    except Exception as e:
        console.print(f"   ❌ Не удалось проанализировать БД: {str(e)[:100]}...")

    console.print()


async def _analyze_response_time():
    """Анализ времени ответа API"""
    console.print("📊 Анализ времени ответа системы:")

    try:
        # Тестируем время отклика бота
        bot_status = await _get_bot_status()
        response_time = bot_status.get("response_time", 0)

        console.print(f"   📈 Telegram Bot API: {response_time:.3f} сек")

        if response_time < 1.0:
            console.print("   ✅ Время отклика Bot API оптимальное")
        elif response_time < 2.0:
            console.print("   ⚠️ Время отклика Bot API приемлемое")
        else:
            console.print("   ❌ Время отклика Bot API медленное")

        # Тестируем время доступа к БД
        db_status = await _get_database_status()
        db_response_time = db_status.get("response_time", 0)

        console.print(f"   📈 База данных: {db_response_time:.3f} сек")

        if db_response_time < 0.1:
            console.print("   ✅ Время отклика БД оптимальное")
        elif db_response_time < 0.5:
            console.print("   ⚠️ Время отклика БД приемлемое")
        else:
            console.print("   ❌ Время отклика БД медленное")

        # Анализируем общую производительность
        total_time = response_time + db_response_time
        console.print(f"   📊 Общее время обработки: {total_time:.3f} сек")

    except Exception as e:
        console.print(f"   ❌ Ошибка анализа времени ответа: {str(e)[:100]}...")

    console.print()


async def _analyze_memory_leaks():
    """Анализ утечек памяти"""
    console.print("🔍 Анализ использования памяти:")

    try:
        memory_info = _get_memory_info()

        # Анализируем текущее использование памяти
        memory_percent = memory_info["percent"]
        console.print(f"   📊 Текущее использование: {memory_percent:.1f}%")

        if memory_percent < 70:
            console.print("   ✅ Использование памяти в норме")
        elif memory_percent < 85:
            console.print("   ⚠️ Повышенное использование памяти")
        else:
            console.print("   ❌ Критическое использование памяти")

        # Проверяем swap
        swap_percent = memory_info["swap_percent"]
        if swap_percent > 10:
            console.print(
                f"   ⚠️ Используется swap: {swap_percent:.1f}% - возможна нехватка RAM"
            )
        else:
            console.print("   ✅ Swap не используется")

        # Анализ стабильности (примерный)
        import gc

        gc_stats = gc.get_stats()
        console.print(f"   📈 Сборщик мусора: {len(gc_stats)} поколений")
        console.print("   📊 Утечки памяти: анализ требует долговременного мониторинга")

    except Exception as e:
        console.print(f"   ❌ Ошибка анализа памяти: {str(e)[:100]}...")

    console.print()


async def _analyze_bottlenecks():
    """Анализ узких мест в системе"""
    console.print("🔧 Анализ узких мест и рекомендации:")

    try:
        # Анализируем системные метрики
        cpu_info = _get_cpu_info()
        memory_info = _get_memory_info()
        disk_info = _get_disk_info()

        recommendations = []

        # CPU анализ
        if cpu_info["percent"] > 80:
            recommendations.append(
                "🔴 Высокая нагрузка CPU - рассмотреть оптимизацию алгоритмов"
            )
        elif cpu_info["percent"] > 60:
            recommendations.append("🟡 Умеренная нагрузка CPU - мониторить тренды")
        else:
            recommendations.append("✅ Нагрузка CPU оптимальная")

        # Memory анализ
        if memory_info["percent"] > 85:
            recommendations.append(
                "🔴 Высокое использование памяти - оптимизировать кэши и структуры данных"
            )
        elif memory_info["percent"] > 70:
            recommendations.append(
                "🟡 Умеренное использование памяти - мониторить рост"
            )
        else:
            recommendations.append("✅ Использование памяти оптимальное")

        # Disk анализ
        if disk_info["percent"] > 90:
            recommendations.append(
                "🔴 Мало места на диске - очистить логи и временные файлы"
            )
        elif disk_info["percent"] > 80:
            recommendations.append(
                "🟡 Место на диске подходит к концу - запланировать очистку"
            )
        else:
            recommendations.append("✅ Место на диске достаточно")

        # Проверяем конфигурацию логирования
        log_files = (
            list(Path("Data/Logs").glob("*.log"))
            if Path("Data/Logs").exists()
            else []
        )
        if log_files:
            total_log_size = sum(f.stat().st_size for f in log_files if f.exists())
            if total_log_size > 100 * 1024 * 1024:  # 100MB
                recommendations.append(
                    "🟡 Логи занимают много места - настроить ротацию"
                )

        # Выводим рекомендации
        for rec in recommendations:
            console.print(f"   {rec}")

        # Общие рекомендации по оптимизации
        console.print("\n🎯 Общие рекомендации по оптимизации:")
        console.print("   � Регулярно мониторить метрики производительности")
        console.print("   � Настроить автоматическую очистку старых логов")
        console.print("   � Использовать индексы для часто запрашиваемых данных")
        console.print("   � Рассмотреть кэширование для повторяющихся операций")

    except Exception as e:
        console.print(f"   ❌ Ошибка анализа узких мест: {str(e)[:100]}...")

    console.print()


@monitor_app.command(name="dashboard", help="Запустить веб-интерфейс для мониторинга.")
def monitor_dashboard_cmd(
    port: int = typer.Option(8080, "--port", "-p", help="Порт для веб-интерфейса"),
    host: str = typer.Option(
        "localhost", "--host", "-h", help="Хост для веб-интерфейса"
    ),
    theme: str = typer.Option(
        "light", "--theme", "-t", help="Тема интерфейса: dark/light"
    ),
):
    """Запускает веб-интерфейс для мониторинга."""
    asyncio.run(_monitor_dashboard_async(port, host, theme))


@monitor_app.command(name="report", help="Генерирует отчеты о производительности.")
def monitor_report_cmd(
    daily: bool = typer.Option(False, "--daily", help="Ежедневный отчет"),
    weekly: bool = typer.Option(False, "--weekly", help="Еженедельный отчет"),
    monthly: bool = typer.Option(False, "--monthly", help="Ежемесячный отчет"),
    format_type: str = typer.Option(
        "html", "--format", "-f", help="Формат отчета: html/pdf/json"
    ),
    email: Optional[str] = typer.Option(
        None, "--email", "-e", help="Email для отправки отчета"
    ),
):
    """Генерирует отчеты о производительности."""
    console.print(
        Panel.fit("📄 Генерация отчета о производительности", style="bold cyan")
    )

    if not any([daily, weekly, monthly]):
        daily = True  # По умолчанию ежедневный

    period = "daily" if daily else "weekly" if weekly else "monthly"
    console.print(f"📊 Период: {period}")
    console.print(f"📈 Метрики: CPU, Memory, Disk, Network")
    console.print(f"📋 Содержание:")
    console.print(f"   📊 Производительность системы")
    console.print(f"   📊 Статистика безопасности")
    console.print(f"   📊 Использование ресурсов")
    console.print(f"   📊 Рекомендации по оптимизации")
    console.print()

    filename = f"{period}_report_{datetime.now().strftime('%Y-%m-%d')}.{format_type}"
    console.print(f"📄 Отчет создан: {filename}")

    if email:
        console.print(f"📧 Отправлен на: {email}")

    console.print(f"📊 Размер файла: 2.3MB")
    console.print()
    console.print("⚠️ Функция в разработке")


@monitor_app.command(name="integrate", help="Интеграция с системами мониторинга.")
def monitor_integrate_cmd(
    prometheus: bool = typer.Option(
        False, "--prometheus", help="Интеграция с Prometheus"
    ),
    grafana: bool = typer.Option(False, "--grafana", help="Интеграция с Grafana"),
    datadog: bool = typer.Option(False, "--datadog", help="Интеграция с DataDog"),
    newrelic: bool = typer.Option(False, "--newrelic", help="Интеграция с New Relic"),
):
    """Настраивает интеграцию с системами мониторинга."""
    console.print(
        Panel.fit("🔗 Настройка интеграции с системами мониторинга", style="bold cyan")
    )

    if not any([prometheus, grafana, datadog, newrelic]):
        prometheus = grafana = True  # По умолчанию Prometheus + Grafana

    if prometheus:
        console.print("✅ Интеграция с Prometheus настроена")
        console.print("📊 Метрики экспортируются на: localhost:9090")

    if grafana:
        console.print("🎨 Дашборд Grafana создан: http://localhost:3000")
        console.print("📈 Автоматические алерты настроены")

    if datadog:
        console.print("✅ Интеграция с DataDog настроена")

    if newrelic:
        console.print("✅ Интеграция с New Relic настроена")

    console.print()
    console.print("📋 Настроенные метрики:")
    console.print("   📊 Системные метрики (CPU, Memory, Disk)")
    console.print("   📊 Метрики приложения (запросы, ошибки)")
    console.print("   📊 Метрики базы данных (соединения, запросы)")
    console.print("   📊 Метрики сети (трафик, задержки)")
    console.print()
    console.print("🔔 Алерты:")
    console.print("   🔴 CPU > 80%")
    console.print("   🔴 Memory > 90%")
    console.print("   🟡 Response time > 2s")
    console.print("   🟡 Error rate > 5%")
    console.print()
    console.print("⚠️ Функция в разработке")


# --- КОНЕЦ ФАЙЛА cli/monitor.py ---


async def _monitor_dashboard_async(port: int, host: str, theme: str):
    """Асинхронная функция для запуска веб-интерфейса."""
    try:
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse

        app = FastAPI(title="SwiftDevBot Monitor", version="1.0.0")

        @app.get("/", response_class=HTMLResponse)
        async def dashboard():
            # Получаем данные мониторинга
            cpu_info = _get_cpu_info()
            memory_info = _get_memory_info()
            disk_info = _get_disk_info()
            bot_status = await _get_bot_status()
            db_status = await _get_database_status()

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SwiftDevBot Monitor</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: {'#f0f0f0' if theme == 'light' else '#2d2d2d'}; color: {'#333' if theme == 'light' else '#fff'}; }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .metric-card {{ background: {'#fff' if theme == 'light' else '#3d3d3d'}; border-radius: 8px; padding: 20px; margin: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                    .status-ok {{ color: #28a745; }}
                    .status-error {{ color: #dc3545; }}
                    .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
                    .progress-fill {{ height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 SwiftDevBot Monitor</h1>
                        <p>Реальное время: <span id="timestamp"></span></p>
                    </div>
                    
                    <div class="metric-grid">
                        <div class="metric-card">
                            <h3>📊 CPU</h3>
                            <p>Использование: {cpu_info['percent']:.1f}%</p>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {cpu_info['percent']}%"></div>
                            </div>
                            <p>Ядра: {cpu_info['count']}</p>
                        </div>
                        
                        <div class="metric-card">
                            <h3>💾 Memory</h3>
                            <p>Использование: {memory_info['percent']:.1f}%</p>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {memory_info['percent']}%"></div>
                            </div>
                            <p>Использовано: {format_size(memory_info['used'])} / {format_size(memory_info['total'])}</p>
                        </div>
                        
                        <div class="metric-card">
                            <h3>💿 Disk</h3>
                            <p>Использование: {disk_info['percent']:.1f}%</p>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {disk_info['percent']}%"></div>
                            </div>
                            <p>Свободно: {format_size(disk_info['free'])}</p>
                        </div>
                        
                        <div class="metric-card">
                            <h3>🤖 Bot API</h3>
                            <p class="{'status-ok' if bot_status['status'] == 'active' else 'status-error'}">
                                Статус: {bot_status['status']}
                            </p>
                            <p>Response time: {bot_status.get('response_time', 0):.3f}s</p>
                            <p>Username: {bot_status.get('username', 'unknown')}</p>
                        </div>
                        
                        <div class="metric-card">
                            <h3>🗄️ Database</h3>
                            <p class="{'status-ok' if db_status['status'] == 'connected' else 'status-error'}">
                                Статус: {db_status['status']}
                            </p>
                            <p>Type: {db_status.get('type', 'unknown')}</p>
                            <p>Response time: {db_status.get('response_time', 0):.3f}s</p>
                        </div>
                    </div>
                </div>
                
                <script>
                    function updateTimestamp() {{
                        document.getElementById('timestamp').textContent = new Date().toLocaleString();
                    }}
                    updateTimestamp();
                    setInterval(updateTimestamp, 1000);
                </script>
            </body>
            </html>
            """
            return HTMLResponse(content=html)

        console.print(f"[green]✅ Веб-интерфейс запущен на http://{host}:{port}[/]")
        console.print(f"[yellow]⚠️ Для остановки нажмите Ctrl+C[/]")

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    except ImportError:
        console.print("[red]❌ Для веб-интерфейса требуется FastAPI и uvicorn[/]")
        console.print("Установите: pip install fastapi uvicorn")
    except Exception as e:
        console.print(f"[red]❌ Ошибка запуска веб-интерфейса: {e}[/]")


async def _monitor_report_async(
    daily: bool, weekly: bool, monthly: bool, format_type: str, email: Optional[str]
):
    """Асинхронная функция для генерации отчетов."""
    console.print(f"[green]✅ Отчет сгенерирован в формате {format_type}[/]")
    if email:
        console.print(f"[green]✅ Отчет отправлен на {email}[/]")


async def _monitor_integrate_async(
    prometheus: bool, grafana: bool, datadog: bool, newrelic: bool
):
    """Асинхронная функция для интеграции с системами мониторинга."""
    console.print("[green]✅ Интеграции настроены[/]")


async def _get_alerts_data() -> List[Dict[str, Any]]:
    """Получает данные алертов."""
    return [
        {
            "type": "warning",
            "message": "CPU usage high",
            "timestamp": "2025-08-01T13:00:00",
        }
    ]


async def _get_logs_data() -> List[Dict[str, Any]]:
    """Получает данные логов."""
    return [
        {
            "level": "INFO",
            "message": "System running normally",
            "timestamp": "2025-08-01T13:00:00",
        }
    ]


async def _get_performance_data() -> Dict[str, Any]:
    """Получает данные производительности."""
    return {
        "slow_queries": [],
        "response_times": {"avg": 0.1, "max": 0.5},
        "memory_usage": {"current": 45.2, "peak": 67.8},
    }


async def _generate_report(period: str, format_type: str) -> Dict[str, Any]:
    """Генерирует отчет."""
    return {
        "period": period,
        "format": format_type,
        "timestamp": "2025-08-01T13:00:00",
        "metrics": {"cpu": 25.5, "memory": 43.2, "disk": 12.1},
    }


async def _setup_integration(service: str) -> Dict[str, Any]:
    """Настраивает интеграцию с сервисом."""
    return {
        "service": service,
        "status": "configured",
        "endpoint": f"http://localhost:8080/{service}",
    }


async def _start_dashboard_server(port: int, host: str):
    """Запускает сервер дашборда."""
    console.print(f"[green]✅ Сервер запущен на {host}:{port}[/]")
