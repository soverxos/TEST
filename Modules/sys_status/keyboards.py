# Клавиатуры для модуля sys_status

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем общие клавиатурные утилиты и фабрики
from core.admin.keyboards_admin_common import get_back_to_admin_main_menu_button
from core.ui.callback_data_factories import CoreMenuNavigate
from .callback_data_factories import SysStatusCallback

def get_sys_status_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для меню статуса системы.
    """
    builder = InlineKeyboardBuilder()

    # Кнопка для обновления информации
    builder.button(
        text="Обновить 🔄",
        callback_data=SysStatusCallback(action="refresh").pack()
    )

    # Кнопка для возврата в главное меню админ-панели
    builder.row(get_back_to_admin_main_menu_button())

    return builder.as_markup()