# core/admin/users/handlers_direct_perms.py
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from loguru import logger
from sqlalchemy.orm import selectinload
from aiogram.filters import StateFilter # Импортируем StateFilter
from aiogram.exceptions import TelegramBadRequest # Импортируем TelegramBadRequest

from Systems.core.ui.callback_data_factories import AdminUsersPanelNavigate
from .keyboards_users import get_user_direct_perms_keyboard, USERS_MGMT_TEXTS 
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS 
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from Systems.core.rbac.service import PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS 
from Systems.core.database.core_models import User as DBUser, Permission as DBPermission, Role as DBRole # Добавил DBRole

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession

user_direct_perms_router = Router(name="sdb_admin_user_direct_perms_handlers")
MODULE_NAME_FOR_LOG = "AdminUserDirectPerms"

#user_direct_perms_router.callback_query.filter(can_view_admin_panel_filter)

# --- FSM для навигации по прямым разрешениям пользователя ---
class FSMDirectUserPermsNavigation(StatesGroup):
    navigating_direct_perms = State()

# --- Вход в FSM для управления прямыми разрешениями ---
@user_direct_perms_router.callback_query(AdminUsersPanelNavigate.filter(F.action == "edit_direct_perms_start"))
async def cq_admin_user_edit_direct_perms_entry( # Переименовано для консистентности
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    admin_user_id = query.from_user.id
    target_user_db_id = callback_data.item_id

    if target_user_db_id is None:
        await query.answer("Ошибка: ID пользователя не указан.", show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} входит в FSM управления прямыми правами для User DB ID: {target_user_db_id}")

    async with services_provider.db.get_session() as session:
        current_admin_is_owner = admin_user_id in services_provider.config.core.super_admins
        if not current_admin_is_owner and \
           not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS):
            await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True)
            return
        
        target_user = await session.get(DBUser, target_user_db_id)
        if not target_user:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return
        if target_user.telegram_id in services_provider.config.core.super_admins:
            await query.answer("Нельзя управлять прямыми разрешениями Владельца системы.", show_alert=True); return

    await state.clear() 
    await state.set_state(FSMDirectUserPermsNavigation.navigating_direct_perms)
    await state.update_data(
        target_user_id_for_perms=target_user_db_id, 
    )
    
    await _show_user_direct_perms_menu(query, services_provider, state)

# --- Навигация по категориям/сущностям/страницам прямых разрешений ---
@user_direct_perms_router.callback_query(
    AdminUsersPanelNavigate.filter(F.action == "direct_perms_nav"),
    StateFilter(FSMDirectUserPermsNavigation.navigating_direct_perms)
)
async def cq_admin_user_direct_perms_navigate(
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    fsm_data = await state.get_data()
    target_user_db_id = fsm_data.get("target_user_id_for_perms")
    if target_user_db_id is None: 
        await query.answer("Ошибка состояния FSM. Попробуйте выйти и войти снова.", show_alert=True)
        await state.clear(); return

    new_fsm_context_data = {
        "category_key": callback_data.category_key,
        "entity_name": callback_data.entity_name,
        "current_page": callback_data.page or 1
    }
    await state.update_data(**new_fsm_context_data)
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {query.from_user.id} навигация по прямым правам (User ID: {target_user_db_id}). "
                f"Новый FSM контекст навигации: {new_fsm_context_data}")
    
    await _show_user_direct_perms_menu(query, services_provider, state)

# --- Переключение прямого разрешения для пользователя ---
@user_direct_perms_router.callback_query(
    AdminUsersPanelNavigate.filter(F.action == "toggle_direct_perm"),
    StateFilter(FSMDirectUserPermsNavigation.navigating_direct_perms)
)
async def cq_admin_user_toggle_direct_perm(
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate,
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    admin_user_id = query.from_user.id
    fsm_data = await state.get_data()
    target_user_db_id: Optional[int] = fsm_data.get("target_user_id_for_perms")
    permission_to_toggle_id: Optional[int] = callback_data.permission_id

    if target_user_db_id is None or permission_to_toggle_id is None:
        await query.answer("Ошибка: неверные данные для изменения разрешения.", show_alert=True); return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Админ {admin_user_id} изменяет прямое разрешение "
                f"PermID:'{permission_to_toggle_id}' для User DBID:{target_user_db_id}")

    async with services_provider.db.get_session() as session:
        current_admin_is_owner = admin_user_id in services_provider.config.core.super_admins
        if not current_admin_is_owner and \
           not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS):
            await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return
        
        target_user = await session.get(DBUser, target_user_db_id, options=[selectinload(DBUser.direct_permissions)])
        permission_to_modify = await session.get(DBPermission, permission_to_toggle_id)

        if not target_user or not permission_to_modify:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return
        if target_user.telegram_id in services_provider.config.core.super_admins: 
            await query.answer("Нельзя изменять прямые разрешения Владельца.", show_alert=True); return

        user_has_direct_perm = permission_to_modify in target_user.direct_permissions
        alert_text, action_performed = "", False

        if user_has_direct_perm:
            if await services_provider.rbac.remove_direct_permission_from_user(session, target_user, permission_to_modify.name):
                action_performed = True
                alert_text = f"Прямое разрешение '{permission_to_modify.name}' снято."
            else: alert_text = f"Не удалось снять прямое разрешение '{permission_to_modify.name}'."
        else:
            if await services_provider.rbac.assign_direct_permission_to_user(session, target_user, permission_to_modify.name, auto_create_perm=False):
                action_performed = True
                alert_text = f"Прямое разрешение '{permission_to_modify.name}' назначено."
            else: alert_text = f"Не удалось назначить прямое разрешение '{permission_to_modify.name}'."
        
        if action_performed:
            try: await session.commit(); logger.info(f"[{MODULE_NAME_FOR_LOG}] {alert_text} для User ID: {target_user.id}"); await session.refresh(target_user, attribute_names=['direct_permissions'])
            except Exception as e: await session.rollback(); logger.error(f"Ошибка commit: {e}"); alert_text = "Ошибка сохранения."
        
        await query.answer(alert_text, show_alert=action_performed and "Не удалось" not in alert_text)
        await _show_user_direct_perms_menu(query, services_provider, state) 

# --- Вспомогательная функция для отображения меню прямых разрешений ---
async def _show_user_direct_perms_menu(
    query: types.CallbackQuery, 
    services_provider: 'BotServicesProvider', 
    state: FSMContext
):
    admin_user_id = query.from_user.id
    fsm_data = await state.get_data()
    
    target_user_db_id = fsm_data.get("target_user_id_for_perms")
    category_key = fsm_data.get("category_key")
    entity_name = fsm_data.get("entity_name")
    page = fsm_data.get("current_page", 1)

    if target_user_db_id is None:
        await query.answer("Ошибка состояния FSM (ID пользователя).", show_alert=True); await state.clear(); return

    async with services_provider.db.get_session() as session:
        target_user = await session.get(DBUser, target_user_db_id, options=[
            selectinload(DBUser.direct_permissions), 
            selectinload(DBUser.roles).selectinload(DBRole.permissions) 
        ])
        if not target_user:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); await state.clear(); return

        all_system_permissions = await services_provider.rbac.get_all_permissions(session)
        
        base_text = USERS_MGMT_TEXTS["edit_direct_perms_for_user"].format(user_name=hbold(target_user.full_name))
        current_level_text = ""
        if category_key == "core":
            current_level_text = " / Ядро"
            if entity_name: current_level_text += f" / {ADMIN_COMMON_TEXTS.get(f'perm_core_group_{entity_name}', entity_name.capitalize())}"
        elif category_key == "module":
            current_level_text = " / Модули"
            if entity_name:
                mod_info = services_provider.modules.get_module_info(entity_name)
                current_level_text += f" / {mod_info.manifest.display_name if mod_info and mod_info.manifest else entity_name}"
        
        text = f"{base_text}{current_level_text}\nОтметьте прямые разрешения:"
        
        keyboard = await get_user_direct_perms_keyboard(
            target_user=target_user, 
            all_system_permissions=all_system_permissions, 
            services=services_provider, 
            current_admin_tg_id=admin_user_id, 
            session=session,
            category_key=category_key, entity_name=entity_name, page=page
        )

        if query.message:
            try:
                if query.message.text != text or query.message.reply_markup != keyboard:
                    await query.message.edit_text(text, reply_markup=keyboard)
            except TelegramBadRequest as e: # Используем импортированный TelegramBadRequest
                if "message is not modified" not in str(e).lower(): 
                    logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка edit_text (_show_user_direct_perms_menu): {e}")
            except Exception as e_edit:
                logger.error(f"Непредвиденная ошибка в _show_user_direct_perms_menu: {e_edit}", exc_info=True)
                if query.message: await query.answer("Ошибка отображения.", show_alert=True)

# Выход из FSM управления прямыми правами (если пользователь нажимает "К деталям пользователя")
@user_direct_perms_router.callback_query(
    AdminUsersPanelNavigate.filter(F.action == "view"), 
    StateFilter(FSMDirectUserPermsNavigation.navigating_direct_perms) 
)
async def cq_back_to_user_details_from_direct_perms_fsm(
    query: types.CallbackQuery,
    callback_data: AdminUsersPanelNavigate, 
    services_provider: 'BotServicesProvider',
    state: FSMContext
):
    await state.clear() 
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {query.from_user.id} вышел из FSM управления прямыми разрешениями.")
    from .handlers_details import cq_admin_user_view_details_entry
    await cq_admin_user_view_details_entry(query, callback_data, services_provider)