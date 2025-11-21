# core/admin/modules_mgmt/keyboards_modules.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from typing import List, Dict, Any

from Systems.core.ui.callback_data_factories import AdminModulesPanelNavigate, AdminMainMenuNavigate
from Systems.core.admin.keyboards_admin_common import get_admin_texts, get_back_to_admin_main_menu_button
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider

async def get_modules_list_keyboard(modules_info: List[Dict[str, Any]], services_provider: Optional['BotServicesProvider'] = None, locale: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура списка модулей"""
    builder = InlineKeyboardBuilder()
    
    if modules_info:
        for module in modules_info:
            # Показываем статус модуля
            status_icon = "✅" if module['is_enabled'] else "❌"
            error_icon = "⚠️" if module.get('error') else ""
            system_icon = "🔧" if module.get('is_system_module') else ""
            
            display_text = f"{status_icon} {system_icon} {module['name']} {error_icon}"
            callback_data = AdminModulesPanelNavigate(action="view", item_id=module['name']).pack()
            builder.button(text=display_text, callback_data=callback_data)
    
    # Кнопка возврата в админ-панель
    if services_provider:
        builder.row(get_back_to_admin_main_menu_button(services_provider, locale))
    else:
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад в админ-панель",
                callback_data=AdminMainMenuNavigate(target_section="main_admin").pack()
            )
        )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()

async def get_module_details_keyboard(module_name: str, is_enabled: bool, services_provider: Optional['BotServicesProvider'] = None, locale: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура для детальной информации о модуле"""
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы
    if services_provider:
        admin_texts = get_admin_texts(services_provider, locale)
    else:
        admin_texts = {}
    
    # Кнопка переключения статуса
    toggle_text = admin_texts.get("modules_mgmt_toggle_disable", "❌ Отключить") if is_enabled else admin_texts.get("modules_mgmt_toggle_enable", "✅ Включить")
    toggle_action = "disable" if is_enabled else "enable"
    builder.button(
        text=toggle_text,
        callback_data=AdminModulesPanelNavigate(action="toggle", item_id=module_name).pack()
    )
    
    # Кнопка действий
    builder.button(
        text=admin_texts.get("modules_mgmt_actions", "🔧 Действия"),
        callback_data=AdminModulesPanelNavigate(action="actions", item_id=module_name).pack()
    )
    
    # Кнопка возврата к списку модулей
    builder.row(
        InlineKeyboardButton(
            text=admin_texts.get("modules_mgmt_back_to_module_list", "⬅️ Назад к списку модулей"),
            callback_data=AdminModulesPanelNavigate(action="list").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()

async def get_module_actions_keyboard(module_name: str, is_enabled: bool, services_provider: Optional['BotServicesProvider'] = None, locale: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура для действий с модулем"""
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы
    if services_provider:
        admin_texts = get_admin_texts(services_provider, locale)
    else:
        admin_texts = {}
    
    # Кнопка переключения статуса
    toggle_text = admin_texts.get("modules_mgmt_toggle_disable", "❌ Отключить") if is_enabled else admin_texts.get("modules_mgmt_toggle_enable", "✅ Включить")
    toggle_action = "disable" if is_enabled else "enable"
    builder.button(
        text=toggle_text,
        callback_data=AdminModulesPanelNavigate(action="toggle", item_id=module_name).pack()
    )
    
    # Кнопка очистки таблиц (опасное действие)
    builder.button(
        text=admin_texts.get("modules_mgmt_clean_tables", "🗑️ Очистить таблицы"),
        callback_data=AdminModulesPanelNavigate(action="clean_tables", item_id=module_name).pack()
    )
    
    # Кнопка возврата к информации о модуле
    builder.button(
        text=admin_texts.get("modules_mgmt_back_to_module_info", "⬅️ Назад к информации"),
        callback_data=AdminModulesPanelNavigate(action="view", item_id=module_name).pack()
    )
    
    # Кнопка возврата к списку модулей
    builder.row(
        InlineKeyboardButton(
            text=admin_texts.get("modules_mgmt_back_to_module_list", "⬅️ Назад к списку модулей"),
            callback_data=AdminModulesPanelNavigate(action="list").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()