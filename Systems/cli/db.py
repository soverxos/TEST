# cli_commands/db_cmd.py

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()

db_app = typer.Typer(
    name="db",
    help="🗄️ Управление базой данных и миграциями Alembic.",
    rich_markup_mode="rich",
)

# Корень проекта определяется относительно текущего файла (__file__)
# Systems/cli/db.py -> Systems/cli/ -> Systems/ -> PROJECT_ROOT
PROJECT_ROOT_FROM_DB_CMD = Path(__file__).resolve().parent.parent.parent
ALEMBIC_INI_PATH_STR = str(PROJECT_ROOT_FROM_DB_CMD / "alembic.ini")


def _run_alembic_command(
    args: list[str], suppress_success_output: bool = False
) -> bool:
    try:
        alembic_ini_actual_path = Path(ALEMBIC_INI_PATH_STR)
        if not alembic_ini_actual_path.is_file():
            console.print(
                f"[bold red]Ошибка: Файл конфигурации Alembic '{ALEMBIC_INI_PATH_STR}' не найден.[/]"
            )
            console.print(
                f"  Убедитесь, что команда выполняется из корня проекта или путь к alembic.ini корректен."
            )
            return False

        command = ["alembic", "-c", ALEMBIC_INI_PATH_STR] + args

        env = os.environ.copy()
        # Добавляем корень проекта в PYTHONPATH, чтобы Alembic мог найти core и Modules
        # Это важно, так как env.py импортирует компоненты SDB
        existing_python_path = env.get("PYTHONPATH", "")
        project_root_str = str(PROJECT_ROOT_FROM_DB_CMD)

        if existing_python_path:
            # Убедимся, что project_root_str не дублируется, если он уже есть
            path_parts = existing_python_path.split(os.pathsep)
            if project_root_str not in path_parts:
                env["PYTHONPATH"] = (
                    f"{project_root_str}{os.pathsep}{existing_python_path}"
                )
            else:  # Уже есть, не добавляем
                env["PYTHONPATH"] = existing_python_path
        else:
            env["PYTHONPATH"] = project_root_str

        # Дополнительно убедимся, что sys.path передан в окружение, если это необходимо
        # (Обычно PYTHONPATH достаточно)
        # current_sys_path_str = os.pathsep.join(s.strip() for s in sys.path if s.strip())
        # env["PYTHONPATH"] = f"{current_sys_path_str}{os.pathsep}{env.get('PYTHONPATH', '')}"

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=str(PROJECT_ROOT_FROM_DB_CMD),  # Запускаем из корня проекта
        )

        if process.stdout and not (process.returncode == 0 and suppress_success_output):
            console.print(process.stdout.strip())

        if process.stderr:
            is_actual_error_in_stderr = (
                "error" in process.stderr.lower()
                or "fail" in process.stderr.lower()
                or "traceback" in process.stderr.lower()
                or "critical" in process.stderr.lower()
            )

            if process.returncode != 0 or is_actual_error_in_stderr:
                console.print(f"[bold red]Alembic STDERR:[/]\n{process.stderr.strip()}")
            elif not (process.returncode == 0 and suppress_success_output):
                console.print(
                    f"[dim yellow]Alembic STDERR (info/warnings):[/]\n{process.stderr.strip()}"
                )

        if process.returncode != 0:
            console.print(
                f"[bold red]Команда Alembic завершилась с ошибкой (код: {process.returncode}). Проверьте вывод выше.[/]"
            )
            return False
        return True

    except FileNotFoundError:
        console.print(f"[bold red]Ошибка: Команда 'alembic' не найдена.[/]")
        console.print(
            "Убедитесь, что Alembic установлен в вашем виртуальном окружении и доступен в системном PATH."
        )
        console.print(f"Попробуйте: [cyan]pip install alembic[/]")
        return False
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка при выполнении команды Alembic: {e}[/]"
        )
        return False


@db_app.command(
    name="upgrade",
    help="Применить миграции Alembic (по умолчанию до 'head', т.е. последней).",
)
def db_upgrade_cmd(
    revision: str = typer.Argument(
        "head",
        help="ID ревизии для обновления (например, 'head', 'base', specific_id, '+1', '-2').",
    )
):
    console.print(
        f"Запуск применения миграций Alembic до ревизии: [cyan]{revision}[/]..."
    )
    if not _run_alembic_command(["upgrade", revision]):
        raise typer.Exit(code=1)
    console.print(f"[bold green]Команда 'db upgrade {revision}' успешно выполнена.[/]")


@db_app.command(name="downgrade", help="Откатить миграции Alembic.")
def db_downgrade_cmd(
    revision: str = typer.Argument(
        "1",
        help="ID ревизии для отката (например, 'base', specific_id) или количество ревизий для отката (например, '1' для отката последней, '2' для двух последних). Для отката на одну ревизию можно также указать '-1'.",
    )
):
    target_revision = revision
    if revision.isdigit():
        target_revision = f"-{revision}"
        description_log = f"на {revision} ревизию(и) назад (до {target_revision})"
    else:
        description_log = f"до ревизии '{revision}'"

    console.print(f"Запуск отката миграций Alembic {description_log}...")
    if typer.confirm(
        f"Вы [bold red]УВЕРЕНЫ[/], что хотите откатить миграции {description_log}? Это может привести к потере данных.",
        abort=True,
    ):
        if not _run_alembic_command(["downgrade", revision]):
            raise typer.Exit(code=1)
        console.print(
            f"[bold green]Команда 'db downgrade {revision}' успешно выполнена.[/]"
        )


@db_app.command(name="revision", help="Создать новый файл миграции Alembic.")
def db_revision_cmd(
    message: str = typer.Option(
        ...,
        "-m",
        "--message",
        help="Краткое описание изменений для новой ревизии (обязательно).",
    ),
    autogenerate: bool = typer.Option(
        True,
        "--autogenerate/--no-autogenerate",
        help="Попытаться автоматически определить изменения в моделях (рекомендуется).",
    ),
):
    args = ["revision"]
    if autogenerate:
        args.append("--autogenerate")
    args.extend(["-m", message])

    console.print(
        f"Создание новой ревизии Alembic с сообщением: '[cyan]{message}[/]' (autogenerate: {autogenerate})..."
    )
    if not _run_alembic_command(args):
        raise typer.Exit(code=1)
    console.print(
        f"[bold green]Команда 'db revision' успешно выполнена. Новый файл миграции должен быть создан в 'alembic_migrations/versions/'.[/]"
    )


@db_app.command(name="status", help="Показать текущий статус миграций и историю.")
def db_status_cmd(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Показать более детальный вывод."
    )
):
    """
    Показать статус миграций Alembic.
    Не требует BOT_TOKEN - Alembic сам загрузит настройки БД через env.py когда нужно.
    """
    console.print(
        Panel(
            "[bold blue]Текущий статус миграций Alembic (команда 'current')[/]",
            expand=False,
            border_style="blue",
        )
    )
    current_args = ["current"]
    if verbose:
        current_args.append("--verbose")

    success_current = _run_alembic_command(
        current_args, suppress_success_output=verbose
    )
    if not success_current:
        console.print(
            "[yellow]Не удалось получить текущий статус Alembic (Alembic current).[/yellow]"
        )

    console.print(
        Panel(
            "[bold blue]История миграций Alembic (команда 'history')[/]",
            expand=False,
            border_style="blue",
            style="blue",
        )
    )
    history_args = ["history"]
    if not _run_alembic_command(history_args):
        console.print(
            "[yellow]Не удалось получить историю миграций Alembic (Alembic history).[/yellow]"
        )


@db_app.command(
    name="init-core",
    help="[ОПАСНО] Создать таблицы ядра и дефолтные роли напрямую, минуя Alembic.",
)
def db_init_core_cmd():
    console.print(
        Panel(
            "[bold yellow]Инициализация таблиц ядра SDB и стандартных ролей напрямую[/]",
            expand=False,
            border_style="yellow",
        )
    )
    console.print(
        "[bold red]ПРЕДУПРЕЖДЕНИЕ:[/bold red] Эта команда создаст таблицы ядра и роли напрямую, игнорируя Alembic."
    )
    if typer.confirm(
        "Вы уверены, что хотите создать таблицы ядра и стандартные роли напрямую?",
        abort=True,
    ):
        try:
            from Systems.core.app_settings import load_app_settings
            from Systems.core.database.manager import DBManager
            from Systems.core.rbac.service import RBACService
            from Systems.core.services_provider import BotServicesProvider
            from Systems.core.module_loader import ModuleLoader

            settings = load_app_settings()

            async def _init_core_data_task_runner():
                nonlocal settings
                console.print(
                    f"Используется БД: {settings.db.type} (URL строится на основе настроек)."
                )
                db_m = DBManager(db_settings=settings.db, app_settings=settings)
                try:
                    await db_m.initialize()

                    console.print(
                        "Вызов DBManager.create_all_core_tables() для создания таблиц ядра..."
                    )
                    await db_m.create_all_core_tables()
                    console.print(
                        "[bold green]Таблицы ядра успешно созданы (или уже существовали).[/]"
                    )

                    console.print("Попытка создания стандартных ролей и разрешений...")
                    # Создаем минимальный BotServicesProvider для RBACService
                    # (нужен для регистрации разрешений модулей)
                    services = BotServicesProvider(settings=settings)
                    services._db_manager = db_m
                    
                    # Инициализируем ModuleLoader для регистрации разрешений модулей
                    module_loader = ModuleLoader(settings=settings, services_provider=services)
                    module_loader.scan_all_available_modules()
                    services._module_loader = module_loader
                    
                    rbac_s = RBACService(services=services)
                    async with db_m.get_session() as session:
                        roles_count, core_perms_count, mod_perms_count = await rbac_s.ensure_default_entities_exist(session)
                        await session.commit()
                        
                        if roles_count > 0 or core_perms_count > 0 or mod_perms_count > 0:
                            console.print(
                                f"[bold green]Успешно создано: {roles_count} ролей, {core_perms_count} разрешений ядра, {mod_perms_count} разрешений модулей.[/bold green]"
                            )
                        else:
                            console.print(
                                "[dim]Стандартные роли и разрешения уже существовали или не были созданы (проверьте логи RBACService).[/dim]"
                            )
                except Exception as e_task:
                    console.print(
                        f"[bold red]Ошибка во время выполнения задачи инициализации: {e_task}[/]"
                    )
                    import traceback
                    console.print(f"[dim]{traceback.format_exc()}[/]")
                    raise
                finally:
                    await db_m.dispose()

            asyncio.run(_init_core_data_task_runner())
            console.print("\n[bold green]Команда 'db init-core' успешно завершена.[/]")
            console.print(
                "[yellow]ВАЖНО: Если вы использовали Alembic ранее, состояние миграций может быть некорректным.[/]"
            )
            console.print(
                "  [yellow]Возможно, потребуется выполнить 'sdb db stamp head', чтобы синхронизировать Alembic с текущей схемой БД.[/]"
            )
            console.print(
                "  [yellow]Делайте это, только если вы уверены, что текущая схема БД является целевой 'головой'.[/]"
            )

        except ImportError as e_imp:
            console.print(
                f"[bold red]Ошибка импорта: Не удалось загрузить компоненты ядра для 'db init-core': {e_imp}[/]"
            )
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red]Ошибка при выполнении 'db init-core': {e}[/]")
            raise typer.Exit(code=1)


@db_app.command(
    name="stamp", help="Установить текущую ревизию Alembic в БД, не применяя миграции."
)
def db_stamp_cmd(
    revision: str = typer.Argument(
        ..., help="ID ревизии для установки (например, 'head', 'base', specific_id)."
    ),
    purge: bool = typer.Option(
        False,
        "--purge",
        help="Очистить таблицу версий Alembic перед установкой новой ревизии (используйте с осторожностью!).",
    ),
):
    console.print(
        f"Установка ревизии Alembic: [cyan]{revision}[/]"
        + ("[bold yellow] с очисткой таблицы версий[/]" if purge else "")
    )
    if purge:
        if not typer.confirm(
            f"[bold red]ВНИМАНИЕ: Опция --purge УДАЛИТ ВСЕ ЗАПИСИ из таблицы версий Alembic перед установкой ревизии '{revision}'. Это может привести к потере истории миграций в БД. Продолжить?",
            abort=True,
        ):
            return

    args = ["stamp"]
    if purge:
        args.append("--purge")
    args.append(revision)

    if not _run_alembic_command(args):
        raise typer.Exit(code=1)
    console.print(
        f"[bold green]Команда 'db stamp {revision}{' --purge' if purge else ''}' успешно выполнена.[/]"
    )
