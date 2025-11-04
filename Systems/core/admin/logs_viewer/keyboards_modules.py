# core/admin/logs_viewer/keyboards_logs.py
# Пока пустой, но файл существует для будущей логики клавиатур этого раздела.
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
# from Systems.core.admin.keyboards_admin_common import get_back_to_admin_main_menu_button

# Пример функции, если понадобится:
# def get_logs_viewer_main_keyboard() -> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     # builder.button(text="Скачать последний лог-файл", callback_data=...)
#     # builder.button(text="Выбрать лог-файл для просмотра", callback_data=...)
#     # builder.row(get_back_to_admin_main_menu_button())
#     return builder.as_markup()