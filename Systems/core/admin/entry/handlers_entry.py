# core/admin/entry/handlers_entry.py
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from loguru import logger
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_admin_main_menu_keyboard 
from Systems.core.ui.callback_data_factories import CoreMenuNavigate, AdminMainMenuNavigate
from Systems.core.admin.filters_admin import can_view_admin_panel_filter 

from typing import TYPE_CHECKING, Union
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession 


admin_entry_router = Router(name="sdb_admin_entry_handlers")
MODULE_NAME_FOR_LOG = "AdminEntry"

#admin_entry_router.message.filter(can_view_admin_panel_filter)
#admin_entry_router.callback_query.filter(can_view_admin_panel_filter)


async def send_admin_main_menu(message_or_query: Union[types.Message, types.CallbackQuery], services_provider: 'BotServicesProvider'):
    user_id = message_or_query.from_user.id 
    
    text = (f"🛠 {hbold('Административная панель SwiftDevBot')}\n"
            f"Выберите раздел для управления:")
    
    async with services_provider.db.get_session() as session: 
        keyboard = await get_admin_main_menu_keyboard(services_provider, user_id, session)

    if isinstance(message_or_query, types.Message):
        await message_or_query.answer(text, reply_markup=keyboard)
    elif isinstance(message_or_query, types.CallbackQuery) and message_or_query.message:
        try:
            if message_or_query.message.text != text or message_or_query.message.reply_markup != keyboard:
                await message_or_query.message.edit_text(text, reply_markup=keyboard)
            else:
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение админ-панели не было изменено.")
            await message_or_query.answer() 
        except TelegramBadRequest as e_tbr: # Используем импортированный TelegramBadRequest
            if "message is not modified" in str(e_tbr).lower():
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение админ-панели не было изменено (поймано исключение TelegramBadRequest).")
                await message_or_query.answer()
            else:
                logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка редактирования сообщения для админ-панели: {e_tbr}")
                if isinstance(message_or_query, types.CallbackQuery): 
                    try:
                        await message_or_query.bot.send_message(user_id, text, reply_markup=keyboard)
                        await message_or_query.message.delete() 
                        await message_or_query.answer()
                    except Exception as e_send_new:
                        logger.error(f"[{MODULE_NAME_FOR_LOG}] Не удалось отправить новое сообщение после ошибки редактирования: {e_send_new}")
                        await message_or_query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)
                else: 
                    await message_or_query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)
        except Exception as e:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Непредвиденная ошибка при отправке меню админ-панели: {e}", exc_info=True)
            if isinstance(message_or_query, types.CallbackQuery):
                await message_or_query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)


@admin_entry_router.message(Command("admin_cp"))
async def cmd_admin_panel_main(message: types.Message, services_provider: 'BotServicesProvider'):
    user_id = message.from_user.id 
    
    # Проверяем права доступа к админ-панели
    has_admin_access = False
    is_super_admin = user_id in services_provider.config.core.super_admins
    
    if is_super_admin:
        has_admin_access = True
    else:
        try:
            async with services_provider.db.get_session() as session:
                from Systems.core.rbac.service import PERMISSION_CORE_VIEW_ADMIN_PANEL
                has_admin_access = await services_provider.rbac.user_has_permission(session, user_id, PERMISSION_CORE_VIEW_ADMIN_PANEL)
        except Exception as e:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка проверки прав доступа для пользователя {user_id}: {e}")
            has_admin_access = False
    
    if has_admin_access:
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} (с правами) вошел в админ-панель через команду /admin_cp.")
        await send_admin_main_menu(message, services_provider)
    else:
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} (без прав) попытался войти в админ-панель через команду /admin_cp.")
        await message.answer(
            "🚫 У вас нет прав доступа к административной панели.\n\n"
            "Если вы считаете, что это ошибка, обратитесь к администратору бота.",
            show_alert=False
        )

@admin_entry_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "admin_panel_main"))
async def cq_core_nav_to_admin_panel_main(query: types.CallbackQuery, services_provider: 'BotServicesProvider'):
    user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} (с правами) вошел в админ-панель через главное меню SDB.")
    await send_admin_main_menu(query, services_provider)

@admin_entry_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "main_admin"))
async def cq_admin_nav_to_main_admin_menu(query: types.CallbackQuery, services_provider: 'BotServicesProvider'):
    user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} вернулся в главное меню админ-панели.")
    await send_admin_main_menu(query, services_provider)

@admin_entry_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "users"))
async def cq_admin_main_to_users_list(
    query: types.CallbackQuery, 
    services_provider: 'BotServicesProvider'
):
    from Systems.core.admin.users.handlers_list import cq_admin_users_list_entry
    from Systems.core.ui.callback_data_factories import AdminUsersPanelNavigate 
    await cq_admin_users_list_entry(query, AdminUsersPanelNavigate(action="list", page=1), services_provider)

@admin_entry_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "roles"))
async def cq_admin_main_to_roles_list(
    query: types.CallbackQuery, 
    services_provider: 'BotServicesProvider',
    bot: Bot 
):
    from Systems.core.admin.roles.handlers_list import cq_admin_roles_list_entry
    from Systems.core.ui.callback_data_factories import AdminRolesPanelNavigate 
    await cq_admin_roles_list_entry(query, AdminRolesPanelNavigate(action="list"), services_provider)

@admin_entry_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "sys_info"))
async def cq_admin_main_to_sys_info(
    query: types.CallbackQuery, 
    services_provider: 'BotServicesProvider',
    bot: Bot
):
    from Systems.core.admin.sys_info.handlers_sys_info import cq_admin_show_system_info_entry
    from Systems.core.ui.callback_data_factories import AdminSysInfoPanelNavigate 
    await cq_admin_show_system_info_entry(query, AdminSysInfoPanelNavigate(action="show"), services_provider, bot)

@admin_entry_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "modules"))
async def cq_admin_main_to_modules(query: types.CallbackQuery, services_provider: 'BotServicesProvider'):
    await query.answer("Раздел 'Управление модулями' в разработке.", show_alert=True)