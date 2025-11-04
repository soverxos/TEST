"""
Клавиатуры для универсального шаблона модуля

Этот файл содержит функции для создания inline клавиатур.
Клавиатуры используются для навигации и взаимодействия с модулем.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

from .callback_data_factories import (
    TemplateAction, TemplateAdminAction, TemplateDataAction,
    TemplateCallback, TemplateDataCallback, TemplateAdminCallback,
    create_main_menu_callback, create_admin_panel_callback,
    create_stats_callback, create_settings_callback,
    create_back_callback, create_item_callback,
    create_user_callback, create_pagination_callback,
    create_fsm_callback, create_settings_toggle_callback
)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню модуля
    
    Returns:
        InlineKeyboardMarkup с основными действиями
    """
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
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=create_back_callback()
        )
    )
    
    return builder.as_markup()

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Админ меню модуля
    
    Returns:
        InlineKeyboardMarkup с административными действиями
    """
    builder = InlineKeyboardBuilder()
    
    # Управление пользователями
    builder.row(
        InlineKeyboardButton(
            text="👥 Управление пользователями",
            callback_data=TemplateAdminCallback(action=TemplateAdminAction.MANAGE_USERS).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📈 Системная статистика",
            callback_data=TemplateAdminCallback(action=TemplateAdminAction.SYSTEM_STATS).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔧 Настройки модуля",
            callback_data=TemplateAdminCallback(action=TemplateAdminAction.MODULE_SETTINGS).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Очистка данных",
            callback_data=create_fsm_callback("cleanup_data")
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data=create_main_menu_callback()
        )
    )
    
    return builder.as_markup()

def get_settings_keyboard(settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек модуля
    
    Args:
        settings: Текущие настройки
        
    Returns:
        InlineKeyboardMarkup с настройками
    """
    builder = InlineKeyboardBuilder()
    
    # Уведомления
    notifications_enabled = settings.get('notification_enabled', True)
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 Уведомления: {'✅' if notifications_enabled else '❌'}",
            callback_data=create_settings_toggle_callback('notification_enabled', notifications_enabled)
        )
    )
    
    # Режим отладки
    debug_mode = settings.get('debug_mode', False)
    builder.row(
        InlineKeyboardButton(
            text=f"🐛 Отладка: {'✅' if debug_mode else '❌'}",
            callback_data=create_settings_toggle_callback('debug_mode', debug_mode)
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=create_main_menu_callback()
        )
    )
    
    return builder.as_markup()

def get_items_list_keyboard(items: List[Dict[str, Any]], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """
    Клавиатура списка элементов с пагинацией
    
    Args:
        items: Список элементов
        page: Текущая страница
        per_page: Элементов на странице
        
    Returns:
        InlineKeyboardMarkup со списком элементов
    """
    builder = InlineKeyboardBuilder()
    
    # Элементы текущей страницы
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_items = items[start_idx:end_idx]
    
    for item in page_items:
        builder.row(
            InlineKeyboardButton(
                text=f"📄 {item.get('title', 'Без названия')}",
                callback_data=create_item_callback(item['id'], TemplateDataAction.VIEW_ITEM)
            )
        )
    
    # Пагинация
    total_pages = (len(items) + per_page - 1) // per_page
    if total_pages > 1:
        pagination_buttons = []
        
        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="◀️",
                    callback_data=create_pagination_callback("list_items", page - 1)
                )
            )
        
        pagination_buttons.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                callback_data="noop"
            )
        )
        
        if page < total_pages - 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="▶️",
                    callback_data=create_pagination_callback("list_items", page + 1)
                )
            )
        
        builder.row(*pagination_buttons)
    
    # Действия
    builder.row(
        InlineKeyboardButton(
            text="➕ Создать новый",
            callback_data=create_fsm_callback("create_item")
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=create_main_menu_callback()
        )
    )
    
    return builder.as_markup()

def get_item_detail_keyboard(item_id: int, is_owner: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура детального просмотра элемента
    
    Args:
        item_id: ID элемента
        is_owner: Является ли пользователь владельцем
        
    Returns:
        InlineKeyboardMarkup с действиями для элемента
    """
    builder = InlineKeyboardBuilder()
    
    if is_owner:
        # Действия владельца
        builder.row(
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=create_item_callback(item_id, TemplateDataAction.EDIT_ITEM)
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=create_item_callback(item_id, TemplateDataAction.DELETE_ITEM)
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 К списку",
            callback_data=create_fsm_callback("list_items")
        )
    )
    
    return builder.as_markup()

def get_confirmation_keyboard(action: str, item_id: int = None, user_id: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия
    
    Args:
        action: Действие для подтверждения
        item_id: ID элемента (если применимо)
        user_id: ID пользователя (если применимо)
        
    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки подтверждения
    if action == "delete_item" and item_id:
        builder.row(
            InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=create_item_callback(item_id, TemplateDataAction.DELETE_ITEM)
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=create_item_callback(item_id, TemplateDataAction.VIEW_ITEM)
            )
        )
    elif action == "cleanup_data":
        builder.row(
            InlineKeyboardButton(
                text="✅ Да, очистить",
                callback_data=create_fsm_callback("confirm_cleanup")
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=create_admin_panel_callback()
            )
        )
    
    return builder.as_markup()

def get_fsm_navigation_keyboard(step: int, total_steps: int, can_skip: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации для FSM диалогов
    
    Args:
        step: Текущий шаг
        total_steps: Общее количество шагов
        can_skip: Можно ли пропустить шаг
        
    Returns:
        InlineKeyboardMarkup с навигацией
    """
    builder = InlineKeyboardBuilder()
    
    # Навигация
    nav_buttons = []
    
    if step > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=create_fsm_callback("prev_step", step - 1)
            )
        )
    
    if can_skip:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⏭️ Пропустить",
                callback_data=create_fsm_callback("skip_step", step)
            )
        )
    
    if step < total_steps - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Далее ▶️",
                callback_data=create_fsm_callback("next_step", step + 1)
            )
        )
    else:
        nav_buttons.append(
            InlineKeyboardButton(
                text="✅ Завершить",
                callback_data=create_fsm_callback("finish", step)
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Отмена
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=create_fsm_callback("cancel")
        )
    )
    
    return builder.as_markup()

def get_user_management_keyboard(user_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура управления пользователем
    
    Args:
        user_id: ID пользователя
        is_active: Активен ли пользователь
        
    Returns:
        InlineKeyboardMarkup с действиями для пользователя
    """
    builder = InlineKeyboardBuilder()
    
    # Статус пользователя
    builder.row(
        InlineKeyboardButton(
            text=f"👤 Статус: {'✅ Активен' if is_active else '❌ Заблокирован'}",
            callback_data=create_user_callback(user_id, TemplateAdminAction.TOGGLE_USER_STATUS)
        )
    )
    
    # Детали пользователя
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика пользователя",
            callback_data=create_user_callback(user_id, TemplateAdminAction.USER_DETAILS)
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 К списку пользователей",
            callback_data=create_fsm_callback("manage_users")
        )
    )
    
    return builder.as_markup()

def get_simple_back_keyboard(back_action: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Простая клавиатура с кнопкой "Назад"
    
    Args:
        back_action: Действие для кнопки "Назад"
        
    Returns:
        InlineKeyboardMarkup с кнопкой "Назад"
    """
    builder = InlineKeyboardBuilder()
    
    if back_action == "main_menu":
        callback_data = create_main_menu_callback()
    elif back_action == "admin_panel":
        callback_data = create_admin_panel_callback()
    else:
        callback_data = create_back_callback()
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=callback_data
        )
    )
    
    return builder.as_markup()

def get_yes_no_keyboard(yes_action: str, no_action: str, yes_text: str = "✅ Да", no_text: str = "❌ Нет") -> InlineKeyboardMarkup:
    """
    Клавиатура "Да/Нет"
    
    Args:
        yes_action: Действие для кнопки "Да"
        no_action: Действие для кнопки "Нет"
        yes_text: Текст кнопки "Да"
        no_text: Текст кнопки "Нет"
        
    Returns:
        InlineKeyboardMarkup с кнопками "Да/Нет"
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=yes_text,
            callback_data=yes_action
        ),
        InlineKeyboardButton(
            text=no_text,
            callback_data=no_action
        )
    )
    
    return builder.as_markup()
