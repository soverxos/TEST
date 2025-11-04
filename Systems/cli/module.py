import asyncio
import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from Systems.core.database.base import Base as SDBBaseAlchemyModel

from .utils import confirm_action, get_sdb_services_for_cli

console = Console()
module_app = typer.Typer(
    name="module",
    help="🧩 Управление модулями (плагинами) SwiftDevBot.",
    rich_markup_mode="rich",
)


async def _get_module_loader_instance_async() -> Optional[Any]:
    settings_obj, _, _ = await get_sdb_services_for_cli(init_db=False, init_rbac=False)
    if not settings_obj:
        console.print(
            "[bold red]Ошибка: Не удалось загрузить настройки SDB для ModuleLoader (из CLI).[/]"
        )
        return None
    try:
        from Systems.core.module_loader import ModuleLoader
        from Systems.core.services_provider import BotServicesProvider

        # Создаем временный BotServicesProvider только для ModuleLoader,
        # так как полная инициализация сервисов здесь не нужна и может быть долгой.
        # ModuleLoader в основном использует settings и самого себя (для логирования через services.logger).
        # Это не идеальный вариант, но для CLI команд, где нам нужен только ModuleLoader, это может быть приемлемо.
        # Либо ModuleLoader должен быть переделан, чтобы не требовать полного BSP для таких операций.
        # Пока оставим так, но с комментарием.
        temp_bsp = BotServicesProvider(settings=settings_obj)
        # Не вызываем temp_bsp.setup_services(), так как это для рантайма бота.
        # ModuleLoader должен уметь работать с settings и логгером.

        loader = ModuleLoader(
            settings=settings_obj, services_provider=temp_bsp
        )  # Передаем temp_bsp

        # ИЗМЕНЕНО ЗДЕСЬ
        if hasattr(loader, "scan_all_available_modules"):
            loader.scan_all_available_modules()
        else:
            console.print(
                "[bold red]Критическая ошибка: Метод 'scan_all_available_modules' не найден в ModuleLoader.[/]"
            )
            return None

        if hasattr(loader, "_load_enabled_plugin_names"):
            getattr(loader, "_load_enabled_plugin_names")()
        else:
            console.print(
                "[yellow]Предупреждение: Метод '_load_enabled_plugin_names' не найден в ModuleLoader при вызове из CLI.[/yellow]"
            )

        return loader
    except ImportError as e_imp:
        console.print(
            f"[bold red]Ошибка импорта компонентов ядра SDB для ModuleLoader (из CLI): {e_imp}[/]"
        )
        return None
    except Exception as e_load:
        console.print(
            f"[bold red]Ошибка при инициализации ModuleLoader (из CLI): {e_load}[/]"
        )
        console.print_exception(show_locals=False)  # Добавим вывод трейсбека
        return None


def _get_module_loader_sync() -> Optional[Any]:
    try:
        return asyncio.run(_get_module_loader_instance_async())
    except Exception as e:
        # Лог ошибки уже должен быть в _get_module_loader_instance_async
        # console.print(f"[bold red]Не удалось получить ModuleLoader синхронно: {e}[/]")
        return None


def _save_enabled_modules(module_names: List[str], config_path: Path) -> bool:
    try:
        # Убедимся, что сохраняем только уникальные имена
        unique_module_names = sorted(
            list(set(name.strip() for name in module_names if name.strip()))
        )
        data_to_save = {
            "active_modules": unique_module_names,
            "disabled_modules": [],
        }  # disabled_modules пока не используется активно

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        console.print(
            f"[bold red]Ошибка сохранения списка активных модулей в {config_path}: {e}[/]"
        )
        return False


@module_app.command(name="create", help="Создать шаблон нового модуля.")
def create_module_cmd(
    name: str = typer.Argument(
        ..., help="Имя нового модуля (без пробелов, только буквы, цифры, '_')."
    ),
    template: str = typer.Option(
        "demo", "--template", "-t", help="Шаблон: demo (по умолчанию) или universal"
    ),
    enable: bool = typer.Option(
        False, "--enable/--no-enable", help="Сразу добавить модуль в enabled_modules.json"
    ),
    with_rbac: bool = typer.Option(
        False, "--with-rbac/--no-with-rbac", help="Включить пример RBAC-проверок в демо"
    ),
    with_db: bool = typer.Option(
        False, "--with-db/--no-with-db", help="Включить пример БД (только файлы, без вызовов)"
    ),
):
    """Создаёт шаблон нового модуля."""
    from loguru import \
        logger  # Локальный импорт, чтобы не конфликтовать с rich

    # Проверяем валидность имени
    if not name.isidentifier():
        console.print(
            f"[bold red]Ошибка: Имя модуля '{name}' недопустимо. Используйте буквы, цифры и '_', без пробелов.[/]"
        )
        raise typer.Exit(code=1)

    module_dir = Path("modules") / name
    if module_dir.exists():
        console.print(
            f"[bold red]Ошибка: Модуль '{name}' уже существует в {module_dir}.[/]"
        )
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold cyan]Создание модуля: {name}[/]", expand=False, border_style="cyan"
        )
    )
    try:
        # Ветка: универсальный шаблон (копия из UNIVERSAL_MODULE_TEMPLATE)
        if template.lower() == "universal":
            template_dir = Path("modules") / "UNIVERSAL_MODULE_TEMPLATE"
            if not template_dir.exists():
                console.print(f"[bold red]Универсальный шаблон не найден: {template_dir}[/]")
                raise typer.Exit(code=1)

            import shutil as _shutil
            _shutil.copytree(template_dir, module_dir)

            # Обновим manifest.yaml (name/display_name)
            try:
                import yaml as _yaml
                manifest_path = module_dir / "manifest.yaml"
                if manifest_path.exists():
                    data = _yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                    data["name"] = name
                    data["display_name"] = name.replace('_', ' ').title()
                    manifest_path.write_text(
                        _yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                        encoding="utf-8",
                    )
            except Exception:
                pass

            console.print(f"[green]Скопирован универсальный шаблон в: {module_dir}[/]")
        else:
            # Ветка: легкий DEMO-шаблон
            module_dir.mkdir(parents=True)

        # Создаём manifest.yaml
        manifest_content = f"""\
name: "{name}"
display_name: "{name.replace('_', ' ').title()}"
version: "1.0.0"
description: "Модуль {name.replace('_', ' ').title()} для SwiftDevBot"
author: "SwiftDevBot Team"

python_requirements: []
sdb_module_dependencies: []

model_definitions: []

commands:
  - command: "{name}"
    description: "{name.replace('_', ' ').title()}"
    icon: "🔧"
    category: "Общие"
    admin_only: false

permissions:
  - name: "{name}.view"
    description: "Просмотр модуля {name.replace('_', ' ').title()}"
  - name: "{name}.use"
    description: "Использование модуля {name.replace('_', ' ').title()}"
  - name: "{name}.admin"
    description: "[АДМИН] Административный доступ к модулю {name.replace('_', ' ').title()}"
"""
        (module_dir / "manifest.yaml").write_text(manifest_content, encoding="utf-8")
        console.print(f"[green]Создан файл: {module_dir / 'manifest.yaml'}[/]")

        # Создаём __init__.py
        init_content = f'''\
"""
Модуль {name.replace('_', ' ').title()} для SwiftDevBot

Описание функциональности модуля.
"""

from aiogram import Router, Dispatcher, Bot
from Systems.core.services_provider import BotServicesProvider
from .handlers import router as {name}_router

router = Router(name="{name}")
router.include_router({name}_router)


async def setup_module(dp: Dispatcher, bot: Bot, services: BotServicesProvider):
    """Настройка модуля"""
    dp.include_router(router)
    
    services.ui_registry.register_module_entry(
        module_name="{name}",
        display_name="{name.replace('_', ' ').title()}",
        entry_callback_data="module_{name}",
        description="Модуль {name.replace('_', ' ').title()}",
        icon="🔧",
        required_permission_to_view="{name}.view",
    )


__version__ = "1.0.0"
__author__ = "SwiftDevBot Team"
'''
        (module_dir / "__init__.py").write_text(init_content, encoding="utf-8")
        console.print(f"[green]Создан файл: {module_dir / '__init__.py'}[/]")

        # Создаём handlers.py (демо обработчики без RBAC по умолчанию)
        if template.lower() == "demo":
            # DEMO: без RBAC, с клавиатурой и callback'ами
            handlers_content = f'''\
"""
Обработчики модуля {name.replace('_', ' ').title()}
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from Systems.core.services_provider import BotServicesProvider
from .keyboards import main_{name}_keyboard
from .callback_data import {name.title().replace('_', '')}CB

# Создаем роутер модуля
router = Router(name="{name}")

@router.message(Command("{name}"))
async def cmd_{name}(message: Message, services: BotServicesProvider):
    """Команда /{name} - главная команда модуля"""
    await message.answer(
        f"🔧 <b>{name.replace('_', ' ').title()}</b>\\n\\n"
        f"Это демо команды. Ниже — пример клавиатуры:",
        parse_mode="HTML",
        reply_markup=main_{name}_keyboard(),
    )


@router.callback_query({name.title().replace('_', '')}CB.filter(F.action == "function1"))
async def on_function1(cb: CallbackQuery):
    await cb.message.answer("✅ Функция 1 выполнена")
    await cb.answer()


@router.callback_query({name.title().replace('_', '')}CB.filter(F.action == "function2"))
async def on_function2(cb: CallbackQuery):
    await cb.message.answer("⚙️ Функция 2: пример ответа")
    await cb.answer()


@router.callback_query({name.title().replace('_', '')}CB.filter(F.action == "close"))
async def on_close(cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:
        # Если нельзя удалить — просто уберём клавиатуру
        await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()


# Экспорт роутера
__all__ = ["router"]
'''
        else:
            # Универсальный шаблон уже содержит свои handlers; пропускаем создание
            handlers_content = None
        if handlers_content is not None:
            (module_dir / "handlers.py").write_text(handlers_content, encoding="utf-8")
            console.print(f"[green]Создан файл: {module_dir / 'handlers.py'}[/]")

        # Создаём models.py
        models_content = f'''\
"""
Модели для модуля {name.replace('_', ' ').title()}
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from Systems.core.database.base import Base


# Пример модели - удалите или измените по необходимости
class {name.title().replace('_', '')}Item(Base):
    """Пример модели для модуля {name.replace('_', ' ').title()}"""
    __tablename__ = "{name}_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    def __repr__(self):
        return f"<{name.title().replace('_', '')}Item(id={{self.id}}, name='{{self.name}}', user_id={{self.user_id}})>"
'''
        (module_dir / "models.py").write_text(models_content, encoding="utf-8")
        console.print(f"[green]Создан файл: {module_dir / 'models.py'}[/]")

        # Создаём keyboards.py (для demo)
        if template.lower() == "demo":
            keyboards_content = f'''\
"""
Клавиатуры для модуля {name.replace('_', ' ').title()}
"""
from typing import Optional, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callback_data import {name.title().replace('_', '')}CB


def main_{name}_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура модуля {name.replace('_', ' ').title()}"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔧 Функция 1",
            callback_data={name.title().replace('_', '')}CB(action="function1").pack()
        ),
        InlineKeyboardButton(
            text="⚙️ Функция 2", 
            callback_data={name.title().replace('_', '')}CB(action="function2").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="❌ Закрыть",
            callback_data={name.title().replace('_', '')}CB(action="close").pack()
        )
    )
    
    return builder.as_markup()


def confirmation_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data={name.title().replace('_', '')}CB(action="confirm", item_id=item_id).pack()
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data={name.title().replace('_', '')}CB(action="cancel").pack()
        )
    )
    
    return builder.as_markup()
'''
            (module_dir / "keyboards.py").write_text(keyboards_content, encoding="utf-8")
            console.print(f"[green]Создан файл: {module_dir / 'keyboards.py'}[/]")

        # Создаём callback_data.py (для demo)
        if template.lower() == "demo":
            callback_data_content = f'''\
"""
Callback Data фабрики для модуля {name.replace('_', ' ').title()}
"""
from typing import Optional
from aiogram.filters.callback_data import CallbackData


class {name.title().replace('_', '')}CB(CallbackData, prefix="{name}_cb"):
    """Callback для модуля {name.replace('_', ' ').title()}"""
    action: str
    item_id: Optional[int] = None


class {name.title().replace('_', '')}ActionCB(CallbackData, prefix="{name}_action"):
    """Callback для действий модуля {name.replace('_', ' ').title()}"""
    action: str
    data: Optional[str] = None
'''
            (module_dir / "callback_data.py").write_text(
                callback_data_content, encoding="utf-8"
            )
            console.print(f"[green]Создан файл: {module_dir / 'callback_data.py'}[/]")

        # Создаём states.py (оставляем всегда как пример)
        states_content = f'''\
"""
FSM состояния для модуля {name.replace('_', ' ').title()}
"""
from aiogram.fsm.state import State, StatesGroup


class {name.title().replace('_', '')}States(StatesGroup):
    """Состояния для работы с модулем {name.replace('_', ' ').title()}"""
    waiting_for_input = State()
    waiting_for_confirmation = State()
    processing = State()


class {name.title().replace('_', '')}CreationStates(StatesGroup):
    """Состояния для создания элементов"""
    waiting_for_name = State()
    waiting_for_description = State()
    confirm_creation = State()


class {name.title().replace('_', '')}EditStates(StatesGroup):
    """Состояния для редактирования элементов"""
    waiting_for_new_name = State()
    waiting_for_new_description = State()
    confirm_edit = State()
'''
        (module_dir / "states.py").write_text(states_content, encoding="utf-8")
        console.print(f"[green]Создан файл: {module_dir / 'states.py'}[/]")

        # Создаём services.py (пример БД не используется в демо-обработчиках)
        services_content = f'''\
"""
Сервисы для работы с модулем {name.replace('_', ' ').title()}
"""
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from Systems.core.database.manager import DBManager
from Systems.core.users.service import UserService
from .models import {name.title().replace('_', '')}Item


class {name.title().replace('_', '')}Service:
    """Сервис для работы с модулем {name.replace('_', ' ').title()}"""
    
    def __init__(self, db_manager: DBManager, user_service: UserService):
        self.db_manager = db_manager
        self.user_service = user_service
    
    async def create_item(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None
    ) -> {name.title().replace('_', '')}Item:
        """Создает новый элемент"""
        async with self.db_manager.get_async_session() as session:
            item = {name.title().replace('_', '')}Item(
                name=name,
                description=description,
                user_id=user_id
            )
            
            session.add(item)
            await session.commit()
            await session.refresh(item)
            
            return item
    
    async def get_user_items(self, user_id: int) -> List[{name.title().replace('_', '')}Item]:
        """Получает элементы пользователя"""
        async with self.db_manager.get_async_session() as session:
            query = select({name.title().replace('_', '')}Item).where(
                {name.title().replace('_', '')}Item.user_id == user_id
            ).order_by({name.title().replace('_', '')}Item.created_at.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_item_by_id(self, item_id: int, user_id: int) -> Optional[{name.title().replace('_', '')}Item]:
        """Получает элемент по ID с проверкой принадлежности пользователю"""
        async with self.db_manager.get_async_session() as session:
            query = select({name.title().replace('_', '')}Item).where(
                and_(
                    {name.title().replace('_', '')}Item.id == item_id,
                    {name.title().replace('_', '')}Item.user_id == user_id
                )
            )
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def update_item(
        self,
        item_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Обновляет элемент"""
        async with self.db_manager.get_async_session() as session:
            query = select({name.title().replace('_', '')}Item).where(
                and_(
                    {name.title().replace('_', '')}Item.id == item_id,
                    {name.title().replace('_', '')}Item.user_id == user_id
                )
            )
            result = await session.execute(query)
            item = result.scalar_one_or_none()
            
            if not item:
                return False
            
            if name is not None:
                item.name = name
            if description is not None:
                item.description = description
            
            await session.commit()
            return True
    
    async def delete_item(self, item_id: int, user_id: int) -> bool:
        """Удаляет элемент"""
        async with self.db_manager.get_async_session() as session:
            query = select({name.title().replace('_', '')}Item).where(
                and_(
                    {name.title().replace('_', '')}Item.id == item_id,
                    {name.title().replace('_', '')}Item.user_id == user_id
                )
            )
            result = await session.execute(query)
            item = result.scalar_one_or_none()
            
            if not item:
                return False
            
            await session.delete(item)
            await session.commit()
            return True
'''
        (module_dir / "services.py").write_text(services_content, encoding="utf-8")
        console.print(f"[green]Создан файл: {module_dir / 'services.py'}[/]")

        # Создаём utils.py
        utils_content = f'''\
"""
Утилиты для модуля {name.replace('_', ' ').title()}
"""
from datetime import datetime
from typing import Any, Dict, Optional

from .models import {name.title().replace('_', '')}Item


def format_item_info(item: {name.title().replace('_', '')}Item) -> str:
    """Форматирует информацию об элементе"""
    lines = [
        f"🔧 <b>Элемент #{{item.id}}</b>",
        "",
        f"📝 <b>Название:</b> {{item.name}}",
    ]
    
    if item.description:
        lines.append(f"📄 <b>Описание:</b> {{item.description}}")
    
    lines.extend([
        f"📅 <b>Создан:</b> {{item.created_at.strftime('%d.%m.%Y %H:%M')}}",
        f"🔄 <b>Обновлен:</b> {{item.updated_at.strftime('%d.%m.%Y %H:%M')}}"
    ])
    
    return "\\n".join(lines)


def format_items_list(items: list[{name.title().replace('_', '')}Item]) -> str:
    """Форматирует список элементов"""
    if not items:
        return "📭 У вас пока нет элементов."
    
    lines = [f"📝 <b>Ваши элементы ({{len(items)}}):</b>", ""]
    
    for i, item in enumerate(items, 1):
        preview = item.description[:50] + "..." if item.description and len(item.description) > 50 else item.description or "Без описания"
        lines.append(f"{{i}}. <b>{{item.name}}</b> - {{preview}}")
    
    return "\\n".join(lines)


def validate_item_name(name: str) -> tuple[bool, str]:
    """Валидирует название элемента"""
    if not name or not name.strip():
        return False, "Название не может быть пустым"
    
    if len(name) > 200:
        return False, "Название слишком длинное (максимум 200 символов)"
    
    return True, ""


def validate_item_description(description: str) -> tuple[bool, str]:
    """Валидирует описание элемента"""
    if description and len(description) > 1000:
        return False, "Описание слишком длинное (максимум 1000 символов)"
    
    return True, ""


def truncate_text(text: str, max_length: int = 50) -> str:
    """Обрезает текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_duration(start_time: datetime, end_time: Optional[datetime] = None) -> str:
    """Форматирует продолжительность времени"""
    if end_time is None:
        end_time = datetime.utcnow()
    
    duration = end_time - start_time
    
    if duration.days > 0:
        return f"{{duration.days}} дн."
    elif duration.seconds >= 3600:
        hours = duration.seconds // 3600
        return f"{{hours}} ч."
    elif duration.seconds >= 60:
        minutes = duration.seconds // 60
        return f"{{minutes}} мин."
    else:
        return "< 1 мин."
'''
        (module_dir / "utils.py").write_text(utils_content, encoding="utf-8")
        console.print(f"[green]Создан файл: {module_dir / 'utils.py'}[/]")

        # Авто-включение по флагу
        if enable:
            try:
                # Предпочитаем путь из переменной окружения, чтобы избежать кеша настроек при тестах/CLI
                import os as _os
                env_pdp = _os.getenv("SDB_CORE_PROJECT_DATA_PATH")
                if env_pdp:
                    enabled_path = (Path(env_pdp) / "Config" / "enabled_modules.json").resolve()
                else:
                    from Systems.core.app_settings import load_app_settings as _load_settings
                    _settings = _load_settings()
                    enabled_path = Path(_settings.core.enabled_modules_config_path)
                # Прочитаем текущий список
                current = {"active_modules": [], "disabled_modules": []}
                try:
                    if enabled_path.exists():
                        current = json.loads(enabled_path.read_text(encoding="utf-8")) or current
                except Exception:
                    pass
                new_list = list({m for m in current.get("active_modules", [])} | {name})
                if _save_enabled_modules(new_list, enabled_path):
                    console.print(f"[green]Модуль '{name}' добавлен в enabled_modules.json[/]")
                else:
                    console.print(f"[yellow]Не удалось автоматически включить модуль '{name}'. Включите вручную.[/]")
            except Exception as _e_auto:
                console.print(f"[yellow]Авто-включение не выполнено: {_e_auto}[/]")

        console.print(f"[bold green]Модуль '{name}' успешно создан в {module_dir}![/]")
        console.print(f"[yellow]Как проверить демо:[/]")
        console.print(f"1) Включите модуль (если не включали): [cyan]./sdb module enable {name}[/]")
        console.print(f"2) Перезапустите бот: [cyan]./sdb restart[/]")
        console.print(f"3) В Telegram отправьте команду: /{name}")
        logger.success(f"Модуль {name} создан в {module_dir}")
    except Exception as e:
        console.print(f"[bold red]Ошибка при создании модуля '{name}': {e}[/]")
        logger.error(f"Ошибка создания модуля {name}: {e}")
        shutil.rmtree(module_dir, ignore_errors=True)
        raise typer.Exit(code=1)


@module_app.command(
    name="list", help="Показать список всех найденных модулей и их статус."
)
def list_modules_cmd():
    loader = _get_module_loader_sync()
    if not loader:
        # Сообщение об ошибке уже должно быть выведено из _get_module_loader_sync или _get_module_loader_instance_async
        raise typer.Exit(code=1)

    table = Table(
        title="[bold cyan]Модули SwiftDevBot[/]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Имя Модуля (name)", style="dim cyan", min_width=20)
    table.add_column("Отображаемое Имя", min_width=25)
    table.add_column("Версия", style="yellow")
    table.add_column("Тип", style="blue")  # Добавим тип
    table.add_column("Статус", style="green")
    table.add_column("Описание", max_width=50, overflow="fold")

    if not loader.available_modules:
        console.print(
            "[yellow]Не найдено ни одного модуля (в modules/ или core/sys_modules/).[/]"
        )
        return

    sorted_modules = sorted(
        loader.available_modules.values(),
        key=lambda m_info: (m_info.is_system_module, m_info.name),
    )

    for module_info in sorted_modules:
        module_type = "Системный" if module_info.is_system_module else "Плагин"

        # Статус для плагинов зависит от enabled_plugin_names
        # Статус для системных - они "всегда активны для загрузки" (но могут не загрузиться из-за ошибок)
        if module_info.is_system_module:
            status_text = Text(
                "Активен (системный)", style="green"
            )  # или "Загружен", если есть is_loaded_successfully
            if module_info.is_loaded_successfully:
                status_text = Text("Загружен ✅ (сист.)", style="green")
            elif module_info.error:
                status_text = Text(f"Ошибка ⚠️ (сист.)", style="red")

        else:  # Это плагин
            status_text = (
                Text("Активен ✅", style="green")
                if module_info.name in loader.enabled_plugin_names
                else Text("Неактивен ❌", style="red")
            )
            if (
                module_info.name in loader.enabled_plugin_names
                and module_info.is_loaded_successfully
            ):
                status_text = Text("Загружен ✅", style="green")
            elif module_info.name in loader.enabled_plugin_names and module_info.error:
                status_text = Text(f"Ошибка ⚠️", style="red")

        version_str = module_info.manifest.version if module_info.manifest else "[N/A]"
        display_name_str = (
            module_info.manifest.display_name
            if module_info.manifest
            else module_info.name
        )  # fallback на имя папки
        description_str = (
            module_info.manifest.description
            if module_info.manifest and module_info.manifest.description
            else "-"
        )

        table.add_row(
            module_info.name,
            display_name_str,
            version_str,
            module_type,
            status_text,
            description_str,
        )
    console.print(table)


@module_app.command(
    name="info", help="Показать детальную информацию о модуле (из manifest)."
)
def info_module_cmd(
    module_name: str = typer.Argument(
        ..., help="Имя модуля (из manifest.name или имя папки)."
    )
):
    loader = _get_module_loader_sync()
    if not loader:
        raise typer.Exit(code=1)

    module_info = loader.get_module_info(module_name)

    if not module_info:
        console.print(f"[bold red]Ошибка: Модуль '{module_name}' не найден.[/]")
        raise typer.Exit(code=1)

    if not module_info.manifest:
        console.print(
            f"[yellow]Модуль '{module_name}' найден, но не имеет валидного манифеста (или он не был распарсен).[/yellow]"
        )
        console.print(f"  Путь к модулю: {module_info.path}")
        console.print(
            f"  Тип: {'Системный' if module_info.is_system_module else 'Плагин'}"
        )
        if module_info.error:
            console.print(
                f"  Ошибка при попытке загрузки манифеста: {module_info.error}"
            )
        raise typer.Exit(code=1)

    display_name_header = module_info.manifest.display_name or module_info.name
    console.print(
        Panel(
            f"[bold cyan]Информация о модуле: {display_name_header} ({module_name})[/]",
            expand=False,
            border_style="cyan",
        )
    )

    try:
        import yaml

        manifest_str = yaml.dump(
            module_info.manifest.model_dump(mode="json"),
            indent=2,
            allow_unicode=True,
            sort_keys=False,
        )
        syntax = Syntax(
            manifest_str,
            "yaml",
            theme="fruity",
            line_numbers=True,
            background_color="default",
        )
    except ImportError:
        manifest_str = json.dumps(
            module_info.manifest.model_dump(mode="json"), indent=2, ensure_ascii=False
        )
        syntax = Syntax(
            manifest_str,
            "json",
            theme="fruity",
            line_numbers=True,
            background_color="default",
        )
    except Exception as e_dump:
        console.print(
            f"[yellow]Не удалось красиво отобразить манифест: {e_dump}. Вывод как словарь:[/]"
        )
        console.print(module_info.manifest.model_dump())
        raise typer.Exit(code=1)
    console.print(syntax)


@module_app.command(
    name="enable", help="Активировать плагин (добавить в enabled_modules.json)."
)
def enable_module_cmd(
    module_name: str = typer.Argument(..., help="Имя плагина для активации.")
):
    loader = _get_module_loader_sync()
    if not loader:
        raise typer.Exit(code=1)

    module_info = loader.get_module_info(module_name)
    if not module_info:
        console.print(
            f"[bold red]Ошибка: Модуль '{module_name}' не найден среди доступных. Проверьте имя.[/]"
        )
        console.print(
            f"Доступные для управления (плагины): {[m.name for m in loader.available_modules.values() if not m.is_system_module]}"
        )
        raise typer.Exit(code=1)

    if module_info.is_system_module:
        console.print(
            f"[bold red]Ошибка: Системные модули ('{module_name}') не управляются через enable/disable. Они загружаются ядром.[/]"
        )
        raise typer.Exit(code=1)

    enabled_modules_file_path = loader._settings.core.enabled_modules_config_path

    if module_name in loader.enabled_plugin_names:
        console.print(f"[yellow]Плагин '{module_name}' уже активен.[/]")
        return

    new_enabled_list = loader.enabled_plugin_names + [module_name]
    if _save_enabled_modules(new_enabled_list, enabled_modules_file_path):
        console.print(f"[bold green]Плагин '{module_name}' успешно активирован![/]")
        console.print(
            f"Изменения вступят в силу после перезапуска бота (`./sdb.py restart`)."
        )
    else:
        console.print(
            f"[bold red]Не удалось сохранить изменения в '{enabled_modules_file_path}'.[/]"
        )
        raise typer.Exit(code=1)


@module_app.command(
    name="disable", help="Деактивировать плагин (удалить из enabled_modules.json)."
)
def disable_module_cmd(
    module_name: str = typer.Argument(..., help="Имя плагина для деактивации.")
):
    loader = _get_module_loader_sync()
    if not loader:
        raise typer.Exit(code=1)

    module_info = loader.get_module_info(module_name)
    if not module_info:
        console.print(f"[bold red]Ошибка: Модуль '{module_name}' не найден.[/]")
        raise typer.Exit(code=1)

    if module_info.is_system_module:
        console.print(
            f"[bold red]Ошибка: Системные модули ('{module_name}') не управляются через enable/disable.[/]"
        )
        raise typer.Exit(code=1)

    enabled_modules_file_path = loader._settings.core.enabled_modules_config_path

    if module_name not in loader.enabled_plugin_names:
        console.print(f"[yellow]Плагин '{module_name}' не был активен.[/]")
        return

    new_enabled_list = [m for m in loader.enabled_plugin_names if m != module_name]
    if _save_enabled_modules(new_enabled_list, enabled_modules_file_path):
        console.print(f"[bold green]Плагин '{module_name}' успешно деактивирован![/]")
        console.print(
            f"Изменения вступят в силу после перезапуска бота (`./sdb.py restart`)."
        )
    else:
        console.print(
            f"[bold red]Не удалось сохранить изменения в '{enabled_modules_file_path}'.[/]"
        )
        raise typer.Exit(code=1)


async def _clean_tables_module_async_internal(
    module_name: str, loader: Any, called_from_uninstall: bool = False
) -> bool:
    if not called_from_uninstall:
        console.print(
            Panel(
                f"[bold red]УДАЛЕНИЕ ТАБЛИЦ МОДУЛЯ: {module_name}[/]",
                expand=False,
                border_style="red",
            )
        )

    module_info = loader.get_module_info(module_name)
    if not module_info:  # Манифест может отсутствовать у системного модуля
        console.print(f"[bold red]Ошибка: Модуль '{module_name}' не найден.[/]")
        return False

    if not module_info.manifest:
        console.print(
            f"[yellow]Модуль '{module_name}' не имеет манифеста. Невозможно определить таблицы для удаления.[/yellow]"
        )
        return True  # Считаем успешным, так как нечего удалять

    model_definitions_paths = module_info.manifest.model_definitions
    if not model_definitions_paths:
        console.print(
            f"[yellow]Модуль '{module_name}' не декларирует модели в манифесте ('model_definitions'). Удаление таблиц не требуется.[/]"
        )
        return True

    if not called_from_uninstall:
        console.print(
            f"Модуль '{module_name}' декларирует следующие пути к моделям для удаления таблиц:"
        )
        for path_str in model_definitions_paths:
            console.print(f"  - {path_str}")
        if not confirm_action(
            f"Вы АБСОЛЮТНО уверены, что хотите УДАЛИТЬ таблицы для моделей модуля '{module_name}'? Это [bold red]НЕОБРАТИМО[/]!",
            default_choice=False,
            abort_on_false=True,
        ):
            return False

    models_to_drop: List[Type[SDBBaseAlchemyModel]] = []
    failed_imports: List[str] = []
    console.print(f"\nИмпорт классов моделей для '{module_name}'...")

    # Определяем базовый путь для импорта в зависимости от типа модуля
    # Это важно, так как model_definitions в манифесте могут быть относительными (хотя рекомендуется полные)
    # Но для простоты, пока ожидаем полные пути типа "modules.my_plugin.models.MyTable"
    # или "core.sys_modules.my_sys_mod.models.SysTable"

    for import_path_str in model_definitions_paths:
        try:
            # Проверяем, есть ли точка в пути, иначе это не путь для импорта
            if "." not in import_path_str:
                failed_imports.append(import_path_str)
                console.print(
                    f"  [yellow]Предупреждение:[/yellow] '{import_path_str}' не является корректным путем для импорта Python-модели."
                )
                continue

            module_path_part, class_name = import_path_str.rsplit(".", 1)
            imported_py_module = importlib.import_module(module_path_part)
            model_class_obj = getattr(
                imported_py_module, class_name
            )  # Получаем сам объект класса

            # Проверяем, что это действительно класс и он наследуется от SDBBaseAlchemyModel
            if (
                isinstance(model_class_obj, type)
                and issubclass(model_class_obj, SDBBaseAlchemyModel)
                and hasattr(model_class_obj, "__table__")
            ):
                models_to_drop.append(
                    model_class_obj
                )  # Добавляем класс, а не экземпляр
                console.print(
                    f"  [green]Успех:[/green] {import_path_str} (таблица: {model_class_obj.__tablename__})"
                )
            else:
                failed_imports.append(import_path_str)
                console.print(
                    f"  [yellow]Предупреждение:[/yellow] '{import_path_str}' не является корректной моделью SQLAlchemy, наследуемой от SDBBaseModel."
                )
        except Exception as e_import:
            failed_imports.append(import_path_str)
            console.print(
                f"  [red]Ошибка импорта для '{import_path_str}':[/red] {type(e_import).__name__} - {e_import}"
            )

    if failed_imports:
        console.print(
            f"\n[bold yellow]Не удалось импортировать {len(failed_imports)} из {len(model_definitions_paths)} объявленных моделей для '{module_name}'.[/]"
        )
        if not models_to_drop:  # Если ВООБЩЕ ничего не удалось импортировать
            console.print(
                "[bold red]Нет успешно импортированных моделей. Операция удаления таблиц прервана.[/]"
            )
            return False
        # Если часть импортировалась, а часть нет - спрашиваем, продолжать ли с тем, что есть
        if not called_from_uninstall and not confirm_action(
            f"Продолжить удаление таблиц для {len(models_to_drop)} успешно импортированных моделей?",
            default_choice=False,
            abort_on_false=True,
        ):
            return False
        elif (
            called_from_uninstall
        ):  # Если это часть деинсталляции, то лучше не продолжать с частичным удалением
            console.print(
                "[bold yellow]Из-за ошибок импорта моделей, автоматическое удаление таблиц при деинсталляции не будет выполнено. "
                "Удалите таблицы вручную, если это необходимо.[/]"
            )
            return False  # Сигнализируем, что удаление данных не было полным/успешным

    if not models_to_drop:  # Если список пуст после всех проверок
        console.print(
            f"[bold yellow]Нет валидных моделей для удаления таблиц для модуля '{module_name}'.[/]"
        )
        return True  # Считаем успешным, так как нечего было удалять

    if (
        not called_from_uninstall
    ):  # Дополнительное подтверждение, если это не часть uninstall
        console.print(
            "\n[bold blue]Следующие таблицы SQLAlchemy будут удалены из БД:[/]"
        )
        for model_cls_to_drop in models_to_drop:
            console.print(f"  - [cyan]{model_cls_to_drop.__tablename__}[/cyan]")
        if not confirm_action(
            f"ПОСЛЕДНЕЕ ПОДТВЕРЖДЕНИЕ: Удалить {len(models_to_drop)} таблиц для '{module_name}'?",
            default_choice=False,
            abort_on_false=True,
        ):
            return False

    settings_obj, db_m, _ = await get_sdb_services_for_cli(init_db=True)
    if not (settings_obj and db_m):
        console.print(
            "[bold red]Не удалось инициализировать DBManager для удаления таблиц.[/]"
        )
        return False
    try:
        console.print(f"\n[magenta]Удаление таблиц для '{module_name}'...[/magenta]")
        await db_m.drop_specific_module_tables(
            models_to_drop
        )  # Передаем список КЛАССОВ моделей
        console.print(f"[bold green]Таблицы для '{module_name}' успешно удалены.[/]")
        if not called_from_uninstall:
            console.print(
                "[yellow]Примечание: Alembic не знает об этом удалении. "
                "Если вы планируете использовать миграции для этих таблиц в будущем, "
                "вам может потребоваться создать новую ревизию или 'заштамповать' состояние Alembic.[/yellow]"
            )
        return True
    except Exception as e_drop:
        console.print(
            f"[bold red]Ошибка при удалении таблиц для '{module_name}': {e_drop}[/]"
        )
        return False
    finally:
        if db_m:
            await db_m.dispose()


@module_app.command(
    name="clean-tables",
    help="[ОПАСНО] Удалить таблицы модуля из БД (согласно manifest).",
)
def clean_tables_module_cmd_wrapper(
    module_name: str = typer.Argument(..., help="Имя модуля, чьи таблицы удалить.")
):
    try:
        loader = asyncio.run(_get_module_loader_instance_async())
        if not loader:
            raise typer.Exit(code=1)
        if not asyncio.run(
            _clean_tables_module_async_internal(module_name=module_name, loader=loader)
        ):
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Ошибка в 'module clean-tables': {e}[/]")
        raise typer.Exit(code=1)


@module_app.command(
    name="uninstall", help="[ОПАСНО] Удалить модуль (файлы и, опционально, его данные)."
)
def uninstall_module_cmd_wrapper(
    module_name: str = typer.Argument(..., help="Имя модуля для полного удаления."),
    remove_data: bool = typer.Option(
        False,
        "--remove-data/--keep-data",
        help="Удалить ли данные модуля (таблицы БД). По умолчанию ДАННЫЕ СОХРАНЯЮТСЯ.",
    ),
):
    try:
        asyncio.run(
            _uninstall_module_async(module_name=module_name, remove_data=remove_data)
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'module uninstall': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _uninstall_module_async(module_name: str, remove_data: bool):
    console.print(
        Panel(
            f"[bold red]УДАЛЕНИЕ МОДУЛЯ: {module_name}[/]",
            expand=False,
            border_style="red",
        )
    )

    loader = await _get_module_loader_instance_async()
    if not loader:
        raise typer.Exit(code=1)

    module_info = loader.get_module_info(module_name)
    if not module_info:
        console.print(
            f"[bold red]Ошибка: Модуль '{module_name}' не найден. Невозможно удалить.[/]"
        )
        raise typer.Exit(code=1)

    if module_info.is_system_module:
        console.print(
            f"[bold red]Ошибка: Системный модуль ('{module_name}') не может быть удален через эту команду.[/]"
        )
        raise typer.Exit(code=1)

    console.print(
        f"Путь к директории плагина для удаления: [cyan]{module_info.path}[/]"
    )
    if not confirm_action(
        f"Вы уверены, что хотите УДАЛИТЬ ФАЙЛЫ плагина '{module_name}'?",
        default_choice=False,
        abort_on_false=True,
    ):
        return

    data_cleaned_successfully = True  # По умолчанию, если удаление данных не требуется
    if remove_data:
        console.print(f"\nЗапрошено удаление данных для плагина '{module_name}'.")
        # Проверяем, есть ли что удалять (декларированы ли модели)
        if module_info.manifest and module_info.manifest.model_definitions:
            if confirm_action(
                f"Удаление данных плагина '{module_name}' приведет к [bold red]ПОТЕРЕ ВСЕХ ЕГО ТАБЛИЦ В БД[/]. Продолжить?",
                default_choice=False,
                abort_on_false=True,
            ):
                data_cleaned_successfully = await _clean_tables_module_async_internal(
                    module_name, loader, called_from_uninstall=True
                )
                if not data_cleaned_successfully:
                    console.print(
                        f"[bold red]Произошла ошибка при удалении данных плагина '{module_name}'.[/]"
                    )
                    if not confirm_action(
                        "Продолжить удаление файлов плагина, несмотря на ошибку удаления данных?",
                        default_choice=False,
                        abort_on_false=True,
                    ):
                        console.print(
                            "[bold yellow]Удаление плагина полностью отменено.[/bold yellow]"
                        )
                        raise typer.Exit(code=1)
            else:  # Пользователь отказался удалять данные
                data_cleaned_successfully = (
                    False  # Данные не удалены по решению пользователя
                )
                console.print(
                    "[yellow]Удаление данных отменено. Файлы плагина все еще будут удалены (если подтверждено).[/yellow]"
                )
        else:  # Нет моделей в манифесте
            console.print(
                f"[dim]Плагин '{module_name}' не декларирует модели в манифесте. Удаление данных (таблиц) не требуется.[/dim]"
            )
            # data_cleaned_successfully остается True
    else:
        console.print(
            f"\n[yellow]Данные плагина '{module_name}' (таблицы БД) не будут удалены (опция --keep-data).[/yellow]"
        )
        data_cleaned_successfully = False  # Данные не удалялись

    console.print(
        f"\nДеактивация плагина '{module_name}' (удаление из enabled_modules.json)..."
    )
    enabled_modules_file_path = loader._settings.core.enabled_modules_config_path
    if module_name in loader.enabled_plugin_names:
        new_enabled_list = [m for m in loader.enabled_plugin_names if m != module_name]
        if _save_enabled_modules(new_enabled_list, enabled_modules_file_path):
            console.print(f"[green]Плагин '{module_name}' успешно деактивирован.[/]")
        else:
            console.print(
                f"[bold red]Ошибка деактивации плагина '{module_name}' (не удалось сохранить enabled_modules.json).[/]"
            )
            if not confirm_action(
                "Продолжить удаление файлов плагина, несмотря на ошибку деактивации?",
                default_choice=False,
                abort_on_false=True,
            ):
                console.print(
                    "[bold yellow]Удаление плагина полностью отменено.[/bold yellow]"
                )
                raise typer.Exit(code=1)
    else:
        console.print(f"[dim]Плагин '{module_name}' не был активен.[/dim]")

    module_dir_path = module_info.path
    console.print(f"\nУдаление директории плагина: [cyan]{module_dir_path}[/]")
    if not confirm_action(
        f"[bold red]ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ: Удалить директорию '{module_dir_path}'? Это НЕОБРАТИМО.[/bold red]",
        default_choice=False,
        abort_on_false=True,
    ):
        return

    try:
        shutil.rmtree(module_dir_path)
        console.print(
            f"[bold green]Директория плагина '{module_dir_path}' успешно удалена.[/]"
        )
    except Exception as e_rmtree:
        console.print(
            f"[bold red]Ошибка при удалении директории '{module_dir_path}': {e_rmtree}[/]"
        )
        raise typer.Exit(code=1)

    console.print(f"\n[bold green]Плагин '{module_name}' успешно удален.[/]")
    if (
        remove_data and not data_cleaned_successfully
    ):  # Если запрашивали удаление данных, но оно не удалось
        console.print(
            "[bold yellow]Однако, при удалении данных плагина (таблиц) возникли проблемы или операция была отменена.[/bold yellow]"
        )
    elif not remove_data:  # Если не запрашивали удаление данных
        console.print("[dim](Данные плагина не удалялись).[/dim]")
    console.print("Перезапустите бота, чтобы изменения вступили в силу.")


@module_app.command(
    name="list-available", help="Показать модули, доступные в репозитории и локально."
)
def list_available_modules_cmd(
    local_only: bool = typer.Option(
        False, "--local-only", help="Показать только локальные модули"
    ),
    show_details: bool = typer.Option(
        False, "--details", "-d", help="Показать детальную информацию о модулях"
    ),
    format: str = typer.Option(
        "table", "--format", "-f", help="Формат вывода: table, json, yaml"
    ),
):
    try:
        asyncio.run(_list_available_modules_async(local_only, show_details, format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'module list-available': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _list_available_modules_async(
    local_only: bool, show_details: bool, format: str
):
    """Показать доступные модули"""
    console.print(
        Panel(
            "[bold blue]ПОИСК ДОСТУПНЫХ МОДУЛЕЙ[/]", expand=False, border_style="blue"
        )
    )

    loader = await _get_module_loader_instance_async()
    if not loader:
        raise typer.Exit(code=1)

    # Получаем локальные модули
    local_modules = loader.get_all_modules_info()

    if local_only:
        console.print("[yellow]Показываю только локальные модули...[/]")
        await _display_modules(local_modules, "Локальные модули", show_details, format)
        return

    # Показываем локальные модули
    console.print("[cyan]Локальные модули:[/]")
    await _display_modules(local_modules, "Локальные модули", show_details, format)

    # Показываем информацию о репозитории
    console.print("\n[cyan]Модули из репозитория:[/]")

    # Пока упрощенная реализация - показываем примеры
    repo_modules = [
        {
            "name": "example-module",
            "version": "1.0.0",
            "description": "Пример модуля из репозитория",
        },
        {"name": "test-plugin", "version": "2.1.0", "description": "Тестовый плагин"},
    ]

    if repo_modules:
        for module in repo_modules:
            console.print(
                f"  📦 {module['name']} v{module['version']} - {module['description']}"
            )
    else:
        console.print("[dim]Нет доступных модулей в репозитории.[/]")

    console.print(
        "[dim]В будущем здесь будет реальная интеграция с центральным репозиторием.[/]"
    )

    # Показываем статистику
    enabled_count = sum(1 for m in local_modules if m.is_enabled)
    total_count = len(local_modules)

    console.print(f"\n[bold green]Статистика:[/]")
    console.print(f"  📦 Всего локальных модулей: {total_count}")
    console.print(f"  ✅ Включено: {enabled_count}")
    console.print(f"  ❌ Отключено: {total_count - enabled_count}")


async def _display_modules(
    modules: List[Any], title: str, show_details: bool, format: str
):
    """Отобразить список модулей"""
    if not modules:
        console.print(f"[dim]Нет {title.lower()}[/]")
        return

    if format == "json":
        await _display_modules_json(modules, show_details)
    elif format == "yaml":
        await _display_modules_yaml(modules, show_details)
    else:
        await _display_modules_table(modules, show_details)


async def _display_modules_table(modules: List[Any], show_details: bool):
    """Отобразить модули в виде таблицы"""
    from rich.table import Table

    table = Table(title="Доступные модули")
    table.add_column("Имя", style="cyan", no_wrap=True)
    table.add_column("Статус", style="green")
    table.add_column("Версия", style="yellow")
    table.add_column("Описание", style="white")

    if show_details:
        table.add_column("Автор", style="blue")
        table.add_column("Тип", style="magenta")

    for module in modules:
        status = "✅ Включен" if module.is_enabled else "❌ Отключен"
        if module.error:
            status = f"⚠️ Ошибка: {module.error}"

        version = module.manifest.version if module.manifest else "Не указана"
        description = module.manifest.description if module.manifest else "Нет описания"

        row = [module.name, status, version, description]

        if show_details:
            author = module.manifest.author if module.manifest else "Не указан"
            module_type = "Системный" if module.is_system_module else "Пользовательский"
            row.extend([author, module_type])

        table.add_row(*row)

    console.print(table)


async def _display_modules_json(modules: List[Any], show_details: bool):
    """Отобразить модули в формате JSON"""
    import json

    modules_data = []
    for module in modules:
        module_data = {
            "name": module.name,
            "enabled": module.is_enabled,
            "error": module.error,
            "is_system_module": module.is_system_module,
        }

        if module.manifest:
            module_data.update(
                {
                    "version": module.manifest.version,
                    "description": module.manifest.description,
                    "author": module.manifest.author,
                    "website": module.manifest.website,
                    "email": module.manifest.email,
                    "license": module.manifest.license,
                }
            )

        modules_data.append(module_data)

    console.print(json.dumps(modules_data, indent=2, ensure_ascii=False))


async def _display_modules_yaml(modules: List[Any], show_details: bool):
    """Отобразить модули в формате YAML"""
    import yaml

    modules_data = []
    for module in modules:
        module_data = {
            "name": module.name,
            "enabled": module.is_enabled,
            "error": module.error,
            "is_system_module": module.is_system_module,
        }

        if module.manifest:
            module_data.update(
                {
                    "version": module.manifest.version,
                    "description": module.manifest.description,
                    "author": module.manifest.author,
                    "website": module.manifest.website,
                    "email": module.manifest.email,
                    "license": module.manifest.license,
                }
            )

        modules_data.append(module_data)

    console.print(yaml.dump(modules_data, default_flow_style=False, allow_unicode=True))


@module_app.command(
    name="install", help="Установить модуль из репозитория или локального источника."
)
def install_module_cmd(
    module_name: str = typer.Argument(..., help="Имя модуля для установки."),
    source: str = typer.Option(
        "local", "--source", "-s", help="Источник модуля: local, repo, url"
    ),
    url: Optional[str] = typer.Option(
        None, "--url", help="URL для установки модуля из интернета"
    ),
):
    try:
        asyncio.run(_install_module_async(module_name, source, url))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'module install': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _install_module_async(module_name: str, source: str, url: Optional[str]):
    """Установить модуль"""
    console.print(
        Panel(
            f"[bold blue]УСТАНОВКА МОДУЛЯ: {module_name}[/]",
            expand=False,
            border_style="blue",
        )
    )

    if source == "local":
        await _install_local_module(module_name)
    elif source == "repo":
        console.print("[cyan]Установка модуля из центрального репозитория...[/]")

        # Пока упрощенная реализация - показываем доступные модули
        repo_modules = [
            {
                "name": "example-module",
                "version": "1.0.0",
                "description": "Пример модуля",
            },
            {
                "name": "test-plugin",
                "version": "2.1.0",
                "description": "Тестовый плагин",
            },
        ]

        # Ищем модуль в репозитории
        module_found = None
        for repo_module in repo_modules:
            if repo_module["name"] == module_name:
                module_found = repo_module
                break

        if module_found:
            console.print(
                f"[green]Найден модуль в репозитории: {module_found['name']} v{module_found['version']}[/]"
            )
            console.print(f"[cyan]Описание: {module_found['description']}[/]")

            if confirm_action(f"Установить модуль '{module_name}' из репозитория?"):
                # Здесь была бы реальная загрузка из репозитория
                console.print(
                    f"[green]Модуль '{module_name}' готов к установке из репозитория![/]"
                )
                console.print(
                    "[dim]В будущем здесь будет реальная загрузка из центрального репозитория.[/]"
                )
            else:
                console.print("[yellow]Установка отменена.[/]")
        else:
            console.print(f"[yellow]Модуль '{module_name}' не найден в репозитории.[/]")
            console.print("[cyan]Доступные модули в репозитории:[/]")
            for repo_module in repo_modules:
                console.print(
                    f"  📦 {repo_module['name']} v{repo_module['version']} - {repo_module['description']}"
                )
    elif source == "url" and url:
        await _install_module_from_url(module_name, url)
    else:
        console.print("[bold red]Ошибка: Неверный источник или отсутствует URL.[/]")
        raise typer.Exit(code=1)


async def _install_local_module(module_name: str):
    """Установить локальный модуль (копирование из другой директории)"""
    console.print(f"[cyan]Поиск локального модуля '{module_name}'...[/]")

    # Поиск модуля в стандартных директориях
    search_dirs = [
        Path.home() / "modules",
        Path.home() / ".local" / "modules",
        Path.cwd() / "external_modules",
        Path.cwd() / "modules_backup",
    ]

    module_found = False
    for search_dir in search_dirs:
        if search_dir.exists():
            module_path = search_dir / module_name
            if module_path.exists() and module_path.is_dir():
                console.print(f"[green]Найден модуль в: {module_path}[/]")

                # Копируем модуль
                target_path = PROJECT_ROOT / "modules" / module_name
                if target_path.exists():
                    if not confirm_action(
                        f"Модуль '{module_name}' уже существует. Перезаписать?"
                    ):
                        console.print("[yellow]Установка отменена.[/]")
                        return
                    import shutil

                    shutil.rmtree(target_path)

                try:
                    import shutil

                    shutil.copytree(module_path, target_path)
                    console.print(
                        f"[bold green]Модуль '{module_name}' успешно установлен![/]"
                    )
                    module_found = True
                    break
                except Exception as e:
                    console.print(f"[bold red]Ошибка при копировании модуля: {e}[/]")
                    return

    if not module_found:
        console.print(
            f"[yellow]Модуль '{module_name}' не найден в стандартных директориях.[/]"
        )
        console.print("[dim]Добавьте модуль в одну из директорий:[/]")
        for search_dir in search_dirs:
            console.print(f"  - {search_dir}")


async def _install_module_from_url(module_name: str, url: str):
    """Установить модуль из URL"""
    console.print(f"[cyan]Установка модуля '{module_name}' из URL: {url}[/]")

    try:
        import shutil
        import tempfile
        import zipfile

        import requests

        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Загружаем файл
            console.print("[cyan]Загрузка модуля...[/]")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Сохраняем во временный файл
            zip_path = temp_path / f"{module_name}.zip"
            with open(zip_path, "wb") as f:
                f.write(response.content)

            # Распаковываем архив
            console.print("[cyan]Распаковка модуля...[/]")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_path)

            # Ищем папку с модулем
            module_dir = None
            for item in temp_path.iterdir():
                if item.is_dir() and (
                    item.name == module_name or item.name.endswith(f"-{module_name}")
                ):
                    module_dir = item
                    break

            if not module_dir:
                # Если не нашли папку с именем модуля, берем первую папку
                for item in temp_path.iterdir():
                    if item.is_dir():
                        module_dir = item
                        break

            if not module_dir:
                console.print(
                    "[bold red]Ошибка: Не удалось найти папку с модулем в архиве.[/]"
                )
                return

            # Копируем модуль
            target_path = PROJECT_ROOT / "modules" / module_name
            if target_path.exists():
                if not confirm_action(
                    f"Модуль '{module_name}' уже существует. Перезаписать?"
                ):
                    console.print("[yellow]Установка отменена.[/]")
                    return
                shutil.rmtree(target_path)

            shutil.copytree(module_dir, target_path)
            console.print(
                f"[bold green]Модуль '{module_name}' успешно установлен из URL![/]"
            )

    except requests.RequestException as e:
        console.print(f"[bold red]Ошибка при загрузке модуля: {e}[/]")
    except zipfile.BadZipFile:
        console.print(
            "[bold red]Ошибка: Загруженный файл не является корректным ZIP архивом.[/]"
        )
    except Exception as e:
        console.print(f"[bold red]Ошибка при установке модуля: {e}[/]")


@module_app.command(
    name="update", help="Обновить модуль из репозитория или локального источника."
)
def update_module_cmd(
    module_name: str = typer.Argument(
        ..., help="Имя модуля для обновления, или '--all'."
    ),
    force: bool = typer.Option(False, "--force", help="Принудительное обновление."),
):
    try:
        asyncio.run(_update_module_async(module_name, force))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Неожиданная ошибка в команде 'module update': {e}[/]")
        raise typer.Exit(code=1)


async def _update_module_async(module_name: str, force: bool):
    """Обновить модуль"""
    console.print(
        Panel(
            f"[bold blue]ОБНОВЛЕНИЕ МОДУЛЯ: {module_name}[/]",
            expand=False,
            border_style="blue",
        )
    )

    loader = await _get_module_loader_instance_async()
    if not loader:
        raise typer.Exit(code=1)

    if module_name == "--all":
        console.print("[cyan]Массовое обновление всех модулей...[/]")

        # Получаем все активные модули
        active_modules = [m for m in loader.get_all_modules_info() if m.is_enabled]

        if not active_modules:
            console.print("[yellow]Нет активных модулей для обновления.[/]")
            return

        updated_count = 0
        for module in active_modules:
            try:
                if await _update_single_module(module.name, force):
                    updated_count += 1
            except Exception as e:
                console.print(
                    f"[red]Ошибка при обновлении модуля '{module.name}': {e}[/]"
                )

        console.print(
            f"[bold green]Обновлено модулей: {updated_count}/{len(active_modules)}[/]"
        )
        return

    # Обновление одного модуля
    await _update_single_module(module_name, force)


async def _update_single_module(module_name: str, force: bool):
    """Обновить один модуль"""
    console.print(f"[cyan]Обновление модуля '{module_name}'...[/]")

    # Проверяем, существует ли модуль
    module_path = PROJECT_ROOT / "modules" / module_name
    if not module_path.exists():
        console.print(f"[bold red]Модуль '{module_name}' не найден.[/]")
        return False

    # Проверяем, есть ли обновления
    if not force:
        console.print("[cyan]Проверка обновлений для модуля...[/]")

        # Пока упрощенная проверка - в будущем здесь будет проверка версий
        console.print(
            "[yellow]Автоматическая проверка обновлений пока не реализована.[/]"
        )
        console.print("[dim]Используйте --force для принудительного обновления.[/]")
        console.print("[cyan]Доступные действия:[/]")
        console.print("  - Используйте --force для принудительного обновления")
        console.print("  - Проверьте обновления вручную на сайте репозитория")
        return False

    # Для демонстрации просто перезаписываем модуль
    console.print(f"[cyan]Принудительное обновление модуля '{module_name}'...[/]")

    # Здесь можно добавить логику загрузки обновлений из репозитория
    # Пока просто показываем, что обновление возможно
    console.print(f"[green]Модуль '{module_name}' готов к обновлению.[/]")
    console.print("[dim]В будущем здесь будет загрузка обновлений из репозитория.[/]")

    return True


@module_app.command(name="sync-deps", help="Собрать Python-зависимости модулей.")
def sync_deps_cmd(
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Файл для сохранения зависимостей"
    ),
    format: str = typer.Option(
        "requirements", "--format", "-f", help="Формат: requirements, pip-tools"
    ),
):
    try:
        asyncio.run(_sync_deps_async(output_file, format))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[bold red]Неожиданная ошибка в команде 'module sync-deps': {e}[/]"
        )
        raise typer.Exit(code=1)


async def _sync_deps_async(output_file: Optional[str], format: str):
    """Синхронизировать зависимости модулей"""
    console.print(
        Panel(
            "[bold blue]СИНХРОНИЗАЦИЯ ЗАВИСИМОСТЕЙ МОДУЛЕЙ[/]",
            expand=False,
            border_style="blue",
        )
    )

    loader = await _get_module_loader_instance_async()
    if not loader:
        raise typer.Exit(code=1)

    # Получаем все активные модули
    active_modules = [m for m in loader.get_all_modules_info() if m.is_enabled]

    if not active_modules:
        console.print("[yellow]Нет активных модулей для анализа зависимостей.[/]")
        return

    console.print(
        f"[cyan]Анализ зависимостей для {len(active_modules)} активных модулей...[/]"
    )

    # Собираем все зависимости
    all_dependencies = set()
    module_deps = {}

    for module in active_modules:
        python_deps = []
        sdb_deps = []

        if module.manifest:
            # Получаем Python зависимости
            if (
                hasattr(module.manifest, "python_requirements")
                and module.manifest.python_requirements
            ):
                python_deps = module.manifest.python_requirements
            elif (
                hasattr(module.manifest, "dependencies")
                and module.manifest.dependencies
            ):
                python_deps = module.manifest.dependencies

            # Получаем SDB зависимости
            if (
                hasattr(module.manifest, "sdb_module_dependencies")
                and module.manifest.sdb_module_dependencies
            ):
                sdb_deps = module.manifest.sdb_module_dependencies

            # Объединяем все зависимости
            all_module_deps = python_deps + sdb_deps

            if all_module_deps:
                all_dependencies.update(all_module_deps)
                module_deps[module.name] = all_module_deps
                console.print(f"  📦 {module.name}: {', '.join(all_module_deps)}")
            else:
                console.print(f"  📦 {module.name}: нет зависимостей")
        else:
            console.print(f"  📦 {module.name}: манифест не найден")

    if not all_dependencies:
        console.print("[yellow]Не найдено зависимостей в активных модулях.[/]")
        return

    # Формируем результат
    if format == "requirements":
        result = "\n".join(sorted(all_dependencies))
    elif format == "pip-tools":
        result = "# requirements.txt для активных модулей\n"
        result += "\n".join(sorted(all_dependencies))
    else:
        console.print(f"[bold red]Неизвестный формат: {format}[/]")
        raise typer.Exit(code=1)

    # Выводим или сохраняем результат
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)
            console.print(f"[green]Зависимости сохранены в файл: {output_file}[/]")
        except Exception as e:
            console.print(f"[bold red]Ошибка при сохранении в файл: {e}[/]")
            raise typer.Exit(code=1)
    else:
        console.print(f"\n[bold green]Собранные зависимости:[/]")
        console.print(result)

    console.print(f"\n[cyan]Статистика:[/]")
    console.print(f"  📦 Модулей с зависимостями: {len(module_deps)}")
    console.print(f"  📋 Всего уникальных зависимостей: {len(all_dependencies)}")


if __name__ == "__main__":
    module_app()
