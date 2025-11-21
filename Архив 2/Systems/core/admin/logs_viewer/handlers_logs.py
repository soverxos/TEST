# core/admin/logs_viewer/handlers_logs.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from Systems.core.ui.callback_data_factories import AdminMainMenuNavigate, AdminLogsViewerNavigate
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from .keyboards_logs import get_logs_main_keyboard, get_log_file_keyboard, get_log_content_keyboard

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider

logs_viewer_router = Router(name="sdb_admin_logs_viewer_handlers")
MODULE_NAME_FOR_LOG = "AdminLogsViewer"

logs_viewer_router.callback_query.filter(can_view_admin_panel_filter)

class FSMAdminLogsViewer(StatesGroup):
    viewing_log_content = State()

@logs_viewer_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "logs_view"))
async def cq_admin_logs_view_start(
    query: types.CallbackQuery,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил просмотр логов.")
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    
    # Получаем список файлов логов
    log_files = await _get_available_log_files(services_provider)
    
    text = f"📄 **{admin_texts.get('logs_viewer_title', 'Просмотр логов системы')}**\n\n"
    if log_files:
        text += f"{admin_texts.get('logs_viewer_files_found', 'Найдено файлов логов')}: {len(log_files)}\n"
        text += admin_texts.get('logs_viewer_select_file', 'Выберите файл для просмотра:')
    else:
        text += admin_texts.get('logs_viewer_no_log_files', '❌ Файлы логов не найдены')
    
    keyboard = await get_logs_main_keyboard(log_files, services_provider, user_locale)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения логов: {e}")
            await query.answer(admin_texts["admin_error_display"], show_alert=True)
    else:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    
    await query.answer()

@logs_viewer_router.callback_query(AdminLogsViewerNavigate.filter(F.action == "view_file"))
async def cq_admin_logs_view_file(
    query: types.CallbackQuery,
    callback_data: AdminLogsViewerNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    file_name = callback_data.payload
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил просмотр файла {file_name}")
    
    # Получаем информацию о файле
    log_file_info = await _get_log_file_info(services_provider, file_name)
    
    if not log_file_info:
        await query.answer(admin_texts.get("logs_viewer_file_not_found", "Файл не найден"), show_alert=True)
        return
    
    text = f"📄 **{admin_texts.get('logs_viewer_file_details_title', 'Файл логов')}: {file_name}**\n\n"
    text += f"📊 {admin_texts.get('logs_viewer_file_size', 'Размер')}: {log_file_info['size_formatted']}\n"
    text += f"📅 {admin_texts.get('logs_viewer_file_last_modified', 'Изменен')}: {log_file_info['modified_formatted']}\n"
    text += f"📝 {admin_texts.get('logs_viewer_file_lines', 'Строк')}: {log_file_info['lines_count']}\n\n"
    text += admin_texts.get('logs_viewer_select_action', 'Выберите действие:')
    
    keyboard = await get_log_file_keyboard(file_name, services_provider, user_locale)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения файла логов: {e}")
            await query.answer(admin_texts["admin_error_display"], show_alert=True)
    
    await query.answer()

@logs_viewer_router.callback_query(AdminLogsViewerNavigate.filter(F.action == "view_content"))
async def cq_admin_logs_view_content(
    query: types.CallbackQuery,
    callback_data: AdminLogsViewerNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    admin_user_id = query.from_user.id
    file_name = callback_data.payload
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил содержимое файла {file_name}")
    
    # Получаем содержимое файла (последние 50 строк)
    log_content = await _get_log_file_content(services_provider, file_name, lines_count=50)
    
    if not log_content:
        await query.answer(admin_texts.get("logs_viewer_error_reading_file", "Не удалось прочитать файл"), show_alert=True)
        return
    
    text = f"📄 **{admin_texts.get('logs_viewer_file_content_title', 'Содержимое файла')}: {file_name}**\n\n"
    text += f"```\n{log_content}\n```"
    
    keyboard = await get_log_content_keyboard(file_name, services_provider, user_locale)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка при обновлении содержимого логов: {e}")
            # Попробуем без Markdown
            text = f"📄 Содержимое файла: {file_name}\n\n{log_content}"
            await query.message.edit_text(text, reply_markup=keyboard)
    
    await query.answer()

@logs_viewer_router.callback_query(AdminLogsViewerNavigate.filter(F.action == "download"))
async def cq_admin_logs_download(
    query: types.CallbackQuery,
    callback_data: AdminLogsViewerNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    file_name = callback_data.payload
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил скачивание файла {file_name}")
    
    # Получаем путь к файлу
    log_file_path = await _get_log_file_path(services_provider, file_name)
    
    if not log_file_path or not log_file_path.exists():
        await query.answer(admin_texts.get("logs_viewer_file_not_found", "Файл не найден"), show_alert=True)
        return
    
    try:
        # Отправляем файл
        await query.message.answer_document(
            types.BufferedInputFile(
                log_file_path.read_bytes(),
                filename=file_name
            ),
            caption=f"📄 {admin_texts.get('logs_viewer_file_details_title', 'Файл логов')}: {file_name}"
        )
        await query.answer(admin_texts.get("logs_viewer_file_sent", "Файл отправлен"))
    except Exception as e:
        logger.error(f"Ошибка при отправке файла логов: {e}")
        await query.answer(admin_texts.get("logs_viewer_error_downloading_file", "Ошибка при отправке файла"), show_alert=True)

@logs_viewer_router.callback_query(AdminLogsViewerNavigate.filter(F.action == "back_to_main"))
async def cq_admin_logs_back_to_main(
    query: types.CallbackQuery,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} вернулся к главному меню логов")
    
    # Повторяем логику из cq_admin_logs_view_start
    log_files = await _get_available_log_files(services_provider)
    
    text = f"📄 **{admin_texts.get('logs_viewer_title', 'Просмотр логов системы')}**\n\n"
    if log_files:
        text += f"{admin_texts.get('logs_viewer_files_found', 'Найдено файлов логов')}: {len(log_files)}\n"
        text += admin_texts.get('logs_viewer_select_file', 'Выберите файл для просмотра:')
    else:
        text += admin_texts.get('logs_viewer_no_log_files', '❌ Файлы логов не найдены')
    
    keyboard = await get_logs_main_keyboard(log_files, services_provider, user_locale)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка при возврате к главному меню логов: {e}")
            await query.answer(admin_texts["admin_error_display"], show_alert=True)
    
    await query.answer()

# Вспомогательные функции
async def _get_available_log_files(services_provider: 'BotServicesProvider') -> List[Dict[str, Any]]:
    """Получить список доступных файлов логов"""
    try:
        log_dir = services_provider.config.core.project_data_path / "logs"
        if not log_dir.exists():
            return []
        
        log_files = []
        for file_path in log_dir.glob("*.log"):
            try:
                stat = file_path.stat()
                log_files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'size_formatted': _format_size(stat.st_size),
                    'modified_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M')
                })
            except Exception as e:
                logger.error(f"Ошибка при чтении информации о файле {file_path}: {e}")
        
        # Сортируем по дате изменения (новые сверху)
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return log_files
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов логов: {e}")
        return []

async def _get_log_file_info(services_provider: 'BotServicesProvider', file_name: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о файле логов"""
    try:
        log_file_path = await _get_log_file_path(services_provider, file_name)
        if not log_file_path or not log_file_path.exists():
            return None
        
        stat = log_file_path.stat()
        
        # Подсчитываем количество строк
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines_count = sum(1 for _ in f)
        except Exception:
            lines_count = 0
        
        return {
            'name': file_name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'size_formatted': _format_size(stat.st_size),
            'modified_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
            'lines_count': lines_count
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о файле {file_name}: {e}")
        return None

async def _get_log_file_content(services_provider: 'BotServicesProvider', file_name: str, lines_count: int = 50) -> Optional[str]:
    """Получить содержимое файла логов (последние строки)"""
    try:
        log_file_path = await _get_log_file_path(services_provider, file_name)
        if not log_file_path or not log_file_path.exists():
            return None
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Берем последние строки
        if len(lines) > lines_count:
            lines = lines[-lines_count:]
        
        return ''.join(lines)
    except Exception as e:
        logger.error(f"Ошибка при чтении содержимого файла {file_name}: {e}")
        return None

async def _get_log_file_path(services_provider: 'BotServicesProvider', file_name: str) -> Optional[Path]:
    """Получить путь к файлу логов"""
    try:
        log_dir = services_provider.config.core.project_data_path / "logs"
        log_file_path = log_dir / file_name
        
        # Проверяем, что файл находится в директории логов (безопасность)
        if not log_file_path.resolve().is_relative_to(log_dir.resolve()):
            logger.warning(f"Попытка доступа к файлу вне директории логов: {file_name}")
            return None
        
        return log_file_path
    except Exception as e:
        logger.error(f"Ошибка при получении пути к файлу {file_name}: {e}")
        return None

def _format_size(size_bytes: int) -> str:
    """Форматировать размер файла"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"