# core/admin/roles/handlers_role_perms.py
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from loguru import logger
from sqlalchemy.orm import selectinload
from aiogram.filters import StateFilter # <--- ДОБАВЛЕН ИМПОРТ
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

# Исправленные импорты
from Systems.core.ui.callback_data_factories import AdminRolesPanelNavigate 
from .keyboards_roles import get_admin_role_edit_permissions_keyboard_local, ROLES_MGMT_TEXTS, get_roles_mgmt_texts
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_admin_texts
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from Systems.core.rbac.service import PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS
from Systems.core.database.core_models import Role as DBRole, Permission as DBPermission

from typing import TYPE_CHECKING, Optional, List
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession

role_permissions_router = Router(name="sdb_admin_role_permissions_handlers")
MODULE_NAME_FOR_LOG = "AdminRolePermissions"

#role_permissions_router.callback_query.filter(can_view_admin_panel_filter)

# --- FSM для навигации по разрешениям роли ---
class FSMEditRolePermissions(StatesGroup):
    navigating_role_permissions = State()

# --- Вход в FSM для управления разрешениями роли ---
@role_permissions_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "edit_perms_start"))
async def cq_admin_role_edit_permissions_entry(
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    admin_user_id = query.from_user.id
    target_role_db_id = callback_data.item_id
    page = callback_data.page or 1 

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

    if target_role_db_id is None:
        await query.answer(admin_texts["admin_error_role_id_not_specified"], show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} входит в FSM управления правами для Role ID: {target_role_db_id}, page: {page}")

    async with services_provider.db.get_session() as session:
        current_admin_is_owner = admin_user_id in services_provider.config.core.super_admins
        if not current_admin_is_owner and \
           not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS):
            await query.answer(admin_texts["access_denied"], show_alert=True)
            return
        
        target_role = await session.get(DBRole, target_role_db_id, options=[selectinload(DBRole.permissions)])
        if not target_role:
            await query.answer(admin_texts["not_found_generic"], show_alert=True); return

    await state.clear()
    await state.set_state(FSMEditRolePermissions.navigating_role_permissions)
    await state.update_data(
        target_role_id_for_perms=target_role_db_id,
        current_page=page, 
        # category_key и entity_name будут установлены при навигации
    )
    
    await _show_role_permissions_menu(query, services_provider, state)

# --- Навигация по категориям/сущностям/страницам разрешений роли ---
@role_permissions_router.callback_query(
    AdminRolesPanelNavigate.filter(F.action == "edit_perms_nav"),
    StateFilter(FSMEditRolePermissions.navigating_role_permissions)
)
async def cq_admin_role_permissions_navigate(
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    fsm_data = await state.get_data()
    target_role_db_id = fsm_data.get("target_role_id_for_perms")
    if target_role_db_id is None:
        await query.answer("Ошибка состояния FSM. Попробуйте выйти и войти снова.", show_alert=True)
        await state.clear(); return

    new_fsm_context_data = {
        "category_key": callback_data.category_key,
        "entity_name": callback_data.entity_name,
        "current_page": callback_data.page or 1
    }
    await state.update_data(**new_fsm_context_data)
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {query.from_user.id} навигация по правам роли (Role ID: {target_role_db_id}). "
                f"Новый FSM контекст навигации: {new_fsm_context_data}")
    
    await _show_role_permissions_menu(query, services_provider, state)

# --- Переключение разрешения для роли ---
@role_permissions_router.callback_query(
    AdminRolesPanelNavigate.filter(F.action == "toggle_perm"),
    StateFilter(FSMEditRolePermissions.navigating_role_permissions)
)
async def cq_admin_role_toggle_permission(
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    admin_user_id = query.from_user.id
    
    # Получаем язык пользователя
    user_locale_toggle = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale_toggle = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts_toggle = get_admin_texts(services_provider, user_locale_toggle)
    
    fsm_data = await state.get_data()
    target_role_db_id: Optional[int] = fsm_data.get("target_role_id_for_perms")
    permission_to_toggle_id: Optional[int] = callback_data.permission_id

    if target_role_db_id is None or permission_to_toggle_id is None:
        await query.answer(admin_texts_toggle["admin_error_invalid_permission_data"], show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} изменяет разрешение "
                f"PermID:'{permission_to_toggle_id}' для Role DBID:{target_role_db_id}")

    async with services_provider.db.get_session() as session:
        current_admin_is_owner = admin_user_id in services_provider.config.core.super_admins
        if not current_admin_is_owner and \
           not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS):
            await query.answer(admin_texts_toggle["access_denied"], show_alert=True); return
        
        target_role = await session.get(DBRole, target_role_db_id, options=[selectinload(DBRole.permissions)])
        permission_to_modify = await session.get(DBPermission, permission_to_toggle_id)

        if not target_role or not permission_to_modify:
            await query.answer(admin_texts_toggle["not_found_generic"], show_alert=True); return

        role_has_this_perm = permission_to_modify in target_role.permissions
        alert_text, action_performed = "", False

        if role_has_this_perm:
            if await services_provider.rbac.remove_permission_from_role(session, target_role, permission_to_modify.name):
                action_performed = True
                alert_text = admin_texts_toggle["admin_role_perm_removed"].format(permission_name=permission_to_modify.name)
            else: alert_text = admin_texts_toggle["admin_role_perm_failed_to_remove"].format(permission_name=permission_to_modify.name)
        else:
            if await services_provider.rbac.assign_permission_to_role(session, target_role, permission_to_modify.name, auto_create_perm=False):
                action_performed = True
                alert_text = admin_texts_toggle["admin_role_perm_assigned"].format(permission_name=permission_to_modify.name)
            else: alert_text = admin_texts_toggle["admin_role_perm_failed_to_assign"].format(permission_name=permission_to_modify.name)
        
        if action_performed:
            try: await session.commit(); logger.info(f"[{MODULE_NAME_FOR_LOG}] {alert_text} для Role ID: {target_role.id}"); await session.refresh(target_role, attribute_names=['permissions'])
            except Exception as e: await session.rollback(); logger.error(f"Ошибка commit: {e}"); alert_text = admin_texts_toggle["admin_error_saving"]
        
        await query.answer(alert_text, show_alert=action_performed and "Не удалось" not in alert_text)
        await _show_role_permissions_menu(query, services_provider, state)

# --- Вспомогательная функция для отображения меню разрешений роли ---
async def _show_role_permissions_menu(
    query: types.CallbackQuery, 
    services_provider: 'BotServicesProvider', 
    state: FSMContext
):
    admin_user_id = query.from_user.id
    fsm_data = await state.get_data()
    
    target_role_db_id = fsm_data.get("target_role_id_for_perms")
    category_key = fsm_data.get("category_key")
    entity_name = fsm_data.get("entity_name")
    page = fsm_data.get("current_page", 1)

    if target_role_db_id is None:
        await query.answer("Ошибка состояния FSM (ID роли).", show_alert=True); await state.clear(); return

    async with services_provider.db.get_session() as session:
        target_role = await session.get(DBRole, target_role_db_id, options=[selectinload(DBRole.permissions)])
        if not target_role:
            await query.answer(admin_texts_show["not_found_generic"], show_alert=True); await state.clear(); return

        all_system_permissions = await services_provider.rbac.get_all_permissions(session)
        
        base_text = roles_texts_show["edit_permissions_for_role"].format(role_name=hbold(target_role.name))
        current_level_text = ""
        if category_key == "core":
            current_level_text = f" / {admin_texts_show.get('admin_perm_category_core', 'Ядро')}"
            if entity_name: current_level_text += f" / {admin_texts_show.get(f'admin_perm_core_group_{entity_name}', entity_name.capitalize())}"
        elif category_key == "module":
            current_level_text = f" / {admin_texts_show.get('admin_perm_category_modules', 'Модули')}"
            if entity_name:
                mod_info = services_provider.modules.get_module_info(entity_name)
                current_level_text += f" / {mod_info.manifest.display_name if mod_info and mod_info.manifest else entity_name}"
        
        text = f"{base_text}{current_level_text}\nОтметьте разрешения для назначения/снятия:"  # TODO: добавить в переводы
        
        keyboard = await get_admin_role_edit_permissions_keyboard_local(
            target_role=target_role, 
            all_system_permissions=all_system_permissions, 
            services=services_provider, 
            current_admin_tg_id=admin_user_id, 
            session=session,
            category_key=category_key, entity_name=entity_name, page=page,
            locale=user_locale_show
        )

        if query.message:
            try:
                if query.message.text != text or query.message.reply_markup != keyboard:
                    await query.message.edit_text(text, reply_markup=keyboard)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e).lower(): 
                    logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка edit_text (_show_role_permissions_menu): {e}")
            except Exception as e_edit:
                logger.error(f"Непредвиденная ошибка в _show_role_permissions_menu: {e_edit}", exc_info=True)
                if query.message: await query.answer("Ошибка отображения.", show_alert=True)

# Выход из FSM управления разрешениями роли (если пользователь нажимает "К деталям роли")
@role_permissions_router.callback_query(
    AdminRolesPanelNavigate.filter(F.action == "view"), 
    StateFilter(FSMEditRolePermissions.navigating_role_permissions) 
)
async def cq_back_to_role_details_from_perms_fsm(
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate, 
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    await state.clear() 
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {query.from_user.id} вышел из FSM управления разрешениями роли.")
    from .handlers_details import cq_admin_role_view_details_entry
    await cq_admin_role_view_details_entry(query, callback_data, services_provider)