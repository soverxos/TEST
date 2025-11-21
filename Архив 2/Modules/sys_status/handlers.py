# Хэндлеры для модуля sys_status

import psutil
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.markdown import hbold, hcode
from loguru import logger
from aiogram.exceptions import TelegramBadRequest

# Импорты из нашего проекта
from .permissions import MODULE_NAME, PERM_VIEW_SYS_STATUS
from .keyboards import get_sys_status_keyboard
from .callback_data_factories import SysStatusCallback
from core.ui.callback_data_factories import ModuleMenuEntry

from typing import TYPE_CHECKING, Union
if TYPE_CHECKING:
    from core.services_provider import BotServicesProvider

# Создаем роутер для этого модуля
sys_status_router = Router(name=f"sdb_{MODULE_NAME}_handlers")

def _get_system_status_text() -> str:
    """Собирает и форматирует текстовую информацию о состоянии системы."""
    
    # CPU
    cpu_percent = psutil.cpu_percent()
    cpu_bar = "█" * int(cpu_percent / 10) + "─" * (10 - int(cpu_percent / 10))

    # RAM
    ram = psutil.virtual_memory()
    ram_bar = "█" * int(ram.percent / 10) + "─" * (10 - int(ram.percent / 10))
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)
    
    # Disk
    disk = psutil.disk_usage('/')
    disk_bar = "█" * int(disk.percent / 10) + "─" * (10 - int(disk.percent / 10))
    disk_used_gb = disk.used / (1024**3)
    disk_total_gb = disk.total / (1024**3)
    
    text = (
        f"📊 {hbold('Статус системных ресурсов')}\n\n"
        f"🖥️ {hbold('CPU')}:\n"
        f"  `[{cpu_bar}]` {cpu_percent}%\n\n"
        f"🧠 {hbold('RAM (Память)')}:\n"
        f"  `[{ram_bar}]` {ram.percent}%\n"
        f"  ({hcode(f'{ram_used_gb:.1f} GB')} / {hcode(f'{ram_total_gb:.1f} GB')})\n\n"
        f"💽 {hbold('Disk (/)')}:\n"
        f"  `[{disk_bar}]` {disk.percent}%\n"
        f"  ({hcode(f'{disk_used_gb:.1f} GB')} / {hcode(f'{disk_total_gb:.1f} GB')})"
    )
    return text

async def _send_status_message(target: Union[types.Message, types.CallbackQuery], services: 'BotServicesProvider'):
    """Отправляет или редактирует сообщение со статусом системы."""
    user_id = target.from_user.id
    
    # Проверка разрешений
    async with services.db.get_session() as session:
        if not await services.rbac.user_has_permission(session, user_id, PERM_VIEW_SYS_STATUS):
            if isinstance(target, types.CallbackQuery):
                await target.answer("У вас нет доступа к этой информации.", show_alert=True)
            else:
                await target.answer("У вас нет доступа к этой информации.")
            return

    text = _get_system_status_text()
    keyboard = get_sys_status_keyboard()
    
    if isinstance(target, types.Message):
        await target.answer(text, reply_markup=keyboard)
    elif isinstance(target, types.CallbackQuery) and target.message:
        try:
            # Проверяем, изменилось ли сообщение, чтобы избежать ошибки "message is not modified"
            if target.message.text != text or target.message.reply_markup != keyboard:
                await target.message.edit_text(text, reply_markup=keyboard)
            await target.answer("Данные обновлены!")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                await target.answer() # Просто подтверждаем получение колбэка
            else:
                logger.warning(f"Ошибка при обновлении сообщения статуса: {e}")
                await target.answer("Не удалось обновить информацию.", show_alert=True)


# Хэндлер для команды /sysinfo
@sys_status_router.message(Command("sysinfo"))
async def cmd_sys_status(message: types.Message, services_provider: 'BotServicesProvider'):
    logger.info(f"Пользователь {message.from_user.id} вызвал команду /sysinfo.")
    await _send_status_message(message, services_provider)

# Хэндлер для входа через меню "Модули"
@sys_status_router.callback_query(ModuleMenuEntry.filter(F.module_name == MODULE_NAME))
async def cq_sys_status_from_menu(query: types.CallbackQuery, services_provider: 'BotServicesProvider'):
    logger.info(f"Пользователь {query.from_user.id} вошел в модуль '{MODULE_NAME}' через меню.")
    await _send_status_message(query, services_provider)

# Хэндлер для кнопки "Обновить"
@sys_status_router.callback_query(SysStatusCallback.filter(F.action == "refresh"))
async def cq_refresh_sys_status(query: types.CallbackQuery, services_provider: 'BotServicesProvider'):
    logger.info(f"Пользователь {query.from_user.id} обновил информацию о статусе системы.")
    await _send_status_message(query, services_provider)