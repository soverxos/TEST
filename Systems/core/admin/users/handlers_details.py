# core/admin/users/handlers_details.py
from aiogram import Router, types, F
from aiogram.utils.markdown import hbold, hcode
from loguru import logger
from sqlalchemy.orm import selectinload
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

from Systems.core.ui.callback_data_factories import AdminUsersPanelNavigate
from .keyboards_users import get_admin_user_details_keyboard_local, USERS_MGMT_TEXTS, get_users_mgmt_texts
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_admin_texts 
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from Systems.core.rbac.service import PERMISSION_CORE_USERS_VIEW_DETAILS, PERMISSION_CORE_USERS_MANAGE_STATUS
from Systems.core.database.core_models import User as DBUser

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession

user_details_router = Router(name="sdb_admin_user_details_handlers")
MODULE_NAME_FOR_LOG = "AdminUserDetails"

#user_details_router.callback_query.filter(can_view_admin_panel_filter)

async def _send_or_edit_user_details_local( 
    query: types.CallbackQuery, 
    target_user: DBUser, 
    services_provider: 'BotServicesProvider', 
    session: 'AsyncSession', 
    admin_tg_id: int,
    locale: Optional[str] = None
):
    # Получаем язык пользователя
    if not locale:
        try:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_tg_id))
            admin_user = result.scalar_one_or_none()
            if admin_user and admin_user.preferred_language_code:
                locale = admin_user.preferred_language_code
        except Exception:
            pass
        
        if not locale:
            locale = services_provider.config.core.i18n.default_locale
    
    # Получаем переводы
    users_texts = get_users_mgmt_texts(services_provider, locale)
    admin_texts = get_admin_texts(services_provider, locale)
    
    target_user_is_owner = target_user.telegram_id in services_provider.config.core.super_admins
    
    roles_display_str: str
    if target_user_is_owner:
        roles_display_str = users_texts["user_is_owner_text"]
    elif target_user.roles:
        roles_display_str = ", ".join(sorted([role.name for role in target_user.roles]))
    else:
        roles_display_str = users_texts["user_no_roles"]

    text_parts = [
        f"👤 {hbold(users_texts['user_details_title'])}: {target_user.full_name}",
        f"   {users_texts['user_telegram_id']}: {hcode(str(target_user.telegram_id))}",
        f"   {users_texts['user_db_id']}: {hcode(str(target_user.id))}",
        f"   {users_texts['user_username']}: {hcode(f'@{target_user.username}') if target_user.username else '-'}",
        f"   {users_texts['user_first_name']}: {hcode(target_user.first_name or '-')}",
        f"   {users_texts['user_last_name']}: {hcode(target_user.last_name or '-')}",
        f"   {users_texts['user_language']}: {hcode(target_user.preferred_language_code or '-')}",
        f"   {users_texts['user_active']}: {users_texts['user_active_yes'] if target_user.is_active else users_texts['user_active_no']}",
        f"   {users_texts['user_bot_blocked']}: {users_texts['user_blocked_yes'] if target_user.is_bot_blocked else users_texts['user_blocked_no']}",
        f"   {users_texts['user_roles_status']}: {hbold(roles_display_str)}",
        f"   {users_texts['user_registration']}: {target_user.created_at.strftime('%Y-%m-%d %H:%M') if target_user.created_at else '-'}",
        f"   {users_texts['user_last_activity']}: {target_user.last_activity_at.strftime('%Y-%m-%d %H:%M') if target_user.last_activity_at else '-'}",
    ]
    text = "\n".join(text_parts)
    keyboard = await get_admin_user_details_keyboard_local(target_user, services_provider, admin_tg_id, session, locale=locale)

    if query.message:
        try:
            if query.message.text != text or query.message.reply_markup != keyboard:
                await query.message.edit_text(text, reply_markup=keyboard)
            else:
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение деталей пользователя ({target_user.id}) не было изменено.")
        except TelegramBadRequest as e_tbr: # Используем импортированный TelegramBadRequest
            if "message is not modified" in str(e_tbr).lower():
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Сообщение деталей пользователя ({target_user.id}) не было изменено (поймано исключение).")
            else:
                logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка редактирования деталей пользователя ({target_user.id}): {e_tbr}")
        except Exception as e_edit:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Непредвиденная ошибка в _send_or_edit_user_details_local для пользователя {target_user.id}: {e_edit}", exc_info=True)


@user_details_router.callback_query(AdminUsersPanelNavigate.filter(F.action == "view"))
async def cq_admin_user_view_details_entry( 
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
    
    if callback_data.item_id is not None:
        try: target_user_db_id = int(str(callback_data.item_id))
        except ValueError:
            await query.answer(admin_texts["admin_error_invalid_user_id_format"], show_alert=True); return
    
    if target_user_db_id is None:
        await query.answer(admin_texts["admin_error_user_id_not_specified"], show_alert=True); return
        
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил детали пользователя с DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_VIEW_DETAILS):
                await query.answer(admin_texts["access_denied"], show_alert=True); return

        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        
        if not target_user:
            await query.answer(admin_texts["not_found_generic"], show_alert=True); return
        
        await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id, locale=user_locale)
    await query.answer() 

@user_details_router.callback_query(AdminUsersPanelNavigate.filter(F.action == "toggle_active"))
async def cq_admin_user_toggle_active_details( 
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    target_user_db_id: Optional[int] = None
    if callback_data.item_id is not None:
        try: target_user_db_id = int(str(callback_data.item_id))
        except ValueError: pass
    
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
    
    if target_user_db_id is None:
        await query.answer(admin_texts["admin_error_user_id_not_specified"], show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} изменяет статус активности для пользователя DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_MANAGE_STATUS):
                await query.answer(admin_texts["access_denied"], show_alert=True); return

        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        if not target_user:
            await query.answer(admin_texts["not_found_generic"], show_alert=True); return
        
        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer(admin_texts["admin_error_cannot_change_owner_status"], show_alert=True)
            await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id, locale=user_locale)
            return

        new_status = not target_user.is_active
        changed = await services_provider.user_service.set_user_active_status(target_user, new_status, session)
        alert_text = ""
        if changed:
            try:
                await session.commit()
                status_text = users_texts["user_active_yes"] if new_status else users_texts["user_active_no"]
                alert_text = admin_texts["admin_user_status_active_changed"].format(user_name=target_user.full_name, status=status_text)
                logger.info(f"[{MODULE_NAME_FOR_LOG}] {alert_text}")
            except Exception as e_commit:
                await session.rollback()
                alert_text = admin_texts["admin_error_saving"]
        else:
            alert_text = admin_texts["admin_user_status_active_not_changed"]
        await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id, locale=user_locale)
        await query.answer(alert_text, show_alert=bool(changed and "Ошибка" not in alert_text)) 

@user_details_router.callback_query(AdminUsersPanelNavigate.filter(F.action == "toggle_blocked"))
async def cq_admin_user_toggle_blocked_details( 
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    target_user_db_id: Optional[int] = None
    if callback_data.item_id is not None:
        try: target_user_db_id = int(str(callback_data.item_id))
        except ValueError: pass
    
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
    
    if target_user_db_id is None:
        await query.answer(admin_texts["admin_error_user_id_not_specified"], show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} изменяет статус блокировки для пользователя DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_MANAGE_STATUS):
                await query.answer(admin_texts["access_denied"], show_alert=True); return

        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        if not target_user:
            await query.answer(admin_texts["not_found_generic"], show_alert=True); return
        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer(admin_texts["admin_error_cannot_change_owner_block_status"], show_alert=True)
            await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id, locale=user_locale)
            return

        new_status = not target_user.is_bot_blocked
        changed = await services_provider.user_service.set_user_bot_blocked_status(target_user, new_status, session)
        alert_text = ""
        if changed:
            try:
                await session.commit()
                status_text = users_texts["user_blocked_yes"] if new_status else users_texts["user_blocked_no"]
                alert_text = admin_texts["admin_user_block_status_changed"].format(user_name=target_user.full_name, status=status_text)
            except Exception as e_commit: await session.rollback(); alert_text = admin_texts["admin_error_saving"]
        else: alert_text = admin_texts["admin_user_block_status_not_changed"]
        await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id, locale=user_locale)
        await query.answer(alert_text, show_alert=bool(changed and "Ошибка" not in alert_text))