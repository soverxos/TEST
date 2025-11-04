# SwiftDevBot/core/admin/sys_info/handlers_sys_info.py
import sys
import platform
from datetime import datetime, timezone 
import psutil 
import aiogram 
import asyncio 
import os 
from pathlib import Path

from aiogram import Router, types, F, Bot
from aiogram.utils.markdown import hbold, hcode 
from loguru import logger
from sqlalchemy import select, func as sql_func 
from aiogram.exceptions import TelegramBadRequest

from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS
from .keyboards_sys_info import get_sys_info_keyboard
from Systems.core.ui.callback_data_factories import AdminSysInfoPanelNavigate
from Systems.core.admin.filters_admin import can_view_admin_panel_filter 
from Systems.core.rbac.service import PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL, PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC
from Systems.core.database.core_models import User as DBUserModel 
from Systems.core.bot_entrypoint import PID_FILENAME

from typing import TYPE_CHECKING, List, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider

sys_info_router = Router(name="sdb_admin_sys_info_handlers")
MODULE_NAME_FOR_LOG = "AdminSysInfo"

async def _get_local_total_users_count(services_provider: 'BotServicesProvider') -> Optional[int]:
    try:
        async with services_provider.db.get_session() as session:
            count_stmt = select(sql_func.count(DBUserModel.id))
            total_users_result = await session.execute(count_stmt)
            return total_users_result.scalar_one_or_none() or 0
    except Exception as e: 
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при подсчете пользователей для SysInfo: {e}")
        return None

def format_uptime(start_time: Optional[datetime]) -> str:
    if not start_time:
        return "Н/Д"
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    uptime_delta = datetime.now(timezone.utc) - start_time
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days > 0: parts.append(f"{int(days)}д")
    if hours > 0: parts.append(f"{int(hours)}ч")
    if minutes > 0: parts.append(f"{int(minutes)}м")
    parts.append(f"{int(seconds)}с")
    return " ".join(parts) or "~0с"

@sys_info_router.callback_query(AdminSysInfoPanelNavigate.filter(F.action == "show"))
async def cq_admin_show_system_info_entry( 
    query: types.CallbackQuery, 
    callback_data: AdminSysInfoPanelNavigate, 
    services_provider: 'BotServicesProvider',
    bot: Bot 
):
    user_id = query.from_user.id 
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} запросил системную информацию.")

    can_view_full = False
    can_view_basic = False
    is_owner_from_config = user_id in services_provider.config.core.super_admins
    async with services_provider.db.get_session() as session:
        if not is_owner_from_config: 
            can_view_full = await services_provider.rbac.user_has_permission(session, user_id, PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL)
            if not can_view_full: 
                can_view_basic = await services_provider.rbac.user_has_permission(session, user_id, PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC)
        
    if not (is_owner_from_config or can_view_full or can_view_basic):
        await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True)
        return

    s = services_provider.config 
    
    text_parts: List[str] = [f"🖥️ {hbold('Системная информация SwiftDevBot')}\n"]

    # Общая информация
    text_parts.append(f"ℹ️ {hbold('Общая информация')} ───")
    text_parts.append(f"  ▸ {hbold('SDB Core')}: {hcode(f'v{s.core.sdb_version}')}")
    text_parts.append(f"  ▸ {hbold('Python')}: {hcode(f'v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')}")
    text_parts.append(f"  ▸ {hbold('Aiogram')}: {hcode(f'v{aiogram.__version__}')}")
    text_parts.append(f"  ▸ {hbold('ОС')}: {platform.system()} {platform.release()} ({platform.machine()})")
    
    # Процесс бота
    text_parts.append(f"\n🤖 {hbold('Процесс бота')} ───")
    current_pid_handler = os.getpid() 
    pid_file_path = s.core.project_data_path / PID_FILENAME
    
    pid_for_psutil_stats = current_pid_handler
    pid_display_str = hcode(str(current_pid_handler))

    if pid_file_path.is_file():
        try:
            pid_from_file = int(pid_file_path.read_text().strip())
            pid_display_str = hcode(str(pid_from_file))
            if psutil and psutil.pid_exists(pid_from_file):
                process = psutil.Process(pid_from_file)
                create_time = datetime.fromtimestamp(process.create_time(), tz=timezone.utc)
                uptime_val = format_uptime(create_time)
                start_time_str = create_time.strftime('%d.%m.%Y %H:%M')
                text_parts.append(f"  ▸ {hbold('Запущен')}: {start_time_str}")
                text_parts.append(f"  ▸ {hbold('PID')}: {pid_display_str}")
                text_parts.append(f"  ▸ {hbold('Время работы')}: {hbold(uptime_val)}")
                pid_for_psutil_stats = pid_from_file 
            else:
                status_msg = "Процесс не найден"
                if not psutil: status_msg += " (psutil недоступен)"
                text_parts.append(f"  ▸ {hbold('Статус (PID из файла)')}: {hcode(status_msg)} (PID: {pid_display_str})")
                text_parts.append(f"  ▸ {hbold('PID (хэндлера)')}: {hcode(str(current_pid_handler))}")
        except Exception as e_pid:
            logger.warning(f"Ошибка обработки PID-файла: {e_pid}")
            text_parts.append(f"  ▸ {hbold('PID (из файла)')}: {hcode('Ошибка чтения')}")
            text_parts.append(f"  ▸ {hbold('PID (хэндлера)')}: {hcode(str(current_pid_handler))}")
    elif psutil:
        try:
            process = psutil.Process(current_pid_handler)
            create_time = datetime.fromtimestamp(process.create_time(), tz=timezone.utc)
            uptime_val = format_uptime(create_time)
            start_time_str = create_time.strftime('%d.%m.%Y %H:%M')
            text_parts.append(f"  ▸ {hbold('Запущен (тек. процесс)')}: {start_time_str} (PID: {pid_display_str})")
            text_parts.append(f"  ▸ {hbold('Время работы (тек.)')}: {hbold(uptime_val)}")
        except Exception: 
             text_parts.append(f"  ▸ {hbold('Время работы')}: Н/Д (ошибка psutil для PID: {pid_display_str})")
    else:
        text_parts.append(f"  ▸ {hbold('PID')}: {pid_display_str}")
        text_parts.append(f"  ▸ {hbold('Время работы')}: Н/Д (PID-файл не найден / psutil недоступен)")

    if psutil:
        try:
            target_ps_proc = psutil.Process(pid_for_psutil_stats)
            mem_rss_mb = target_ps_proc.memory_info().rss / (1024 * 1024)
            cpu_perc = target_ps_proc.cpu_percent(interval=0.05)
            text_parts.append(f"  ▸ {hbold('Память (RSS)')}: {hbold(f'{mem_rss_mb:.2f} MB')}")
            text_parts.append(f"  ▸ {hbold('CPU (мгновен.)')}: {hbold(f'{cpu_perc:.1f}%')}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
             text_parts.append(f"  ▸ {hbold('Память/CPU')}: {hcode(f'Н/Д (процесс {pid_for_psutil_stats} недоступен)')}")
        except Exception as e_ps_stats:
             logger.warning(f"Ошибка psutil для статистики PID {pid_for_psutil_stats}: {e_ps_stats}")
             text_parts.append(f"  ▸ {hbold('Память/CPU')}: {hcode('Н/Д (ошибка psutil)')}")
    else:
        text_parts.append(f"  ▸ {hbold('Память/CPU')}: {hcode('psutil не установлен')}")

    # База данных
    text_parts.append(f"\n🗃️ {hbold('База данных')} ───")
    text_parts.append(f"  ▸ Тип: {hbold(s.db.type.upper())}")
    if s.db.type == "sqlite":
        text_parts.append(f"  ▸ Путь: {hcode(s.db.sqlite_path)}")
    
    # Кэш
    text_parts.append(f"\n💾 {hbold('Кэш')} ───")
    text_parts.append(f"  ▸ Тип: {hbold(s.cache.type.capitalize())}")
    if s.cache.type == "redis" and s.cache.redis_url:
        text_parts.append(f"  ▸ URL: {hcode(str(s.cache.redis_url))}") 
    text_parts.append(f"  ▸ Доступен: {'✅ Да' if services_provider.cache.is_available() else '❌ Нет'}")

    # Модули
    try:
        total_modules = len(services_provider.modules.get_all_modules_info())
        loaded_modules = len(services_provider.modules.get_loaded_modules_info(True, True))
        enabled_plugins = len(services_provider.modules.enabled_plugin_names)
        text_parts.append(f"\n🧩 {hbold('Модули')} ───")
        text_parts.append(f"  ▸ Всего найдено: {hbold(str(total_modules))}")
        text_parts.append(f"  ▸ Активных плагинов: {hbold(str(enabled_plugins))}")
        text_parts.append(f"  ▸ Успешно загружено: {hbold(str(loaded_modules))}")
    except Exception as e_mod_info:
        logger.warning(f"Не удалось получить информацию о модулях: {e_mod_info}")
        text_parts.append(f"\n🧩 {hbold('Модули')} ───")
        text_parts.append(f"  ▸ Ошибка получения информации")

    # Пользователи
    total_users_count = await _get_local_total_users_count(services_provider)
    total_users_str = hbold(str(total_users_count)) if total_users_count is not None else f"{hcode('[Ошибка]')}"
    text_parts.append(f"\n👥 {hbold('Пользователи')} ───")
    text_parts.append(f"  ▸ Всего в БД: {total_users_str}")

    text_response = "\n".join(text_parts)
    keyboard_sysinfo = get_sys_info_keyboard()

    if query.message:
        try:
            if query.message.text != text_response or query.message.reply_markup != keyboard_sysinfo:
                await query.message.edit_text(text_response, reply_markup=keyboard_sysinfo)
            else:
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение системной информации не было изменено.")
            await query.answer()
        except TelegramBadRequest as e_tbr: 
            if "message is not modified" in str(e_tbr).lower():
                 logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение системной информации не было изменено (поймано исключение).")
                 await query.answer()
            else:
                logger.error(f"[{MODULE_NAME_FOR_LOG}] TelegramBadRequest при отображении системной информации: {e_tbr}", exc_info=True)
                await query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)
        except Exception as e_edit:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Непредвиденная ошибка при отображении системной информации: {e_edit}", exc_info=True)
            await query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)
    else:
        await query.answer()