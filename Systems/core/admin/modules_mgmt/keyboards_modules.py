# core/admin/modules_mgmt/keyboards_modules.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from typing import List, Dict, Any

from Systems.core.ui.callback_data_factories import AdminModulesPanelNavigate, AdminMainMenuNavigate

async def get_modules_list_keyboard(modules_info: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
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
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админ-панель",
            callback_data=AdminMainMenuNavigate(target_section="main_admin").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()

async def get_module_details_keyboard(module_name: str, is_enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура для детальной информации о модуле"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка переключения статуса
    toggle_text = "❌ Отключить" if is_enabled else "✅ Включить"
    toggle_action = "disable" if is_enabled else "enable"
    builder.button(
        text=toggle_text,
        callback_data=AdminModulesPanelNavigate(action="toggle", item_id=module_name).pack()
    )
    
    # Кнопка действий
    builder.button(
        text="🔧 Действия",
        callback_data=AdminModulesPanelNavigate(action="actions", item_id=module_name).pack()
    )
    
    # Кнопка возврата к списку модулей
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к списку модулей",
            callback_data=AdminModulesPanelNavigate(action="list").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()

async def get_module_actions_keyboard(module_name: str, is_enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура для действий с модулем"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка переключения статуса
    toggle_text = "❌ Отключить" if is_enabled else "✅ Включить"
    toggle_action = "disable" if is_enabled else "enable"
    builder.button(
        text=toggle_text,
        callback_data=AdminModulesPanelNavigate(action="toggle", item_id=module_name).pack()
    )
    
    # Кнопка очистки таблиц (опасное действие)
    builder.button(
        text="🗑️ Очистить таблицы",
        callback_data=AdminModulesPanelNavigate(action="clean_tables", item_id=module_name).pack()
    )
    
    # Кнопка возврата к информации о модуле
    builder.button(
        text="⬅️ Назад к информации",
        callback_data=AdminModulesPanelNavigate(action="view", item_id=module_name).pack()
    )
    
    # Кнопка возврата к списку модулей
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к списку модулей",
            callback_data=AdminModulesPanelNavigate(action="list").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()