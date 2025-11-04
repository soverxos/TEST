# core/admin/roles/keyboards_roles.py
from typing import TYPE_CHECKING, List, Optional, Set, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton # Убедимся что types импортирован
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger 

from Systems.core.ui.callback_data_factories import AdminRolesPanelNavigate
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_back_to_admin_main_menu_button
from Systems.core.rbac.service import (
    PERMISSION_CORE_ROLES_CREATE, 
    PERMISSION_CORE_ROLES_EDIT, 
    PERMISSION_CORE_ROLES_DELETE, 
    PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS,
    DEFAULT_ROLES_DEFINITIONS 
)

if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession
    from Systems.core.database.core_models import Role as DBRole, Permission as DBPermission
    from aiogram import types as AiogramTypes # Используем псевдоним, чтобы не путать с types в аннотациях

ROLES_MGMT_TEXTS = {
    "role_list_title": "🛡️ Управление ролями",
    "role_list_select_action": "Выберите роль для просмотра или управления:",
    "role_list_no_roles": "Нет ролей для отображения",
    "role_details_title": "🛡️ Детали роли",
    "role_action_edit_permissions": "Изменить разрешения",
    "role_action_edit_role": "✏️ Редактировать роль", 
    "role_action_delete_role": "🗑️ Удалить роль",    
    "back_to_roles_list": "⬅️ К списку ролей",
    "edit_permissions_for_role": "Разрешения для роли: {role_name}", 
    "role_action_create_role": "➕ Создать роль",
}


async def get_admin_roles_list_keyboard_local( 
    all_roles: List['DBRole'],
    services: Optional['BotServicesProvider'] = None, 
    user_tg_id: Optional[int] = None,          
    session: Optional['AsyncSession'] = None    
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    texts = ROLES_MGMT_TEXTS

    logger.debug(f"[AdminRolesKeyboards] Генерация списка ролей. Всего ролей: {len(all_roles)}")
    if not all_roles:
        cb_dummy_data = AdminRolesPanelNavigate(action="dummy_no_roles").pack()
        builder.button(
            text=texts["role_list_no_roles"],
            callback_data=cb_dummy_data
        )
        logger.debug(f"[AdminRolesKeyboards] Добавлена кнопка 'нет ролей', callback: {cb_dummy_data}")
    else:
        for role in sorted(all_roles, key=lambda r: r.name):
            cb_data = AdminRolesPanelNavigate(action="view", item_id=role.id).pack()
            builder.button(
                text=f"🛡️ {role.name}",
                callback_data=cb_data
            )
            logger.debug(f"[AdminRolesKeyboards] Добавлена кнопка для роли '{role.name}' (ID: {role.id}), callback: {cb_data}")
        builder.adjust(1)
    
    if services and user_tg_id and session:
        is_owner_from_config = user_tg_id in services.config.core.super_admins
        can_create_roles = False
        try: 
            can_create_roles = is_owner_from_config or await services.rbac.user_has_permission(session, user_tg_id, PERMISSION_CORE_ROLES_CREATE)
        except Exception as e_perm_check:
            logger.error(f"[AdminRolesKeyboards] Ошибка проверки права PERMISSION_CORE_ROLES_CREATE для user {user_tg_id}: {e_perm_check}")

        if can_create_roles:
            cb_create_data = AdminRolesPanelNavigate(action="create_start").pack()
            builder.row( 
                InlineKeyboardButton(
                    text=texts["role_action_create_role"],
                    callback_data=cb_create_data
                )
            )
            logger.debug(f"[AdminRolesKeyboards] Добавлена кнопка 'создать роль', callback: {cb_create_data}")

    builder.row(get_back_to_admin_main_menu_button())
    return builder.as_markup()


async def get_admin_role_details_keyboard_local( 
    target_role: 'DBRole',
    services: 'BotServicesProvider',
    current_admin_tg_id: int,
    session: 'AsyncSession'
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    texts = ROLES_MGMT_TEXTS
    rbac = services.rbac
    current_admin_is_owner = current_admin_tg_id in services.config.core.super_admins
    logger.debug(f"[AdminRolesKeyboards] Генерация деталей для роли '{target_role.name}' (ID: {target_role.id}). Админ: {current_admin_tg_id}, владелец: {current_admin_is_owner}")

    can_edit_role = False
    can_assign_perms = False
    can_delete_role = False

    try: 
        can_edit_role = current_admin_is_owner or await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_ROLES_EDIT)
        can_assign_perms = current_admin_is_owner or await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS)
        can_delete_role = current_admin_is_owner or await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_ROLES_DELETE)
    except Exception as e_perm_check_details:
        logger.error(f"[AdminRolesKeyboards] Ошибка проверки прав для деталей роли {target_role.id} админом {current_admin_tg_id}: {e_perm_check_details}")


    if can_edit_role:
        cb_edit_data = AdminRolesPanelNavigate(action="edit_start", item_id=target_role.id).pack()
        builder.button(
            text=texts["role_action_edit_role"],
            callback_data=cb_edit_data
        )
        logger.debug(f"[AdminRolesKeyboards] Добавлена кнопка 'редактировать роль', callback: {cb_edit_data}")
        
    if can_assign_perms:
        cb_edit_perms_data = AdminRolesPanelNavigate(action="edit_perms_start", item_id=target_role.id, page=1).pack()
        builder.button(
            text=texts["role_action_edit_permissions"],
            callback_data=cb_edit_perms_data
        )
        logger.debug(f"[AdminRolesKeyboards] Добавлена кнопка 'изменить разрешения', callback: {cb_edit_perms_data}")
    
    if target_role.name not in DEFAULT_ROLES_DEFINITIONS: 
        if can_delete_role:
            cb_delete_data = AdminRolesPanelNavigate(action="delete_confirm", item_id=target_role.id).pack()
            builder.button(
                text=texts["role_action_delete_role"],
                callback_data=cb_delete_data
            )
            logger.debug(f"[AdminRolesKeyboards] Добавлена кнопка 'удалить роль', callback: {cb_delete_data}")

    if builder.export(): 
        builder.adjust(1)
    
    builder.row(InlineKeyboardButton(
        text=texts["back_to_roles_list"],
        callback_data=AdminRolesPanelNavigate(action="list").pack()
    ))
    builder.row(get_back_to_admin_main_menu_button())
    return builder.as_markup()

async def get_admin_role_edit_permissions_keyboard_local( 
    target_role: 'DBRole',
    services: 'BotServicesProvider',
    current_admin_tg_id: int,
    session: 'AsyncSession',
    all_system_permissions: Optional[List['DBPermission']] = None,
    category_key: Optional[str] = None,
    entity_name: Optional[str] = None,
    page: int = 1,
    perms_per_page: int = 7 
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    texts = ADMIN_COMMON_TEXTS 
    rbac = services.rbac
    
    role_permission_ids: Set[int] = {perm.id for perm in target_role.permissions if perm.id is not None}

    builder.row(InlineKeyboardButton(
        text=ROLES_MGMT_TEXTS.get("back_to_role_details", "⬅️ К деталям роли"),
        callback_data=AdminRolesPanelNavigate(action="view", item_id=target_role.id).pack()
    ))

    if not category_key:
        builder.button(
            text=texts["perm_category_core"], 
            callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key="core", page=1).pack()
        )
        module_perms_exist = False
        if services.modules:
            declared_module_perms = services.modules.get_all_declared_permissions_from_active_modules()
            if declared_module_perms: module_perms_exist = True
        if module_perms_exist:
            builder.button(
                text=texts["perm_category_modules"],
                callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key="module", page=1).pack()
            )
        builder.adjust(1)
        # Не забываем добавить кнопку "Назад в Админ-панель" и здесь, если это верхний уровень выбора категорий
        builder.row(get_back_to_admin_main_menu_button())
        return builder.as_markup()

    permissions_to_display_final: List['DBPermission'] = []
    if all_system_permissions is None: 
        all_system_permissions = await rbac.get_all_permissions(session)

    back_to_category_selection_button = InlineKeyboardButton(
        text=texts["back_to_perm_categories"], 
        callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key=None, entity_name=None, page=1).pack()
    )

    if category_key == "core":
        CORE_PERM_GROUPS_MAP_ROLES: Dict[str, str] = { 
            k: texts[f"perm_core_group_{k}"] for k in ["users", "roles", "modules_core", "system", "settings_core", "other"]
        }
        CORE_PERM_PREFIXES_MAP_ROLES: Dict[str, str] = {
            "users": "core.users.", "roles": "core.roles.", "modules_core": "core.modules.",
            "system": "core.system.", "settings_core": "core.settings."
        }
        if not entity_name: 
            for group_key, group_display_name in CORE_PERM_GROUPS_MAP_ROLES.items():
                prefix_to_check = CORE_PERM_PREFIXES_MAP_ROLES.get(group_key)
                has_perms_in_group = False
                if prefix_to_check:
                    if any(p.name.startswith(prefix_to_check) for p in all_system_permissions): has_perms_in_group = True
                elif group_key == "other": 
                    known_prefixes = list(CORE_PERM_PREFIXES_MAP_ROLES.values())
                    if any(p.name.startswith("core.") and not any(p.name.startswith(kp) for kp in known_prefixes) for p in all_system_permissions): has_perms_in_group = True
                if has_perms_in_group:
                    builder.button(text=group_display_name, callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key="core", entity_name=group_key, page=1).pack())
            builder.adjust(1)
            builder.row(back_to_category_selection_button)
        else: 
            if entity_name == "other":
                known_prefixes = list(CORE_PERM_PREFIXES_MAP_ROLES.values())
                permissions_to_display_final = [p for p in all_system_permissions if p.name.startswith("core.") and not any(p.name.startswith(kp) for kp in known_prefixes)]
            elif entity_name in CORE_PERM_PREFIXES_MAP_ROLES:
                prefix = CORE_PERM_PREFIXES_MAP_ROLES[entity_name]
                permissions_to_display_final = [p for p in all_system_permissions if p.name.startswith(prefix)]
            builder.row(InlineKeyboardButton(text=texts["back_to_core_perm_groups"], callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key="core", entity_name=None, page=1).pack()))
    elif category_key == "module":
        if not services.modules: 
            builder.button(text="Ошибка: Загрузчик модулей недоступен.", callback_data="dummy_error_no_module_loader_perms"); return builder.as_markup() # Изменена dummy_data
        module_permissions_map: Dict[str, List['DBPermission']] = {}
        module_display_names: Dict[str, str] = {}
        for p in all_system_permissions:
            if not p.name.startswith("core."):
                module_name_candidate = p.name.split('.')[0]
                if module_name_candidate not in module_permissions_map:
                    module_permissions_map[module_name_candidate] = []
                    mod_info = services.modules.get_module_info(module_name_candidate)
                    module_display_names[module_name_candidate] = mod_info.manifest.display_name if mod_info and mod_info.manifest else module_name_candidate
                module_permissions_map[module_name_candidate].append(p)
        if not entity_name: 
            sorted_module_names = sorted(module_permissions_map.keys())
            if not sorted_module_names: builder.button(text=texts["no_modules_with_perms"], callback_data="dummy_no_mod_perms_for_role") # Изменена dummy_data
            else:
                for mod_name in sorted_module_names:
                    builder.button(text=f"🧩 {module_display_names.get(mod_name, mod_name)}", callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key="module", entity_name=mod_name, page=1).pack())
            builder.adjust(1)
            builder.row(back_to_category_selection_button)
        else: 
            permissions_to_display_final = module_permissions_map.get(entity_name, [])
            builder.row(InlineKeyboardButton(text=texts["back_to_module_list_for_perms"], callback_data=AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key="module", entity_name=None, page=1).pack()))
    
    if permissions_to_display_final:
        permissions_to_display_final.sort(key=lambda p: p.name)
        total_perms_in_list = len(permissions_to_display_final)
        total_perm_pages = (total_perms_in_list + perms_per_page - 1) // perms_per_page
        total_perm_pages = max(1, total_perm_pages)
        current_perm_page = max(1, min(page, total_perm_pages))
        start_idx = (current_perm_page - 1) * perms_per_page
        end_idx = start_idx + perms_per_page
        paginated_perms = permissions_to_display_final[start_idx:end_idx]
        if not paginated_perms and current_perm_page == 1: builder.button(text=texts["no_permissions_in_group"], callback_data="dummy_no_perms_in_group_for_role") # Изменена dummy_data
        else:
            for perm in paginated_perms:
                is_assigned = perm.id in role_permission_ids
                prefix = "✅ " if is_assigned else "⬜ "
                button_text = f"{prefix}{perm.name}"
                if perm.id is None: continue 
                builder.button(text=button_text, callback_data=AdminRolesPanelNavigate(action="toggle_perm", item_id=target_role.id, permission_id=perm.id, category_key=category_key, entity_name=entity_name, page=current_perm_page).pack())
            builder.adjust(1)
            if total_perm_pages > 1:
                pagination_row_perms = []
                nav_cb_data_base = AdminRolesPanelNavigate(action="edit_perms_nav", item_id=target_role.id, category_key=category_key, entity_name=entity_name) 
                if current_perm_page > 1: pagination_row_perms.append(InlineKeyboardButton(text=texts["pagination_prev"], callback_data=nav_cb_data_base.model_copy(update={"page": current_perm_page - 1}).pack()))
                pagination_row_perms.append(InlineKeyboardButton(text=f"{current_perm_page}/{total_perm_pages}", callback_data="dummy_role_perm_page")) # Изменена dummy_data
                if current_perm_page < total_perm_pages: pagination_row_perms.append(InlineKeyboardButton(text=texts["pagination_next"], callback_data=nav_cb_data_base.model_copy(update={"page": current_perm_page + 1}).pack()))
                if pagination_row_perms: builder.row(*pagination_row_perms)
    elif entity_name: 
        builder.button(text=texts["no_permissions_in_group"], callback_data="dummy_no_perms_in_group_for_role_entity") # Изменена dummy_data

    builder.row(get_back_to_admin_main_menu_button())
    return builder.as_markup()