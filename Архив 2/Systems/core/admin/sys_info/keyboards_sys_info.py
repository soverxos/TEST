# core/admin/sys_info/keyboards_sys_info.py
from aiogram import types # <--- ДОБАВЛЕН ЭТОТ ИМПОРТ
from aiogram.utils.keyboard import InlineKeyboardBuilder
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_back_to_admin_main_menu_button

def get_sys_info_keyboard() -> types.InlineKeyboardMarkup: # Используем types.InlineKeyboardMarkup
    builder = InlineKeyboardBuilder()
    builder.row(get_back_to_admin_main_menu_button())
    return builder.as_markup()

# Если для sys_info потребуются свои тексты, их можно добавить сюда:
SYS_INFO_TEXTS = {
    "system_info_title": "🖥️ Системная информация SwiftDevBot",
    # ... другие тексты ...
}