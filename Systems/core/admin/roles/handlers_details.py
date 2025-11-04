# core/admin/roles/handlers_details.py
from aiogram import Router, types, F, Bot
from aiogram.utils.markdown import hbold, hcode, hitalic
from loguru import logger
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func as sql_func 
from aiogram.exceptions import TelegramBadRequest 

from Systems.core.ui.callback_data_factories import AdminRolesPanelNavigate
from .keyboards_roles import get_admin_role_details_keyboard_local, ROLES_MGMT_TEXTS
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from Systems.core.rbac.service import PERMISSION_CORE_ROLES_VIEW, DEFAULT_ROLES_DEFINITIONS
from Systems.core.database.core_models import Role as DBRole

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession 

role_details_router = Router(name="sdb_admin_role_details_handlers")
MODULE_NAME_FOR_LOG = "AdminRoleMgmtDetails"

#role_details_router.callback_query.filter(can_view_admin_panel_filter)

@role_details_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "view"))
async def cq_admin_role_view_details_entry( 
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate, 
    services_provider: 'BotServicesProvider'
):
    # logger.critical(f"!!! [{MODULE_NAME_FOR_LOG}] ХЭНДЛЕР cq_admin_role_view_details_entry ВЫЗВАН! Callback: {callback_data.model_dump_json(exclude_none=True)}") # <--- УБРАНО
    
    admin_user_id = query.from_user.id
    target_role_db_id: Optional[int] = None 
    
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] Получен callback для просмотра деталей роли: {callback_data.model_dump_json(exclude_none=True)}")

    if callback_data.item_id is None or not str(callback_data.item_id).isdigit():
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Отсутствует или некорректный item_id (ID роли: {callback_data.item_id}) для просмотра деталей.")
        await query.answer("Ошибка: ID роли не указан или некорректен.", show_alert=True)
        return
    
    target_role_db_id = int(str(callback_data.item_id))
        
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил детали роли с DB ID: {target_role_db_id}")

    async with services_provider.db.get_session() as session: # type: AsyncSession
        has_perm_to_view = False
        is_owner_from_config = admin_user_id in services_provider.config.core.super_admins
        if is_owner_from_config:
            has_perm_to_view = True
            logger.trace(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} является Владельцем, доступ к деталям роли разрешен.")
        else:
            try:
                has_perm_to_view = await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_VIEW)
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} имеет право '{PERMISSION_CORE_ROLES_VIEW}': {has_perm_to_view}")
            except Exception as e_perm:
                 logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка проверки права PERMISSION_CORE_ROLES_VIEW для {admin_user_id}: {e_perm}")
                 await query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)
                 return

        if not has_perm_to_view:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} не имеет прав для просмотра деталей роли.")
            await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True)
            return

        role = await session.get(DBRole, target_role_db_id, options=[selectinload(DBRole.permissions)])
        
        if not role:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Роль с DB ID: {target_role_db_id} не найдена.")
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True)
            return
        
        logger.debug(f"[{MODULE_NAME_FOR_LOG}] Роль '{role.name}' найдена, генерация текста и клавиатуры...")
        permissions_list_str = "\n".join(
            [f"  ▫️ {hcode(p.name)} ({hitalic(p.description or 'без описания')})" for p in sorted(role.permissions, key=lambda x: x.name)]
        ) if role.permissions else "  (нет назначенных разрешений)"

        text_parts = [
            f"{ROLES_MGMT_TEXTS['role_details_title']}: {hcode(role.name)}",
            f"   DB ID: {hcode(str(role.id))}",
            f"   Описание: {hitalic(role.description or 'отсутствует')}",
            f"\n{hbold('Разрешения этой роли:')}",
            permissions_list_str
        ]
        text = "\n".join(text_parts)
        
        keyboard = await get_admin_role_details_keyboard_local(role, services_provider, admin_user_id, session)
        logger.debug(f"[{MODULE_NAME_FOR_LOG}] Клавиатура для деталей роли '{role.name}' сгенерирована.")

        if query.message:
            try:
                if query.message.text != text or query.message.reply_markup != keyboard:
                    await query.message.edit_text(text, reply_markup=keyboard)
                    logger.debug(f"[{MODULE_NAME_FOR_LOG}] Сообщение с деталями роли '{role.name}' отредактировано.")
                else:
                    logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение деталей роли ({role.id}) не было изменено.")
                await query.answer()
            except TelegramBadRequest as e_tbr:
                if "message is not modified" in str(e_tbr).lower():
                    logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение деталей роли ({role.id}) не было изменено (поймано исключение).")
                    await query.answer()
                else:
                    logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка редактирования деталей роли ({role.id}): {e_tbr}")
            except Exception as e_edit:
                logger.error(f"[{MODULE_NAME_FOR_LOG}] Непредвиденная ошибка в cq_admin_role_view_details_entry для роли {role.id}: {e_edit}", exc_info=True)
                await query.answer(ADMIN_COMMON_TEXTS["error_general"], show_alert=True)
        else: 
             logger.warning(f"[{MODULE_NAME_FOR_LOG}] query.message is None в cq_admin_role_view_details_entry для роли {role.id}.")
             await query.answer()