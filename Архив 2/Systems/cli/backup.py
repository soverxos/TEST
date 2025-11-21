# --- Файл: cli/backup_unified.py ---
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from typing import Tuple as TypingTuple
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .utils import confirm_action, sdb_console

backup_app = typer.Typer(
    name="backup",
    help="💾 Объединенная система бэкапов с хешами, поддержкой БД и сравнением",
    no_args_is_help=True,
)

console = Console()

# === КОНСТАНТЫ ===
DB_BACKUP_DIR_NAME = "database"
FILES_BACKUP_DIR_NAME = "files"
DATA_ARCHIVE_EXTENSION = ".tar.gz"
POSTGRES_BACKUP_FILENAME = "postgres_dump.sql"
MYSQL_BACKUP_FILENAME = "mysql_dump.sql"
USER_CONFIG_DIR_NAME_FOR_BACKUP_DEFAULT = "Config"


# === УТИЛИТЫ ХЕШИРОВАНИЯ ===
def sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Вычисляет SHA256 хеш файла."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_directory(path: Path, excludes: Optional[List[str]] = None) -> dict[str, str]:
    """Сканирует директорию и создает хеши файлов с улучшенной логикой исключений."""
    import fnmatch
    
    hashes = {}
    excludes = excludes or []
    
    for file in path.rglob("*"):
        if file.is_file():
            rel_path = file.relative_to(path).as_posix()
            
            # Проверяем исключения
            excluded = False
            for exclude in excludes:
                # Паттерны с звездочкой (*.pyc, *.log и т.д.)
                if "*" in exclude:
                    if fnmatch.fnmatch(rel_path, exclude) or fnmatch.fnmatch(file.name, exclude):
                        excluded = True
                        break
                # Полные пути (Data/Cache_data)
                elif "/" in exclude:
                    if rel_path.startswith(exclude) or rel_path == exclude:
                        excluded = True
                        break
                # Имена папок или файлов
                else:
                    path_parts = rel_path.split("/")
                    if exclude in path_parts or exclude == file.name:
                        excluded = True
                        break
            
            if excluded:
                continue
                
            hashes[rel_path] = sha256(file)
    return hashes


# === УТИЛИТЫ БД ===
def _get_backup_base_dir() -> Optional[Path]:
    """Получает базовую директорию для бэкапов."""
    try:
        project_root = Path(__file__).resolve().parent.parent
        backup_dir = project_root / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    except Exception as e:
        console.print(f"[bold red]Ошибка при создании директории бэкапов: {e}[/]")
        return None


def _find_system_utility(name: str) -> Optional[str]:
    """Находит системную утилиту."""
    return shutil.which(name)


def _execute_system_command(
    command: List[str],
    env_vars: Optional[dict] = None,
    input_data: Optional[str] = None,
    show_stdout_on_success: bool = False,
) -> bool:
    """Выполняет системную команду."""
    full_env = os.environ.copy()
    if env_vars:
        full_env.update(env_vars)

    try:
        result = subprocess.run(
            command,
            env=full_env,
            input=input_data,
            text=True,
            capture_output=True,
            check=True,
        )

        if show_stdout_on_success and result.stdout.strip():
            console.print(result.stdout.strip())

        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Ошибка выполнения команды: {e}[/]")
        if e.stderr:
            console.print(f"[red]{e.stderr}[/]")
        return False
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка: {e}[/]")
        return False


# === ОСНОВНЫЕ КОМАНДЫ ===


@backup_app.command("create")
def create_backup(
    backup_type: str = typer.Option(
        "full", "--type", "-t", help="Тип бэкапа: full, files, db, custom"
    ),
    dest: Optional[Path] = typer.Option(
        None, "--dest", "-d", help="Папка назначения для бэкапа"
    ),
    compress: bool = typer.Option(
        True, "--compress/--no-compress", help="Сжимать архив (по умолчанию включено)"
    ),
    verify_hashes: bool = typer.Option(
        True,
        "--verify-hashes/--no-verify-hashes",
        help="Создавать и проверять хеши файлов",
    ),
    exclude: Optional[List[str]] = typer.Option(
        None, "--exclude", "-x", help="Исключить файлы/папки"
    ),
    include_data_dirs: Optional[List[str]] = typer.Option(
        None, "--data-dir", "-dd", help=f"Директории из Data для бэкапа"
    ),
    db_url: Optional[str] = typer.Option(None, "--db-url", help="URL БД для бэкапа"),
):
    """🚀 Создать объединенный бэкап файлов и/или базы данных с хешированием."""
    import time

    start_time = time.time()

    console.print(f"[bold cyan]🚀 Создание бэкапа типа: {backup_type.upper()}[/]")

    # Определяем исходную директорию
    if backup_type == "custom" and dest:
        # Для custom можно указать любую директорию
        project_root = Path(__file__).resolve().parent.parent
        source_path = project_root
    else:
        # По умолчанию - корень проекта
        project_root = Path(__file__).resolve().parent.parent
        source_path = project_root

    # Анализируем область бэкапа
    scope_analysis = analyze_backup_scope(source_path)

    # Показываем предупреждения и рекомендации
    for warning in scope_analysis["warnings"]:
        console.print(f"[yellow]{warning}[/]")

    for recommendation in scope_analysis["recommendations"]:
        console.print(f"[blue]{recommendation}[/]")

    # Определяем что включать
    include_files = backup_type in ["full", "files", "custom"]
    include_db = backup_type in ["full", "db"]

    # Базовые настройки
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_base_dir = _get_backup_base_dir()
    if not backup_base_dir:
        return

    # Создаем рабочую директорию
    working_name = f"unified_{backup_type}_{timestamp}"
    if compress:
        temp_target = backup_base_dir / f"temp_{working_name}"
        final_target = dest or backup_base_dir / f"{working_name}.tar.gz"
        temp_target.mkdir(parents=True, exist_ok=True)
        working_target = temp_target
    else:
        final_target = dest or backup_base_dir / working_name
        final_target = Path(final_target).expanduser().resolve()
        final_target.mkdir(parents=True, exist_ok=True)
        working_target = final_target

    console.print(f"[dim]🎯 Назначение: {final_target}[/]")

    # Метаданные бэкапа
    backup_metadata = {
        "type": f"unified_{backup_type}",
        "timestamp": timestamp,
        "includes_files": include_files,
        "includes_db": include_db,
        "compressed": compress,
        "verify_hashes": verify_hashes,
        "creation_time": datetime.now().isoformat() + "Z",
        "excluded_patterns": [],  # Будет заполнено позже
        "files": {},
        "database": {},
    }

    total_size = 0
    files_count = 0

    # === ЭТАП 1: ФАЙЛЫ ===
    if include_files:
        console.print(f"\n[cyan]📁 Этап 1: Обработка файлов[/]")

        project_root = Path(__file__).resolve().parent.parent

        # Автоматические исключения (кэш, временные и системные файлы)
        auto_excludes = [
            # Git и VCS
            ".git",
            ".gitignore",
            ".gitattributes",
            ".hg",
            ".svn",
            
            # Виртуальные окружения Python
            ".venv",
            "venv",
            ".env",
            "env",
            "ENV",
            "virtualenv",
            ".virtualenv",
            "pyenv",
            ".python-version",
            
            # Python кэш и временные файлы
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".Python",
            "*.so",
            ".pytest_cache",
            ".mypy_cache",
            ".coverage",
            ".tox",
            ".nox",
            "htmlcov",
            ".cache",
            "pip-log.txt",
            "pip-delete-this-directory.txt",
            
            # Node.js и JavaScript
            "node_modules",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            ".npm",
            ".yarn-integrity",
            
            # IDE и редакторы
            ".vscode",
            ".idea",
            "*.swp",
            "*.swo",
            "*~",
            ".vim",
            ".emacs.d",
            
            # Системные файлы
            ".DS_Store",
            ".DS_Store?",
            "._*",
            ".Spotlight-V100",
            ".Trashes",
            "ehthumbs.db",
            "Thumbs.db",
            "Desktop.ini",
            
            # Логи и временные файлы
            "*.log",
            "logs",
            "*.tmp",
            "*.temp",
            "tmp",
            "temp",
            ".tmp",
            
            # Дистрибутивы и сборки
            "dist",
            "build",
            "*.egg-info",
            ".eggs",
            "*.egg",
            "*.whl",
            
            # Кэш данных проекта
            "Data/Cache_data",
            "Data/Logs",
            "Data/api/cache",
            "Data/monitor/cache",
            
            # Резервные копии
            "backup",
            "backups",
            "*.bak",
            "*.backup",
            "temp_*",  # Исключаем временные папки бэкапов
            
            # Docker и контейнеры
            ".dockerignore",
            "Dockerfile*",
            "docker-compose*.yml",
            ".docker",
            
            # Прочие файлы разработки
            ".env.local",
            ".env.*.local",
            "*.orig",
            ".sass-cache",
            ".parcel-cache",
        ]

        if exclude:
            auto_excludes.extend(exclude)

        # Сохраняем исключения в метаданные
        backup_metadata["excluded_patterns"] = auto_excludes

        console.print(f"[dim]🚫 Исключений применено: {len(auto_excludes)} ({', '.join(auto_excludes[:5])}...)[/]")

        # Сканируем файлы
        if verify_hashes:
            console.print("[cyan]🔍 Сканирование и хеширование файлов...[/]")
            file_hashes = scan_directory(project_root, excludes=auto_excludes)
        else:
            console.print("[cyan]📁 Сканирование файлов без хеширования...[/]")
            import fnmatch
            
            file_hashes = {}
            for file in project_root.rglob("*"):
                if file.is_file():
                    rel_path = file.relative_to(project_root).as_posix()
                    
                    # Применяем ту же логику исключений
                    excluded = False
                    for exclude in auto_excludes:
                        if "*" in exclude:
                            if fnmatch.fnmatch(rel_path, exclude) or fnmatch.fnmatch(file.name, exclude):
                                excluded = True
                                break
                        elif "/" in exclude:
                            if rel_path.startswith(exclude) or rel_path == exclude:
                                excluded = True
                                break
                        else:
                            path_parts = rel_path.split("/")
                            if exclude in path_parts or exclude == file.name:
                                excluded = True
                                break
                    
                    if not excluded:
                        file_hashes[rel_path] = ""  # Пустой хеш

        # Подсчитываем размер
        for rel_path in file_hashes.keys():
            file_path = project_root / rel_path
            if file_path.exists():
                total_size += file_path.stat().st_size

        files_count = len(file_hashes)
        console.print(f"   📁 Файлов найдено: {files_count:,}")
        console.print(f"   📊 Размер файлов: {total_size / (1024*1024):.1f}MB")

        # Копируем файлы
        files_dir = working_target / FILES_BACKUP_DIR_NAME
        files_dir.mkdir(parents=True, exist_ok=True)

        console.print("[cyan]📦 Копирование файлов...[/]")
        for rel_path in file_hashes:
            src = project_root / rel_path
            dest_path = files_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_path)

        # Сохраняем хеши файлов
        if verify_hashes:
            with open(working_target / "file_hashes.json", "w", encoding="utf-8") as f:
                json.dump(file_hashes, f, indent=2)

        backup_metadata["files"] = {
            "count": files_count,
            "total_size": total_size,
            "hashes_enabled": verify_hashes,
        }

    # === ЭТАП 2: БАЗА ДАННЫХ ===
    if include_db:
        console.print(f"\n[cyan]🗃️  Этап 2: Обработка базы данных[/]")

        # Обнаруживаем тип БД
        db_info = detect_database_type()
        console.print(f"[cyan]🔍 Обнаружен тип БД: {db_info['type'].upper()}[/]")

        db_dir = working_target / DB_BACKUP_DIR_NAME
        db_dir.mkdir(parents=True, exist_ok=True)

        db_success = False

        if db_info["type"] == "sqlite":
            console.print(
                "[cyan]📄 SQLite обнаружен - файлы уже включены в бэкап файлов[/]"
            )
            if db_info["detected_files"]:
                console.print(
                    f"[green]✅ Найдены SQLite файлы: {', '.join(db_info['detected_files'])}[/]"
                )

            # Создаем информационный файл
            sqlite_info = {
                "type": "sqlite",
                "files": db_info["detected_files"],
                "note": "SQLite files are included in files backup",
                "location": db_info["location"],
            }
            with open(db_dir / "sqlite_info.json", "w", encoding="utf-8") as f:
                json.dump(sqlite_info, f, indent=2)

            db_success = True
            backup_metadata["database"] = {
                "type": "sqlite",
                "success": True,
                "files": db_info["detected_files"],
                "backup_method": "included_in_files",
            }

        elif db_info["type"] == "postgresql":
            console.print("[cyan]🐘 Создание бэкапа PostgreSQL...[/]")
            pg_dump = _find_system_utility("pg_dump")
            if pg_dump and db_info["location"]:
                dump_file = db_dir / POSTGRES_BACKUP_FILENAME
                cmd = [pg_dump, db_info["location"], "-f", str(dump_file)]
                db_success = _execute_system_command(cmd)
                if db_success:
                    console.print("[green]✅ PostgreSQL бэкап создан[/]")
            else:
                console.print("[red]❌ pg_dump не найден или URL БД не указан[/]")

        elif db_info["type"] == "mysql":
            console.print("[cyan]🐬 Создание бэкапа MySQL...[/]")
            mysqldump = _find_system_utility("mysqldump")
            if mysqldump and db_info["location"]:
                dump_file = db_dir / MYSQL_BACKUP_FILENAME
                # Упрощенная команда, в реальности нужно парсить URL
                console.print(
                    "[yellow]⚠️ MySQL бэкап требует дополнительной настройки[/]"
                )
            else:
                console.print("[red]❌ mysqldump не найден или URL БД не указан[/]")

        elif db_info["type"] == "none":
            console.print("[yellow]⚠️ База данных не обнаружена[/]")
            console.print(
                "[dim]💡 Если используется SQLite, файлы БД будут включены в бэкап файлов[/]"
            )

        else:
            console.print(f"[yellow]⚠️ Неизвестный тип БД: {db_info['type']}[/]")

        # Обновляем метаданные БД
        if "database" not in backup_metadata:
            backup_metadata["database"] = {
                "type": db_info["type"],
                "success": db_success,
                "needs_separate_backup": db_info["needs_separate_backup"],
                "detected_files": db_info["detected_files"],
            }

    # === ЭТАП 3: МЕТАДАННЫЕ ===
    console.print(f"\n[cyan]📋 Этап 3: Сохранение метаданных[/]")

    with open(working_target / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(backup_metadata, f, indent=2, ensure_ascii=False)

    # === ЭТАП 4: АРХИВАЦИЯ ===
    if compress:
        console.print(f"\n[cyan]🗜️ Этап 4: Архивация[/]")
        final_target = Path(final_target).expanduser().resolve()

        with tarfile.open(final_target, "w:gz") as tar:
            for item in working_target.rglob("*"):
                if item.is_file():
                    arcname = item.relative_to(working_target)
                    tar.add(item, arcname=arcname)

        # Удаляем временную папку
        shutil.rmtree(working_target)

        # Статистика сжатия
        archive_size = final_target.stat().st_size
        compression_ratio = (
            (1 - archive_size / total_size) * 100 if total_size > 0 else 0
        )

        console.print(f"   📦 Архив создан: {final_target.name}")
        console.print(f"   📊 Размер архива: {archive_size / (1024*1024):.1f}MB")
        console.print(f"   📈 Сжатие: {compression_ratio:.1f}%")

    # === ФИНАЛЬНАЯ СТАТИСТИКА ===
    end_time = time.time()
    duration = end_time - start_time

    console.print(f"\n[green]🎉 Бэкап завершен успешно![/]")
    console.print(
        Panel.fit(
            f"[green]✅ Тип:[/] {backup_type.upper()}\n"
            f"[green]📁 Файлов:[/] {files_count:,} ({total_size / (1024*1024):.1f}MB)\n"
            f"[green]🗃️ БД:[/] {'включена' if include_db else 'не включена'}\n"
            f"[green]🔍 Хеши:[/] {'включены' if verify_hashes else 'отключены'}\n"
            f"[green]⏱️ Время:[/] {duration:.1f}с\n"
            f"[green]📦 Результат:[/] {final_target}",
            title="📊 Статистика бэкапа",
            border_style="green",
        )
    )


@backup_app.command("list")
def list_backups(
    backup_type: str = typer.Option(
        "all", "--type", "-t", help="Тип бэкапов для показа: all, files, db, unified"
    ),
    show_hashes: bool = typer.Option(
        False, "--show-hashes", help="Показать информацию о хешах"
    ),
):
    """📋 Показать список всех доступных бэкапов."""
    backup_base_dir = _get_backup_base_dir()
    if not backup_base_dir:
        return

    console.print("[bold cyan]📋 Список доступных бэкапов[/]")

    # Собираем все бэкапы
    backups = []

    # Поиск архивов .tar.gz
    for backup_file in backup_base_dir.glob("*.tar.gz"):
        try:
            # Пробуем прочитать метаданные
            with tarfile.open(backup_file, "r:gz") as tar:
                try:
                    metadata_member = tar.getmember("metadata.json")
                    metadata_file = tar.extractfile(metadata_member)
                    metadata = json.load(metadata_file)

                    backup_info = {
                        "name": backup_file.name,
                        "path": backup_file,
                        "type": metadata.get("type", "unknown"),
                        "timestamp": metadata.get("timestamp", "unknown"),
                        "size": backup_file.stat().st_size,
                        "includes_files": metadata.get("includes_files", False),
                        "includes_db": metadata.get("includes_db", False),
                        "compressed": True,
                        "verify_hashes": metadata.get("verify_hashes", False),
                    }
                    backups.append(backup_info)
                except:
                    # Старый формат бэкапа
                    backup_info = {
                        "name": backup_file.name,
                        "path": backup_file,
                        "type": "legacy",
                        "timestamp": "unknown",
                        "size": backup_file.stat().st_size,
                        "includes_files": True,
                        "includes_db": False,
                        "compressed": True,
                        "verify_hashes": False,
                    }
                    backups.append(backup_info)
        except:
            continue

    # Поиск папок с бэкапами
    for backup_dir in backup_base_dir.iterdir():
        if backup_dir.is_dir() and not backup_dir.name.startswith("temp_"):
            metadata_file = backup_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, encoding="utf-8") as f:
                        metadata = json.load(f)

                    backup_info = {
                        "name": backup_dir.name,
                        "path": backup_dir,
                        "type": metadata.get("type", "unknown"),
                        "timestamp": metadata.get("timestamp", "unknown"),
                        "size": sum(
                            f.stat().st_size
                            for f in backup_dir.rglob("*")
                            if f.is_file()
                        ),
                        "includes_files": metadata.get("includes_files", False),
                        "includes_db": metadata.get("includes_db", False),
                        "compressed": False,
                        "verify_hashes": metadata.get("verify_hashes", False),
                    }
                    backups.append(backup_info)
                except:
                    continue

    # Фильтруем по типу
    if backup_type != "all":
        backups = [b for b in backups if backup_type in b["type"]]

    if not backups:
        console.print("[yellow]📭 Бэкапы не найдены[/]")
        return

    # Создаем таблицу
    table = Table(title="💾 Доступные бэкапы")
    table.add_column("Имя", style="cyan")
    table.add_column("Тип", style="magenta")
    table.add_column("Размер", style="green")
    table.add_column("Файлы", style="blue")
    table.add_column("БД", style="red")
    if show_hashes:
        table.add_column("Хеши", style="yellow")
    table.add_column("Дата", style="dim")

    # Сортируем по дате (новые сначала)
    backups.sort(key=lambda x: x["timestamp"], reverse=True)

    for backup in backups:
        size_mb = backup["size"] / (1024 * 1024)
        files_icon = "✅" if backup["includes_files"] else "❌"
        db_icon = "✅" if backup["includes_db"] else "❌"
        hashes_icon = "🔍" if backup["verify_hashes"] else "❌"

        row = [backup["name"], backup["type"], f"{size_mb:.1f}MB", files_icon, db_icon]

        if show_hashes:
            row.append(hashes_icon)

        row.append(backup["timestamp"])
        table.add_row(*row)

    console.print(table)
    console.print(f"\n[dim]Всего найдено: {len(backups)} бэкапов[/]")


@backup_app.command("restore")
def restore_backup(
    backup_path: str = typer.Argument(..., help="Имя или путь к бэкапу для восстановления"),
    dest: Path = typer.Argument(..., help="Целевая директория для восстановления"),
    backup_type: str = typer.Option(
        "auto", "--type", "-t", help="Что восстанавливать: auto, files, db, all"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Показать что будет восстановлено без выполнения"
    ),
    verify_hashes: bool = typer.Option(
        True,
        "--verify-hashes/--no-verify-hashes",
        help="Проверять хеши при восстановлении",
    ),
    skip_on_error: bool = typer.Option(
        False, "--skip-on-error", help="Пропускать поврежденные файлы"
    ),
    restore_db: bool = typer.Option(
        True, "--db/--no-db", help="Восстанавливать базу данных"
    ),
    db_url: Optional[str] = typer.Option(
        None, "--db-url", help="URL БД для восстановления"
    ),
):
    """📥 Восстановить файлы и/или БД из объединенного бэкапа."""
    backup_path = _resolve_backup_path(backup_path)
    console.print(f"[bold cyan]📥 Восстановление из: {backup_path}[/]")

    if dry_run:
        console.print(
            "[bold yellow]🔍 СУХОЙ ЗАПУСК: Показываю что будет восстановлено[/]"
        )
    else:
        console.print(f"[bold cyan]📥 Восстановление из: {backup_path}[/]")

    # Определяем тип бэкапа
    is_archive = backup_path.suffix == ".gz" and backup_path.suffixes[-2:] == [
        ".tar",
        ".gz",
    ]

    if is_archive:
        console.print("[cyan]📦 Обнаружен сжатый архив[/]")
        temp_dir = (
            backup_path.parent
            / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        temp_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)
            restore_source = temp_dir
            cleanup_temp = True
        except Exception as e:
            console.print(f"[red]❌ Ошибка распаковки: {e}[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
    else:
        console.print("[cyan]📁 Обнаружена папка с бэкапом[/]")
        restore_source = backup_path
        cleanup_temp = False

    try:
        # Читаем метаданные
        metadata_file = restore_source / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            console.print(
                "[yellow]⚠️ Метаданные не найдены, используем совместимый режим[/]"
            )
            metadata = {
                "includes_files": True,
                "includes_db": False,
                "verify_hashes": False,
            }

        # Определяем что восстанавливать
        should_restore_files = backup_type in ["auto", "files", "all"] and metadata.get(
            "includes_files", False
        )
        should_restore_db = (
            backup_type in ["auto", "db", "all"]
            and metadata.get("includes_db", False)
            and restore_db
        )

        console.print(f"[cyan]📋 План восстановления:[/]")
        console.print(f"   📁 Файлы: {'✅' if should_restore_files else '❌'}")
        console.print(f"   🗃️ БД: {'✅' if should_restore_db else '❌'}")

        if not should_restore_files and not should_restore_db:
            console.print("[red]❌ Нечего восстанавливать![/]")
            return

        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)

        restored_files = 0
        skipped_files = 0
        hash_errors = []

        # === ВОССТАНОВЛЕНИЕ ФАЙЛОВ ===
        if should_restore_files:
            console.print(f"\n[cyan]📁 Восстановление файлов[/]")

            files_dir = restore_source / FILES_BACKUP_DIR_NAME
            if files_dir.exists():
                # Проверяем хеши если включено
                file_hashes = {}
                hash_file = restore_source / "file_hashes.json"
                if verify_hashes and hash_file.exists():
                    with open(hash_file, encoding="utf-8") as f:
                        file_hashes = json.load(f)
                    console.print(f"[cyan]🔍 Загружено хешей: {len(file_hashes)}[/]")

                # Восстанавливаем файлы
                for src_file in files_dir.rglob("*"):
                    if src_file.is_file():
                        rel_path = src_file.relative_to(files_dir).as_posix()
                        dest_file = dest / rel_path

                        # Проверяем хеш если нужно
                        if verify_hashes and rel_path in file_hashes:
                            expected_hash = file_hashes[rel_path]
                            if expected_hash:  # Пропускаем пустые хеши
                                actual_hash = sha256(src_file)
                                if actual_hash != expected_hash:
                                    error_msg = f"❌ Неверный хеш: {rel_path}"
                                    hash_errors.append(error_msg)

                                    if skip_on_error:
                                        console.print(
                                            f"[yellow]{error_msg} (пропускаем)[/]"
                                        )
                                        skipped_files += 1
                                        continue
                                    else:
                                        console.print(f"[red]{error_msg}[/]")
                                        console.print(
                                            f"[red]❌ Восстановление прервано![/]"
                                        )
                                        return

                        if dry_run:
                            console.print(f"  [cyan]→[/] {rel_path}")
                        else:
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_file, dest_file)
                            restored_files += 1

                if not dry_run:
                    console.print(
                        f"[green]✅ Восстановлено файлов: {restored_files}[/]"
                    )
            else:
                console.print("[yellow]⚠️ Файлы в бэкапе не найдены[/]")

        # === ВОССТАНОВЛЕНИЕ БД ===
        if should_restore_db and not dry_run:
            console.print(f"\n[cyan]🗃️ Восстановление базы данных[/]")

            db_dir = restore_source / DB_BACKUP_DIR_NAME
            if db_dir.exists():
                db_info = metadata.get("database", {})
                db_type = db_info.get("type", "unknown")

                if db_type == "postgresql":
                    pg_restore = _find_system_utility("psql")
                    dump_file = db_dir / POSTGRES_BACKUP_FILENAME
                    if pg_restore and dump_file.exists():
                        console.print("[cyan]🐘 Восстановление PostgreSQL...[/]")
                        cmd = [pg_restore, db_url, "-f", str(dump_file)]
                        if _execute_system_command(cmd):
                            console.print("[green]✅ БД PostgreSQL восстановлена[/]")
                        else:
                            console.print("[red]❌ Ошибка восстановления PostgreSQL[/]")

                elif db_type == "mysql":
                    mysql = _find_system_utility("mysql")
                    dump_file = db_dir / MYSQL_BACKUP_FILENAME
                    if mysql and dump_file.exists():
                        console.print("[cyan]🐬 Восстановление MySQL...[/]")
                        # Команду нужно адаптировать под конкретную БД
                        console.print(
                            "[yellow]⚠️ Восстановление MySQL требует ручной настройки[/]"
                        )
            else:
                console.print("[yellow]⚠️ БД в бэкапе не найдена[/]")

        # === ИТОГОВАЯ СТАТИСТИКА ===
        if dry_run:
            console.print(f"\n[yellow]🔍 Сухой запуск завершен[/]")
        else:
            console.print(f"\n[green]🎉 Восстановление завершено![/]")
            if verify_hashes and hash_errors:
                console.print(f"[red]⚠️ Ошибок хешей: {len(hash_errors)}[/]")
                if skipped_files:
                    console.print(f"[yellow]⏭️ Пропущено файлов: {skipped_files}[/]")
            elif verify_hashes:
                console.print("[green]🔍 Все хеши проверены и корректны[/]")

    finally:
        if cleanup_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)


@backup_app.command("verify")
def verify_backup(
    backup_path: str = typer.Argument(..., help="Имя или путь к бэкапу для проверки"),
    checksum: bool = typer.Option(
        True, "--checksum/--no-checksum", help="Проверять контрольные суммы файлов"
    ),
):
    """🔍 Проверить целостность объединенного бэкапа."""
    backup_path = _resolve_backup_path(backup_path)
    console.print(f"[bold cyan]🔍 Проверка бэкапа: {backup_path}[/]")

    # Аналогично restore - определяем тип и распаковываем если нужно
    is_archive = backup_path.suffix == ".gz" and backup_path.suffixes[-2:] == [
        ".tar",
        ".gz",
    ]

    if is_archive:
        console.print("[cyan]📦 Проверка сжатого архива[/]")
        temp_dir = (
            backup_path.parent
            / f"temp_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        temp_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)
            verify_source = temp_dir
            cleanup_temp = True
        except Exception as e:
            console.print(f"[red]❌ Ошибка при распаковке: {e}[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
    else:
        verify_source = backup_path
        cleanup_temp = False

    try:
        # Проверяем метаданные
        metadata_file = verify_source / "metadata.json"
        if not metadata_file.exists():
            console.print("[red]❌ Файл metadata.json не найден[/]")
            return

        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)

        console.print(f"[green]📋 Тип бэкапа: {metadata.get('type', 'unknown')}[/]")

        errors = []
        total_files = 0
        verified_files = 0

        # Проверяем файлы
        if metadata.get("includes_files", False):
            console.print(f"[cyan]📁 Проверка файлов...[/]")

            files_dir = verify_source / FILES_BACKUP_DIR_NAME
            if files_dir.exists():
                hash_file = verify_source / "file_hashes.json"
                if checksum and hash_file.exists():
                    with open(hash_file, encoding="utf-8") as f:
                        file_hashes = json.load(f)

                    console.print(
                        f"[cyan]🔍 Проверка {len(file_hashes)} файлов с хешами...[/]"
                    )

                    for rel_path, expected_hash in file_hashes.items():
                        total_files += 1
                        file_path = files_dir / rel_path

                        if not file_path.exists():
                            errors.append(f"Файл отсутствует: {rel_path}")
                            continue

                        if expected_hash:  # Проверяем только непустые хеши
                            actual_hash = sha256(file_path)
                            if actual_hash != expected_hash:
                                errors.append(f"Неверный хеш: {rel_path}")
                                continue

                        verified_files += 1
                else:
                    console.print(
                        "[yellow]⚠️ Проверка хешей отключена или недоступна[/]"
                    )
                    for file_path in files_dir.rglob("*"):
                        if file_path.is_file():
                            total_files += 1
                            verified_files += 1

        # Проверяем БД
        if metadata.get("includes_db", False):
            console.print(f"[cyan]🗃️ Проверка базы данных...[/]")

            db_dir = verify_source / DB_BACKUP_DIR_NAME
            if db_dir.exists():
                db_info = metadata.get("database", {})
                expected_file = db_info.get("backup_file", "")
                if expected_file:
                    db_file = db_dir / expected_file
                    if db_file.exists():
                        console.print(f"[green]✅ Файл БД найден: {expected_file}[/]")
                    else:
                        errors.append(f"Файл БД отсутствует: {expected_file}")

        # Итоговый результат
        if errors:
            console.print(f"\n[red]❌ Найдено ошибок: {len(errors)}[/]")
            for error in errors[:10]:
                console.print(f"  • {error}")
            if len(errors) > 10:
                console.print(f"  • ... и ещё {len(errors) - 10} ошибок")
        else:
            console.print(f"\n[green]✅ Бэкап целостен![/]")
            console.print(f"   📁 Проверено файлов: {verified_files}/{total_files}")
            if checksum:
                console.print(f"   🔍 Все хеши корректны")

    finally:
        if cleanup_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)


@backup_app.command("info")
def backup_info(
    backup_path: str = typer.Argument(
        ..., help="Имя или путь к бэкапу для получения информации"
    )
):
    """📊 Показать подробную информацию о бэкапе."""
    backup_path = _resolve_backup_path(backup_path)
    console.print(f"[bold cyan]📊 Информация о бэкапе: {backup_path}[/]")

    # Определяем тип бэкапа и читаем метаданные аналогично другим командам
    is_archive = backup_path.suffix == ".gz" and backup_path.suffixes[-2:] == [
        ".tar",
        ".gz",
    ]

    if is_archive:
        archive_size = backup_path.stat().st_size
        console.print(
            f"[cyan]📦 Тип: Сжатый архив ({archive_size / (1024*1024):.1f}MB)[/]"
        )

        temp_dir = (
            backup_path.parent / f"temp_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        temp_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                metadata_files = ["metadata.json"]
                for member in tar.getmembers():
                    if member.name in metadata_files:
                        tar.extract(member, temp_dir)

            info_source = temp_dir
            cleanup_temp = True
        except Exception as e:
            console.print(f"[red]❌ Ошибка чтения архива: {e}[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
    else:
        console.print("[cyan]📁 Тип: Папка с файлами[/]")
        info_source = backup_path
        cleanup_temp = False

    try:
        metadata_file = info_source / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

            # Основная информация
            console.print(
                Panel.fit(
                    f"[green]🏷️ Тип:[/] {metadata.get('type', 'unknown')}\n"
                    f"[green]📅 Создан:[/] {metadata.get('timestamp', 'unknown')}\n"
                    f"[green]📁 Включает файлы:[/] {'✅' if metadata.get('includes_files') else '❌'}\n"
                    f"[green]🗃️ Включает БД:[/] {'✅' if metadata.get('includes_db') else '❌'}\n"
                    f"[green]🔍 Хеши:[/] {'✅' if metadata.get('verify_hashes') else '❌'}\n"
                    f"[green]🗜️ Сжатие:[/] {'✅' if metadata.get('compressed') else '❌'}",
                    title="📋 Общая информация",
                    border_style="green",
                )
            )

            # Информация о файлах
            files_info = metadata.get("files", {})
            if files_info:
                console.print(
                    Panel.fit(
                        f"[blue]📁 Файлов:[/] {files_info.get('count', 0):,}\n"
                        f"[blue]📊 Размер:[/] {files_info.get('total_size', 0) / (1024*1024):.1f}MB\n"
                        f"[blue]🔍 Хеши:[/] {'включены' if files_info.get('hashes_enabled') else 'отключены'}",
                        title="📁 Файлы",
                        border_style="blue",
                    )
                )

            # Информация о БД
            db_info = metadata.get("database", {})
            if db_info and db_info.get("type") != "unknown":
                console.print(
                    Panel.fit(
                        f"[red]🗃️ Тип БД:[/] {db_info.get('type', 'unknown')}\n"
                        f"[red]✅ Успешно:[/] {'✅' if db_info.get('success') else '❌'}\n"
                        f"[red]📄 Файл:[/] {db_info.get('backup_file', 'не указан')}",
                        title="🗃️ База данных",
                        border_style="red",
                    )
                )

            console.print("[green]✅ Информация загружена успешно[/]")
        else:
            console.print("[red]❌ Метаданные недоступны[/]")

    finally:
        if cleanup_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)


# === УЛУЧШЕННЫЕ УТИЛИТЫ ОБНАРУЖЕНИЯ ===


def detect_database_type(path: Optional[Path] = None) -> Dict[str, Any]:
    """Определить тип базы данных в проекте."""

    if path is None:
        # Путь к корню проекта (где находится sdb.py)
        search_path = Path(__file__).resolve().parent.parent
    else:
        search_path = path.resolve()

    # Поиск SQLite файлов
    sqlite_files = []
    for pattern in ["**/*.db", "**/*.sqlite", "**/*.sqlite3"]:
        sqlite_files.extend(search_path.glob(pattern))

    # Исключаем временные файлы
    sqlite_files = [
        f
        for f in sqlite_files
        if not any(
            exclude in str(f)
            for exclude in [".git", "__pycache__", ".pytest_cache", ".venv"]
        )
    ]

    if sqlite_files:
        return {
            "type": "sqlite",
            "location": str(sqlite_files[0]),  # Берём первый найденный
            "needs_separate_backup": False,
            "detected_files": [str(f.relative_to(search_path)) for f in sqlite_files],
        }

    # Поиск конфигурационных файлов для внешних БД
    config_files = [
        search_path / ".env",
        search_path / ".env.local",
        search_path / "config.py",
        search_path / "settings.py",
    ]

    for config_file in config_files:
        if config_file.exists():
            content = config_file.read_text()

            # Поиск PostgreSQL
            if any(
                keyword in content.lower()
                for keyword in ["postgresql", "postgres", "psycopg"]
            ):
                return {
                    "type": "postgresql",
                    "location": "external_server",
                    "needs_separate_backup": True,
                    "config_file": str(config_file),
                    "detected_files": [],
                }

            # Поиск MySQL
            if any(
                keyword in content.lower()
                for keyword in ["mysql", "pymysql", "mysqlclient"]
            ):
                return {
                    "type": "mysql",
                    "location": "external_server",
                    "needs_separate_backup": True,
                    "config_file": str(config_file),
                    "detected_files": [],
                }

    return {
        "type": "none",
        "location": "not_found",
        "needs_separate_backup": False,
        "detected_files": [],
    }


def analyze_backup_scope(source_path: Path) -> dict:
    """Анализирует область бэкапа и выдает рекомендации."""
    project_root = Path(__file__).resolve().parent.parent
    analysis = {
        "is_project_root": False,
        "is_external_path": False,
        "includes_project_files": False,
        "missing_important_dirs": [],
        "recommendations": [],
        "warnings": [],
    }

    source_path = source_path.resolve()

    # Проверяем, является ли путь корнем проекта
    if source_path == project_root:
        analysis["is_project_root"] = True
        analysis["includes_project_files"] = True

    # Проверяем, находится ли путь вне проекта
    try:
        source_path.relative_to(project_root)
        analysis["is_external_path"] = False
    except ValueError:
        analysis["is_external_path"] = True
        analysis["warnings"].append(
            "⚠️ Указанный путь находится ВНЕ проекта SwiftDevBot"
        )

    # Проверяем важные директории проекта
    important_dirs = [
        ("Systems/core", "Основной код бота"),
        ("Systems/cli", "CLI команды"),
        ("modules", "Модули бота"),
        ("Data", "Данные проекта"),
        ("Systems/locales", "Локализация"),
    ]

    for dir_name, description in important_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            try:
                # Проверяем, включается ли эта директория в бэкап
                source_path.relative_to(dir_path.parent)
                if not any(source_path == parent for parent in dir_path.parents):
                    analysis["missing_important_dirs"].append(
                        f"{dir_name} ({description})"
                    )
            except ValueError:
                analysis["missing_important_dirs"].append(f"{dir_name} ({description})")

    # Генерируем рекомендации
    if analysis["is_external_path"]:
        analysis["recommendations"].append(
            "💡 Для бэкапа проекта SwiftDevBot используйте корневую папку проекта"
        )

    if analysis["missing_important_dirs"]:
        analysis["warnings"].append(
            f"⚠️ Не включены важные директории: {', '.join(analysis['missing_important_dirs'][:3])}"
        )
        analysis["recommendations"].append(
            "💡 Рассмотрите возможность бэкапа всего проекта: --type=full без указания пути"
        )

    return analysis


@backup_app.command("check")
def check_project_config(
    path: Optional[Path] = typer.Argument(
        None, help="Путь для проверки (по умолчанию - корень проекта)"
    )
):
    """🔍 Проверить конфигурацию проекта и дать рекомендации по бэкапу."""

    if path is None:
        path = Path(__file__).resolve().parent.parent
    else:
        path = path.expanduser().resolve()

    console.print(f"[bold cyan]🔍 Анализ конфигурации проекта: {path}[/]")

    # Анализируем область
    scope_analysis = analyze_backup_scope(path)

    # Обнаруживаем БД для указанного пути
    db_info = detect_database_type(path)

    # Создаем отчет
    console.print(
        Panel.fit(
            f"[green]📍 Анализируемый путь:[/] {path}\n"
            f"[green]🏠 Корень проекта:[/] {'✅' if scope_analysis['is_project_root'] else '❌'}\n"
            f"[green]🌐 Внешний путь:[/] {'⚠️' if scope_analysis['is_external_path'] else '✅'}\n"
            f"[green]📁 Включает файлы проекта:[/] {'✅' if scope_analysis['includes_project_files'] else '❌'}",
            title="📋 Анализ области бэкапа",
            border_style="blue",
        )
    )

    console.print(
        Panel.fit(
            f"[green]🗃️ Тип БД:[/] {db_info['type'].upper()}\n"
            f"[green]📍 Местоположение:[/] {db_info['location'] or 'не найдено'}\n"
            f"[green]🔄 Нужен отдельный бэкап:[/] {'✅' if db_info['needs_separate_backup'] else '❌'}\n"
            f"[green]📄 Обнаружены файлы:[/] {', '.join(db_info['detected_files']) if db_info['detected_files'] else 'нет'}",
            title="🗃️ Конфигурация БД",
            border_style="green",
        )
    )

    # Показываем предупреждения
    if scope_analysis["warnings"]:
        console.print("\n[bold red]⚠️ Предупреждения:[/]")
        for warning in scope_analysis["warnings"]:
            console.print(f"  {warning}")

    # Показываем рекомендации
    if scope_analysis["recommendations"]:
        console.print("\n[bold blue]💡 Рекомендации:[/]")
        for recommendation in scope_analysis["recommendations"]:
            console.print(f"  {recommendation}")

    # Рекомендации по бэкапу
    console.print(f"\n[bold cyan]🎯 Рекомендуемые команды бэкапа:[/]")

    if scope_analysis["is_project_root"]:
        console.print("  [green]# Полный бэкап проекта (рекомендуется)[/]")
        console.print("  [dim]python sdb.py backup create --type=full[/]")

        if db_info["type"] == "sqlite":
            console.print("\n  [green]# Только файлы (SQLite уже включен)[/]")
            console.print("  [dim]python sdb.py backup create --type=files[/]")

        if db_info["needs_separate_backup"]:
            console.print("\n  [green]# Только БД (PostgreSQL/MySQL)[/]")
            console.print(
                "  [dim]python sdb.py backup create --type=db --db-url=ваш_url[/]"
            )

    else:
        console.print("  [yellow]# Кастомный бэкап указанного пути[/]")
        console.print(f"  [dim]python sdb.py backup create --type=custom {path}[/]")

        console.print("\n  [green]# Бэкап всего проекта (рекомендуется)[/]")
        console.print("  [dim]python sdb.py backup create --type=full[/]")

    console.print(f"\n[green]✅ Анализ завершен[/]")


@backup_app.command("diff")
def diff_backup(
    backup_path: str = typer.Argument(..., help="Имя или путь к бэкапу для сравнения"),
    show_details: bool = typer.Option(
        False, "--details", "-d", help="Показать подробную информацию об изменениях"
    ),
    check_hashes: bool = typer.Option(
        True, "--check-hashes/--no-check-hashes", help="Проверять хеши файлов"
    ),
    ignore_timestamps: bool = typer.Option(
        False, "--ignore-timestamps", help="Игнорировать изменения времени модификации"
    ),
    exclude: Optional[List[str]] = typer.Option(
        None, "--exclude", "-x", help="Дополнительные исключения для сравнения"
    ),
):
    """🔍 Сравнить текущее состояние системы с сохранённым бэкапом."""
    backup_path = _resolve_backup_path(backup_path)
    console.print(f"[bold cyan]🔍 Сравнение системы с бэкапом: {backup_path}[/]")
    
    # Определяем тип бэкапа
    is_archive = backup_path.suffix == ".gz" and backup_path.suffixes[-2:] == [".tar", ".gz"]
    
    if is_archive:
        console.print("[cyan]📦 Анализ сжатого архива...[/]")
        temp_dir = backup_path.parent / f"temp_diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)
            backup_source = temp_dir
            cleanup_temp = True
        except Exception as e:
            console.print(f"[red]❌ Ошибка распаковки: {e}[/]")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
    else:
        console.print("[cyan]📁 Анализ папки с бэкапом...[/]")
        backup_source = backup_path
        cleanup_temp = False
    
    try:
        # Читаем метаданные бэкапа
        metadata_file = backup_source / "metadata.json"
        if not metadata_file.exists():
            console.print("[red]❌ Файл metadata.json не найден в бэкапе[/]")
            return
            
        with open(metadata_file, encoding="utf-8") as f:
            backup_metadata = json.load(f)
        
        console.print(f"[green]📋 Тип бэкапа: {backup_metadata.get('type', 'unknown')}[/]")
        console.print(f"[green]📅 Создан: {backup_metadata.get('timestamp', 'unknown')}[/]")
        
        # Получаем исключения из бэкапа
        backup_excludes = backup_metadata.get("excluded_patterns", [])
        if exclude:
            backup_excludes.extend(exclude)
        
        # === СРАВНЕНИЕ ФАЙЛОВ ===
        if backup_metadata.get("includes_files", False):
            console.print(f"\n[cyan]📁 Сравнение файлов...[/]")
            
            # Читаем хеши из бэкапа
            backup_hashes = {}
            hash_file = backup_source / "file_hashes.json"
            if hash_file.exists():
                with open(hash_file, encoding="utf-8") as f:
                    backup_hashes = json.load(f)
            
            # Сканируем текущее состояние системы
            project_root = Path(__file__).resolve().parent.parent
            console.print("[cyan]🔍 Сканирование текущего состояния...[/]")
            
            if check_hashes and backup_hashes:
                current_hashes = scan_directory(project_root, excludes=backup_excludes)
            else:
                # Сканируем без хешей для быстрого сравнения
                current_hashes = {}
                import fnmatch
                
                for file in project_root.rglob("*"):
                    if file.is_file():
                        rel_path = file.relative_to(project_root).as_posix()
                        
                        # Применяем исключения
                        excluded = False
                        for excl in backup_excludes:
                            if "*" in excl:
                                if fnmatch.fnmatch(rel_path, excl) or fnmatch.fnmatch(file.name, excl):
                                    excluded = True
                                    break
                            elif "/" in excl:
                                if rel_path.startswith(excl) or rel_path == excl:
                                    excluded = True
                                    break
                            else:
                                path_parts = rel_path.split("/")
                                if excl in path_parts or excl == file.name:
                                    excluded = True
                                    break
                        
                        if not excluded:
                            current_hashes[rel_path] = ""  # Пустой хеш для быстрого режима
            
            # Анализ различий
            added_files = []
            deleted_files = []
            modified_files = []
            
            # Файлы в текущей системе, но не в бэкапе (добавленные)
            for file_path in current_hashes:
                if file_path not in backup_hashes:
                    file_stat = (project_root / file_path).stat()
                    added_files.append({
                        "path": file_path,
                        "size": file_stat.st_size,
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    })
            
            # Файлы в бэкапе, но не в текущей системе (удалённые)
            for file_path in backup_hashes:
                if file_path not in current_hashes:
                    deleted_files.append({
                        "path": file_path,
                        "hash": backup_hashes[file_path][:8] if backup_hashes[file_path] else "no-hash",
                    })
            
            # Файлы в обеих системах (потенциально изменённые)
            for file_path in backup_hashes:
                if file_path in current_hashes:
                    current_file = project_root / file_path
                    if current_file.exists():
                        backup_hash = backup_hashes[file_path]
                        current_hash = current_hashes[file_path]
                        
                        # Сравниваем хеши если доступны
                        if check_hashes and backup_hash and current_hash:
                            if backup_hash != current_hash:
                                file_stat = current_file.stat()
                                modified_files.append({
                                    "path": file_path,
                                    "backup_hash": backup_hash[:8],
                                    "current_hash": current_hash[:8],
                                    "size": file_stat.st_size,
                                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                                    "reason": "hash_different"
                                })
                        elif not check_hashes:
                            # Сравниваем по размеру и времени модификации
                            file_stat = current_file.stat()
                            backup_files_dir = backup_source / FILES_BACKUP_DIR_NAME / file_path
                            
                            if backup_files_dir.exists():
                                backup_stat = backup_files_dir.stat()
                                size_different = file_stat.st_size != backup_stat.st_size
                                
                                if not ignore_timestamps:
                                    time_different = abs(file_stat.st_mtime - backup_stat.st_mtime) > 2
                                else:
                                    time_different = False
                                
                                if size_different or time_different:
                                    reasons = []
                                    if size_different:
                                        reasons.append("size_different")
                                    if time_different:
                                        reasons.append("time_different")
                                    
                                    modified_files.append({
                                        "path": file_path,
                                        "backup_size": backup_stat.st_size,
                                        "current_size": file_stat.st_size,
                                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                                        "reason": "+".join(reasons)
                                    })
            
            # === ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ===
            console.print(f"\n[bold green]📊 Результаты сравнения:[/]")
            
            # Статистика
            stats_table = Table(title="📈 Сводка изменений")
            stats_table.add_column("Категория", style="bold")
            stats_table.add_column("Количество", style="cyan")
            stats_table.add_column("Описание", style="dim")
            
            stats_table.add_row("✅ Добавлено", f"{len(added_files)}", "Новые файлы в системе")
            stats_table.add_row("❌ Удалено", f"{len(deleted_files)}", "Файлы отсутствуют в системе")
            stats_table.add_row("🔄 Изменено", f"{len(modified_files)}", "Файлы изменились")
            
            console.print(stats_table)
            
            # Подробная информация если запрошена
            if show_details:
                if added_files:
                    console.print(f"\n[bold green]✅ ДОБАВЛЕННЫЕ ФАЙЛЫ ({len(added_files)}):[/]")
                    added_table = Table()
                    added_table.add_column("Файл", style="green")
                    added_table.add_column("Размер", style="cyan")
                    added_table.add_column("Изменён", style="dim")
                    
                    for file_info in added_files[:20]:  # Показываем первые 20
                        size_mb = file_info["size"] / (1024 * 1024) if file_info["size"] > 1024*1024 else file_info["size"]
                        size_str = f"{size_mb:.1f}MB" if file_info["size"] > 1024*1024 else f"{file_info['size']}B"
                        added_table.add_row(
                            file_info["path"],
                            size_str,
                            file_info["modified"][:16]
                        )
                    
                    console.print(added_table)
                    if len(added_files) > 20:
                        console.print(f"[dim]... и ещё {len(added_files) - 20} файлов[/]")
                
                if deleted_files:
                    console.print(f"\n[bold red]❌ УДАЛЁННЫЕ ФАЙЛЫ ({len(deleted_files)}):[/]")
                    deleted_table = Table()
                    deleted_table.add_column("Файл", style="red")
                    deleted_table.add_column("Хеш (бэкап)", style="dim")
                    
                    for file_info in deleted_files[:20]:
                        deleted_table.add_row(
                            file_info["path"],
                            file_info["hash"]
                        )
                    
                    console.print(deleted_table)
                    if len(deleted_files) > 20:
                        console.print(f"[dim]... и ещё {len(deleted_files) - 20} файлов[/]")
                
                if modified_files:
                    console.print(f"\n[bold yellow]🔄 ИЗМЕНЁННЫЕ ФАЙЛЫ ({len(modified_files)}):[/]")
                    modified_table = Table()
                    modified_table.add_column("Файл", style="yellow")
                    modified_table.add_column("Причина", style="magenta")
                    
                    if check_hashes:
                        modified_table.add_column("Хеш (бэкап)", style="dim")
                        modified_table.add_column("Хеш (текущий)", style="cyan")
                    else:
                        modified_table.add_column("Размер (бэкап)", style="dim")
                        modified_table.add_column("Размер (текущий)", style="cyan")
                    
                    for file_info in modified_files[:20]:
                        if check_hashes:
                            modified_table.add_row(
                                file_info["path"],
                                file_info["reason"],
                                file_info.get("backup_hash", "N/A"),
                                file_info.get("current_hash", "N/A")
                            )
                        else:
                            backup_size = file_info.get("backup_size", 0)
                            current_size = file_info.get("current_size", 0)
                            backup_size_str = f"{backup_size}B" if backup_size < 1024*1024 else f"{backup_size/(1024*1024):.1f}MB"
                            current_size_str = f"{current_size}B" if current_size < 1024*1024 else f"{current_size/(1024*1024):.1f}MB"
                            
                            modified_table.add_row(
                                file_info["path"],
                                file_info["reason"],
                                backup_size_str,
                                current_size_str
                            )
                    
                    console.print(modified_table)
                    if len(modified_files) > 20:
                        console.print(f"[dim]... и ещё {len(modified_files) - 20} файлов[/]")
            else:
                # Краткая информация
                if added_files:
                    console.print(f"[green]✅ Добавлено файлов: {len(added_files)} (используйте --details для подробностей)[/]")
                if deleted_files:
                    console.print(f"[red]❌ Удалено файлов: {len(deleted_files)} (используйте --details для подробностей)[/]")
                if modified_files:
                    console.print(f"[yellow]🔄 Изменено файлов: {len(modified_files)} (используйте --details для подробностей)[/]")
            
            # Итоговая оценка
            total_changes = len(added_files) + len(deleted_files) + len(modified_files)
            if total_changes == 0:
                console.print(f"\n[bold green]🎉 Система идентична бэкапу![/]")
            else:
                console.print(f"\n[bold yellow]⚠️ Обнаружено {total_changes} изменений в системе[/]")
                
                # Рекомендации
                if len(added_files) > 10 or len(modified_files) > 10:
                    console.print(f"[blue]💡 Рекомендация: Создайте новый бэкап для сохранения изменений[/]")
                    console.print(f"[dim]   python3 sdb.py backup create --type=full[/]")
        
        else:
            console.print("[yellow]⚠️ Бэкап не содержит файлов для сравнения[/]")
        
        # === СРАВНЕНИЕ БАЗЫ ДАННЫХ ===
        if backup_metadata.get("includes_db", False):
            console.print(f"\n[cyan]🗃️ Сравнение базы данных...[/]")
            
            # Сравниваем информацию о БД
            backup_db = backup_metadata.get("database", {})
            current_db = detect_database_type()
            
            console.print(f"[dim]Тип БД в бэкапе: {backup_db.get('type', 'unknown')}[/]")
            console.print(f"[dim]Текущий тип БД: {current_db.get('type', 'unknown')}[/]")
            
            if backup_db.get("type") != current_db.get("type"):
                console.print("[yellow]⚠️ Тип базы данных изменился![/]")
            
            if current_db.get("type") == "sqlite":
                # Для SQLite сравниваем размеры файлов БД
                current_db_files = current_db.get("detected_files", [])
                backup_db_files = backup_db.get("files", [])
                
                if set(current_db_files) != set(backup_db_files):
                    console.print("[yellow]🔄 Файлы базы данных изменились[/]")
                    console.print(f"   Бэкап: {backup_db_files}")
                    console.print(f"   Текущие: {current_db_files}")
                else:
                    console.print("[green]✅ Файлы базы данных соответствуют бэкапу[/]")
            else:
                console.print("[blue]💡 Для внешних БД требуется отдельное сравнение дампов[/]")
        
    finally:
        if cleanup_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    console.print(f"\n[green]✅ Сравнение завершено[/]")

def _resolve_backup_path(backup_path: Union[str, Path]) -> Path:
    """Определяет абсолютный путь к бэкапу по имени или относительному/абсолютному пути."""
    p = Path(backup_path)
    if p.exists():
        return p.resolve()
    # Если путь не существует и не содержит / — ищем в backup/
    if not p.is_absolute() and '/' not in str(p):
        backup_dir = _get_backup_base_dir()
        candidate = backup_dir / p
        if candidate.exists():
            return candidate.resolve()
    # Если не найден — возвращаем исходный путь
    return p.resolve()

# --- Конец backup_unified.py ---
