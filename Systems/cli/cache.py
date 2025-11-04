# cli/cache.py
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from Systems.cli.utils import confirm_action

console = Console()
cache_app = typer.Typer(name="cache", help="💾 Управление кэшем системы")


@cache_app.command(name="clear", help="Очистить весь кэш системы.")
def cache_clear_cmd(
    cache_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Тип кэша: memory, redis, all"
    ),
    confirm: bool = typer.Option(
        False, "--confirm", "-y", help="Подтвердить очистку без запроса"
    ),
):
    """Очистить кэш системы"""
    try:
        asyncio.run(_cache_clear_async(cache_type, confirm))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'cache clear': {e}[/]")
        raise typer.Exit(code=1)


async def _get_cache_manager_only():
    """Получить только CacheManager без полной инициализации всех сервисов."""
    try:
        from pathlib import Path

        import yaml

        from Systems.core.app_settings import PROJECT_ROOT_DIR

        # Минимальные настройки только для кэша
        project_data_path = PROJECT_ROOT_DIR / "Data"
        config_file = project_data_path / "Config" / "core_settings.yaml"

        # Читаем только настройки кэша из YAML
        cache_config = {"type": "memory", "ttl": 300, "max_size": 1024}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                    if "cache" in yaml_data:
                        cache_config.update(yaml_data["cache"])
            except Exception:
                pass  # Используем дефолты

        # Создаём минимальный объект настроек кэша
        class CacheSettings:
            def __init__(self, config):
                self.type = config.get("type", "memory")
                self.ttl = config.get("ttl", 300)
                self.max_size = config.get("max_size", 1024)
                # Redis настройки (если нужны)
                self.redis_url = config.get("redis_url", "redis://localhost:6379/0")
                self.redis_password = config.get("redis_password")

        cache_settings = CacheSettings(cache_config)

        from Systems.core.cache.manager import CacheManager

        cache_manager = CacheManager(cache_settings=cache_settings)
        await cache_manager.initialize()

        return cache_manager

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка инициализации кэша: {e}[/]")
        raise


async def _cache_clear_async(cache_type: Optional[str], confirm: bool):
    """Очистить кэш"""
    console.print(
        Panel("[bold blue]ОЧИСТКА КЭША СИСТЕМЫ[/]", expand=False, border_style="blue")
    )

    if not confirm:
        cache_type_display = cache_type or "memory"
        if not confirm_action(
            f"Вы уверены, что хотите очистить кэш {cache_type_display}?",
            default_choice=False,
            abort_on_false=False,
        ):
            console.print("[yellow]⚠️ Очистка кэша отменена.[/]")
            return

    # Получаем только cache_manager (легковесная инициализация)
    try:
        cache_manager = await _get_cache_manager_only()
        cleared_count = 0

        # Определяем тип кэша по умолчанию
        if cache_type is None:
            cache_type = "memory"  # По умолчанию только memory кэш

        if cache_type == "memory" or cache_type == "all":
            console.print("[cyan]Очистка memory кэша...[/]")
            try:
                if cache_manager.is_available():
                    await cache_manager.clear_all_cache()
                    console.print("[green]✅ Memory кэш очищен.[/]")
                    cleared_count += 1
                else:
                    console.print("[yellow]⚠️ Memory кэш недоступен.[/]")
            except Exception as e:
                console.print(f"[yellow]❌ Ошибка при очистке memory кэша: {e}[/]")

        if cache_type == "redis" or cache_type == "all":
            console.print("[cyan]Очистка Redis кэша...[/]")
            try:
                redis_client = await cache_manager.get_redis_client_instance()
                if redis_client:
                    await redis_client.flushdb()
                    console.print("[green]✅ Redis кэш очищен.[/]")
                    cleared_count += 1
                else:
                    console.print(
                        "[yellow]⚠️ Redis клиент недоступен или не настроен.[/]"
                    )
            except Exception as e:
                console.print(f"[yellow]❌ Ошибка при очистке Redis кэша: {e}[/]")

        if cleared_count > 0:
            console.print(
                f"[bold green]🎉 Очистка кэша завершена успешно! Очищено типов кэша: {cleared_count}[/]"
            )
        else:
            console.print("[yellow]⚠️ Не удалось очистить ни один тип кэша.[/]")

        # Очистка ресурсов
        await cache_manager.dispose()

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при очистке кэша: {e}[/]")
        raise typer.Exit(code=1)


@cache_app.command(name="stats", help="Показать статистику кэша.")
def cache_stats_cmd(
    cache_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Тип кэша: memory, redis, all"
    ),
    format: str = typer.Option(
        "table", "--format", "-f", help="Формат вывода: table, json"
    ),
):
    """Показать статистику кэша"""
    try:
        asyncio.run(_cache_stats_async(cache_type, format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'cache stats': {e}[/]")
        raise typer.Exit(code=1)


async def _cache_stats_async(cache_type: Optional[str], format: str):
    """Показать статистику кэша"""
    console.print(
        Panel("[bold blue]СТАТИСТИКА КЭША[/]", expand=False, border_style="blue")
    )

    try:
        cache_manager = await _get_cache_manager_only()
        stats = {}

        # Memory кэш статистика
        if cache_type in ["memory", None]:
            console.print("[cyan]Сбор статистики memory кэша...[/]")
            try:
                memory_stats = {
                    "type": "memory",
                    "status": (
                        "available" if cache_manager.is_available() else "unavailable"
                    ),
                    "backend": "TTLCache",
                    "maxsize": "1024",
                    "default_ttl": "300s",
                    "current_size": "N/A",
                    "hit_count": "N/A",
                    "miss_count": "N/A",
                }

                # Попытка получить более детальную статистику
                if hasattr(cache_manager, "_cache"):
                    cache_obj = cache_manager._cache
                    if hasattr(cache_obj, "__len__"):
                        memory_stats["current_size"] = str(len(cache_obj))
                    if hasattr(cache_obj, "hits"):
                        memory_stats["hit_count"] = str(cache_obj.hits)
                    if hasattr(cache_obj, "misses"):
                        memory_stats["miss_count"] = str(cache_obj.misses)

                stats["memory"] = memory_stats
            except Exception as e:
                stats["memory"] = {"type": "memory", "status": "error", "error": str(e)}

        # Redis кэш статистика
        if cache_type in ["redis", None]:
            console.print("[cyan]Сбор статистики Redis кэша...[/]")
            redis_client = await cache_manager.get_redis_client_instance()
            if redis_client:
                try:
                    info = await redis_client.info()
                    redis_stats = {
                        "type": "redis",
                        "status": "available",
                        "connected_clients": info.get("connected_clients", "N/A"),
                        "used_memory_human": info.get("used_memory_human", "N/A"),
                        "total_commands_processed": info.get(
                            "total_commands_processed", "N/A"
                        ),
                        "keyspace_hits": info.get("keyspace_hits", "N/A"),
                        "keyspace_misses": info.get("keyspace_misses", "N/A"),
                        "total_keys": info.get("db0", {}).get("keys", "N/A"),
                        "uptime_seconds": info.get("uptime_in_seconds", "N/A"),
                    }

                    # Вычисляем hit ratio
                    hits = int(info.get("keyspace_hits", 0))
                    misses = int(info.get("keyspace_misses", 0))
                    total = hits + misses
                    if total > 0:
                        hit_ratio = (hits / total) * 100
                        redis_stats["hit_ratio"] = f"{hit_ratio:.2f}%"
                    else:
                        redis_stats["hit_ratio"] = "N/A"

                except Exception as e:
                    redis_stats = {"type": "redis", "status": "error", "error": str(e)}
            else:
                redis_stats = {"type": "redis", "status": "unavailable"}

            stats["redis"] = redis_stats

        # Отображаем результаты
        await _display_cache_stats(stats, format)

        # Очистка ресурсов
        await cache_manager.dispose()

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при сборе статистики кэша: {e}[/]")
        raise typer.Exit(code=1)


async def _display_cache_stats(stats: dict, format: str):
    """Отобразить статистику кэша"""

    if format == "json":
        console.print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    # Табличный формат
    for cache_type, cache_stats in stats.items():
        console.print(f"\n[bold cyan]{cache_type.upper()} КЭШ:[/]")

        table = Table()
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="white")

        for key, value in cache_stats.items():
            if key != "type":
                table.add_row(key, str(value))

        console.print(table)


@cache_app.command(name="keys", help="Управление ключами кэша.")
def cache_keys_cmd(
    action: str = typer.Argument(..., help="Действие: list, get, delete, search, info"),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Шаблон для поиска ключей"
    ),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Конкретный ключ"),
    cache_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Тип кэша: memory, redis"
    ),
    limit: int = typer.Option(
        50, "--limit", "-l", help="Максимальное количество ключей для отображения"
    ),
):
    """Управление ключами кэша"""
    try:
        asyncio.run(_cache_keys_async(action, pattern, key, cache_type, limit))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'cache keys': {e}[/]")
        raise typer.Exit(code=1)


async def _cache_keys_async(
    action: str,
    pattern: Optional[str],
    key: Optional[str],
    cache_type: Optional[str],
    limit: int,
):
    """Асинхронная реализация управления ключами кэша"""
    console.print(
        Panel(
            "[bold blue]УПРАВЛЕНИЕ КЛЮЧАМИ КЭША[/]", expand=False, border_style="blue"
        )
    )

    try:
        cache_manager = await _get_cache_manager_only()

        if action == "list":
            await _list_cache_keys(cache_manager, pattern or "*", limit)
        elif action == "get":
            if not key:
                console.print(
                    "[bold red]Для действия 'get' необходимо указать ключ (--key).[/]"
                )
                raise typer.Exit(code=1)
            await _get_cache_key_value(cache_manager, key)
        elif action == "delete":
            if not key:
                console.print(
                    "[bold red]Для действия 'delete' необходимо указать ключ (--key).[/]"
                )
                raise typer.Exit(code=1)
            await _delete_cache_key(cache_manager, key, auto_confirm=False)
        elif action == "search":
            if not pattern:
                console.print(
                    "[bold red]Для действия 'search' необходимо указать шаблон (--pattern).[/]"
                )
                raise typer.Exit(code=1)
            await _search_cache_keys(cache_manager, pattern, limit)
        elif action == "info":
            await _cache_keys_info(cache_manager)
        else:
            console.print(f"[bold red]Неизвестное действие: {action}[/]")
            console.print("[dim]Доступные действия: list, get, delete, search, info[/]")
            raise typer.Exit(code=1)

        # Очистка ресурсов
        await cache_manager.dispose()

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при работе с ключами кэша: {e}[/]")
        raise typer.Exit(code=1)


async def _list_cache_keys(cache_manager, pattern: str, limit: int):
    """Получить список ключей кэша"""
    console.print(
        f"[cyan]Получение списка ключей кэша (паттерн: {pattern}, лимит: {limit})...[/]"
    )

    if not cache_manager.is_available():
        console.print("[yellow]⚠️ Кэш недоступен.[/]")
        return

    keys = await cache_manager.keys(pattern)

    if not keys:
        console.print("[yellow]📭 Ключи не найдены.[/]")
        return

    # Применяем лимит
    displayed_keys = keys[:limit] if len(keys) > limit else keys

    # Создаем таблицу
    table = Table(title=f"Ключи кэша ({len(displayed_keys)} из {len(keys)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Ключ", style="cyan")
    table.add_column("Существует", justify="center", width=10)

    for i, cache_key in enumerate(displayed_keys, 1):
        exists = await cache_manager.exists(cache_key)
        status = "[green]✓[/]" if exists else "[red]✗[/]"
        table.add_row(str(i), cache_key, status)

    console.print(table)

    if len(keys) > limit:
        console.print(
            f"[dim]Показаны первые {limit} ключей из {len(keys)}. Используйте --limit для изменения количества.[/]"
        )


async def _get_cache_key_value(cache_manager, key: str):
    """Получить значение ключа кэша"""
    console.print(f"[cyan]Получение значения ключа: [bold]{key}[/]")

    if not cache_manager.is_available():
        console.print("[yellow]⚠️ Кэш недоступен.[/]")
        return

    try:
        value = await cache_manager.get(key)

        if value is None:
            console.print(
                f"[yellow]📭 Ключ '{key}' не найден или его значение равно None.[/]"
            )
            return

        # Форматируем вывод в зависимости от типа значения
        table = Table(title=f"Значение ключа: {key}")
        table.add_column("Свойство", style="cyan", width=15)
        table.add_column("Значение", style="white")

        table.add_row("Тип", str(type(value).__name__))
        table.add_row("Размер", f"{len(str(value))} символов")

        # Обрезаем длинные значения для отображения
        display_value = str(value)
        if len(display_value) > 500:
            display_value = display_value[:497] + "..."

        table.add_row("Значение", display_value)

        console.print(table)

    except Exception as e:
        console.print(
            f"[bold red]❌ Ошибка при получении значения ключа '{key}': {e}[/]"
        )


async def _delete_cache_key(cache_manager, key: str, auto_confirm: bool = False):
    """Удалить ключ из кэша"""
    console.print(f"[cyan]Удаление ключа: [bold]{key}[/]")

    if not cache_manager.is_available():
        console.print("[yellow]⚠️ Кэш недоступен.[/]")
        return

    try:
        # Проверяем существование ключа
        exists = await cache_manager.exists(key)
        if not exists:
            console.print(f"[yellow]📭 Ключ '{key}' не найден в кэше.[/]")
            return

        # Подтверждение удаления
        if not auto_confirm and not confirm_action(
            f"Вы уверены, что хотите удалить ключ '{key}'?",
            default_choice=False,
            abort_on_false=False,
        ):
            console.print("[yellow]⚠️ Удаление ключа отменено.[/]")
            return

        # Удаляем ключ
        deleted = await cache_manager.delete(key)

        if deleted:
            console.print(f"[green]✅ Ключ '{key}' успешно удален из кэша.[/]")
        else:
            console.print(
                f"[yellow]⚠️ Не удалось удалить ключ '{key}' (возможно, он уже не существует).[/]"
            )

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при удалении ключа '{key}': {e}[/]")


async def _search_cache_keys(cache_manager, pattern: str, limit: int):
    """Поиск ключей по паттерну"""
    console.print(
        f"[cyan]Поиск ключей по паттерну: [bold]{pattern}[/] (лимит: {limit})"
    )

    if not cache_manager.is_available():
        console.print("[yellow]⚠️ Кэш недоступен.[/]")
        return

    try:
        keys = await cache_manager.keys(pattern)

        if not keys:
            console.print(f"[yellow]📭 Ключи по паттерну '{pattern}' не найдены.[/]")
            return

        # Применяем лимит
        displayed_keys = keys[:limit] if len(keys) > limit else keys

        # Создаем таблицу результатов
        table = Table(
            title=f"Результаты поиска: {pattern} ({len(displayed_keys)} из {len(keys)})"
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Ключ", style="cyan")
        table.add_column("Длина значения", justify="center", width=15)

        for i, cache_key in enumerate(displayed_keys, 1):
            try:
                value = await cache_manager.get(cache_key)
                value_length = len(str(value)) if value is not None else 0
                table.add_row(str(i), cache_key, str(value_length))
            except:
                table.add_row(str(i), cache_key, "[red]ошибка[/]")

        console.print(table)

        if len(keys) > limit:
            console.print(
                f"[dim]Показаны первые {limit} результатов из {len(keys)}. Используйте --limit для изменения количества.[/]"
            )

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при поиске ключей: {e}[/]")


async def _cache_keys_info(cache_manager):
    """Показать общую информацию о ключах кэша"""
    console.print("[cyan]Получение информации о ключах кэша...[/]")

    if not cache_manager.is_available():
        console.print("[yellow]⚠️ Кэш недоступен.[/]")
        return

    try:
        # Получаем общую информацию о кэше
        cache_info = await cache_manager.get_cache_info()

        # Создаем таблицу информации
        table = Table(title="Информация о ключах кэша")
        table.add_column("Параметр", style="cyan", width=20)
        table.add_column("Значение", style="white")

        for key, value in cache_info.items():
            if key != "type":
                display_value = str(value)
                if key == "available":
                    display_value = "[green]✓[/]" if value else "[red]✗[/]"
                table.add_row(key.replace("_", " ").title(), display_value)

        console.print(table)

        # Дополнительная статистика по типам ключей, если возможно
        try:
            all_keys = await cache_manager.keys("*")
            if all_keys:
                console.print(f"\n[dim]💡 Всего ключей в кэше: {len(all_keys)}[/]")

                # Группируем ключи по префиксам
                prefixes = {}
                for key in all_keys[:100]:  # Ограничиваем анализ первыми 100 ключами
                    prefix = key.split(":")[0] if ":" in key else "other"
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1

                if len(prefixes) > 1:
                    console.print(
                        "\n[cyan]Распределение ключей по префиксам (топ-10):[/]"
                    )
                    sorted_prefixes = sorted(
                        prefixes.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    for prefix, count in sorted_prefixes:
                        console.print(f"  {prefix}: {count}")
        except:
            pass  # Игнорируем ошибки дополнительной статистики

    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при получении информации о кэше: {e}[/]")


if __name__ == "__main__":
    cache_app()
