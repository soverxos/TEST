# core/admin/users/handlers_roles_assign.py
from aiogram import Router, types, F
from aiogram.utils.markdown import hbold
from loguru import logger
from sqlalchemy.orm import selectinload
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

from Systems.core.ui.callback_data_factories import AdminUsersPanelNavigate
from .keyboards_users import get_admin_user_edit_roles_keyboard_local, USERS_MGMT_TEXTS, get_users_mgmt_texts
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_admin_texts 
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from Systems.core.rbac.service import PERMISSION_CORE_USERS_ASSIGN_ROLES, DEFAULT_ROLE_USER
from Systems.core.database.core_models import User as DBUser, Role as DBRole
from .handlers_details import _send_or_edit_user_details_local

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession

user_roles_assign_router = Router(name="sdb_admin_user_roles_assign_handlers")
MODULE_NAME_FOR_LOG = "AdminUserRolesAssign"

#user_roles_assign_router.callback_query.filter(can_view_admin_panel_filter)

@user_roles_assign_router.callback_query(AdminUsersPanelNavigate.filter(F.action == "edit_roles_start"))
async def cq_admin_user_edit_roles_start_assign( 
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    target_user_db_id: Optional[int] = None
    
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
    users_texts = get_users_mgmt_texts(services_provider, user_locale)
    
    if callback_data.item_id is not None:
        try: 
            target_user_db_id = int(str(callback_data.item_id))
        except ValueError:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Некорректный item_id '{callback_data.item_id}' для edit_roles_start.")
            await query.answer(admin_texts["admin_error_invalid_user_id"], show_alert=True)
            return
    
    if target_user_db_id is None: 
        await query.answer(admin_texts["admin_error_user_id_for_roles_not_specified"], show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} открывает интерфейс редактирования ролей для пользователя DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_ASSIGN_ROLES):
                await query.answer(admin_texts["access_denied"], show_alert=True); return
        
        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        if not target_user:
            await query.answer(admin_texts["not_found_generic"], show_alert=True); return

        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer(admin_texts["admin_error_cannot_change_owner_roles"], show_alert=True)
            await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id, locale=user_locale)
            return

        all_system_roles = await services_provider.rbac.get_all_roles(session)
        text = users_texts["edit_roles_for_user"].format(user_name=hbold(target_user.full_name))
        keyboard = await get_admin_user_edit_roles_keyboard_local(target_user, all_system_roles, services_provider, admin_user_id, session, locale=user_locale)

        if query.message:
            try:
                if query.message.text != text or query.message.reply_markup != keyboard:
                    await query.message.edit_text(text, reply_markup=keyboard)
                await query.answer()
            except TelegramBadRequest as e_tbr: # Используем импортированный TelegramBadRequest
                if "message is not modified" not in str(e_tbr).lower(): await query.answer()
                else: logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка edit_text для ролей: {e_tbr}")
            except Exception as e_edit:
                logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка в cq_admin_user_edit_roles_start_assign: {e_edit}", exc_info=True)
                await query.answer(admin_texts["error_general"], show_alert=True)

@user_roles_assign_router.callback_query(AdminUsersPanelNavigate.filter(F.action == "toggle_role"))
async def cq_admin_user_toggle_role_assign( 
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    target_user_db_id: Optional[int] = None
    role_to_toggle_id: Optional[int] = None

    if callback_data.item_id is not None: 
        try: 
            target_user_db_id = int(str(callback_data.item_id))
        except ValueError: 
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Некорректный item_id '{callback_data.item_id}' для toggle_role.")
            pass 
    
    if callback_data.role_id is not None: 
        try: 
            role_to_toggle_id = int(str(callback_data.role_id))
        except ValueError: 
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Некорректный role_id '{callback_data.role_id}' для toggle_role.")
            pass 

    if target_user_db_id is None or role_to_toggle_id is None:
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Некорректные или отсутствующие ID для переключения роли: user_id={target_user_db_id}, role_id={role_to_toggle_id}")
        await query.answer("Ошибка: неверные данные для изменения роли.", show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} пытается изменить роль ID:{role_to_toggle_id} для пользователя DB ID:{target_user_db_id}")

    async with services_provider.db.get_session() as session:
        is_current_admin_owner = admin_user_id in services_provider.config.core.super_admins
        if not is_current_admin_owner:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_ASSIGN_ROLES):
                await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return
        
        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        role_to_modify = await session.get(DBRole, role_to_toggle_id)

        if not target_user or not role_to_modify:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return
        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer("Нельзя изменять роли Владельца.", show_alert=True); return
            
        user_has_this_role = role_to_modify in target_user.roles
        if role_to_modify.name == DEFAULT_ROLE_USER and user_has_this_role and len(target_user.roles) == 1:
            await query.answer(f"Нельзя снять последнюю роль '{DEFAULT_ROLE_USER}'.", show_alert=True); return
        
        alert_text, action_performed = "", False
        if user_has_this_role: 
            if await services_provider.rbac.remove_role_from_user(session, target_user, role_to_modify.name):
                action_performed, alert_text = True, f"Роль '{role_to_modify.name}' снята."
            else: alert_text = f"Не удалось снять роль '{role_to_modify.name}'."
        else: 
            if await services_provider.rbac.assign_role_to_user(session, target_user, role_to_modify.name):
                action_performed, alert_text = True, f"Роль '{role_to_modify.name}' назначена."
            else: alert_text = f"Не удалось назначить роль '{role_to_modify.name}'."
        
        if action_performed:
            try: 
                await session.commit()
                logger.info(f"[{MODULE_NAME_FOR_LOG}] {alert_text} для {target_user.full_name}")
                await session.refresh(target_user, attribute_names=['roles'])
            except Exception as e: 
                await session.rollback()
                logger.error(f"Ошибка commit: {e}")
                alert_text = "Ошибка сохранения."
                action_performed=False 
        
        all_roles = await services_provider.rbac.get_all_roles(session) 
        keyboard_text = USERS_MGMT_TEXTS["edit_roles_for_user"].format(user_name=hbold(target_user.full_name))
        kb = await get_admin_user_edit_roles_keyboard_local(target_user, all_roles, services_provider, admin_user_id, session)
        if query.message: 
            try: 
                await query.message.edit_text(keyboard_text, reply_markup=kb) # Имя переменной клавиатуры keyboard_text
            except TelegramBadRequest as e_tbr: # Используем импортированный TelegramBadRequest
                if "message is not modified" not in str(e_tbr).lower():
                    logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка обновления клавиатуры ролей (toggle): {e_tbr}")
            except Exception as e: 
                logger.warning(f"Ошибка обновления kb ролей (toggle): {e}")
        await query.answer(alert_text, show_alert=action_performed and "Не удалось" not in alert_text)