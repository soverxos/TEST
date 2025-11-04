# cli/tasks.py
import asyncio
import json
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
tasks_app = typer.Typer(name="tasks", help="📋 Управление задачами системы")

# Константы для задач
TASKS_DIR = Path("Data/tasks")
TASKS_CONFIG_FILE = TASKS_DIR / "tasks_config.json"
TASKS_LOG_FILE = TASKS_DIR / "tasks.log"


def _ensure_tasks_directory():
    """Создать директорию для задач если её нет"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    if not TASKS_CONFIG_FILE.exists():
        with open(TASKS_CONFIG_FILE, "w") as f:
            json.dump({"tasks": {}, "schedules": {}}, f)


def _load_tasks_config() -> Dict[str, Any]:
    """Загрузить конфигурацию задач"""
    _ensure_tasks_directory()
    try:
        with open(TASKS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tasks": {}, "schedules": {}}


def _save_tasks_config(config: Dict[str, Any]):
    """Сохранить конфигурацию задач"""
    _ensure_tasks_directory()
    with open(TASKS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _log_task_event(task_id: str, event: str, details: str = ""):
    """Записать событие задачи в лог"""
    _ensure_tasks_directory()
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {task_id}: {event}"
    if details:
        log_entry += f" - {details}"

    with open(TASKS_LOG_FILE, "a") as f:
        f.write(log_entry + "\n")


@tasks_app.command(name="list", help="Показать список задач.")
def tasks_list_cmd(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Фильтр по статусу: running, completed, failed, pending",
    ),
    limit: int = typer.Option(
        20, "--limit", "-l", help="Максимальное количество задач", min=1, max=100
    ),
):
    """Показать список задач"""
    try:
        asyncio.run(_tasks_list_async(status, limit))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'tasks list': {e}[/]")
        raise typer.Exit(code=1)


async def _tasks_list_async(status: Optional[str], limit: int):
    """Показать список задач"""
    console.print(
        Panel("[bold blue]СПИСОК ЗАДАЧ СИСТЕМЫ[/]", expand=False, border_style="blue")
    )

    config = _load_tasks_config()
    tasks = config.get("tasks", {})

    if not tasks:
        console.print("[yellow]Задачи не найдены[/]")
        return

    # Фильтруем задачи по статусу
    filtered_tasks = []
    for task_id, task_info in tasks.items():
        if status is None or task_info.get("status") == status:
            filtered_tasks.append((task_id, task_info))

    if not filtered_tasks:
        console.print(f"[yellow]Задачи со статусом '{status}' не найдены[/]")
        return

    # Сортируем по времени создания (новые сначала)
    filtered_tasks.sort(key=lambda x: x[1].get("created_at", ""), reverse=True)

    # Ограничиваем количество
    filtered_tasks = filtered_tasks[:limit]

    table = Table(title=f"Задачи системы (показано: {len(filtered_tasks)})")
    table.add_column("ID", style="cyan")
    table.add_column("Название", style="white")
    table.add_column("Тип", style="blue")
    table.add_column("Статус", style="green")
    table.add_column("Создана", style="yellow")
    table.add_column("Прогресс", style="red")

    for task_id, task_info in filtered_tasks:
        created_at = task_info.get("created_at", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                created_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                created_str = created_at
        else:
            created_str = "N/A"

        status = task_info.get("status", "unknown")
        status_color = {
            "running": "green",
            "completed": "blue",
            "failed": "red",
            "pending": "yellow",
            "cancelled": "red",
        }.get(status, "white")

        progress = task_info.get("progress", "0%")

        table.add_row(
            task_id,
            task_info.get("name", "Без названия"),
            task_info.get("type", "unknown"),
            f"[{status_color}]{status}[/{status_color}]",
            created_str,
            progress,
        )

    console.print(table)


@tasks_app.command(name="cancel", help="Отменить задачу.")
def tasks_cancel_cmd(
    task_id: str = typer.Argument(..., help="ID задачи для отмены"),
    force: bool = typer.Option(False, "--force", "-f", help="Принудительная отмена"),
):
    """Отменить задачу"""
    try:
        asyncio.run(_tasks_cancel_async(task_id, force))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'tasks cancel': {e}[/]")
        raise typer.Exit(code=1)


async def _tasks_cancel_async(task_id: str, force: bool):
    """Отменить задачу"""
    console.print(
        Panel(
            f"[bold blue]ОТМЕНА ЗАДАЧИ: {task_id}[/]", expand=False, border_style="blue"
        )
    )

    config = _load_tasks_config()
    tasks = config.get("tasks", {})

    if task_id not in tasks:
        console.print(f"[bold red]Задача '{task_id}' не найдена[/]")
        raise typer.Exit(code=1)

    task_info = tasks[task_id]
    status = task_info.get("status", "unknown")

    if status == "completed":
        console.print(f"[yellow]Задача '{task_id}' уже завершена[/]")
        return

    if status == "cancelled":
        console.print(f"[yellow]Задача '{task_id}' уже отменена[/]")
        return

    if status == "failed":
        console.print(f"[yellow]Задача '{task_id}' уже завершилась с ошибкой[/]")
        return

    # Проверяем, есть ли процесс задачи
    pid = task_info.get("pid")
    if pid and status == "running":
        try:
            process = psutil.Process(pid)
            if not force:
                console.print(f"[yellow]Задача '{task_id}' выполняется (PID: {pid})[/]")
                console.print("[dim]Используйте --force для принудительной отмены[/]")
                return

            # Принудительно завершаем процесс
            process.terminate()
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()

            console.print(f"[green]Процесс задачи '{task_id}' (PID: {pid}) завершен[/]")
        except psutil.NoSuchProcess:
            console.print(
                f"[yellow]Процесс задачи '{task_id}' (PID: {pid}) не найден[/]"
            )
        except Exception as e:
            console.print(f"[yellow]Ошибка при завершении процесса: {e}[/]")

    # Обновляем статус задачи
    task_info["status"] = "cancelled"
    task_info["cancelled_at"] = datetime.now().isoformat()
    task_info["progress"] = "0%"

    _save_tasks_config(config)
    _log_task_event(task_id, "cancelled", f"force={force}")

    console.print(f"[green]Задача '{task_id}' успешно отменена[/]")


@tasks_app.command(name="schedule", help="Запланировать задачу.")
def tasks_schedule_cmd(
    task_type: str = typer.Argument(
        ..., help="Тип задачи: backup, cleanup, sync, custom"
    ),
    schedule: str = typer.Option(
        ..., "--schedule", "-s", help="Расписание (cron формат или 'now')"
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Название задачи"),
    params: Optional[str] = typer.Option(
        None, "--params", "-p", help="Параметры задачи в JSON"
    ),
):
    """Запланировать задачу"""
    try:
        asyncio.run(_tasks_schedule_async(task_type, schedule, name, params))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'tasks schedule': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _tasks_schedule_async(
    task_type: str, schedule: str, name: Optional[str], params: Optional[str]
):
    """Запланировать задачу"""
    console.print(
        Panel(
            f"[bold blue]ПЛАНИРОВАНИЕ ЗАДАЧИ: {task_type}[/]",
            expand=False,
            border_style="blue",
        )
    )

    # Валидация типа задачи
    valid_types = ["backup", "cleanup", "sync", "custom"]
    if task_type not in valid_types:
        console.print(f"[bold red]Неизвестный тип задачи: {task_type}[/]")
        console.print(f"[dim]Доступные типы: {', '.join(valid_types)}[/]")
        raise typer.Exit(code=1)

    # Парсим параметры
    task_params = {}
    if params:
        try:
            task_params = json.loads(params)
        except json.JSONDecodeError as e:
            console.print(f"[bold red]Ошибка в JSON параметрах: {e}[/]")
            raise typer.Exit(code=1)

    # Генерируем ID задачи
    task_id = f"task_{uuid.uuid4().hex[:8]}"

    # Создаем информацию о задаче
    task_info = {
        "id": task_id,
        "name": name or f"{task_type} task",
        "type": task_type,
        "schedule": schedule,
        "params": task_params,
        "status": "pending",
        "progress": "0%",
        "created_at": datetime.now().isoformat(),
        "scheduled_at": datetime.now().isoformat() if schedule == "now" else None,
    }

    # Сохраняем в конфигурацию
    config = _load_tasks_config()
    config["tasks"][task_id] = task_info

    # Если задача должна выполниться сейчас
    if schedule == "now":
        task_info["status"] = "running"
        task_info["started_at"] = datetime.now().isoformat()

        # Запускаем задачу асинхронно
        asyncio.create_task(_execute_task(task_id, task_info))

    _save_tasks_config(config)
    _log_task_event(task_id, "scheduled", f"type={task_type}, schedule={schedule}")

    console.print(f"[green]Задача '{task_id}' успешно запланирована[/]")
    console.print(f"[dim]Тип: {task_type}[/]")
    console.print(f"[dim]Расписание: {schedule}[/]")
    if name:
        console.print(f"[dim]Название: {name}[/]")


async def _execute_task(task_id: str, task_info: Dict[str, Any]):
    """Выполнить задачу"""
    task_type = task_info["type"]

    try:
        _log_task_event(task_id, "started")

        if task_type == "backup":
            await _execute_backup_task(task_id, task_info)
        elif task_type == "cleanup":
            await _execute_cleanup_task(task_id, task_info)
        elif task_type == "sync":
            await _execute_sync_task(task_id, task_info)
        elif task_type == "custom":
            await _execute_custom_task(task_id, task_info)
        else:
            raise ValueError(f"Неизвестный тип задачи: {task_type}")

        # Обновляем статус на завершенный
        config = _load_tasks_config()
        if task_id in config["tasks"]:
            config["tasks"][task_id]["status"] = "completed"
            config["tasks"][task_id]["progress"] = "100%"
            config["tasks"][task_id]["completed_at"] = datetime.now().isoformat()
            _save_tasks_config(config)
            _log_task_event(task_id, "completed")

    except Exception as e:
        # Обновляем статус на ошибку
        config = _load_tasks_config()
        if task_id in config["tasks"]:
            config["tasks"][task_id]["status"] = "failed"
            config["tasks"][task_id]["error"] = str(e)
            config["tasks"][task_id]["failed_at"] = datetime.now().isoformat()
            _save_tasks_config(config)
            _log_task_event(task_id, "failed", str(e))


async def _execute_backup_task(task_id: str, task_info: Dict[str, Any]):
    """Выполнить задачу резервного копирования"""
    console.print(f"[cyan]Выполнение задачи резервного копирования: {task_id}[/]")

    # Симуляция выполнения
    await asyncio.sleep(2)

    # Здесь была бы реальная логика резервного копирования
    console.print(f"[green]Резервное копирование завершено: {task_id}[/]")


async def _execute_cleanup_task(task_id: str, task_info: Dict[str, Any]):
    """Выполнить задачу очистки"""
    console.print(f"[cyan]Выполнение задачи очистки: {task_id}[/]")

    # Симуляция выполнения
    await asyncio.sleep(1)

    # Здесь была бы реальная логика очистки
    console.print(f"[green]Очистка завершена: {task_id}[/]")


async def _execute_sync_task(task_id: str, task_info: Dict[str, Any]):
    """Выполнить задачу синхронизации"""
    console.print(f"[cyan]Выполнение задачи синхронизации: {task_id}[/]")

    # Симуляция выполнения
    await asyncio.sleep(3)

    # Здесь была бы реальная логика синхронизации
    console.print(f"[green]Синхронизация завершена: {task_id}[/]")


async def _execute_custom_task(task_id: str, task_info: Dict[str, Any]):
    """Выполнить пользовательскую задачу"""
    console.print(f"[cyan]Выполнение пользовательской задачи: {task_id}[/]")

    params = task_info.get("params", {})
    command = params.get("command")

    if command:
        try:
            # Выполняем команду
            process = await asyncio.create_subprocess_exec(
                *command.split(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                console.print(f"[green]Команда выполнена успешно: {command}[/]")
            else:
                raise Exception(f"Команда завершилась с ошибкой: {stderr.decode()}")

        except Exception as e:
            raise Exception(f"Ошибка выполнения команды: {e}")
    else:
        # Симуляция выполнения
        await asyncio.sleep(1)
        console.print(f"[green]Пользовательская задача завершена: {task_id}[/]")


@tasks_app.command(name="info", help="Показать информацию о задаче.")
def tasks_info_cmd(task_id: str = typer.Argument(..., help="ID задачи")):
    """Показать информацию о задаче"""
    try:
        asyncio.run(_tasks_info_async(task_id))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'tasks info': {e}[/]")
        raise typer.Exit(code=1)


async def _tasks_info_async(task_id: str):
    """Показать информацию о задаче"""
    console.print(
        Panel(
            f"[bold blue]ИНФОРМАЦИЯ О ЗАДАЧЕ: {task_id}[/]",
            expand=False,
            border_style="blue",
        )
    )

    config = _load_tasks_config()
    tasks = config.get("tasks", {})

    if task_id not in tasks:
        console.print(f"[bold red]Задача '{task_id}' не найдена[/]")
        raise typer.Exit(code=1)

    task_info = tasks[task_id]

    console.print(f"[cyan]ID:[/] {task_id}")
    console.print(f"[cyan]Название:[/] {task_info.get('name', 'N/A')}")
    console.print(f"[cyan]Тип:[/] {task_info.get('type', 'N/A')}")
    console.print(f"[cyan]Статус:[/] {task_info.get('status', 'N/A')}")
    console.print(f"[cyan]Прогресс:[/] {task_info.get('progress', 'N/A')}")
    console.print(f"[cyan]Расписание:[/] {task_info.get('schedule', 'N/A')}")
    console.print(f"[cyan]Создана:[/] {task_info.get('created_at', 'N/A')}")

    if task_info.get("started_at"):
        console.print(f"[cyan]Начата:[/] {task_info['started_at']}")

    if task_info.get("completed_at"):
        console.print(f"[cyan]Завершена:[/] {task_info['completed_at']}")

    if task_info.get("failed_at"):
        console.print(f"[cyan]Ошибка:[/] {task_info['failed_at']}")
        console.print(f"[cyan]Сообщение об ошибке:[/] {task_info.get('error', 'N/A')}")

    if task_info.get("cancelled_at"):
        console.print(f"[cyan]Отменена:[/] {task_info['cancelled_at']}")

    if task_info.get("params"):
        console.print(
            f"[cyan]Параметры:[/] {json.dumps(task_info['params'], indent=2)}"
        )


if __name__ == "__main__":
    tasks_app()
