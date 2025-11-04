# core/admin/users/handlers_details.py
from aiogram import Router, types, F
from aiogram.utils.markdown import hbold, hcode
from loguru import logger
from sqlalchemy.orm import selectinload
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

from Systems.core.ui.callback_data_factories import AdminUsersPanelNavigate
from .keyboards_users import get_admin_user_details_keyboard_local, USERS_MGMT_TEXTS 
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS 
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
    admin_tg_id: int
):
    target_user_is_owner = target_user.telegram_id in services_provider.config.core.super_admins
    
    roles_display_str: str
    if target_user_is_owner:
        roles_display_str = USERS_MGMT_TEXTS["user_is_owner_text"]
    elif target_user.roles:
        roles_display_str = ", ".join(sorted([role.name for role in target_user.roles]))
    else:
        roles_display_str = "нет"

    text_parts = [
        f"👤 {hbold(USERS_MGMT_TEXTS['user_details_title'])}: {target_user.full_name}",
        f"   Telegram ID: {hcode(str(target_user.telegram_id))}",
        f"   DB ID: {hcode(str(target_user.id))}",
        f"   Username: {hcode(f'@{target_user.username}') if target_user.username else '-'}",
        f"   Имя: {hcode(target_user.first_name or '-')}",
        f"   Фамилия: {hcode(target_user.last_name or '-')}",
        f"   Язык: {hcode(target_user.preferred_language_code or '-')}",
        f"   Активен: {'Да ✅' if target_user.is_active else 'Нет 💤'}",
        f"   Бот заблокирован: {'Да 🚫' if target_user.is_bot_blocked else 'Нет ✅'}",
        f"   Роли/Статус: {hbold(roles_display_str)}",
        f"   Регистрация: {target_user.created_at.strftime('%Y-%m-%d %H:%M') if target_user.created_at else '-'}",
        f"   Посл. активность: {target_user.last_activity_at.strftime('%Y-%m-%d %H:%M') if target_user.last_activity_at else '-'}",
    ]
    text = "\n".join(text_parts)
    keyboard = await get_admin_user_details_keyboard_local(target_user, services_provider, admin_tg_id, session)

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

    if callback_data.item_id is not None:
        try: target_user_db_id = int(str(callback_data.item_id))
        except ValueError:
            await query.answer("Ошибка: неверный формат ID пользователя.", show_alert=True); return
    
    if target_user_db_id is None:
        await query.answer("Ошибка: ID пользователя не указан.", show_alert=True); return
        
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил детали пользователя с DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_VIEW_DETAILS):
                await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return

        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        
        if not target_user:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return
        
        await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id)
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
    
    if target_user_db_id is None:
        await query.answer("Ошибка: ID пользователя не указан.", show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} изменяет статус активности для пользователя DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_MANAGE_STATUS):
                await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return

        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        if not target_user:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return
        
        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer("Нельзя изменять статус Владельца системы.", show_alert=True)
            await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id)
            return

        new_status = not target_user.is_active
        changed = await services_provider.user_service.set_user_active_status(target_user, new_status, session)
        alert_text = ""
        if changed:
            try:
                await session.commit()
                alert_text = f"Статус активности {target_user.full_name} изменен на: {'Активен ✅' if new_status else 'Неактивен 💤'}"
                logger.info(f"[{MODULE_NAME_FOR_LOG}] {alert_text}")
            except Exception as e_commit:
                await session.rollback()
                alert_text = "Ошибка сохранения изменений."
        else:
            alert_text = "Статус активности не был изменен."
        await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id)
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
    if target_user_db_id is None:
        await query.answer("Ошибка: ID пользователя не указан.", show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} изменяет статус блокировки для пользователя DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_MANAGE_STATUS):
                await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return

        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.roles)])
        if not target_user:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return
        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer("Нельзя изменять статус блокировки Владельца системы.", show_alert=True)
            await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id)
            return

        new_status = not target_user.is_bot_blocked
        changed = await services_provider.user_service.set_user_bot_blocked_status(target_user, new_status, session)
        alert_text = ""
        if changed:
            try:
                await session.commit()
                alert_text = f"Блокировка для {target_user.full_name} изменена на: {'Заблокировал 🚫' if new_status else 'Не блокировал ✅'}"
            except Exception as e_commit: await session.rollback(); alert_text = "Ошибка сохранения."
        else: alert_text = "Статус блокировки не изменен."
        await _send_or_edit_user_details_local(query, target_user, services_provider, session, admin_user_id)
        await query.answer(alert_text, show_alert=bool(changed and "Ошибка" not in alert_text))