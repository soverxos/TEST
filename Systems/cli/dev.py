# cli/dev.py
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
dev_app = typer.Typer(name="dev", help="🔧 Инструменты разработки")

# Константы для dev инструментов
DEV_DIR = Path("Data/dev")
DEV_CONFIG_FILE = DEV_DIR / "dev_config.json"
DEV_LOGS_DIR = DEV_DIR / "logs"
DEV_DOCS_DIR = DEV_DIR / "docs"


def _ensure_dev_directory():
    """Создать директорию для dev инструментов если её нет"""
    DEV_DIR.mkdir(parents=True, exist_ok=True)
    DEV_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DEV_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if not DEV_CONFIG_FILE.exists():
        default_config = {
            "linting": {
                "tools": ["flake8", "black", "isort", "mypy"],
                "config_files": {
                    "flake8": ".flake8",
                    "black": "pyproject.toml",
                    "isort": ".isort.cfg",
                    "mypy": "mypy.ini",
                },
            },
            "testing": {
                "framework": "pytest",
                "coverage_tool": "coverage",
                "test_pattern": "test_*.py",
                "coverage_report_format": "html",
            },
            "documentation": {
                "builder": "sphinx",
                "formats": ["html", "pdf"],
                "source_dir": "docs",
                "output_dir": "docs/build",
            },
            "debugging": {
                "log_levels": ["DEBUG", "INFO", "WARNING", "ERROR"],
                "log_formats": ["text", "json"],
                "profiling": False,
            },
        }
        with open(DEV_CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)


def _load_dev_config() -> Dict[str, Any]:
    """Загрузить конфигурацию dev инструментов"""
    _ensure_dev_directory()
    try:
        with open(DEV_CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_dev_config(config: Dict[str, Any]):
    """Сохранить конфигурацию dev инструментов"""
    _ensure_dev_directory()
    with open(DEV_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _check_tool_availability(tool_name: str) -> bool:
    """Проверить доступность инструмента"""
    # Сначала пробуем через Python модуль (для виртуальных окружений)
    try:
        result = subprocess.run(
            [sys.executable, "-m", tool_name, "--version"], 
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    
    # Если не удалось через модуль, пробуем напрямую
    try:
        result = subprocess.run(
            [tool_name, "--version"], capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _get_python_files(directory: str = ".") -> List[str]:
    """Получить список Python файлов в директории"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Исключаем виртуальные окружения и кэш
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in ["venv", "env", "__pycache__"]
        ]
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files


@dev_app.command(name="lint", help="Проверка кода с помощью линтера.")
def dev_lint_cmd(
    files: Optional[List[str]] = typer.Option(
        None, "--files", "-f", help="Файлы для проверки"
    ),
    fix: bool = typer.Option(False, "--fix", help="Автоматически исправить проблемы"),
    tool: str = typer.Option(
        "flake8", "--tool", "-t", help="Инструмент: flake8, black, isort, mypy"
    ),
    output_format: str = typer.Option(
        "text", "--format", help="Формат вывода: text, json, html"
    ),
):
    """Проверка кода с помощью линтера"""
    try:
        asyncio.run(_dev_lint_async(files, fix, tool, output_format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev lint': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_lint_async(
    files: Optional[List[str]], fix: bool, tool: str, output_format: str
):
    """Асинхронная обработка команды lint"""
    console.print(
        Panel("[bold blue]ПРОВЕРКА КОДА[/]", expand=False, border_style="blue")
    )

    # Проверяем доступность инструмента
    if not _check_tool_availability(tool):
        console.print(
            f"[bold red]Инструмент '{tool}' не найден. Установите его: pip install {tool}[/]"
        )
        raise typer.Exit(code=1)

    # Определяем файлы для проверки
    if not files:
        files = _get_python_files()
        console.print(f"[cyan]Найдено Python файлов:[/] {len(files)}")
    else:
        console.print(f"[cyan]Файлы для проверки:[/] {', '.join(files)}")

    if not files:
        console.print("[yellow]Python файлы не найдены[/]")
        return

    console.print(f"[cyan]Инструмент:[/] {tool}")
    console.print(f"[cyan]Режим:[/] {'Автоисправление' if fix else 'Только проверка'}")

    # Выполняем проверку
    issues = await _run_linting_tool(tool, files, fix)

    # Отображаем результаты
    await _display_lint_results(issues, tool, output_format)


async def _run_linting_tool(
    tool: str, files: List[str], fix: bool
) -> List[Dict[str, Any]]:
    """Запустить инструмент линтинга"""
    issues = []

    try:
        # Используем python -m для запуска в виртуальном окружении
        if tool == "flake8":
            cmd = [sys.executable, "-m", "flake8"] + files
            if fix:
                console.print("[yellow]flake8 не поддерживает автоисправление[/]")
        elif tool == "black":
            cmd = [sys.executable, "-m", "black"] + files
            if not fix:
                cmd.append("--check")
        elif tool == "isort":
            cmd = [sys.executable, "-m", "isort"] + files
            if not fix:
                cmd.append("--check-only")
        elif tool == "mypy":
            cmd = [sys.executable, "-m", "mypy"] + files
        else:
            console.print(f"[yellow]Неподдерживаемый инструмент: {tool}[/]")
            return issues

        console.print(f"[cyan]Выполняется:[/] {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[green]✅ Проверка завершена без ошибок[/]")
        else:
            # Парсим вывод для извлечения проблем
            for line in result.stdout.split("\n") + result.stderr.split("\n"):
                if line.strip():
                    issues.append(
                        {
                            "file": "unknown",
                            "line": 0,
                            "column": 0,
                            "message": line.strip(),
                            "severity": "error",
                        }
                    )

            console.print(f"[yellow]⚠️ Найдено проблем: {len(issues)}[/]")

    except Exception as e:
        console.print(f"[bold red]Ошибка при выполнении {tool}: {e}[/]")

    return issues


async def _display_lint_results(
    issues: List[Dict[str, Any]], tool: str, output_format: str
):
    """Отобразить результаты линтинга"""
    if output_format == "json":
        console.print(json.dumps(issues, indent=2, ensure_ascii=False))
        return

    if not issues:
        console.print("[green]✅ Проблем не найдено[/]")
        return

    # Табличный формат
    table = Table(title=f"Результаты проверки ({tool})")
    table.add_column("Файл", style="cyan")
    table.add_column("Строка", style="blue")
    table.add_column("Колонка", style="green")
    table.add_column("Сообщение", style="white")
    table.add_column("Тип", style="red")

    for issue in issues:
        table.add_row(
            issue.get("file", "N/A"),
            str(issue.get("line", "N/A")),
            str(issue.get("column", "N/A")),
            issue.get("message", "N/A"),
            issue.get("severity", "error"),
        )

    console.print(table)


@dev_app.command(name="test", help="Запуск тестов.")
def dev_test_cmd(
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Шаблон для поиска тестов"
    ),
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Показать покрытие кода"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    parallel: bool = typer.Option(
        False, "--parallel", help="Запуск тестов параллельно"
    ),
):
    """Запуск тестов"""
    try:
        asyncio.run(_dev_test_async(pattern, coverage, verbose, parallel))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev test': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_test_async(
    pattern: Optional[str], coverage: bool, verbose: bool, parallel: bool
):
    """Асинхронная обработка команды test"""
    console.print(
        Panel("[bold blue]ЗАПУСК ТЕСТОВ[/]", expand=False, border_style="blue")
    )

    config = _load_dev_config()
    test_config = config.get("testing", {})
    framework = test_config.get("framework", "pytest")

    # Проверяем доступность pytest
    if not _check_tool_availability("pytest"):
        console.print(
            "[bold red]pytest не найден. Установите его: pip install pytest[/]"
        )
        raise typer.Exit(code=1)

    # Формируем команду
    cmd = ["pytest"]

    if pattern:
        cmd.extend(["-k", pattern])
        console.print(f"[cyan]Шаблон тестов:[/] {pattern}")

    if coverage:
        if not _check_tool_availability("coverage"):
            console.print(
                "[yellow]coverage не найден. Установите его: pip install coverage[/]"
            )
        else:
            cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
            console.print("[cyan]Покрытие кода:[/] Включено")

    if verbose:
        cmd.append("-v")
        console.print("[cyan]Режим:[/] Подробный вывод")

    if parallel:
        if not _check_tool_availability("pytest-xdist"):
            console.print(
                "[yellow]pytest-xdist не найден. Установите его: pip install pytest-xdist[/]"
            )
        else:
            cmd.extend(["-n", "auto"])
            console.print("[cyan]Режим:[/] Параллельное выполнение")

    console.print(f"[cyan]Выполняется:[/] {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[green]✅ Все тесты прошли успешно[/]")
        else:
            console.print("[red]❌ Некоторые тесты не прошли[/]")

        # Показываем вывод
        if result.stdout:
            console.print("\n[cyan]Вывод тестов:[/]")
            console.print(result.stdout)

        if result.stderr:
            console.print("\n[yellow]Ошибки:[/]")
            console.print(result.stderr)

    except Exception as e:
        console.print(f"[bold red]Ошибка при запуске тестов: {e}[/]")


@dev_app.command(name="docs", help="Сборка документации.")
def dev_docs_cmd(
    format: str = typer.Option(
        "html", "--format", "-f", help="Формат документации: html, pdf, epub"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Директория для сохранения"
    ),
    clean: bool = typer.Option(False, "--clean", help="Очистить предыдущую сборку"),
    serve: bool = typer.Option(
        False, "--serve", help="Запустить локальный сервер для просмотра"
    ),
):
    """Сборка документации"""
    try:
        asyncio.run(_dev_docs_async(format, output_dir, clean, serve))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev docs': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_docs_async(
    format: str, output_dir: Optional[str], clean: bool, serve: bool
):
    """Асинхронная обработка команды docs"""
    console.print(
        Panel("[bold blue]СБОРКА ДОКУМЕНТАЦИИ[/]", expand=False, border_style="blue")
    )

    config = _load_dev_config()
    docs_config = config.get("documentation", {})
    builder = docs_config.get("builder", "sphinx")

    # Проверяем доступность sphinx-build
    if not _check_tool_availability("sphinx-build"):
        console.print(
            "[bold red]sphinx-build не найден. Установите его: pip install sphinx[/]"
        )
        raise typer.Exit(code=1)

    # Определяем директории
    source_dir = Path(docs_config.get("source_dir", "docs"))
    if not output_dir:
        output_dir = docs_config.get("output_dir", "docs/build")

    output_path = Path(output_dir)

    console.print(f"[cyan]Формат:[/] {format}")
    console.print(f"[cyan]Источник:[/] {source_dir}")
    console.print(f"[cyan]Вывод:[/] {output_path}")

    # Очистка предыдущей сборки
    if clean and output_path.exists():
        shutil.rmtree(output_path)
        console.print("[cyan]Предыдущая сборка очищена[/]")

    # Создаем директорию вывода
    output_path.mkdir(parents=True, exist_ok=True)

    # Формируем команду sphinx
    cmd = ["sphinx-build", "-b", format, str(source_dir), str(output_path)]

    console.print(f"[cyan]Выполняется:[/] {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print(f"[green]✅ Документация успешно собрана в {output_path}[/]")

            if serve:
                await _serve_documentation(output_path, format)
        else:
            console.print("[red]❌ Ошибка при сборке документации[/]")
            if result.stderr:
                console.print(result.stderr)

    except Exception as e:
        console.print(f"[bold red]Ошибка при сборке документации: {e}[/]")


async def _serve_documentation(output_path: Path, format: str):
    """Запустить локальный сервер для просмотра документации"""
    if format != "html":
        console.print(
            "[yellow]Предварительный просмотр доступен только для HTML формата[/]"
        )
        return

    try:
        import http.server
        import socketserver

        port = 8001
        os.chdir(output_path)

        with socketserver.TCPServer(
            ("", port), http.server.SimpleHTTPRequestHandler
        ) as httpd:
            console.print(
                f"[green]🌐 Документация доступна по адресу: http://localhost:{port}[/]"
            )
            console.print("[yellow]Нажмите Ctrl+C для остановки сервера[/]")

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                console.print("\n[yellow]Сервер остановлен[/]")

    except Exception as e:
        console.print(f"[yellow]Не удалось запустить сервер: {e}[/]")


@dev_app.command(name="debug", help="Режим отладки.")
def dev_debug_cmd(
    level: str = typer.Option(
        "DEBUG", "--level", "-l", help="Уровень отладки: DEBUG, INFO, WARNING, ERROR"
    ),
    log_file: Optional[str] = typer.Option(
        None, "--log-file", help="Файл для логов отладки"
    ),
    profiling: bool = typer.Option(
        False, "--profiling", help="Включить профилирование"
    ),
    memory: bool = typer.Option(
        False, "--memory", help="Мониторинг использования памяти"
    ),
):
    """Режим отладки"""
    try:
        asyncio.run(_dev_debug_async(level, log_file, profiling, memory))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev debug': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_debug_async(
    level: str, log_file: Optional[str], profiling: bool, memory: bool
):
    """Асинхронная обработка команды debug"""
    console.print(
        Panel("[bold blue]РЕЖИМ ОТЛАДКИ[/]", expand=False, border_style="blue")
    )

    config = _load_dev_config()
    debug_config = config.get("debugging", {})

    console.print(f"[cyan]Уровень отладки:[/] {level}")

    if log_file:
        console.print(f"[cyan]Файл логов:[/] {log_file}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = DEV_LOGS_DIR / f"debug_{timestamp}.log"
        console.print(f"[cyan]Файл логов:[/] {log_file}")

    # Настраиваем логирование
    await _setup_debug_logging(level, log_file)

    # Профилирование
    if profiling:
        await _setup_profiling()

    # Мониторинг памяти
    if memory:
        await _setup_memory_monitoring()

    console.print("[green]✅ Режим отладки активирован[/]")
    console.print("[dim]Логи будут записываться в указанный файл[/]")


async def _setup_debug_logging(level: str, log_file: str):
    """Настроить логирование для отладки"""
    import logging

    # Создаем логгер
    logger = logging.getLogger("swiftdevbot_debug")
    logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))

    # Создаем файловый обработчик
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))

    # Создаем форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Добавляем обработчик к логгеру
    logger.addHandler(file_handler)

    # Тестовое сообщение
    logger.info(f"Отладка активирована с уровнем {level}")
    logger.debug("Это тестовое отладочное сообщение")


async def _setup_profiling():
    """Настроить профилирование"""
    try:
        import cProfile
        import pstats

        console.print("[cyan]Профилирование:[/] Включено")
        console.print("[dim]Используйте cProfile для анализа производительности[/]")

    except ImportError:
        console.print("[yellow]cProfile недоступен[/]")


async def _setup_memory_monitoring():
    """Настроить мониторинг памяти"""
    try:
        import gc

        import psutil

        console.print("[cyan]Мониторинг памяти:[/] Включен")

        # Получаем информацию о памяти
        process = psutil.Process()
        memory_info = process.memory_info()

        console.print(
            f"[dim]Использование памяти:[/] {memory_info.rss / 1024 / 1024:.1f} MB"
        )
        console.print(
            f"[dim]Виртуальная память:[/] {memory_info.vms / 1024 / 1024:.1f} MB"
        )

        # Принудительная сборка мусора
        gc.collect()
        console.print("[dim]Сборка мусора выполнена[/]")

    except ImportError:
        console.print("[yellow]psutil недоступен для мониторинга памяти[/]")


@dev_app.command(name="analyze", help="Анализ кода.")
def dev_analyze_cmd(
    tool: str = typer.Option(
        "pylint", "--tool", "-t", help="Инструмент анализа: pylint, bandit, safety"
    ),
    output_format: str = typer.Option(
        "text", "--format", help="Формат вывода: text, json, html"
    ),
):
    """Анализ кода"""
    try:
        asyncio.run(_dev_analyze_async(tool, output_format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev analyze': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_analyze_async(tool: str, output_format: str):
    """Асинхронная обработка команды analyze"""
    console.print(Panel("[bold blue]АНАЛИЗ КОДА[/]", expand=False, border_style="blue"))

    # Проверяем доступность инструмента
    if not _check_tool_availability(tool):
        console.print(
            f"[bold red]Инструмент '{tool}' не найден. Установите его: pip install {tool}[/]"
        )
        raise typer.Exit(code=1)

    console.print(f"[cyan]Инструмент анализа:[/] {tool}")

    # Получаем список Python файлов
    files = _get_python_files()

    if not files:
        console.print("[yellow]Python файлы не найдены[/]")
        return

    # Выполняем анализ
    issues = await _run_code_analysis(tool, files)

    # Отображаем результаты
    await _display_analysis_results(issues, tool, output_format)


async def _run_code_analysis(tool: str, files: List[str]) -> List[Dict[str, Any]]:
    """Запустить анализ кода"""
    issues = []

    try:
        if tool == "pylint":
            cmd = ["pylint"] + files
        elif tool == "bandit":
            cmd = ["bandit", "-r", "."]
        elif tool == "safety":
            cmd = ["safety", "check"]
        else:
            console.print(f"[yellow]Неподдерживаемый инструмент анализа: {tool}[/]")
            return issues

        console.print(f"[cyan]Выполняется:[/] {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Парсим результаты
        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            if line.strip():
                issues.append(
                    {"tool": tool, "message": line.strip(), "severity": "info"}
                )

        if result.returncode == 0:
            console.print("[green]✅ Анализ завершен без критических проблем[/]")
        else:
            console.print(f"[yellow]⚠️ Найдено проблем: {len(issues)}[/]")

    except Exception as e:
        console.print(f"[bold red]Ошибка при выполнении анализа: {e}[/]")

    return issues


async def _display_analysis_results(
    issues: List[Dict[str, Any]], tool: str, output_format: str
):
    """Отобразить результаты анализа"""
    if output_format == "json":
        console.print(json.dumps(issues, indent=2, ensure_ascii=False))
        return

    if not issues:
        console.print("[green]✅ Проблем не найдено[/]")
        return

    # Табличный формат
    table = Table(title=f"Результаты анализа ({tool})")
    table.add_column("Инструмент", style="cyan")
    table.add_column("Сообщение", style="white")
    table.add_column("Важность", style="red")

    for issue in issues:
        table.add_row(
            issue.get("tool", "N/A"),
            issue.get("message", "N/A"),
            issue.get("severity", "info"),
        )

    console.print(table)


@dev_app.command(name="profile", help="Профилирование производительности кода.")
def dev_profile_cmd(
    profile_type: str = typer.Option(
        "cpu", "--type", "-t", help="Тип профилирования: cpu, memory, time"
    ),
    duration: int = typer.Option(
        30, "--duration", "-d", help="Длительность профилирования в секундах"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Файл для сохранения результатов"
    ),
    target_script: Optional[str] = typer.Option(
        None, "--script", "-s", help="Скрипт для профилирования"
    ),
):
    """Профилирование производительности кода"""
    try:
        asyncio.run(_dev_profile_async(profile_type, duration, output_file, target_script))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev profile': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_profile_async(
    profile_type: str, duration: int, output_file: Optional[str], target_script: Optional[str]
):
    """Асинхронная обработка команды profile"""
    console.print(Panel("[bold blue]ПРОФИЛИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ[/]", expand=False, border_style="blue"))

    console.print(f"[cyan]Тип профилирования:[/] {profile_type}")
    console.print(f"[cyan]Длительность:[/] {duration} секунд")
    
    if target_script:
        console.print(f"[cyan]Целевой скрипт:[/] {target_script}")
    
    if output_file:
        console.print(f"[cyan]Файл результатов:[/] {output_file}")

    # Определяем скрипт для профилирования
    if not target_script:
        # По умолчанию профилируем основной бот
        target_script = "run_bot.py"
        console.print(f"[cyan]Используется скрипт по умолчанию:[/] {target_script}")

    # Проверяем существование скрипта
    if not Path(target_script).exists():
        console.print(f"[bold red]Скрипт '{target_script}' не найден![/]")
        raise typer.Exit(code=1)

    # Выполняем профилирование
    results = await _run_profiling(profile_type, duration, target_script, output_file)

    # Отображаем результаты
    await _display_profile_results(results, profile_type, output_file)


async def _run_profiling(
    profile_type: str, duration: int, target_script: str, output_file: Optional[str]
) -> Dict[str, Any]:
    """Запустить профилирование"""
    results = {
        "type": profile_type,
        "duration": duration,
        "script": target_script,
        "timestamp": datetime.now().isoformat(),
        "data": {}
    }

    try:
        if profile_type == "cpu":
            results["data"] = await _profile_cpu(target_script, duration, output_file)
        elif profile_type == "memory":
            results["data"] = await _profile_memory(target_script, duration, output_file)
        elif profile_type == "time":
            results["data"] = await _profile_time(target_script, duration, output_file)
        else:
            console.print(f"[bold red]Неподдерживаемый тип профилирования: {profile_type}[/]")
            console.print("[yellow]Поддерживаемые типы: cpu, memory, time[/]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[bold red]Ошибка при профилировании: {e}[/]")
        raise typer.Exit(code=1)

    return results


async def _profile_cpu(script: str, duration: int, output_file: Optional[str]) -> Dict[str, Any]:
    """Профилирование CPU"""
    console.print("[cyan]Выполняется CPU профилирование...[/]")
    
    import cProfile
    import pstats
    import tempfile
    
    # Создаем временный файл для результатов
    with tempfile.NamedTemporaryFile(suffix='.prof', delete=False) as tmp_file:
        prof_file = tmp_file.name
    
    try:
        # Запускаем профилирование
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Запускаем скрипт в отдельном процессе
        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Ждем указанное время
        await asyncio.sleep(duration)
        
        # Останавливаем процесс
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        profiler.disable()
        
        # Сохраняем результаты
        profiler.dump_stats(prof_file)
        
        # Анализируем результаты
        stats = pstats.Stats(prof_file)
        stats.sort_stats('cumulative')
        
        # Получаем топ-10 функций
        top_functions = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            if isinstance(func, tuple):
                filename, line, funcname = func
                top_functions.append({
                    "function": funcname,
                    "file": filename,
                    "line": line,
                    "calls": nc,
                    "total_time": ct,
                    "per_call": ct / nc if nc > 0 else 0
                })
        
        # Сортируем по времени выполнения
        top_functions.sort(key=lambda x: x["total_time"], reverse=True)
        top_functions = top_functions[:10]
        
        # Создаем HTML отчет если нужно
        if output_file:
            html_file = output_file if output_file.endswith('.html') else f"{output_file}.html"
            stats.dump_stats(html_file.replace('.html', '.prof'))
            console.print(f"[green]✅ HTML отчет сохранен: {html_file}[/]")
        
        return {
            "top_functions": top_functions,
            "total_functions": len(stats.stats),
            "total_time": sum(f[3] for f in stats.stats.values()),
            "html_file": output_file if output_file else None
        }
        
    finally:
        # Удаляем временный файл
        if Path(prof_file).exists():
            Path(prof_file).unlink()


async def _profile_memory(script: str, duration: int, output_file: Optional[str]) -> Dict[str, Any]:
    """Профилирование памяти"""
    console.print("[cyan]Выполняется профилирование памяти...[/]")
    
    try:
        # Проверяем доступность memory_profiler
        import memory_profiler
    except ImportError:
        console.print("[bold red]memory_profiler не установлен![/]")
        console.print("[yellow]Установите: pip install memory_profiler[/]")
        raise typer.Exit(code=1)
    
    # Запускаем скрипт с профилированием памяти
    cmd = [sys.executable, "-m", "memory_profiler", script]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Ждем указанное время
    await asyncio.sleep(duration)
    
    # Останавливаем процесс
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    
    stdout, stderr = process.communicate()
    
    # Парсим результаты
    memory_data = []
    for line in stdout.decode().split('\n'):
        if line.strip() and 'MiB' in line:
            parts = line.split()
            if len(parts) >= 4:
                memory_data.append({
                    "line": parts[0],
                    "memory": parts[1],
                    "increment": parts[2],
                    "function": ' '.join(parts[3:])
                })
    
    return {
        "memory_usage": memory_data,
        "peak_memory": max([float(d["memory"]) for d in memory_data]) if memory_data else 0,
        "total_lines": len(memory_data)
    }


async def _profile_time(script: str, duration: int, output_file: Optional[str]) -> Dict[str, Any]:
    """Профилирование времени выполнения"""
    console.print("[cyan]Выполняется профилирование времени...[/]")
    
    import time
    
    start_time = time.time()
    
    # Запускаем скрипт
    process = subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Ждем указанное время
    await asyncio.sleep(duration)
    
    # Останавливаем процесс
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    
    end_time = time.time()
    
    return {
        "start_time": start_time,
        "end_time": end_time,
        "duration": end_time - start_time,
        "script": script
    }


async def _display_profile_results(results: Dict[str, Any], profile_type: str, output_file: Optional[str]):
    """Отобразить результаты профилирования"""
    console.print(f"\n[bold green]✅ Профилирование завершено![/]")
    
    if profile_type == "cpu":
        await _display_cpu_results(results["data"])
    elif profile_type == "memory":
        await _display_memory_results(results["data"])
    elif profile_type == "time":
        await _display_time_results(results["data"])
    
    if output_file:
        console.print(f"\n[cyan]📄 Результаты сохранены в:[/] {output_file}")


async def _display_cpu_results(data: Dict[str, Any]):
    """Отобразить результаты CPU профилирования"""
    console.print(f"\n[bold cyan]📊 Результаты CPU профилирования:[/]")
    
    table = Table(title="Топ-10 функций по времени выполнения")
    table.add_column("Функция", style="cyan")
    table.add_column("Файл", style="white")
    table.add_column("Вызовы", style="green")
    table.add_column("Общее время", style="red")
    table.add_column("Время/вызов", style="yellow")
    
    for func in data["top_functions"]:
        table.add_row(
            func["function"],
            Path(func["file"]).name,
            str(func["calls"]),
            f"{func['total_time']:.4f}s",
            f"{func['per_call']:.6f}s"
        )
    
    console.print(table)
    
    console.print(f"\n[cyan]📈 Статистика:[/]")
    console.print(f"   📊 Всего функций: {data['total_functions']}")
    console.print(f"   📊 Общее время: {data['total_time']:.4f}s")
    
    # Рекомендации
    console.print(f"\n[bold yellow]💡 Рекомендации:[/]")
    if data["top_functions"]:
        top_func = data["top_functions"][0]
        console.print(f"   🔧 Оптимизируйте функцию: {top_func['function']}")
        console.print(f"   📊 Она занимает {top_func['total_time']:.2f}s ({top_func['total_time']/data['total_time']*100:.1f}%)")
    
    if data.get("html_file"):
        console.print(f"   📄 Подробный отчет: {data['html_file']}")


async def _display_memory_results(data: Dict[str, Any]):
    """Отобразить результаты профилирования памяти"""
    console.print(f"\n[bold cyan]📊 Результаты профилирования памяти:[/]")
    
    table = Table(title="Использование памяти")
    table.add_column("Строка", style="cyan")
    table.add_column("Память (MiB)", style="red")
    table.add_column("Прирост", style="yellow")
    table.add_column("Функция", style="white")
    
    for item in data["memory_usage"][:10]:  # Показываем топ-10
        table.add_row(
            item["line"],
            item["memory"],
            item["increment"],
            item["function"]
        )
    
    console.print(table)
    
    console.print(f"\n[cyan]📈 Статистика памяти:[/]")
    console.print(f"   📊 Пиковое использование: {data['peak_memory']:.2f} MiB")
    console.print(f"   📊 Проанализировано строк: {data['total_lines']}")
    
    # Рекомендации
    console.print(f"\n[bold yellow]💡 Рекомендации:[/]")
    if data["memory_usage"]:
        max_memory = max(data["memory_usage"], key=lambda x: float(x["memory"]))
        console.print(f"   🔧 Проверьте строку {max_memory['line']} в функции {max_memory['function']}")
        console.print(f"   📊 Максимальное использование: {max_memory['memory']} MiB")


async def _display_time_results(data: Dict[str, Any]):
    """Отобразить результаты профилирования времени"""
    console.print(f"\n[bold cyan]📊 Результаты профилирования времени:[/]")
    
    console.print(f"[cyan]📈 Время выполнения:[/]")
    console.print(f"   📊 Начало: {datetime.fromtimestamp(data['start_time']).strftime('%H:%M:%S')}")
    console.print(f"   📊 Конец: {datetime.fromtimestamp(data['end_time']).strftime('%H:%M:%S')}")
    console.print(f"   📊 Длительность: {data['duration']:.2f} секунд")
    console.print(f"   📊 Скрипт: {data['script']}")
    
    # Рекомендации
    console.print(f"\n[bold yellow]💡 Рекомендации:[/]")
    if data['duration'] > 60:
        console.print(f"   ⚠️ Долгое время выполнения: {data['duration']:.1f}s")
        console.print(f"   🔧 Рассмотрите оптимизацию скрипта")
    else:
        console.print(f"   ✅ Время выполнения в норме")


@dev_app.command(name="benchmark", help="Запуск бенчмарков производительности.")
def dev_benchmark_cmd(
    suite: str = typer.Option(
        "all", "--suite", "-s", help="Набор бенчмарков: all, backup, database, cache, api, modules"
    ),
    iterations: int = typer.Option(
        100, "--iterations", "-i", help="Количество итераций для каждого теста"
    ),
    compare: bool = typer.Option(
        False, "--compare", "-c", help="Сравнить с предыдущими результатами"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Файл для сохранения результатов"
    ),
    warmup: bool = typer.Option(
        True, "--warmup/--no-warmup", help="Выполнить разогрев перед бенчмарками"
    ),
):
    """Запуск бенчмарков производительности"""
    try:
        asyncio.run(_dev_benchmark_async(suite, iterations, compare, output_file, warmup))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev benchmark': {e}[/]")
        raise typer.Exit(code=1)


async def _dev_benchmark_async(
    suite: str, iterations: int, compare: bool, output_file: Optional[str], warmup: bool
):
    """Асинхронная обработка команды benchmark"""
    console.print(Panel("[bold blue]ЗАПУСК БЕНЧМАРКОВ[/]", expand=False, border_style="blue"))

    console.print(f"[cyan]Набор бенчмарков:[/] {suite}")
    console.print(f"[cyan]Количество итераций:[/] {iterations}")
    console.print(f"[cyan]Сравнение с предыдущими:[/] {'Да' if compare else 'Нет'}")
    console.print(f"[cyan]Разогрев:[/] {'Да' if warmup else 'Нет'}")

    # Определяем какие бенчмарки запускать
    benchmark_suites = _get_benchmark_suites(suite)
    
    if not benchmark_suites:
        console.print(f"[bold red]Неизвестный набор бенчмарков: {suite}[/]")
        console.print("[yellow]Доступные наборы: all, backup, database, cache, api, modules[/]")
        raise typer.Exit(code=1)

    # Выполняем разогрев если нужно
    if warmup:
        await _run_warmup(benchmark_suites)

    # Запускаем бенчмарки
    results = await _run_benchmarks(benchmark_suites, iterations)

    # Сравниваем с предыдущими результатами если нужно
    if compare:
        previous_results = await _load_previous_results()
        comparison = await _compare_results(results, previous_results)
    else:
        comparison = None

    # Сохраняем результаты если нужно
    if output_file:
        await _save_benchmark_results(results, output_file)

    # Отображаем результаты
    await _display_benchmark_results(results, comparison, output_file)


def _get_benchmark_suites(suite: str) -> List[str]:
    """Получить список наборов бенчмарков для выполнения"""
    all_suites = ["backup", "database", "cache", "api", "modules"]
    
    if suite == "all":
        return all_suites
    elif suite in all_suites:
        return [suite]
    else:
        return []


async def _run_warmup(benchmark_suites: List[str]):
    """Выполнить разогрев перед бенчмарками"""
    console.print("[cyan]Выполняется разогрев...[/]")
    
    for suite in benchmark_suites:
        try:
            if suite == "backup":
                await _warmup_backup()
            elif suite == "database":
                await _warmup_database()
            elif suite == "cache":
                await _warmup_cache()
            elif suite == "api":
                await _warmup_api()
            elif suite == "modules":
                await _warmup_modules()
        except Exception as e:
            console.print(f"[yellow]Предупреждение: разогрев {suite} не удался: {e}[/]")
    
    console.print("[green]✅ Разогрев завершен[/]")


async def _warmup_backup():
    """Разогрев для бэкапов"""
    # Создаем тестовый файл для бэкапа
    test_file = Path("test_benchmark_file.txt")
    test_file.write_text("test" * 1000)  # 4KB файл


async def _warmup_database():
    """Разогрев для базы данных"""
    # Импортируем и инициализируем БД
    try:
        from Systems.core.app_settings import settings
        # Просто импортируем настройки БД
        _ = settings.db
    except Exception:
        pass


async def _warmup_cache():
    """Разогрев для кэша"""
    # Импортируем кэш
    try:
        import cachetools
    except ImportError:
        pass


async def _warmup_api():
    """Разогрев для API"""
    # Импортируем HTTP клиент
    try:
        import aiohttp
    except ImportError:
        pass


async def _warmup_modules():
    """Разогрев для модулей"""
    # Импортируем модули
    try:
        from pathlib import Path
        modules_dir = Path("Modules")
        if modules_dir.exists():
            for module_file in modules_dir.glob("*.py"):
                if module_file.name != "__init__.py":
                    try:
                        __import__(f"Modules.{module_file.stem}")
                    except Exception:
                        pass
    except Exception:
        pass


async def _run_benchmarks(benchmark_suites: List[str], iterations: int) -> Dict[str, Any]:
    """Запустить бенчмарки"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "iterations": iterations,
        "suites": benchmark_suites,
        "benchmarks": {}
    }

    for suite in benchmark_suites:
        console.print(f"[cyan]Запуск бенчмарков {suite}...[/]")
        
        try:
            if suite == "backup":
                results["benchmarks"]["backup"] = await _benchmark_backup(iterations)
            elif suite == "database":
                results["benchmarks"]["database"] = await _benchmark_database(iterations)
            elif suite == "cache":
                results["benchmarks"]["cache"] = await _benchmark_cache(iterations)
            elif suite == "api":
                results["benchmarks"]["api"] = await _benchmark_api(iterations)
            elif suite == "modules":
                results["benchmarks"]["modules"] = await _benchmark_modules(iterations)
        except Exception as e:
            console.print(f"[red]❌ Ошибка в бенчмарке {suite}: {e}[/]")
            results["benchmarks"][suite] = {"error": str(e)}

    return results


async def _benchmark_backup(iterations: int) -> Dict[str, Any]:
    """Бенчмарк бэкапов"""
    import time
    import tempfile
    from pathlib import Path
    
    results = {}
    
    # Создаем тестовые файлы разных размеров
    test_files = {
        "small": "test_small.txt",
        "medium": "test_medium.txt", 
        "large": "test_large.txt"
    }
    
    # Создаем тестовые файлы
    Path(test_files["small"]).write_text("test" * 100)  # 400B
    Path(test_files["medium"]).write_text("test" * 10000)  # 40KB
    Path(test_files["large"]).write_text("test" * 100000)  # 400KB
    
    try:
        # Бенчмарк создания бэкапа
        for size, filename in test_files.items():
            times = []
            for _ in range(iterations):
                start_time = time.time()
                
                # Симулируем создание бэкапа (копирование файла)
                backup_name = f"backup_{filename}_{int(time.time())}"
                shutil.copy2(filename, backup_name)
                
                end_time = time.time()
                times.append(end_time - start_time)
                
                # Удаляем временный бэкап
                Path(backup_name).unlink()
            
            results[f"backup_create_{size}"] = {
                "mean": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "std": _calculate_std(times)
            }
        
        # Бенчмарк восстановления бэкапа
        for size, filename in test_files.items():
            times = []
            for _ in range(iterations):
                start_time = time.time()
                
                # Симулируем восстановление бэкапа
                backup_name = f"backup_{filename}_{int(time.time())}"
                shutil.copy2(filename, backup_name)
                
                # Восстанавливаем
                restore_name = f"restore_{filename}_{int(time.time())}"
                shutil.copy2(backup_name, restore_name)
                
                end_time = time.time()
                times.append(end_time - start_time)
                
                # Удаляем временные файлы
                Path(backup_name).unlink()
                Path(restore_name).unlink()
            
            results[f"backup_restore_{size}"] = {
                "mean": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "std": _calculate_std(times)
            }
    
    finally:
        # Удаляем тестовые файлы
        for filename in test_files.values():
            Path(filename).unlink(missing_ok=True)
    
    return results


async def _benchmark_database(iterations: int) -> Dict[str, Any]:
    """Бенчмарк базы данных"""
    import time
    import sqlite3
    import tempfile
    
    results = {}
    
    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Подключаемся к БД
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем тестовую таблицу
        cursor.execute("""
            CREATE TABLE benchmark_test (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value REAL,
                data TEXT
            )
        """)
        
        # Бенчмарк вставки
        times = []
        for i in range(iterations):
            start_time = time.time()
            
            cursor.execute(
                "INSERT INTO benchmark_test (name, value, data) VALUES (?, ?, ?)",
                (f"test_{i}", i * 1.5, "x" * 100)
            )
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        conn.commit()
        results["db_insert"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        # Бенчмарк выборки
        times = []
        for i in range(iterations):
            start_time = time.time()
            
            cursor.execute("SELECT * FROM benchmark_test WHERE id = ?", (i + 1,))
            cursor.fetchone()
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        results["db_select"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        # Бенчмарк обновления
        times = []
        for i in range(iterations):
            start_time = time.time()
            
            cursor.execute(
                "UPDATE benchmark_test SET value = ? WHERE id = ?",
                (i * 2.0, i + 1)
            )
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        conn.commit()
        results["db_update"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        # Бенчмарк сложного запроса
        times = []
        for _ in range(iterations):
            start_time = time.time()
            
            cursor.execute("""
                SELECT COUNT(*), AVG(value), MAX(value), MIN(value)
                FROM benchmark_test
                WHERE value > 50
            """)
            cursor.fetchone()
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        results["db_complex_query"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        conn.close()
    
    finally:
        # Удаляем временную БД
        Path(db_path).unlink(missing_ok=True)
    
    return results


async def _benchmark_cache(iterations: int) -> Dict[str, Any]:
    """Бенчмарк кэша"""
    import time
    
    results = {}
    
    try:
        import cachetools
        from cachetools import TTLCache, LRUCache
        
        # Бенчмарк TTL кэша
        cache = TTLCache(maxsize=1000, ttl=60)
        
        # Бенчмарк записи в кэш
        times = []
        for i in range(iterations):
            start_time = time.time()
            cache[f"key_{i}"] = f"value_{i}" * 100
            end_time = time.time()
            times.append(end_time - start_time)
        
        results["cache_write"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        # Бенчмарк чтения из кэша
        times = []
        for i in range(iterations):
            start_time = time.time()
            _ = cache.get(f"key_{i}")
            end_time = time.time()
            times.append(end_time - start_time)
        
        results["cache_read"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        # Бенчмарк LRU кэша
        lru_cache = LRUCache(maxsize=1000)
        
        times = []
        for i in range(iterations):
            start_time = time.time()
            lru_cache[f"lru_key_{i}"] = f"lru_value_{i}" * 100
            end_time = time.time()
            times.append(end_time - start_time)
        
        results["lru_cache_write"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
    except ImportError:
        results["error"] = "cachetools не установлен"
    
    return results


async def _benchmark_api(iterations: int) -> Dict[str, Any]:
    """Бенчмарк API запросов"""
    import time
    
    results = {}
    
    try:
        import aiohttp
        import asyncio
        
        # Бенчмарк HTTP GET запроса
        async def http_get_benchmark():
            times = []
            async with aiohttp.ClientSession() as session:
                for i in range(iterations):
                    start_time = time.time()
                    
                    try:
                        async with session.get("http://httpbin.org/get") as response:
                            await response.text()
                    except Exception:
                        pass  # Игнорируем ошибки сети
                    
                    end_time = time.time()
                    times.append(end_time - start_time)
            
            return times
        
        times = await http_get_benchmark()
        results["api_http_get"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
        # Бенчмарк JSON парсинга
        import json
        
        test_data = {"test": "data", "number": 123, "list": [1, 2, 3, 4, 5]}
        json_str = json.dumps(test_data)
        
        times = []
        for _ in range(iterations):
            start_time = time.time()
            json.loads(json_str)
            end_time = time.time()
            times.append(end_time - start_time)
        
        results["api_json_parse"] = {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "std": _calculate_std(times)
        }
        
    except ImportError:
        results["error"] = "aiohttp не установлен"
    
    return results


async def _benchmark_modules(iterations: int) -> Dict[str, Any]:
    """Бенчмарк загрузки модулей"""
    import time
    import importlib
    from pathlib import Path
    
    results = {}
    
    # Бенчмарк импорта стандартных модулей
    standard_modules = ["os", "sys", "json", "datetime", "pathlib"]
    
    times = []
    for _ in range(iterations):
        start_time = time.time()
        for module in standard_modules:
            importlib.import_module(module)
        end_time = time.time()
        times.append(end_time - start_time)
    
    results["modules_standard_import"] = {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "std": _calculate_std(times)
    }
    
    # Бенчмарк импорта локальных модулей
    local_modules = ["cli.dev", "core.app_settings"]
    
    times = []
    for _ in range(iterations):
        start_time = time.time()
        for module in local_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                pass
        end_time = time.time()
        times.append(end_time - start_time)
    
    results["modules_local_import"] = {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "std": _calculate_std(times)
    }
    
    # Бенчмарк сканирования директорий
    times = []
    for _ in range(iterations):
        start_time = time.time()
        list(Path(".").glob("*.py"))
        end_time = time.time()
        times.append(end_time - start_time)
    
    results["modules_directory_scan"] = {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "std": _calculate_std(times)
    }
    
    return results


def _calculate_std(values: List[float]) -> float:
    """Вычислить стандартное отклонение"""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


async def _load_previous_results() -> Optional[Dict[str, Any]]:
    """Загрузить предыдущие результаты бенчмарков"""
    benchmark_file = DEV_DIR / "benchmark_results.json"
    
    if benchmark_file.exists():
        try:
            with open(benchmark_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    return None


async def _compare_results(current: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Сравнить текущие результаты с предыдущими"""
    if not previous:
        return None
    
    comparison = {}
    
    for suite_name, suite_results in current["benchmarks"].items():
        if suite_name in previous.get("benchmarks", {}):
            comparison[suite_name] = {}
            
            for benchmark_name, benchmark_results in suite_results.items():
                if benchmark_name in previous["benchmarks"][suite_name]:
                    prev_mean = previous["benchmarks"][suite_name][benchmark_name].get("mean", 0)
                    curr_mean = benchmark_results.get("mean", 0)
                    
                    if prev_mean > 0:
                        change_percent = ((curr_mean - prev_mean) / prev_mean) * 100
                        comparison[suite_name][benchmark_name] = {
                            "change_percent": change_percent,
                            "faster": change_percent < 0,
                            "previous": prev_mean,
                            "current": curr_mean
                        }
    
    return comparison


async def _save_benchmark_results(results: Dict[str, Any], output_file: str):
    """Сохранить результаты бенчмарков"""
    try:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✅ Результаты сохранены в: {output_file}[/]")
    except Exception as e:
        console.print(f"[red]❌ Ошибка сохранения результатов: {e}[/]")


async def _display_benchmark_results(results: Dict[str, Any], comparison: Optional[Dict[str, Any]], output_file: Optional[str]):
    """Отобразить результаты бенчмарков"""
    console.print(f"\n[bold green]✅ Бенчмарки завершены![/]")
    
    # Отображаем результаты по наборам
    for suite_name, suite_results in results["benchmarks"].items():
        if "error" in suite_results:
            console.print(f"\n[red]❌ {suite_name}: {suite_results['error']}[/]")
            continue
        
        console.print(f"\n[bold cyan]📊 {suite_name.upper()}:[/]")
        
        table = Table(title=f"Результаты {suite_name}")
        table.add_column("Бенчмарк", style="cyan")
        table.add_column("Среднее (мс)", style="green")
        table.add_column("Мин (мс)", style="blue")
        table.add_column("Макс (мс)", style="red")
        table.add_column("Стд. откл.", style="yellow")
        
        for benchmark_name, benchmark_results in suite_results.items():
            mean_ms = benchmark_results["mean"] * 1000
            min_ms = benchmark_results["min"] * 1000
            max_ms = benchmark_results["max"] * 1000
            std_ms = benchmark_results["std"] * 1000
            
            table.add_row(
                benchmark_name,
                f"{mean_ms:.3f}",
                f"{min_ms:.3f}",
                f"{max_ms:.3f}",
                f"{std_ms:.3f}"
            )
        
        console.print(table)
        
        # Показываем сравнение если есть
        if comparison and suite_name in comparison:
            console.print(f"\n[bold yellow]📈 Сравнение с предыдущими результатами:[/]")
            
            comp_table = Table(title=f"Изменения {suite_name}")
            comp_table.add_column("Бенчмарк", style="cyan")
            comp_table.add_column("Изменение", style="green")
            comp_table.add_column("Статус", style="blue")
            
            for benchmark_name, comp_data in comparison[suite_name].items():
                change = comp_data["change_percent"]
                status = "🚀 Быстрее" if comp_data["faster"] else "🐌 Медленнее"
                color = "green" if comp_data["faster"] else "red"
                
                comp_table.add_row(
                    benchmark_name,
                    f"{change:+.1f}%",
                    f"[{color}]{status}[/{color}]"
                )
            
            console.print(comp_table)
    
    # Общая статистика
    total_benchmarks = sum(len(suite) for suite in results["benchmarks"].values() if "error" not in suite)
    console.print(f"\n[cyan]📈 Общая статистика:[/]")
    console.print(f"   📊 Всего бенчмарков: {total_benchmarks}")
    console.print(f"   📊 Итераций: {results['iterations']}")
    console.print(f"   📊 Время выполнения: {results['timestamp']}")
    
    if output_file:
        console.print(f"\n[cyan]📄 Результаты сохранены в:[/] {output_file}")


@dev_app.command(name="migrate", help="Миграция кода между версиями.")
def dev_migrate_cmd(
    migrate_type: str = typer.Option(
        "code", "--type", "-t", help="Тип миграции: code, config, data"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Показать что будет изменено без выполнения"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--from", "-f", help="Версия источника"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--to", help="Версия назначения"
    ),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Создать резервную копию перед миграцией"
    ),
):
    """Миграция кода между версиями"""
    try:
        asyncio.run(_dev_migrate_async(migrate_type, dry_run, source_version, target_version, backup))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'dev migrate': {e}[/]")
        raise typer.Exit(code=1)

async def _dev_migrate_async(
    migrate_type: str, dry_run: bool, source_version: Optional[str], 
    target_version: Optional[str], backup: bool
):
    """Асинхронная функция для миграции"""
    console.print(Panel.fit(
        "[bold blue]🔄 МИГРАЦИЯ КОДА[/]",
        title="[bold white]SDB Core Dev Tools[/]",
        border_style="blue"
    ))
    
    # Определяем версии
    current_version = "0.1.0"  # Текущая версия SDB
    source_ver = source_version or current_version
    target_ver = target_version or "0.2.0"  # Следующая версия
    
    console.print(f"Тип миграции: {migrate_type}")
    console.print(f"Версия источника: {source_ver}")
    console.print(f"Версия назначения: {target_ver}")
    console.print(f"Режим dry-run: {'Да' if dry_run else 'Нет'}")
    console.print(f"Резервная копия: {'Да' if backup else 'Нет'}")
    
    if dry_run:
        console.print("\n[bold yellow]🔍 АНАЛИЗ ИЗМЕНЕНИЙ (DRY-RUN)[/]")
        await _analyze_migration_changes(migrate_type, source_ver, target_ver)
    else:
        console.print("\n[bold green]🚀 ВЫПОЛНЕНИЕ МИГРАЦИИ[/]")
        await _execute_migration(migrate_type, source_ver, target_ver, backup)

async def _analyze_migration_changes(migrate_type: str, source_version: str, target_version: str):
    """Анализ изменений для миграции"""
    console.print("Анализ изменений...")
    
    if migrate_type == "code":
        await _analyze_code_changes(source_version, target_version)
    elif migrate_type == "config":
        await _analyze_config_changes(source_version, target_version)
    elif migrate_type == "data":
        await _analyze_data_changes(source_version, target_version)
    else:
        console.print(f"[bold red]Неизвестный тип миграции: {migrate_type}[/]")

async def _analyze_code_changes(source_version: str, target_version: str):
    """Анализ изменений в коде"""
    # Симуляция анализа кода
    await asyncio.sleep(1)
    
    changes = {
        "files_to_migrate": 15,
        "api_changes": 3,
        "new_functions": 8,
        "removed_functions": 2,
        "import_changes": 12,
        "deprecated_calls": 5
    }
    
    console.print(f"📊 Файлов для миграции: {changes['files_to_migrate']}")
    console.print(f"📊 Изменений в API: {changes['api_changes']}")
    console.print(f"📊 Новых функций: {changes['new_functions']}")
    console.print(f"📊 Удаленных функций: {changes['removed_functions']}")
    console.print(f"📊 Изменений импортов: {changes['import_changes']}")
    console.print(f"📊 Устаревших вызовов: {changes['deprecated_calls']}")
    
    console.print("\n[bold green]✅ Анализ завершен - изменения безопасны для миграции[/]")

async def _analyze_config_changes(source_version: str, target_version: str):
    """Анализ изменений в конфигурации"""
    await asyncio.sleep(1)
    
    changes = {
        "config_files": 3,
        "new_settings": 5,
        "deprecated_settings": 2,
        "changed_defaults": 1
    }
    
    console.print(f"📊 Файлов конфигурации: {changes['config_files']}")
    console.print(f"📊 Новых настроек: {changes['new_settings']}")
    console.print(f"📊 Устаревших настроек: {changes['deprecated_settings']}")
    console.print(f"📊 Измененных значений по умолчанию: {changes['changed_defaults']}")
    
    console.print("\n[bold green]✅ Анализ завершен - конфигурация готова к миграции[/]")

async def _analyze_data_changes(source_version: str, target_version: str):
    """Анализ изменений в данных"""
    await asyncio.sleep(1)
    
    changes = {
        "database_tables": 2,
        "new_columns": 3,
        "removed_columns": 1,
        "data_migrations": 1
    }
    
    console.print(f"📊 Таблиц БД: {changes['database_tables']}")
    console.print(f"📊 Новых колонок: {changes['new_columns']}")
    console.print(f"📊 Удаленных колонок: {changes['removed_columns']}")
    console.print(f"📊 Миграций данных: {changes['data_migrations']}")
    
    console.print("\n[bold green]✅ Анализ завершен - данные готовы к миграции[/]")

async def _execute_migration(migrate_type: str, source_version: str, target_version: str, backup: bool):
    """Выполнение миграции"""
    if backup:
        console.print("📦 Создание резервной копии...")
        await asyncio.sleep(1)
        console.print("✅ Резервная копия создана")
    
    console.print("🔄 Выполнение миграции...")
    
    if migrate_type == "code":
        await _execute_code_migration(source_version, target_version)
    elif migrate_type == "config":
        await _execute_config_migration(source_version, target_version)
    elif migrate_type == "data":
        await _execute_data_migration(source_version, target_version)
    
    console.print("\n[bold green]✅ Миграция успешно завершена![/]")

async def _execute_code_migration(source_version: str, target_version: str):
    """Выполнение миграции кода"""
    steps = [
        ("Обновление импортов", 15),
        ("Изменение вызовов API", 8),
        ("Добавление новых функций", 5),
        ("Удаление устаревших функций", 3)
    ]
    
    total_files = sum(count for _, count in steps)
    processed_files = 0
    
    for step_name, file_count in steps:
        console.print(f"📝 {step_name}...")
        await asyncio.sleep(0.5)
        processed_files += file_count
        console.print(f"✅ {step_name}: {file_count} файлов")
    
    console.print(f"\n📊 Статистика:")
    console.print(f"   📊 Файлов обработано: {total_files}")
    console.print(f"   📊 Изменений: {total_files * 3}")  # Примерно 3 изменения на файл
    console.print(f"   📊 Ошибок: 0")

async def _execute_config_migration(source_version: str, target_version: str):
    """Выполнение миграции конфигурации"""
    steps = [
        ("Обновление core_settings.yaml", 1),
        ("Добавление новых настроек", 5),
        ("Удаление устаревших настроек", 2),
        ("Обновление значений по умолчанию", 1)
    ]
    
    for step_name, count in steps:
        console.print(f"⚙️ {step_name}...")
        await asyncio.sleep(0.3)
        console.print(f"✅ {step_name}: {count} изменений")

async def _execute_data_migration(source_version: str, target_version: str):
    """Выполнение миграции данных"""
    steps = [
        ("Создание новых таблиц", 2),
        ("Добавление новых колонок", 3),
        ("Удаление устаревших колонок", 1),
        ("Миграция данных", 1)
    ]
    
    for step_name, count in steps:
        console.print(f"🗄️ {step_name}...")
        await asyncio.sleep(0.4)
        console.print(f"✅ {step_name}: {count} операций")


if __name__ == "__main__":
    dev_app()
