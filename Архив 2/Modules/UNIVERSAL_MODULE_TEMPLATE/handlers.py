"""
Обработчики команд и сообщений для универсального шаблона модуля

Этот файл содержит все обработчики для:
- Команд бота
- Callback запросов от inline кнопок
- FSM диалогов
- Обычных сообщений
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from loguru import logger
from typing import TYPE_CHECKING

from .keyboards import (
    get_main_menu_keyboard, get_admin_menu_keyboard, get_settings_keyboard,
    get_items_list_keyboard, get_item_detail_keyboard, get_confirmation_keyboard,
    get_fsm_navigation_keyboard, get_user_management_keyboard,
    get_simple_back_keyboard, get_yes_no_keyboard
)
from .callback_data_factories import (
    TemplateCallback, TemplateAdminCallback, TemplateDataCallback,
    TemplateSettingsCallback, TemplateFSMCallback,
    TemplateAction, TemplateAdminAction, TemplateDataAction,
    parse_template_callback, parse_admin_callback, parse_data_callback,
    parse_settings_callback, parse_fsm_callback,
    create_stats_callback, create_settings_callback, create_admin_panel_callback
)
from .permissions import MODULE_NAME, PERMISSIONS
from .services import TemplateService
from .utils import check_permission, validate_input, log_module_action

# Дополнительные константы модуля
MODULE_DISPLAY_NAME = "Универсальный Шаблон Модуля"
MODULE_VERSION = "1.0.0"

# Вспомогательная функция для получения сервисов
def get_services():
    """Получает провайдер сервисов"""
    try:
        from core.services_provider import get_services_provider
        return get_services_provider()
    except ImportError:
        return None

if TYPE_CHECKING:
    from core.services_provider import BotServicesProvider

# Создаем роутер
template_router = Router(name=MODULE_NAME)

# FSM состояния для диалогов
class TemplateStates(StatesGroup):
    """Состояния для FSM диалогов"""
    waiting_input = State()
    waiting_title = State()
    waiting_description = State()
    waiting_priority = State()
    processing = State()
    confirming_action = State()

# === ОБРАБОТЧИКИ КОМАНД ===

@template_router.message(Command("template"))
async def template_command(message: types.Message):
    """
    Главная команда модуля - /template
    
    Показывает главное меню модуля с основными действиями.
    """
    services = get_services()
    if services and not await check_permission(services, message.from_user.id, PERMISSIONS.ACCESS):
        await message.answer("❌ У вас нет доступа к этому модулю")
        return
    
    # Логируем использование команды
    if services:
        log_module_action(services, "template_command", message.from_user.id)
    
    keyboard = get_main_menu_keyboard()
    await message.answer(
        "🔧 **Универсальный шаблон модуля**\n\n"
        "Добро пожаловать в демонстрационный модуль!\n"
        "Здесь показаны все возможности системы модулей SDB.\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@template_router.message(Command("template_admin"))
async def template_admin_command(message: types.Message):
    """
    Административная команда модуля - /template_admin
    
    Показывает админ панель модуля.
    """
    services = get_services()
    if services and not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ У вас нет прав администратора для этого модуля")
        return
    
    if services:
        log_module_action(services, "template_admin_command", message.from_user.id)
    
    keyboard = get_admin_menu_keyboard()
    await message.answer(
        "⚙️ **Административная панель**\n\n"
        "Управление модулем и пользователями.\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@template_router.message(Command("template_fsm"))
async def template_fsm_command(message: types.Message, state: FSMContext):
    """
    Команда для демонстрации FSM диалога - /template_fsm
    """
    services = get_services()
    if services and not await check_permission(services, message.from_user.id, PERMISSIONS.ACCESS):
        await message.answer("❌ У вас нет доступа к этому модулю")
        return
    
    if services:
        log_module_action(services, "template_fsm_command", message.from_user.id)
    
    await state.set_state(TemplateStates.waiting_title)
    keyboard = get_fsm_navigation_keyboard(0, 3, can_skip=True)
    
    await message.answer(
        "🗣️ **FSM Диалог - Создание элемента**\n\n"
        "Шаг 1/3: Введите заголовок элемента\n\n"
        "Отправьте сообщение с заголовком:",
        reply_markup=keyboard
    )

# === ОБРАБОТЧИКИ CALLBACK ЗАПРОСОВ ===

@template_router.callback_query(TemplateCallback.filter(F.action == TemplateAction.MAIN_MENU))
async def main_menu_callback(callback: types.CallbackQuery):
    """Главное меню"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ACCESS):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    keyboard = get_main_menu_keyboard()
    text = "🔧 **Главное меню**\n\nВыберите действие:"
    
    try:
        if callback.message and (callback.message.text != text or callback.message.reply_markup != keyboard):
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard
            )
        else:
            logger.trace(f"[{MODULE_NAME}] Сообщение главного меню не было изменено.")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.trace(f"[{MODULE_NAME}] Сообщение главного меню не было изменено (поймано исключение).")
        else:
            logger.warning(f"[{MODULE_NAME}] Ошибка редактирования сообщения главного меню: {e}")
    except Exception as e_edit:
        logger.error(f"[{MODULE_NAME}] Непредвиденная ошибка в main_menu_callback: {e_edit}", exc_info=True)
    
    await callback.answer()

@template_router.callback_query(TemplateCallback.filter(F.action == TemplateAction.ADMIN_PANEL))
async def admin_panel_callback(callback: types.CallbackQuery):
    """Админ панель"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ADMIN):
        await callback.answer("❌ Нет прав администратора", show_alert=True)
        return
    
    keyboard = get_admin_menu_keyboard()
    text = "⚙️ **Административная панель**\n\nВыберите действие:"
    
    try:
        if callback.message and (callback.message.text != text or callback.message.reply_markup != keyboard):
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard
            )
        else:
            logger.trace(f"[{MODULE_NAME}] Сообщение админ-панели не было изменено.")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.trace(f"[{MODULE_NAME}] Сообщение админ-панели не было изменено (поймано исключение).")
        else:
            logger.warning(f"[{MODULE_NAME}] Ошибка редактирования сообщения админ-панели: {e}")
    except Exception as e_edit:
        logger.error(f"[{MODULE_NAME}] Непредвиденная ошибка в admin_panel_callback: {e_edit}", exc_info=True)
    
    await callback.answer()

@template_router.callback_query(TemplateCallback.filter(F.action == TemplateAction.SHOW_STATS))
async def show_stats_callback(callback: types.CallbackQuery):
    """Показать статистику"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.VIEW_DATA):
        await callback.answer("❌ Нет доступа к просмотру данных", show_alert=True)
        return
    
    # Получаем статистику
    if not services:
        await callback.answer("❌ Сервисы недоступны", show_alert=True)
        return
    template_service = TemplateService(services, services.modules.get_module_settings(MODULE_NAME) or {})
    user_stats = await template_service.get_user_stats(callback.from_user.id)
    global_stats = await template_service.get_global_stats()
    
    stats_text = (
        "📊 **Статистика модуля**\n\n"
        f"**Ваша статистика:**\n"
        f"• Создано элементов: {user_stats.get('items_created', 0)}\n"
        f"• Активных элементов: {user_stats.get('active_items', 0)}\n"
        f"• Публичных элементов: {user_stats.get('public_items', 0)}\n"
        f"• Лимит: {user_stats.get('max_items', 0)}\n"
        f"• Можно создать еще: {'Да' if user_stats.get('can_create_more', False) else 'Нет'}\n\n"
        f"**Глобальная статистика:**\n"
        f"• Всего элементов: {global_stats.get('total_items', 0)}\n"
        f"• Активных элементов: {global_stats.get('active_items', 0)}\n"
        f"• Уникальных пользователей: {global_stats.get('unique_users', 0)}"
    )
    
    keyboard = get_simple_back_keyboard("main_menu")
    
    try:
        if callback.message and (callback.message.text != stats_text or callback.message.reply_markup != keyboard):
            await callback.message.edit_text(stats_text, reply_markup=keyboard)
        else:
            logger.trace(f"[{MODULE_NAME}] Сообщение статистики не было изменено.")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.trace(f"[{MODULE_NAME}] Сообщение статистики не было изменено (поймано исключение).")
        else:
            logger.warning(f"[{MODULE_NAME}] Ошибка редактирования сообщения статистики: {e}")
    except Exception as e_edit:
        logger.error(f"[{MODULE_NAME}] Непредвиденная ошибка в show_stats_callback: {e_edit}", exc_info=True)
    
    await callback.answer()

@template_router.callback_query(TemplateCallback.filter(F.action == TemplateAction.SHOW_SETTINGS))
async def show_settings_callback(callback: types.CallbackQuery):
    """Показать настройки"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ACCESS):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Получаем настройки модуля
    if not services:
        await callback.answer("❌ Сервисы недоступны", show_alert=True)
        return
    settings = services.modules.get_module_settings(MODULE_NAME) or {}
    
    keyboard = get_settings_keyboard(settings)
    await callback.message.edit_text(
        "⚙️ **Настройки модуля**\n\n"
        "Настройте параметры модуля:",
        reply_markup=keyboard
    )
    await callback.answer()

@template_router.callback_query(TemplateCallback.filter(F.action == TemplateAction.START_INPUT))
async def start_input_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать ввод данных"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.MANAGE_DATA):
        await callback.answer("❌ Нет прав на создание элементов", show_alert=True)
        return
    
    await state.set_state(TemplateStates.waiting_title)
    await state.update_data(step=0, total_steps=3)
    
    keyboard = get_fsm_navigation_keyboard(0, 3, can_skip=True)
    await callback.message.edit_text(
        "📝 **Создание элемента**\n\n"
        "Шаг 1 из 3: Введите заголовок\n\n"
        "Отправьте заголовок для нового элемента:",
        reply_markup=keyboard
    )
    await callback.answer()

@template_router.callback_query(TemplateCallback.filter(F.action == TemplateAction.BACK))
async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' - возвращает в главное меню модуля"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ACCESS):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Очищаем состояние FSM, если оно есть
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    # Показываем главное меню
    keyboard = get_main_menu_keyboard()
    text = (
        f"🎯 **{MODULE_DISPLAY_NAME}**\n\n"
        f"Добро пожаловать в универсальный шаблон модуля!\n\n"
        f"📊 **Статистика:**\n"
        f"• Версия: {MODULE_VERSION}\n"
        f"• Статус: Активен\n\n"
        f"Выберите действие:"
    )
    
    try:
        if callback.message and (callback.message.text != text or callback.message.reply_markup != keyboard):
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard
            )
        else:
            logger.trace(f"[{MODULE_NAME}] Сообщение главного меню не было изменено.")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.trace(f"[{MODULE_NAME}] Сообщение главного меню не было изменено (поймано исключение).")
        else:
            logger.warning(f"[{MODULE_NAME}] Ошибка редактирования сообщения главного меню: {e}")
    except Exception as e_edit:
        logger.error(f"[{MODULE_NAME}] Непредвиденная ошибка в back_callback: {e_edit}", exc_info=True)
    
    await callback.answer()

# === ОБРАБОТЧИКИ АДМИН ДЕЙСТВИЙ ===

@template_router.callback_query(TemplateAdminCallback.filter(F.action == TemplateAdminAction.MANAGE_USERS))
async def manage_users_callback(callback: types.CallbackQuery):
    """Управление пользователями"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ADMIN):
        await callback.answer("❌ Нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👥 **Управление пользователями**\n\n"
        "Функция в разработке...",
        reply_markup=get_simple_back_keyboard("admin_panel")
    )
    await callback.answer()

@template_router.callback_query(TemplateAdminCallback.filter(F.action == TemplateAdminAction.SYSTEM_STATS))
async def system_stats_callback(callback: types.CallbackQuery):
    """Системная статистика"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ADMIN):
        await callback.answer("❌ Нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📈 **Системная статистика**\n\n"
        "Функция в разработке...",
        reply_markup=get_simple_back_keyboard("admin_panel")
    )
    await callback.answer()

@template_router.callback_query(TemplateAdminCallback.filter(F.action == TemplateAdminAction.MODULE_SETTINGS))
async def module_settings_callback(callback: types.CallbackQuery):
    """Настройки модуля"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.ADMIN):
        await callback.answer("❌ Нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔧 **Настройки модуля**\n\n"
        "Функция в разработке...",
        reply_markup=get_simple_back_keyboard("admin_panel")
    )
    await callback.answer()

# === ОБРАБОТЧИКИ FSM ДИАЛОГОВ ===

@template_router.callback_query(TemplateFSMCallback.filter(F.action == "create_item"))
async def start_create_item_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать создание элемента"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.MANAGE_DATA):
        await callback.answer("❌ Нет прав на создание элементов", show_alert=True)
        return
    
    await state.set_state(TemplateStates.waiting_title)
    await state.update_data(step=0, total_steps=3)
    
    keyboard = get_fsm_navigation_keyboard(0, 3, can_skip=True)
    await callback.message.edit_text(
        "🗣️ **Создание элемента**\n\n"
        "Шаг 1/3: Введите заголовок элемента\n\n"
        "Отправьте сообщение с заголовком:",
        reply_markup=keyboard
    )
    await callback.answer()

@template_router.message(StateFilter(TemplateStates.waiting_title))
async def process_title_input(message: types.Message, state: FSMContext):
    """Обработка ввода заголовка"""
    if not validate_input(message.text, min_length=1, max_length=255):
        await message.answer("❌ Заголовок должен содержать от 1 до 255 символов")
        return
    
    await state.update_data(title=message.text)
    await state.set_state(TemplateStates.waiting_description)
    
    keyboard = get_fsm_navigation_keyboard(1, 3, can_skip=True)
    await message.answer(
        "✅ Заголовок сохранен!\n\n"
        "Шаг 2/3: Введите описание элемента\n\n"
        "Отправьте сообщение с описанием:",
        reply_markup=keyboard
    )

@template_router.message(StateFilter(TemplateStates.waiting_description))
async def process_description_input(message: types.Message, state: FSMContext):
    """Обработка ввода описания"""
    if not validate_input(message.text, min_length=0, max_length=1000):
        await message.answer("❌ Описание должно содержать не более 1000 символов")
        return
    
    await state.update_data(description=message.text)
    await state.set_state(TemplateStates.waiting_priority)
    
    keyboard = get_fsm_navigation_keyboard(2, 3, can_skip=False)
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/3: Введите приоритет элемента (0-100)\n\n"
        "Отправьте число от 0 до 100:",
        reply_markup=keyboard
    )

@template_router.message(StateFilter(TemplateStates.waiting_priority))
async def process_priority_input(message: types.Message, state: FSMContext):
    """Обработка ввода приоритета"""
    services = get_services()
    if not services:
        await message.answer("❌ Сервисы недоступны")
        return
    
    try:
        priority = int(message.text)
        if priority < 0 or priority > 100:
            await message.answer("❌ Приоритет должен быть от 0 до 100")
            return
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return
    
    await state.update_data(priority=priority)
    await state.set_state(TemplateStates.processing)
    
    # Показываем индикатор загрузки
    processing_msg = await message.answer("⏳ Создаю элемент...")
    
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        
        # Создаем элемент через сервис
        template_service = TemplateService(services, services.modules.get_module_settings(MODULE_NAME) or {})
        new_item = await template_service.create_item(
            user_id=message.from_user.id,
            title=data['title'],
            description=data['description'],
            priority=priority
        )
        
        if new_item:
            await processing_msg.edit_text(
                f"✅ **Элемент успешно создан!**\n\n"
                f"**ID:** {new_item.id}\n"
                f"**Заголовок:** {new_item.title}\n"
                f"**Описание:** {new_item.description}\n"
                f"**Приоритет:** {new_item.priority}\n"
                f"**Создан:** {new_item.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            await processing_msg.edit_text("❌ Не удалось создать элемент. Возможно, превышен лимит элементов.")
        
    except Exception as e:
        logger.error(f"Ошибка создания элемента: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при создании элемента")
    
    finally:
        await state.clear()

# === ОБРАБОТЧИКИ ДЕЙСТВИЙ С ДАННЫМИ ===

@template_router.callback_query(TemplateDataCallback.filter(F.action == TemplateDataAction.LIST_ITEMS))
async def list_items_callback(callback: types.CallbackQuery):
    """Список элементов пользователя"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.VIEW_DATA):
        await callback.answer("❌ Нет доступа к просмотру данных", show_alert=True)
        return
    
    # Получаем элементы пользователя
    if not services:
        await callback.answer("❌ Сервисы недоступны", show_alert=True)
        return
    template_service = TemplateService(services, services.modules.get_module_settings(MODULE_NAME) or {})
    items = await template_service.get_user_items(callback.from_user.id)
    
    if not items:
        keyboard = get_simple_back_keyboard("main_menu")
        await callback.message.edit_text(
            "📋 **Мои элементы**\n\n"
            "У вас пока нет созданных элементов.\n\n"
            "Создайте первый элемент, нажав кнопку ниже:",
            reply_markup=keyboard
        )
    else:
        # Конвертируем в формат для клавиатуры
        items_data = [{"id": item.id, "title": item.title} for item in items]
        keyboard = get_items_list_keyboard(items_data)
        
        await callback.message.edit_text(
            f"📋 **Мои элементы**\n\n"
            f"Найдено элементов: {len(items)}\n\n"
            f"Выберите элемент для просмотра:",
            reply_markup=keyboard
        )
    
    await callback.answer()

@template_router.callback_query(TemplateDataCallback.filter(F.action == TemplateDataAction.VIEW_ITEM))
async def view_item_callback(callback: types.CallbackQuery):
    """Просмотр элемента"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.VIEW_DATA):
        await callback.answer("❌ Нет доступа к просмотру данных", show_alert=True)
        return
    
    # Получаем ID элемента из callback data
    callback_data = parse_data_callback(callback.data)
    if not callback_data or not callback_data.item_id:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    # Получаем элемент
    if not services:
        await callback.answer("❌ Сервисы недоступны", show_alert=True)
        return
    template_service = TemplateService(services, services.modules.get_module_settings(MODULE_NAME) or {})
    item = await template_service.get_item_by_id(callback_data.item_id, callback.from_user.id)
    
    if not item:
        await callback.answer("❌ Элемент не найден", show_alert=True)
        return
    
    # Формируем текст
    item_text = (
        f"📄 **{item.title}**\n\n"
        f"**Описание:** {item.description or 'Не указано'}\n"
        f"**Приоритет:** {item.priority}\n"
        f"**Статус:** {'✅ Активен' if item.is_active else '❌ Неактивен'}\n"
        f"**Публичный:** {'✅ Да' if item.is_public else '❌ Нет'}\n"
        f"**Создан:** {item.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"**Обновлен:** {item.updated_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    if item.tags:
        item_text += f"\n**Теги:** {item.tags}"
    
    keyboard = get_item_detail_keyboard(item.id, is_owner=True)
    await callback.message.edit_text(item_text, reply_markup=keyboard)
    await callback.answer()

@template_router.callback_query(TemplateDataCallback.filter(F.action == TemplateDataAction.DELETE_ITEM))
async def delete_item_callback(callback: types.CallbackQuery):
    """Удаление элемента"""
    services = get_services()
    if services and not await check_permission(services, callback.from_user.id, PERMISSIONS.MANAGE_DATA):
        await callback.answer("❌ Нет прав на удаление элементов", show_alert=True)
        return
    
    # Получаем ID элемента
    callback_data = parse_data_callback(callback.data)
    if not callback_data or not callback_data.item_id:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    # Получаем элемент для подтверждения
    if not services:
        await callback.answer("❌ Сервисы недоступны", show_alert=True)
        return
    template_service = TemplateService(services, services.modules.get_module_settings(MODULE_NAME) or {})
    item = await template_service.get_item_by_id(callback_data.item_id, callback.from_user.id)
    
    if not item:
        await callback.answer("❌ Элемент не найден", show_alert=True)
        return
    
    # Показываем подтверждение
    keyboard = get_confirmation_keyboard("delete_item", callback_data.item_id)
    await callback.message.edit_text(
        f"🗑️ **Подтверждение удаления**\n\n"
        f"Вы действительно хотите удалить элемент:\n"
        f"**{item.title}**\n\n"
        f"⚠️ Это действие нельзя отменить!",
        reply_markup=keyboard
    )
    await callback.answer()

# === ОБРАБОТЧИКИ ОШИБОК ===

@template_router.callback_query(lambda c: c.data == f"sdb_core_module_entry:{MODULE_NAME}")
async def handle_module_entry(callback: types.CallbackQuery):
    """Обработчик входа в модуль через UI"""
    user_id = callback.from_user.id
    
    # Получаем сервисы через глобальный доступ
    try:
        from Systems.core.services_provider import get_services_provider
        services = get_services_provider()
    except ImportError:
        # Если нет глобального доступа, пропускаем проверку разрешений
        services = None
    
    # Проверяем разрешения (если есть доступ к сервисам)
    if services and not await check_permission(services, user_id, PERMISSIONS.ACCESS):
        await callback.answer("❌ У вас нет доступа к этому модулю", show_alert=True)
        return
    
    # Показываем главное меню модуля с кнопкой "Назад" в список модулей системы
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from Systems.core.ui.callback_data_factories import CoreMenuNavigate
    
    # Создаем клавиатуру главного меню модуля с кнопкой "Назад к модулям"
    builder = InlineKeyboardBuilder()
    
    # Основные действия
    builder.row(
        InlineKeyboardButton(
            text="📝 Создать элемент",
            callback_data=TemplateCallback(action=TemplateAction.START_INPUT).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📋 Мои элементы",
            callback_data=TemplateDataCallback(action=TemplateDataAction.LIST_ITEMS).pack()
        ),
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data=create_stats_callback()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data=create_settings_callback()
        ),
        InlineKeyboardButton(
            text="🔧 Админ панель",
            callback_data=create_admin_panel_callback()
        )
    )
    
    # Кнопка "Назад к модулям" вместо обычной "Назад"
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к модулям",
            callback_data=CoreMenuNavigate(target_menu="modules_list").pack()
        )
    )
    
    keyboard = builder.as_markup()
    
    text = (
        f"🎯 **{MODULE_DISPLAY_NAME}**\n\n"
        f"Добро пожаловать в универсальный шаблон модуля!\n\n"
        f"📊 **Статистика:**\n"
        f"• Версия: {MODULE_VERSION}\n"
        f"• Статус: Активен\n\n"
        f"Выберите действие:"
    )
    
    try:
        if callback.message and (callback.message.text != text or callback.message.reply_markup != keyboard):
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            logger.trace(f"[{MODULE_NAME}] Сообщение входа в модуль не было изменено.")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.trace(f"[{MODULE_NAME}] Сообщение входа в модуль не было изменено (поймано исключение).")
        else:
            logger.warning(f"[{MODULE_NAME}] Ошибка редактирования сообщения входа в модуль: {e}")
    except Exception as e_edit:
        logger.error(f"[{MODULE_NAME}] Непредвиденная ошибка в handle_module_entry: {e_edit}", exc_info=True)
    
    await callback.answer()

@template_router.callback_query()
async def unknown_callback(callback: types.CallbackQuery):
    """Обработчик неизвестных callback запросов"""
    # Игнорируем callback'и ядра - они должны обрабатываться ядром
    if callback.data and (
        callback.data.startswith("sdb_core_") or 
        callback.data.startswith("sdb_admin_")
    ):
        # Это callback ядра или админ-панели, пропускаем его
        return
    
    logger.warning(f"[{MODULE_NAME}] Неизвестный callback запрос в модуле: {callback.data}")
    await callback.answer("❌ Неизвестная команда", show_alert=True)

@template_router.message()
async def unknown_message(message: types.Message, state: FSMContext):
    """Обработчик неизвестных сообщений"""
    current_state = await state.get_state()
    if current_state:
        # Если есть активное состояние FSM, обрабатываем как часть диалога
        return
    
    # Иначе игнорируем сообщение
    logger.debug(f"Получено сообщение вне контекста модуля: {message.text}")
