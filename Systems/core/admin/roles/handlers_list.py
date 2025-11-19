# core/admin/roles/handlers_list.py
from aiogram import Router, types, F, Bot 
from aiogram.utils.markdown import hbold
from loguru import logger
from sqlalchemy import select, func as sql_func
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

from Systems.core.ui.callback_data_factories import AdminRolesPanelNavigate
from .keyboards_roles import get_admin_roles_list_keyboard_local, ROLES_MGMT_TEXTS, get_roles_mgmt_texts
from Systems.core.admin.keyboards_admin_common import get_admin_texts
from Systems.core.admin.filters_admin import can_view_admin_panel_filter 
from Systems.core.rbac.service import PERMISSION_CORE_ROLES_VIEW
from Systems.core.database.core_models import Role as DBRole

from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession 

roles_list_router = Router(name="sdb_admin_roles_list_handlers")
MODULE_NAME_FOR_LOG = "AdminRoleMgmtList"

#roles_list_router.callback_query.filter(can_view_admin_panel_filter) 

@roles_list_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "list"))
async def cq_admin_roles_list_entry( 
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил список ролей.")

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
    roles_texts = get_roles_mgmt_texts(services_provider, user_locale)

    async with services_provider.db.get_session() as session: # type: AsyncSession
        has_perm_to_view_list = False
        is_owner_from_config = admin_user_id in services_provider.config.core.super_admins
        if is_owner_from_config:
            has_perm_to_view_list = True
        else:
            try:
                has_perm_to_view_list = await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_VIEW)
            except Exception as e_perm_check_list:
                logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка проверки права PERMISSION_CORE_ROLES_VIEW для user {admin_user_id}: {e_perm_check_list}")
                await query.answer(admin_texts["admin_error_checking_permissions"], show_alert=True) 
                return

        if not has_perm_to_view_list:
            await query.answer(admin_texts["admin_error_no_permission_to_view_roles"], show_alert=True) 
            return
        
        all_roles: List[DBRole] = await services_provider.rbac.get_all_roles(session)
        
        text = f"{roles_texts['role_list_title']}\n{roles_texts['role_list_select_action']}"
        keyboard = await get_admin_roles_list_keyboard_local(all_roles, services_provider, admin_user_id, session, locale=user_locale)

        target_chat_id = query.message.chat.id if query.message else admin_user_id

        try:
            if query.message and (query.message.text != text or query.message.reply_markup != keyboard):
                await query.message.edit_text(text, reply_markup=keyboard)
                logger.debug(f"[{MODULE_NAME_FOR_LOG}] Сообщение со списком ролей отредактировано.")
            elif not query.message: 
                 await query.bot.send_message(target_chat_id, text, reply_markup=keyboard)
                 logger.debug(f"[{MODULE_NAME_FOR_LOG}] Сообщение со списком ролей отправлено (т.к. query.message был None).")
            else:
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение списка ролей не изменено.")
            await query.answer()
        except TelegramBadRequest as e_tbr: # Используем импортированный TelegramBadRequest
            if query.message and "message to edit not found" in str(e_tbr).lower(): 
                logger.warning(f"[{MODULE_NAME_FOR_LOG}] Сообщение для редактирования не найдено, отправка нового: {e_tbr}")
                await query.bot.send_message(target_chat_id, text, reply_markup=keyboard)
                await query.answer()
            elif "message is not modified" in str(e_tbr).lower():
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение списка ролей не изменено (поймано исключение).")
                await query.answer()
            else:
                logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка Telegram BadRequest при редактировании/отправке списка ролей: {e_tbr}")
                await query.answer(admin_texts["admin_error_displaying_list"], show_alert=True)
        except Exception as e_edit:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Непредвиденная ошибка в cq_admin_roles_list_entry: {e_edit}", exc_info=True)
            await query.answer(admin_texts["admin_error_displaying_role_list"], show_alert=True)