"""
Фабрики callback data для универсального шаблона модуля

Этот файл содержит классы для создания и парсинга callback data
для inline кнопок. Callback data используется для передачи
параметров при нажатии на кнопки.
"""

from aiogram.filters.callback_data import CallbackData
from typing import Optional, List
from enum import Enum

class TemplateAction(str, Enum):
    """Действия для основного меню"""
    MAIN_MENU = "main_menu"
    ADMIN_PANEL = "admin_panel"
    SHOW_STATS = "show_stats"
    SHOW_SETTINGS = "show_settings"
    START_INPUT = "start_input"
    BACK = "back"

class TemplateAdminAction(str, Enum):
    """Действия для админ панели"""
    MANAGE_USERS = "manage_users"
    SYSTEM_STATS = "system_stats"
    MODULE_SETTINGS = "module_settings"
    USER_DETAILS = "user_details"
    TOGGLE_USER_STATUS = "toggle_user_status"

class TemplateDataAction(str, Enum):
    """Действия для работы с данными"""
    CREATE_ITEM = "create_item"
    EDIT_ITEM = "edit_item"
    DELETE_ITEM = "delete_item"
    VIEW_ITEM = "view_item"
    LIST_ITEMS = "list_items"

class TemplateCallback(CallbackData, prefix="template"):
    """
    Основной callback data для шаблона модуля
    
    Используется для основных действий в модуле.
    """
    action: str
    data: Optional[str] = None
    page: Optional[int] = None

class TemplateAdminCallback(CallbackData, prefix="template_admin"):
    """
    Callback data для административных функций
    
    Используется для действий, требующих админских прав.
    """
    action: str
    user_id: Optional[int] = None
    item_id: Optional[int] = None
    page: Optional[int] = None

class TemplateDataCallback(CallbackData, prefix="template_data"):
    """
    Callback data для работы с данными
    
    Используется для CRUD операций с данными модуля.
    """
    action: str
    item_id: Optional[int] = None
    user_id: Optional[int] = None
    page: Optional[int] = None

class TemplateSettingsCallback(CallbackData, prefix="template_settings"):
    """
    Callback data для настроек модуля
    
    Используется для управления настройками.
    """
    action: str
    setting: Optional[str] = None
    value: Optional[str] = None

class TemplateFSMCallback(CallbackData, prefix="template_fsm"):
    """
    Callback data для FSM диалогов
    
    Используется для управления состоянием диалогов.
    """
    action: str
    step: Optional[int] = None
    data: Optional[str] = None

# Утилитарные функции для работы с callback data

def create_main_menu_callback() -> str:
    """Создает callback data для главного меню"""
    return TemplateCallback(action=TemplateAction.MAIN_MENU).pack()

def create_admin_panel_callback() -> str:
    """Создает callback data для админ панели"""
    return TemplateCallback(action=TemplateAction.ADMIN_PANEL).pack()

def create_stats_callback() -> str:
    """Создает callback data для статистики"""
    return TemplateCallback(action=TemplateAction.SHOW_STATS).pack()

def create_settings_callback() -> str:
    """Создает callback data для настроек"""
    return TemplateCallback(action=TemplateAction.SHOW_SETTINGS).pack()

def create_back_callback() -> str:
    """Создает callback data для кнопки "Назад" """
    return TemplateCallback(action=TemplateAction.BACK).pack()

def create_item_callback(item_id: int, action: str = TemplateDataAction.VIEW_ITEM) -> str:
    """Создает callback data для работы с элементом"""
    return TemplateDataCallback(action=action, item_id=item_id).pack()

def create_user_callback(user_id: int, action: str = TemplateAdminAction.USER_DETAILS) -> str:
    """Создает callback data для работы с пользователем"""
    return TemplateAdminCallback(action=action, user_id=user_id).pack()

def create_pagination_callback(action: str, page: int, data: str = None) -> str:
    """Создает callback data для пагинации"""
    return TemplateCallback(action=action, page=page, data=data).pack()

def create_fsm_callback(action: str, step: int = None, data: str = None) -> str:
    """Создает callback data для FSM диалогов"""
    return TemplateFSMCallback(action=action, step=step, data=data).pack()

def create_settings_toggle_callback(setting: str, current_value: bool) -> str:
    """Создает callback data для переключения настроек"""
    new_value = "false" if current_value else "true"
    return TemplateSettingsCallback(action="toggle", setting=setting, value=new_value).pack()

# Функции для парсинга callback data

def parse_template_callback(callback_data: str) -> Optional[TemplateCallback]:
    """Парсит основной callback data"""
    try:
        return TemplateCallback.unpack(callback_data)
    except Exception:
        return None

def parse_admin_callback(callback_data: str) -> Optional[TemplateAdminCallback]:
    """Парсит админский callback data"""
    try:
        return TemplateAdminCallback.unpack(callback_data)
    except Exception:
        return None

def parse_data_callback(callback_data: str) -> Optional[TemplateDataCallback]:
    """Парсит callback data для данных"""
    try:
        return TemplateDataCallback.unpack(callback_data)
    except Exception:
        return None

def parse_settings_callback(callback_data: str) -> Optional[TemplateSettingsCallback]:
    """Парсит callback data для настроек"""
    try:
        return TemplateSettingsCallback.unpack(callback_data)
    except Exception:
        return None

def parse_fsm_callback(callback_data: str) -> Optional[TemplateFSMCallback]:
    """Парсит callback data для FSM"""
    try:
        return TemplateFSMCallback.unpack(callback_data)
    except Exception:
        return None

# Валидация callback data

def is_valid_template_callback(callback_data: str) -> bool:
    """Проверяет, является ли callback data валидным для шаблона"""
    return parse_template_callback(callback_data) is not None

def is_valid_admin_callback(callback_data: str) -> bool:
    """Проверяет, является ли callback data валидным для админки"""
    return parse_admin_callback(callback_data) is not None

def is_valid_data_callback(callback_data: str) -> bool:
    """Проверяет, является ли callback data валидным для данных"""
    return parse_data_callback(callback_data) is not None

# Генерация callback data для списков

def generate_list_callback_data(items: List[dict], action: str, page: int = 0, per_page: int = 10) -> List[dict]:
    """
    Генерирует callback data для списка элементов с пагинацией
    
    Args:
        items: Список элементов
        action: Действие для callback data
        page: Текущая страница
        per_page: Элементов на странице
        
    Returns:
        Список элементов с callback data
    """
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_items = items[start_idx:end_idx]
    
    result = []
    for item in page_items:
        item_data = item.copy()
        item_data['callback_data'] = create_item_callback(item['id'], action)
        result.append(item_data)
    
    return result

def generate_pagination_buttons(total_items: int, current_page: int, per_page: int = 10, action: str = "list") -> List[dict]:
    """
    Генерирует кнопки пагинации
    
    Args:
        total_items: Общее количество элементов
        current_page: Текущая страница
        per_page: Элементов на странице
        action: Действие для callback data
        
    Returns:
        Список кнопок пагинации
    """
    total_pages = (total_items + per_page - 1) // per_page
    
    if total_pages <= 1:
        return []
    
    buttons = []
    
    # Кнопка "Предыдущая"
    if current_page > 0:
        buttons.append({
            'text': '◀️ Предыдущая',
            'callback_data': create_pagination_callback(action, current_page - 1)
        })
    
    # Информация о странице
    buttons.append({
        'text': f'{current_page + 1}/{total_pages}',
        'callback_data': 'noop'  # Неактивная кнопка
    })
    
    # Кнопка "Следующая"
    if current_page < total_pages - 1:
        buttons.append({
            'text': 'Следующая ▶️',
            'callback_data': create_pagination_callback(action, current_page + 1)
        })
    
    return buttons
