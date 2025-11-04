# core/admin/logs_viewer/keyboards_logs.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from typing import List, Dict, Any

from Systems.core.ui.callback_data_factories import AdminLogsViewerNavigate, AdminMainMenuNavigate

async def get_logs_main_keyboard(log_files: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура главного меню просмотра логов"""
    builder = InlineKeyboardBuilder()
    
    if log_files:
        for log_file in log_files:
            # Показываем имя файла и размер
            display_text = f"📄 {log_file['name']} ({log_file['size_formatted']})"
            callback_data = AdminLogsViewerNavigate(action="view_file", payload=log_file['name']).pack()
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

async def get_log_file_keyboard(file_name: str) -> InlineKeyboardMarkup:
    """Клавиатура для действий с файлом логов"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка просмотра содержимого
    builder.button(
        text="👁️ Просмотреть содержимое",
        callback_data=AdminLogsViewerNavigate(action="view_content", payload=file_name).pack()
    )
    
    # Кнопка скачивания
    builder.button(
        text="📥 Скачать файл",
        callback_data=AdminLogsViewerNavigate(action="download", payload=file_name).pack()
    )
    
    # Кнопка возврата к списку файлов
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к списку файлов",
            callback_data=AdminLogsViewerNavigate(action="back_to_main").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()

async def get_log_content_keyboard(file_name: str) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра содержимого файла"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка скачивания
    builder.button(
        text="📥 Скачать файл",
        callback_data=AdminLogsViewerNavigate(action="download", payload=file_name).pack()
    )
    
    # Кнопка возврата к информации о файле
    builder.button(
        text="⬅️ Назад к информации о файле",
        callback_data=AdminLogsViewerNavigate(action="view_file", payload=file_name).pack()
    )
    
    # Кнопка возврата к списку файлов
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к списку файлов",
            callback_data=AdminLogsViewerNavigate(action="back_to_main").pack()
        )
    )
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup() 