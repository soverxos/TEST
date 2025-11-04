"""
Примеры продвинутых функций универсального шаблона модуля

Этот файл содержит сложные примеры использования компонентов
шаблона для создания мощных и функциональных модулей.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from .services import TemplateService
from .utils import check_permission, log_module_action, validate_input
from .permissions import PERMISSIONS
from .keyboards import get_confirmation_keyboard, get_simple_back_keyboard
from .callback_data_factories import create_fsm_callback, create_item_callback

# === ПРИМЕР 1: МНОГОШАГОВЫЙ FSM ДИАЛОГ С ВАЛИДАЦИЕЙ ===

class AdvancedStates(StatesGroup):
    """Состояния для продвинутого FSM диалога"""
    waiting_project_name = State()
    waiting_project_description = State()
    waiting_project_deadline = State()
    waiting_project_priority = State()
    waiting_project_tags = State()
    confirming_creation = State()

advanced_router = Router(name="advanced_examples")

@advanced_router.message(Command("advanced_dialog"))
async def start_advanced_dialog(message: types.Message, state: FSMContext, services):
    """
    Начало продвинутого многошагового диалога
    
    Этот пример показывает создание сложного диалога с валидацией
    и возможностью возврата к предыдущим шагам.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.MANAGE_DATA):
        await message.answer("❌ Нет прав на создание проектов")
        return
    
    await state.set_state(AdvancedStates.waiting_project_name)
    await state.update_data({
        "step": 0,
        "total_steps": 5,
        "project_data": {}
    })
    
    keyboard = get_navigation_keyboard(0, 5, can_go_back=False)
    await message.answer(
        "🚀 **Создание проекта**\n\n"
        "Шаг 1/5: Название проекта\n\n"
        "Введите название вашего проекта:",
        reply_markup=keyboard
    )

@advanced_router.message(StateFilter(AdvancedStates.waiting_project_name))
async def process_project_name(message: types.Message, state: FSMContext):
    """Обработка названия проекта"""
    if not validate_input(message.text, min_length=3, max_length=100):
        await message.answer("❌ Название должно содержать от 3 до 100 символов")
        return
    
    data = await state.get_data()
    data["project_data"]["name"] = message.text
    data["step"] = 1
    await state.set_data(data)
    
    await state.set_state(AdvancedStates.waiting_project_description)
    keyboard = get_navigation_keyboard(1, 5, can_go_back=True)
    
    await message.answer(
        f"✅ Название сохранено: **{message.text}**\n\n"
        "Шаг 2/5: Описание проекта\n\n"
        "Введите подробное описание проекта:",
        reply_markup=keyboard
    )

@advanced_router.message(StateFilter(AdvancedStates.waiting_project_description))
async def process_project_description(message: types.Message, state: FSMContext):
    """Обработка описания проекта"""
    if not validate_input(message.text, min_length=10, max_length=1000):
        await message.answer("❌ Описание должно содержать от 10 до 1000 символов")
        return
    
    data = await state.get_data()
    data["project_data"]["description"] = message.text
    data["step"] = 2
    await state.set_data(data)
    
    await state.set_state(AdvancedStates.waiting_project_deadline)
    keyboard = get_navigation_keyboard(2, 5, can_go_back=True)
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/5: Срок выполнения\n\n"
        "Введите дату окончания проекта в формате ДД.ММ.ГГГГ:",
        reply_markup=keyboard
    )

@advanced_router.message(StateFilter(AdvancedStates.waiting_project_deadline))
async def process_project_deadline(message: types.Message, state: FSMContext):
    """Обработка срока выполнения"""
    try:
        deadline = datetime.strptime(message.text, "%d.%m.%Y")
        if deadline <= datetime.now():
            await message.answer("❌ Дата должна быть в будущем")
            return
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return
    
    data = await state.get_data()
    data["project_data"]["deadline"] = deadline
    data["step"] = 3
    await state.set_data(data)
    
    await state.set_state(AdvancedStates.waiting_project_priority)
    keyboard = get_navigation_keyboard(3, 5, can_go_back=True)
    
    await message.answer(
        f"✅ Срок установлен: **{deadline.strftime('%d.%m.%Y')}**\n\n"
        "Шаг 4/5: Приоритет проекта\n\n"
        "Введите приоритет от 1 до 10 (1 - низкий, 10 - высокий):",
        reply_markup=keyboard
    )

@advanced_router.message(StateFilter(AdvancedStates.waiting_project_priority))
async def process_project_priority(message: types.Message, state: FSMContext):
    """Обработка приоритета проекта"""
    try:
        priority = int(message.text)
        if priority < 1 or priority > 10:
            await message.answer("❌ Приоритет должен быть от 1 до 10")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 10")
        return
    
    data = await state.get_data()
    data["project_data"]["priority"] = priority
    data["step"] = 4
    await state.set_data(data)
    
    await state.set_state(AdvancedStates.waiting_project_tags)
    keyboard = get_navigation_keyboard(4, 5, can_go_back=True)
    
    await message.answer(
        f"✅ Приоритет установлен: **{priority}**\n\n"
        "Шаг 5/5: Теги проекта\n\n"
        "Введите теги через запятую (например: важный, срочный, работа):",
        reply_markup=keyboard
    )

@advanced_router.message(StateFilter(AdvancedStates.waiting_project_tags))
async def process_project_tags(message: types.Message, state: FSMContext):
    """Обработка тегов проекта"""
    tags = [tag.strip() for tag in message.text.split(",") if tag.strip()]
    
    if len(tags) > 10:
        await message.answer("❌ Максимум 10 тегов")
        return
    
    data = await state.get_data()
    data["project_data"]["tags"] = tags
    await state.set_data(data)
    
    await state.set_state(AdvancedStates.confirming_creation)
    
    # Показываем сводку для подтверждения
    project_data = data["project_data"]
    summary = (
        f"📋 **Сводка проекта**\n\n"
        f"**Название:** {project_data['name']}\n"
        f"**Описание:** {project_data['description'][:100]}{'...' if len(project_data['description']) > 100 else ''}\n"
        f"**Срок:** {project_data['deadline'].strftime('%d.%m.%Y')}\n"
        f"**Приоритет:** {project_data['priority']}/10\n"
        f"**Теги:** {', '.join(project_data['tags'])}\n\n"
        f"Создать проект?"
    )
    
    keyboard = get_confirmation_keyboard("create_project")
    await message.answer(summary, reply_markup=keyboard)

# === ПРИМЕР 2: АСИНХРОННАЯ ОБРАБОТКА С ПРОГРЕССОМ ===

@advanced_router.message(Command("async_processing"))
async def async_processing_example(message: types.Message, services):
    """
    Пример асинхронной обработки с показом прогресса
    
    Этот пример показывает, как выполнять длительные операции
    с обновлением прогресса для пользователя.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADVANCED):
        await message.answer("❌ Нет доступа к продвинутым функциям")
        return
    
    # Отправляем начальное сообщение
    progress_msg = await message.answer("⏳ **Обработка данных...**\n\n🔄 Подготовка...")
    
    try:
        # Имитируем длительную обработку
        total_steps = 10
        for i in range(total_steps):
            # Обновляем прогресс
            progress_bar = "█" * (i + 1) + "░" * (total_steps - i - 1)
            progress_text = (
                f"⏳ **Обработка данных...**\n\n"
                f"🔄 Шаг {i + 1}/{total_steps}\n"
                f"`{progress_bar}` {((i + 1) / total_steps * 100):.0f}%\n\n"
                f"Обрабатываю данные..."
            )
            
            await progress_msg.edit_text(progress_text)
            
            # Имитируем работу
            await asyncio.sleep(1)
        
        # Завершение
        await progress_msg.edit_text(
            "✅ **Обработка завершена!**\n\n"
            "Все данные успешно обработаны."
        )
        
    except Exception as e:
        logger.error(f"Ошибка в async_processing_example: {e}")
        await progress_msg.edit_text("❌ Произошла ошибка при обработке данных")

# === ПРИМЕР 3: РАБОТА С ФАЙЛАМИ ===

@advanced_router.message(Command("file_processing"))
async def file_processing_example(message: types.Message, services):
    """
    Пример обработки файлов
    
    Этот пример показывает, как работать с файлами,
    загруженными пользователями.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.MANAGE_DATA):
        await message.answer("❌ Нет прав на обработку файлов")
        return
    
    await message.answer(
        "📁 **Обработка файлов**\n\n"
        "Отправьте файл для обработки.\n\n"
        "Поддерживаемые форматы:\n"
        "• Текстовые файлы (.txt, .md)\n"
        "• Изображения (.jpg, .png)\n"
        "• Документы (.pdf, .docx)"
    )

@advanced_router.message(F.document)
async def process_document(message: types.Message, services):
    """Обработка загруженного документа"""
    if not await check_permission(services, message.from_user.id, PERMISSIONS.MANAGE_DATA):
        return
    
    document = message.document
    
    # Проверяем размер файла (максимум 10 МБ)
    max_size = 10 * 1024 * 1024  # 10 МБ
    if document.file_size > max_size:
        await message.answer("❌ Файл слишком большой. Максимальный размер: 10 МБ")
        return
    
    # Проверяем тип файла
    allowed_extensions = ['.txt', '.md', '.jpg', '.png', '.pdf', '.docx']
    file_extension = document.file_name.split('.')[-1].lower() if document.file_name else ''
    
    if f'.{file_extension}' not in allowed_extensions:
        await message.answer(
            f"❌ Неподдерживаемый формат файла: .{file_extension}\n\n"
            f"Поддерживаемые форматы: {', '.join(allowed_extensions)}"
        )
        return
    
    # Показываем информацию о файле
    file_info = (
        f"📄 **Информация о файле**\n\n"
        f"**Имя:** {document.file_name}\n"
        f"**Размер:** {document.file_size / 1024:.1f} КБ\n"
        f"**Тип:** {document.mime_type}\n"
        f"**ID файла:** {document.file_id}\n\n"
        f"Файл готов к обработке!"
    )
    
    await message.answer(file_info)

# === ПРИМЕР 4: РАБОТА С ВНЕШНИМИ API ===

import aiohttp
import json

@advanced_router.message(Command("api_example"))
async def api_example(message: types.Message, services):
    """
    Пример работы с внешними API
    
    Этот пример показывает, как делать запросы к внешним сервисам
    и обрабатывать ответы.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADVANCED):
        await message.answer("❌ Нет доступа к API функциям")
        return
    
    # Получаем настройки модуля
    settings = services.modules.get_module_settings("my_module") or {}
    api_key = settings.get('api_key', '')
    
    if not api_key:
        await message.answer(
            "❌ **API ключ не настроен**\n\n"
            "Для использования API функций необходимо настроить API ключ в настройках модуля."
        )
        return
    
    loading_msg = await message.answer("⏳ Запрашиваю данные из API...")
    
    try:
        # Пример запроса к внешнему API
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Имитируем API запрос
            async with session.get(
                'https://api.example.com/data',
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    await loading_msg.edit_text(
                        f"✅ **Данные получены из API**\n\n"
                        f"**Статус:** {response.status}\n"
                        f"**Записей:** {len(data.get('items', []))}\n"
                        f"**Время ответа:** {response.headers.get('X-Response-Time', 'N/A')}"
                    )
                else:
                    await loading_msg.edit_text(
                        f"❌ **Ошибка API**\n\n"
                        f"**Статус:** {response.status}\n"
                        f"**Сообщение:** {await response.text()}"
                    )
    
    except asyncio.TimeoutError:
        await loading_msg.edit_text("❌ Превышено время ожидания ответа от API")
    except aiohttp.ClientError as e:
        await loading_msg.edit_text(f"❌ Ошибка соединения с API: {e}")
    except Exception as e:
        logger.error(f"Ошибка в api_example: {e}")
        await loading_msg.edit_text("❌ Произошла неожиданная ошибка")

# === ПРИМЕР 5: КЭШИРОВАНИЕ ДАННЫХ ===

@advanced_router.message(Command("cache_example"))
async def cache_example(message: types.Message, services):
    """
    Пример использования кэширования
    
    Этот пример показывает, как использовать кэш для
    оптимизации производительности.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.VIEW_DATA):
        await message.answer("❌ Нет доступа к данным")
        return
    
    cache_key = f"user_stats_{message.from_user.id}"
    
    try:
        # Пытаемся получить данные из кэша
        cached_data = await services.cache.get(cache_key)
        
        if cached_data:
            await message.answer(
                f"📊 **Статистика (из кэша)**\n\n"
                f"**Данные:** {cached_data}\n"
                f"**Источник:** Кэш"
            )
        else:
            # Если данных нет в кэше, получаем их из БД
            template_service = TemplateService(services, services.modules.get_module_settings("my_module") or {})
            stats = await template_service.get_user_stats(message.from_user.id)
            
            # Сохраняем в кэш на 5 минут
            await services.cache.set(cache_key, stats, ttl=300)
            
            await message.answer(
                f"📊 **Статистика (из БД)**\n\n"
                f"**Данные:** {stats}\n"
                f"**Источник:** База данных\n"
                f"**Кэшировано:** Да (5 минут)"
            )
    
    except Exception as e:
        logger.error(f"Ошибка в cache_example: {e}")
        await message.answer("❌ Ошибка работы с кэшем")

# === ПРИМЕР 6: ПАГИНАЦИЯ И ФИЛЬТРАЦИЯ ===

@advanced_router.message(Command("pagination_example"))
async def pagination_example(message: types.Message, services):
    """
    Пример пагинации и фильтрации данных
    
    Этот пример показывает, как реализовать пагинацию
    и фильтрацию больших объемов данных.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.VIEW_DATA):
        await message.answer("❌ Нет доступа к данным")
        return
    
    # Получаем аргументы команды
    args = message.text.split()[1:]
    page = 0
    filter_type = "all"
    
    if len(args) >= 1:
        try:
            page = int(args[0]) - 1  # Пользователь вводит с 1, мы работаем с 0
            if page < 0:
                page = 0
        except ValueError:
            pass
    
    if len(args) >= 2:
        filter_type = args[1].lower()
    
    # Получаем данные с пагинацией
    template_service = TemplateService(services, services.modules.get_module_settings("my_module") or {})
    items = await template_service.get_user_items(message.from_user.id)
    
    # Применяем фильтры
    if filter_type == "active":
        items = [item for item in items if item.is_active]
    elif filter_type == "public":
        items = [item for item in items if item.is_public]
    elif filter_type == "high_priority":
        items = [item for item in items if item.priority >= 7]
    
    # Пагинация
    per_page = 5
    total_pages = (len(items) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_items = items[start_idx:end_idx]
    
    # Формируем сообщение
    filter_names = {
        "all": "Все",
        "active": "Активные",
        "public": "Публичные",
        "high_priority": "Высокий приоритет"
    }
    
    message_text = (
        f"📋 **Список элементов**\n\n"
        f"**Фильтр:** {filter_names.get(filter_type, 'Все')}\n"
        f"**Страница:** {page + 1}/{total_pages}\n"
        f"**Всего элементов:** {len(items)}\n\n"
    )
    
    if page_items:
        for i, item in enumerate(page_items, start=start_idx + 1):
            message_text += f"{i}. **{item.title}** (приоритет: {item.priority})\n"
    else:
        message_text += "Элементы не найдены"
    
    # Создаем клавиатуру с пагинацией
    keyboard = get_pagination_keyboard(page, total_pages, filter_type)
    await message.answer(message_text, reply_markup=keyboard)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_navigation_keyboard(current_step: int, total_steps: int, can_go_back: bool = True) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру навигации для FSM диалога"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    if can_go_back and current_step > 0:
        builder.row(
            types.InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=create_fsm_callback("prev_step", current_step - 1)
            )
        )
    
    if current_step < total_steps - 1:
        builder.row(
            types.InlineKeyboardButton(
                text="⏭️ Пропустить",
                callback_data=create_fsm_callback("skip_step", current_step)
            )
        )
    
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=create_fsm_callback("cancel")
        )
    )
    
    return builder.as_markup()

def get_pagination_keyboard(current_page: int, total_pages: int, filter_type: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру пагинации"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    nav_buttons = []
    
    if current_page > 0:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="◀️",
                callback_data=create_fsm_callback("pagination", current_page - 1, filter_type)
            )
        )
    
    nav_buttons.append(
        types.InlineKeyboardButton(
            text=f"{current_page + 1}/{total_pages}",
            callback_data="noop"
        )
    )
    
    if current_page < total_pages - 1:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="▶️",
                callback_data=create_fsm_callback("pagination", current_page + 1, filter_type)
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки фильтров
    filter_buttons = [
        types.InlineKeyboardButton(
            text="📋 Все",
            callback_data=create_fsm_callback("filter", 0, "all")
        ),
        types.InlineKeyboardButton(
            text="✅ Активные",
            callback_data=create_fsm_callback("filter", 0, "active")
        ),
        types.InlineKeyboardButton(
            text="🌐 Публичные",
            callback_data=create_fsm_callback("filter", 0, "public")
        )
    ]
    
    builder.row(*filter_buttons)
    
    return builder.as_markup()
