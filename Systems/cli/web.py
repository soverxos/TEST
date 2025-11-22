# cli/web.py
"""
CLI команды для управления веб-панелью.
"""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()

web_app = typer.Typer(
    name="web",
    help="🌐 Управление веб-панелью SwiftDevBot",
    rich_markup_mode="rich",
)


@web_app.command(name="start", help="Запустить веб-панель.")
def web_start_cmd(
    host: str = typer.Option(None, "--host", "-h", help="Хост для веб-панели (переопределяет SDB_WEB_HOST)"),
    port: int = typer.Option(None, "--port", "-p", help="Порт для веб-панели (переопределяет SDB_WEB_PORT)"),
    reload: bool = typer.Option(None, "--reload/--no-reload", help="Автоперезагрузка при изменениях (переопределяет SDB_WEB_RELOAD)"),
    workers: int = typer.Option(None, "--workers", "-w", help="Количество воркеров (переопределяет SDB_WEB_WORKERS)"),
):
    """
    Запустить веб-панель SwiftDevBot.
    
    Все параметры можно настроить в .env файле:
    - SDB_WEB_HOST - хост (по умолчанию: 127.0.0.1)
    - SDB_WEB_PORT - порт (по умолчанию: 8000)
    - SDB_WEB_RELOAD - автоперезагрузка true/false (по умолчанию: false)
    - SDB_WEB_WORKERS - количество воркеров (по умолчанию: 1)
    
    Параметры командной строки имеют приоритет над переменными окружения.
    """
    # Загружаем переменные окружения, если параметры не указаны
    import os
    from dotenv import load_dotenv
    load_dotenv('.env')
    
    # Хост: параметр > переменная окружения > значение по умолчанию
    if host is None:
        host = os.environ.get("SDB_WEB_HOST", "127.0.0.1")
    
    # Порт: параметр > переменная окружения > значение по умолчанию
    if port is None:
        port = int(os.environ.get("SDB_WEB_PORT", "8000"))
    
    # Reload: параметр > переменная окружения > значение по умолчанию
    if reload is None:
        reload_str = os.environ.get("SDB_WEB_RELOAD", "false").lower()
        reload = reload_str in ("true", "1", "yes", "on")
    
    # Workers: параметр > переменная окружения > значение по умолчанию
    if workers is None:
        workers = int(os.environ.get("SDB_WEB_WORKERS", "1"))
    
    try:
        asyncio.run(_web_start_async(host, port, reload, workers))
    except KeyboardInterrupt:
        console.print("\n[yellow]Остановка веб-панели...[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Ошибка запуска веб-панели:[/] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")
        raise typer.Exit(code=1)


async def _web_start_async(host: str, port: int, reload: bool, workers: int):
    """Асинхронный запуск веб-панели."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[bold red]uvicorn не установлен![/]\n"
            "[yellow]Установите его командой:[/] pip install uvicorn[standard]"
        )
        raise typer.Exit(code=1)
    
    console.print(
        Panel(
            f"[bold cyan]🌐 ЗАПУСК ВЕБ-ПАНЕЛИ SWIFTDEVBOT[/]\n\n"
            f"[cyan]Хост:[/] {host}\n"
            f"[cyan]Порт:[/] {port}\n"
            f"[cyan]Режим:[/] {'Development' if reload else 'Production'}\n"
            f"[cyan]Воркеры:[/] {workers}",
            expand=False,
            border_style="cyan",
        )
    )
    
    # Импортируем create_app из web.app
    try:
        from Systems.web.app import create_app
        from Systems.core.services_provider import BotServicesProvider
        from Systems.core.app_settings import load_app_settings
        
        # Загружаем настройки SDB
        settings = load_app_settings()
        
        # Создаем сервисы (только для веб-панели, без полной инициализации бота)
        services = BotServicesProvider(settings=settings)
        
        # Инициализируем сервисы перед созданием приложения
        try:
            await services.setup_services()
            console.print("[green]✅ Сервисы SDB инициализированы[/]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Предупреждение при инициализации сервисов:[/] {e}")
            # Продолжаем работу даже если сервисы не полностью инициализированы
        
        # Создаем приложение
        app = create_app(sdb_services=services, debug=reload)
    except ImportError as e:
        console.print(f"[bold red]Ошибка импорта веб-приложения:[/] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Ошибка при создании приложения:[/] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")
        raise typer.Exit(code=1)
    
    # Запускаем uvicorn
    try:
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,  # reload не поддерживает workers
            log_level="info",
        )
        server = uvicorn.Server(config)
        console.print(f"\n[bold green]✅ Веб-панель запущена![/]")
        console.print(f"[cyan]Откройте в браузере:[/] http://{host}:{port}")
        await server.serve()
    except Exception as e:
        console.print(f"[bold red]Ошибка запуска сервера:[/] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")
        raise typer.Exit(code=1)


@web_app.command(name="status", help="Показать статус веб-панели.")
def web_status_cmd():
    """Показать статус веб-панели."""
    import os
    from dotenv import load_dotenv
    import socket
    
    load_dotenv('.env')
    
    # Получаем настройки из переменных окружения
    host = os.environ.get("SDB_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("SDB_WEB_PORT", "8000"))
    
    console.print(Panel("[bold cyan]СТАТУС ВЕБ-ПАНЕЛИ[/]", expand=False, border_style="cyan"))
    console.print(f"[dim]Проверка на {host}:{port}[/]")
    
    # Проверяем, запущен ли сервер
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port))
        sock.close()
        
        if result == 0:
            console.print("[green]✅ Веб-панель запущена[/]")
            display_host = host if host != "0.0.0.0" else "localhost"
            console.print(f"[cyan]URL:[/] http://{display_host}:{port}")
        else:
            console.print("[yellow]⚠️ Веб-панель не запущена[/]")
            console.print(f"[dim]Ожидаемый адрес: {host}:{port}[/]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Не удалось проверить статус: {e}[/]")


if __name__ == "__main__":
    web_app()

