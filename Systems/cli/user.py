# cli_commands/user_cmd.py

import asyncio
from typing import Any, List, Optional, Tuple

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text  # Для более гибкого форматирования текста

from .utils import get_sdb_services_for_cli  # Наша утилита

console = Console()
user_app = typer.Typer(
    name="user",
    help="👤 Управление пользователями SDB и их ролями (RBAC).",
    rich_markup_mode="rich",
)

# --- Асинхронная логика команд ---


async def _list_users_cmd_async(limit: int, offset: int, sort_by: str, sort_desc: bool):
    panel_title = "[bold blue]Список пользователей SwiftDevBot[/]"
    db_m = None
    try:
        # Используем только БД, без полной конфигурации и токена
        from .utils import get_db_only_for_cli

        db_m = await get_db_only_for_cli()

        async with db_m.get_session() as session:
            from sqlalchemy import asc, desc
            from sqlalchemy import func as sql_func
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from Systems.core.database.core_models import User

            count_stmt = select(sql_func.count(User.id))
            total_users_result = await session.execute(count_stmt)
            total_users = total_users_result.scalar_one_or_none() or 0

            if total_users == 0:
                console.print(
                    Panel(
                        "[yellow]В базе данных нет зарегистрированных пользователей.[/yellow]",
                        title=panel_title,
                    )
                )
                return

            # Логика сортировки
            order_column = getattr(
                User, sort_by, User.id
            )  # Дефолт по id, если атрибут не найден
            order_expression = desc(order_column) if sort_desc else asc(order_column)

            stmt = (
                select(User)
                .options(selectinload(User.roles))
                .order_by(order_expression)
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            users: List[User] = list(result.scalars().all())

            if (
                not users and total_users > 0
            ):  # Если есть пользователи, но не на этой странице
                console.print(
                    Panel(
                        f"[yellow]На этой странице (смещение {offset}, лимит {limit}) пользователей нет, но всего в БД: {total_users}.[/yellow]",
                        title=panel_title,
                    )
                )
                return
            elif not users:  # Это условие уже покрыто выше, но для ясности
                console.print(
                    Panel(
                        "[yellow]В базе данных нет зарегистрированных пользователей.[/yellow]",
                        title=panel_title,
                    )
                )
                return

            table_title = f"Пользователи SDB (Показано: {len(users)} из {total_users}, Лимит: {limit}, Смещение: {offset}, Сортировка: {sort_by} {'DESC' if sort_desc else 'ASC'})"
            table = Table(
                title=table_title,
                show_header=True,
                header_style="bold magenta",
                expand=True,
            )
            table.add_column("DB ID", style="dim cyan", justify="right", no_wrap=True)
            table.add_column("TG ID", style="cyan", justify="right", no_wrap=True)
            table.add_column("Полное Имя", min_width=20)
            table.add_column("Username", style="yellow", no_wrap=True)
            table.add_column("Роли", min_width=15)
            table.add_column("Язык", justify="center", no_wrap=True)
            table.add_column("Активен", justify="center", no_wrap=True)
            table.add_column("Бот блок.", justify="center", no_wrap=True)
            table.add_column("Регистрация", no_wrap=True)
            table.add_column("Активность", no_wrap=True)

            for user_obj in users:
                roles_str = (
                    ", ".join(sorted([role.name for role in user_obj.roles]))
                    if user_obj.roles
                    else "-"
                )
                active_str = "✅" if user_obj.is_active else "❌"
                blocked_str = "🚫" if user_obj.is_bot_blocked else "✅"
                created_at_str = (
                    user_obj.created_at.strftime("%Y-%m-%d %H:%M")
                    if user_obj.created_at
                    else "-"
                )
                last_activity_str = (
                    user_obj.last_activity_at.strftime("%Y-%m-%d %H:%M")
                    if user_obj.last_activity_at
                    else "-"
                )

                table.add_row(
                    str(user_obj.id),
                    str(user_obj.telegram_id),
                    user_obj.full_name,
                    f"@{user_obj.username}" if user_obj.username else "-",
                    roles_str,
                    user_obj.preferred_language_code or "-",
                    active_str,
                    blocked_str,
                    created_at_str,
                    last_activity_str,
                )
            console.print(
                Panel(table, title=panel_title, border_style="blue", padding=(1, 1))
            )
    except Exception as e:
        console.print(
            f"[bold red]Ошибка выполнения команды 'user list': {type(e).__name__} - {e}[/]"
        )
        raise
    finally:
        if db_m:
            await db_m.dispose()


async def _find_user_interactive(
    session: Any, identifier: str
) -> Optional[Any]:  # User
    """Интерактивный поиск пользователя по ID или username."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from Systems.core.database.core_models import User

    user: Optional[User] = None
    if identifier.isdigit():
        user_id_int = int(identifier)
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.telegram_id == user_id_int)
        )
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            return user
        # Если не нашли по TG ID, попробуем по DB ID
        stmt_db_id = (
            select(User).options(selectinload(User.roles)).where(User.id == user_id_int)
        )
        result_db_id = await session.execute(stmt_db_id)
        user = result_db_id.scalars().first()
        if user:
            return user

    # Если не число или не найдено по ID, ищем по username (без @)
    username_to_search = identifier.lstrip("@")
    stmt_uname = (
        select(User)
        .options(selectinload(User.roles))
        .where(User.username_lower == username_to_search.lower())
    )
    # Предполагая, что у тебя есть колонка username_lower или ты используешь ILIKE для PostgreSQL/других БД
    # Для SQLite это будет WHERE lower(username) = lower(:username_to_search)
    # Чтобы это работало кросс-СУБД без ILIKE, лучше иметь отдельное поле username_lower или делать lower() в запросе
    # stmt_uname = select(User).options(selectinload(User.roles)).where(func.lower(User.username) == username_to_search.lower())
    result_uname = await session.execute(stmt_uname)
    user = result_uname.scalars().first()
    return user


async def _info_user_cmd_async(user_identifier: str):
    db_m = None
    try:
        # Используем только БД, без полной конфигурации и токена
        from .utils import get_db_only_for_cli

        db_m = await get_db_only_for_cli()

        async with db_m.get_session() as session:
            user = await _find_user_interactive(session, user_identifier)

            if not user:
                console.print(
                    f"[bold red]Ошибка: Пользователь с идентификатором '{user_identifier}' не найден в базе данных.[/]"
                )
                raise typer.Exit(code=1)

            panel_title = f"[bold blue]Информация о пользователе: {user.full_name} (TG ID: {user.telegram_id})[/]"
            info_text = Text()
            info_text.append(f"DB ID: {user.id}\n", style="bold")
            info_text.append(f"Telegram ID: {user.telegram_id}\n", style="bold")
            info_text.append(f"Полное имя: {user.full_name}\n")
            info_text.append(
                f"Username: @{user.username}\n" if user.username else "Username: -\n"
            )
            info_text.append(
                f"Язык бота: {user.preferred_language_code or '(не установлен)'}\n"
            )
            info_text.append(
                f"Активен в системе: {'Да ✅' if user.is_active else 'Нет ❌'}\n"
            )
            info_text.append(
                f"Бот заблокирован: {'Да 🚫' if user.is_bot_blocked else 'Нет ✅'}\n"
            )
            created_at_str = (
                user.created_at.strftime("%Y-%m-%d %H:%M:%S %Z")
                if user.created_at and user.created_at.tzinfo
                else (
                    user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if user.created_at
                    else "-"
                )
            )
            updated_at_str = (
                user.updated_at.strftime("%Y-%m-%d %H:%M:%S %Z")
                if user.updated_at and user.updated_at.tzinfo
                else (
                    user.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if user.updated_at
                    else "-"
                )
            )
            last_activity_str = (
                user.last_activity_at.strftime("%Y-%m-%d %H:%M:%S %Z")
                if user.last_activity_at and user.last_activity_at.tzinfo
                else (
                    user.last_activity_at.strftime("%Y-%m-%d %H:%M:%S")
                    if user.last_activity_at
                    else " (нет данных)"
                )
            )
            info_text.append(f"Дата регистрации: {created_at_str}\n")
            info_text.append(f"Последнее обновление: {updated_at_str}\n")
            info_text.append(f"Последняя активность: {last_activity_str}\n")
            roles_str = (
                ", ".join(sorted([role.name for role in user.roles]))
                if user.roles
                else " (нет назначенных ролей)"
            )
            info_text.append(f"Роли пользователя: {roles_str}\n", style="bold")

            console.print(
                Panel(info_text, title=panel_title, border_style="blue", padding=1)
            )
    finally:
        if db_m:
            await db_m.dispose()


async def _list_roles_cmd_async():
    panel_title = "[bold blue]Список всех ролей в системе SDB[/]"
    db_m, rbac_s = None, None
    try:
        # Используем только БД, без полной конфигурации и токена
        from .utils import get_db_only_for_cli

        db_m = await get_db_only_for_cli()

        # Создаем RBACService с минимальными настройками
        from Systems.core.rbac.service import RBACService

        rbac_s = RBACService(services=None, db_manager=db_m)

        async with db_m.get_session() as session:
            from Systems.core.database.core_models import \
                Role  # Role уже импортирована в RBACService

            all_roles: List[Role] = await rbac_s.get_all_roles(session)

            if not all_roles:
                console.print(
                    Panel(
                        "[yellow]В системе нет определенных ролей.[/yellow]",
                        title=panel_title,
                    )
                )
                return

            table = Table(
                title="Системные роли SDB",
                show_header=True,
                header_style="bold magenta",
                expand=True,
            )
            table.add_column("DB ID", style="dim cyan", justify="right", no_wrap=True)
            table.add_column("Имя Роли", style="cyan", min_width=15)
            table.add_column("Описание", min_width=30, max_width=70, overflow="fold")

            for role_obj in all_roles:
                table.add_row(
                    str(role_obj.id),
                    role_obj.name,
                    role_obj.description if role_obj.description else "-",
                )
            console.print(
                Panel(table, title=panel_title, border_style="blue", padding=(1, 1))
            )
    finally:
        if db_m:
            await db_m.dispose()


async def _assign_role_cmd_async(user_identifier: str, role_name: str):
    console.print(
        f"Попытка назначить роль [cyan]'{role_name}'[/] пользователю [cyan]'{user_identifier}'[/]..."
    )
    db_m, rbac_s = None, None
    try:
        # Используем только БД, без полной конфигурации и токена
        from .utils import get_db_only_for_cli

        db_m = await get_db_only_for_cli()

        # Создаем RBACService с минимальными настройками
        from Systems.core.rbac.service import RBACService

        rbac_s = RBACService(services=None, db_manager=db_m)

        async with db_m.get_session() as session:
            user_obj = await _find_user_interactive(session, user_identifier)
            if not user_obj:
                console.print(
                    f"[bold red]Ошибка: Пользователь '{user_identifier}' не найден.[/]"
                )
                raise typer.Exit(code=1)

            if await rbac_s.assign_role_to_user(session, user_obj, role_name):
                await session.commit()
                console.print(
                    f"[bold green]Роль '{role_name}' успешно назначена пользователю {user_obj.telegram_id} (@{user_obj.username}).[/]"
                )
            else:
                # RBACService должен был залогировать детали
                console.print(
                    f"[bold red]Не удалось назначить роль '{role_name}' пользователю {user_obj.telegram_id}. "
                    "Возможно, роль не существует или уже назначена (см. логи).[/]"
                )
                # Не будем делать rollback здесь, так как assign_role_to_user мог добавить роль в сессию, но не UserRole
                raise typer.Exit(code=1)
    finally:
        if db_m:
            await db_m.dispose()


async def _remove_role_cmd_async(user_identifier: str, role_name: str):
    console.print(
        f"Попытка снять роль [cyan]'{role_name}'[/] с пользователя [cyan]'{user_identifier}'[/]..."
    )
    db_m, rbac_s = None, None
    try:
        # Используем только БД, без полной конфигурации и токена
        from .utils import get_db_only_for_cli

        db_m = await get_db_only_for_cli()

        # Создаем RBACService с минимальными настройками
        from Systems.core.rbac.service import RBACService

        rbac_s = RBACService(services=None, db_manager=db_m)

        async with db_m.get_session() as session:
            user_obj = await _find_user_interactive(session, user_identifier)
            if not user_obj:
                console.print(
                    f"[bold red]Ошибка: Пользователь '{user_identifier}' не найден.[/]"
                )
                raise typer.Exit(code=1)

            if await rbac_s.remove_role_from_user(session, user_obj, role_name):
                await session.commit()
                console.print(
                    f"[bold green]Роль '{role_name}' успешно снята с пользователя {user_obj.telegram_id} (@{user_obj.username}).[/]"
                )
            else:
                console.print(
                    f"[bold red]Не удалось снять роль '{role_name}' с пользователя {user_obj.telegram_id}. "
                    "Возможно, роль не была назначена (см. логи).[/]"
                )
                raise typer.Exit(code=1)
    finally:
        if db_m:
            await db_m.dispose()


async def _block_user_cmd_async(user_identifier: str, reason: str):
    console.print(f"Попытка заблокировать пользователя [cyan]'{user_identifier}'[/]...")
    if reason:
        console.print(f"Причина блокировки: [yellow]{reason}[/]")

    db_m, core_settings = None, None
    try:
        # Используем БД + минимальные core настройки для проверки super_admins
        from .utils import get_db_with_core_config_for_cli

        db_m, core_settings = await get_db_with_core_config_for_cli()

        async with db_m.get_session() as session:
            user_obj = await _find_user_interactive(session, user_identifier)
            if not user_obj:
                console.print(
                    f"[bold red]Ошибка: Пользователь '{user_identifier}' не найден.[/]"
                )
                raise typer.Exit(code=1)

            if user_obj.telegram_id in core_settings.super_admins:
                console.print(
                    f"[bold red]Ошибка: Нельзя заблокировать Владельца системы![/]"
                )
                raise typer.Exit(code=1)

            if user_obj.is_bot_blocked:
                console.print(
                    f"[bold yellow]Пользователь {user_obj.telegram_id} уже заблокирован.[/]"
                )
                return

            from Systems.core.users.service import UserService

            user_service = UserService(
                services_provider=None
            )  # Создаем без services_provider для простоты

            if await user_service.set_user_bot_blocked_status(user_obj, True, session):
                await session.commit()
                console.print(
                    f"[bold green]Пользователь {user_obj.telegram_id} (@{user_obj.username or 'без username'}) успешно заблокирован.[/]"
                )
                if reason:
                    console.print(f"Причина: [yellow]{reason}[/]")
            else:
                console.print(
                    f"[bold red]Не удалось заблокировать пользователя {user_obj.telegram_id}.[/]"
                )
                raise typer.Exit(code=1)
    finally:
        if db_m:
            await db_m.dispose()


async def _unblock_user_cmd_async(user_identifier: str):
    console.print(
        f"Попытка разблокировать пользователя [cyan]'{user_identifier}'[/]..."
    )
    db_m = None
    try:
        # Используем только БД, без полной конфигурации и токена
        from .utils import get_db_only_for_cli

        db_m = await get_db_only_for_cli()

        async with db_m.get_session() as session:
            user_obj = await _find_user_interactive(session, user_identifier)
            if not user_obj:
                console.print(
                    f"[bold red]Ошибка: Пользователь '{user_identifier}' не найден.[/]"
                )
                raise typer.Exit(code=1)

            if not user_obj.is_bot_blocked:
                console.print(
                    f"[bold yellow]Пользователь {user_obj.telegram_id} не заблокирован.[/]"
                )
                return

            from Systems.core.users.service import UserService

            user_service = UserService(
                services_provider=None
            )  # Создаем без services_provider для простоты

            if await user_service.set_user_bot_blocked_status(user_obj, False, session):
                await session.commit()
                console.print(
                    f"[bold green]Пользователь {user_obj.telegram_id} (@{user_obj.username or 'без username'}) успешно разблокирован.[/]"
                )
            else:
                console.print(
                    f"[bold red]Не удалось разблокировать пользователя {user_obj.telegram_id}.[/]"
                )
                raise typer.Exit(code=1)
    finally:
        if db_m:
            await db_m.dispose()


# --- Синхронные обертки для Typer ---


@user_app.command(
    name="list", help="Показать список всех пользователей SDB из базы данных."
)
def list_users_cmd_wrapper(
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Максимальное количество пользователей для отображения.",
        min=1,
        max=200,
    ),
    offset: int = typer.Option(
        0, "--offset", "-o", help="Смещение для пагинации списка пользователей.", min=0
    ),
    sort_by: str = typer.Option(
        "id",
        "--sort-by",
        help="Поле для сортировки (id, telegram_id, username, first_name, last_name, created_at, last_activity_at).",
        case_sensitive=False,
    ),
    desc: bool = typer.Option(False, "--desc", help="Сортировать по убыванию."),
):
    valid_sort_fields = [
        "id",
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "created_at",
        "last_activity_at",
    ]
    if sort_by.lower() not in valid_sort_fields:
        console.print(
            f"[bold red]Ошибка: Недопустимое значение для --sort-by: '{sort_by}'.[/]"
        )
        console.print(f"Допустимые значения: {', '.join(valid_sort_fields)}")
        raise typer.Exit(code=1)
    try:
        asyncio.run(
            _list_users_cmd_async(
                limit=limit, offset=offset, sort_by=sort_by.lower(), sort_desc=desc
            )
        )
    except Exception as e:
        console.print(
            f"[bold red]Ошибка выполнения команды 'user list': {type(e).__name__} - {e}[/]"
        )
        # console.print_exception(show_locals=True) # для отладки
        raise typer.Exit(code=1)


@user_app.command(
    name="info",
    help="Показать детальную информацию о пользователе по его Telegram ID, DB ID или Username.",
)
def info_user_cmd_wrapper(
    user_identifier: str = typer.Argument(
        ..., help="Telegram ID, DB ID или Username (@ник) пользователя."
    )
):
    try:
        asyncio.run(_info_user_cmd_async(user_identifier=user_identifier))
    except typer.Exit:  # Пробрасываем Exit, если пользователь не найден
        raise
    except Exception as e:
        console.print(
            f"[bold red]Ошибка выполнения команды 'user info': {type(e).__name__} - {e}[/]"
        )
        raise typer.Exit(code=1)


@user_app.command(name="roles", help="Показать список всех доступных ролей в системе.")
def list_roles_cmd_wrapper():
    try:
        asyncio.run(_list_roles_cmd_async())
    except Exception as e:
        console.print(
            f"[bold red]Ошибка выполнения команды 'user roles': {type(e).__name__} - {e}[/]"
        )
        raise typer.Exit(code=1)


@user_app.command(name="assign-role", help="Назначить роль пользователю.")
def assign_role_cmd_wrapper(
    user_identifier: str = typer.Argument(
        ..., help="Telegram ID, DB ID или Username (@ник) пользователя."
    ),
    role_name: str = typer.Argument(
        ..., help="Имя роли для назначения (например, 'Admin', 'User')."
    ),
):
    try:
        asyncio.run(
            _assign_role_cmd_async(user_identifier=user_identifier, role_name=role_name)
        )
    except typer.Exit:
        raise
    except Exception as e:
        # Сообщение об ошибке уже должно быть в _assign_role_cmd_async
        raise typer.Exit(code=1)


@user_app.command(name="remove-role", help="Снять роль с пользователя.")
@user_app.command(name="block", help="Заблокировать пользователя в системе.")
@user_app.command(name="unblock", help="Разблокировать пользователя в системе.")
def remove_role_cmd_wrapper(
    user_identifier: str = typer.Argument(
        ..., help="Telegram ID, DB ID или Username (@ник) пользователя."
    ),
    role_name: str = typer.Argument(..., help="Имя роли для снятия."),
):
    try:
        asyncio.run(
            _remove_role_cmd_async(user_identifier=user_identifier, role_name=role_name)
        )
    except typer.Exit:
        raise
    except Exception as e:
        raise typer.Exit(code=1)


@user_app.command(name="block", help="Заблокировать пользователя в системе.")
def block_user_cmd_wrapper(
    user_identifier: str = typer.Argument(
        ..., help="Telegram ID, DB ID или Username (@ник) пользователя."
    ),
    reason: str = typer.Option(
        "", "--reason", "-r", help="Причина блокировки (опционально)."
    ),
):
    try:
        asyncio.run(
            _block_user_cmd_async(user_identifier=user_identifier, reason=reason)
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка: {e}[/bold red]")
        raise typer.Exit(code=1)


@user_app.command(name="unblock", help="Разблокировать пользователя в системе.")
def unblock_user_cmd_wrapper(
    user_identifier: str = typer.Argument(
        ..., help="Telegram ID, DB ID или Username (@ник) пользователя."
    )
):
    try:
        asyncio.run(_unblock_user_cmd_async(user_identifier=user_identifier))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка: {e}[/bold red]")
        raise typer.Exit(code=1)
