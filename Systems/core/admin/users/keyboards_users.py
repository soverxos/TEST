# SwiftDevBot/core/admin/users/keyboards_users.py
from typing import TYPE_CHECKING, List, Set, Dict, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from Systems.core.ui.callback_data_factories import AdminUsersPanelNavigate, AdminMainMenuNavigate
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_back_to_admin_main_menu_button, get_admin_texts
from Systems.core.rbac.service import (
    PERMISSION_CORE_USERS_ASSIGN_ROLES, 
    PERMISSION_CORE_USERS_MANAGE_STATUS,
    PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS, # <--- ДОБАВЛЕН ИМПОРТ
    DEFAULT_ROLE_USER 
)

if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession
    from Systems.core.database.core_models import User as DBUser, Role as DBRole, Permission as DBPermission


def get_users_mgmt_texts(services_provider: 'BotServicesProvider', locale: Optional[str] = None) -> dict:
    """Получает словарь переводов для управления пользователями"""
    if not locale:
        locale = services_provider.config.core.i18n.default_locale
    
    from Systems.core.admin.keyboards_admin_common import _get_admin_translator
    translator = _get_admin_translator(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, locale, **kwargs)
    
    return {
        "user_list_title_template": t("admin_user_list_title_template"),
        "user_details_title": t("admin_user_details_title"),
        "user_action_change_roles": t("admin_user_action_change_roles"),
        "user_action_toggle_active": t("admin_user_action_toggle_active"),
        "user_action_toggle_blocked": t("admin_user_action_toggle_blocked"),
        "edit_roles_for_user": t("admin_edit_roles_for_user"),
        "back_to_user_details": t("admin_back_to_user_details"),
        "user_is_owner_text": t("admin_user_is_owner_text"),
        "user_action_direct_perms": t("admin_user_action_direct_perms"),
        "edit_direct_perms_for_user": t("admin_edit_direct_perms_for_user"),
        "perm_status_direct": t("admin_perm_status_direct"),
        "perm_status_role": t("admin_perm_status_role"),
        "perm_status_none": t("admin_perm_status_none"),
        "back_to_direct_perm_categories": t("admin_back_to_direct_perm_categories"),
        "back_to_direct_perm_core_groups": t("admin_back_to_direct_perm_core_groups"),
        "back_to_direct_perm_module_list": t("admin_back_to_direct_perm_module_list"),
        "no_users_to_display": t("admin_no_users_to_display"),
        "user_active_yes": t("admin_user_active_yes"),
        "user_active_no": t("admin_user_active_no"),
        "user_blocked_yes": t("admin_user_blocked_yes"),
        "user_blocked_no": t("admin_user_blocked_no"),
        "user_no_roles": t("admin_user_no_roles"),
        "user_telegram_id": t("admin_user_telegram_id"),
        "user_db_id": t("admin_user_db_id"),
        "user_username": t("admin_user_username"),
        "user_first_name": t("admin_user_first_name"),
        "user_last_name": t("admin_user_last_name"),
        "user_language": t("admin_user_language"),
        "user_active": t("admin_user_active"),
        "user_bot_blocked": t("admin_user_bot_blocked"),
        "user_roles_status": t("admin_user_roles_status"),
        "user_registration": t("admin_user_registration"),
        "user_last_activity": t("admin_user_last_activity"),
    }

# Старый словарь для обратной совместимости (deprecated)
USERS_MGMT_TEXTS = {
    "user_list_title_template": ADMIN_COMMON_TEXTS.get("user_list_title_template", "Пользователи (Стр. {current_page}/{total_pages})"),
    "user_details_title": ADMIN_COMMON_TEXTS.get("user_details_title", "Информация о пользователе"),
    "user_action_change_roles": ADMIN_COMMON_TEXTS.get("user_action_change_roles", "Изменить роли"),
    "user_action_toggle_active": ADMIN_COMMON_TEXTS.get("user_action_toggle_active", "Активность: {status}"),
    "user_action_toggle_blocked": ADMIN_COMMON_TEXTS.get("user_action_toggle_blocked", "Блокировка: {status}"),
    "edit_roles_for_user": ADMIN_COMMON_TEXTS.get("edit_roles_for_user", "Изменение ролей для: {user_name}"),
    "back_to_user_details": ADMIN_COMMON_TEXTS.get("back_to_user_details", "⬅️ К деталям пользователя"),
    "user_is_owner_text": ADMIN_COMMON_TEXTS.get("user_is_owner_text", "👑 Владелец системы (неизменяемый)"),
    "user_action_direct_perms": "💎 Индивидуальные разрешения",
    "edit_direct_perms_for_user": "💎 Индивидуальные разрешения для: {user_name}",
    "perm_status_direct": "✅ (прямое)",
    "perm_status_role": "☑️ (через роль)",
    "perm_status_none": "⬜ (нет)",
    "back_to_direct_perm_categories": "⬅️ К категориям разрешений (для юзера)",
    "back_to_direct_perm_core_groups": "⬅️ К группам Ядра (для юзера)",
    "back_to_direct_perm_module_list": "⬅️ К модулям (для юзера)",
}


async def get_admin_users_list_keyboard_local( 
    users_on_page: List['DBUser'],
    total_pages: int,
    current_page: int,
    services_provider: Optional['BotServicesProvider'] = None,
    locale: Optional[str] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы
    if services_provider:
        users_texts = get_users_mgmt_texts(services_provider, locale)
        admin_texts = get_admin_texts(services_provider, locale)
    else:
        users_texts = USERS_MGMT_TEXTS
        admin_texts = ADMIN_COMMON_TEXTS
    
    if not users_on_page and current_page == 1:
        builder.button(text=users_texts.get("no_users_to_display", "Нет пользователей для отображения"), callback_data=AdminUsersPanelNavigate(action="dummy_no_users").pack())
    else:
        for user_obj in users_on_page:
            user_display = f"{user_obj.full_name}"
            if user_obj.username: user_display += f" (@{user_obj.username})"
            else: user_display += f" (ID: {user_obj.telegram_id})"
            
            status_icons = ["💤" if not user_obj.is_active else "", "🚫" if user_obj.is_bot_blocked else ""]
            status_prefix = "".join(filter(None, status_icons)) + " " if any(status_icons) else ""

            builder.button(
                text=f"{status_prefix}{user_display}",
                callback_data=AdminUsersPanelNavigate(action="view", item_id=user_obj.id).pack()
            )
        builder.adjust(1)

    if total_pages > 1:
        pagination_row = []
        if current_page > 1:
            pagination_row.append(InlineKeyboardButton(
                text=admin_texts["pagination_prev"],
                callback_data=AdminUsersPanelNavigate(action="list", page=current_page - 1).pack()
            ))
        pagination_row.append(InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data=AdminUsersPanelNavigate(action="dummy_page").pack() 
        ))
        if current_page < total_pages:
            pagination_row.append(InlineKeyboardButton(
                text=admin_texts["pagination_next"],
                callback_data=AdminUsersPanelNavigate(action="list", page=current_page + 1).pack()
            ))
        if pagination_row:
            builder.row(*pagination_row)

    builder.row(get_back_to_admin_main_menu_button(services_provider, locale))
    return builder.as_markup()


async def get_admin_user_details_keyboard_local( 
    target_user: 'DBUser', 
    services: 'BotServicesProvider',
    current_admin_tg_id: int, 
    session: 'AsyncSession',
    locale: Optional[str] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы
    if not locale:
        try:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == current_admin_tg_id))
            admin_user = result.scalar_one_or_none()
            if admin_user and admin_user.preferred_language_code:
                locale = admin_user.preferred_language_code
        except Exception:
            pass
        
        if not locale:
            locale = services.config.core.i18n.default_locale
    
    users_texts = get_users_mgmt_texts(services, locale)
    admin_texts = get_admin_texts(services, locale)
    
    rbac = services.rbac
    current_admin_is_owner = current_admin_tg_id in services.config.core.super_admins
    target_user_is_owner = target_user.telegram_id in services.config.core.super_admins

    # --- ИСПРАВЛЕНИЕ УСЛОВИЯ ОТОБРАЖЕНИЯ КНОПКИ "Индивидуальные разрешения" ---
    can_manage_direct_perms = False
    if not target_user_is_owner: # Нельзя управлять правами владельца
        if current_admin_is_owner: # Владелец конфига может всё (кроме прав других владельцев)
            can_manage_direct_perms = True
        else:
            # Проверяем разрешение PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS
            if await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS):
                can_manage_direct_perms = True
    
    if can_manage_direct_perms:
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
        builder.button(
            text=users_texts["user_action_direct_perms"],
            callback_data=AdminUsersPanelNavigate(action="edit_direct_perms_start", item_id=target_user.id).pack()
        )

    if not target_user_is_owner: 
        if current_admin_is_owner or \
           await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_USERS_ASSIGN_ROLES):
            builder.button(
                text=users_texts["user_action_change_roles"],
                callback_data=AdminUsersPanelNavigate(action="edit_roles_start", item_id=target_user.id).pack()
            )

        if current_admin_is_owner or \
           await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_USERS_MANAGE_STATUS):
            active_status_text = users_texts["user_active_no"] if target_user.is_active else users_texts["user_active_yes"]
            builder.button(
                text=users_texts["user_action_toggle_active"].format(status=active_status_text),
                callback_data=AdminUsersPanelNavigate(action="toggle_active", item_id=target_user.id).pack()
            )
            blocked_status_text = users_texts["user_blocked_yes"] if target_user.is_bot_blocked else users_texts["user_blocked_no"]
            builder.button(
                text=users_texts["user_action_toggle_blocked"].format(status=blocked_status_text),
                callback_data=AdminUsersPanelNavigate(action="toggle_blocked", item_id=target_user.id).pack()
            )
    
    if builder.export(): 
        builder.adjust(1)

    builder.row(InlineKeyboardButton(
        text="⬅️ К списку пользователей",  # TODO: добавить в переводы
        callback_data=AdminUsersPanelNavigate(action="list", page=1).pack() 
    ))
    builder.row(get_back_to_admin_main_menu_button(services, locale))
    return builder.as_markup()

async def get_admin_user_edit_roles_keyboard_local( 
    target_user: 'DBUser',
    all_system_roles: List['DBRole'],
    services: 'BotServicesProvider',
    current_admin_tg_id: int,
    session: 'AsyncSession'
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы
    if not locale:
        try:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == current_admin_tg_id))
            admin_user = result.scalar_one_or_none()
            if admin_user and admin_user.preferred_language_code:
                locale = admin_user.preferred_language_code
        except Exception:
            pass
        
        if not locale:
            locale = services.config.core.i18n.default_locale
    
    users_texts = get_users_mgmt_texts(services, locale)
    admin_texts = get_admin_texts(services, locale)
    
    rbac = services.rbac
    current_admin_is_owner = current_admin_tg_id in services.config.core.super_admins

    target_user_role_ids: Set[int] = {role.id for role in target_user.roles if role.id is not None}

    for role in sorted(all_system_roles, key=lambda r: r.name):
        if role.id is None: continue 

        is_assigned = role.id in target_user_role_ids
        prefix = "✅ " if is_assigned else "⬜ "
        
        can_toggle_this_role = False
        if current_admin_is_owner:
            can_toggle_this_role = True
        elif await rbac.user_has_permission(session, current_admin_tg_id, PERMISSION_CORE_USERS_ASSIGN_ROLES):
            if role.name == DEFAULT_ROLE_USER and is_assigned and len(target_user.roles) == 1:
                can_toggle_this_role = False
                prefix = "🔒 " 
            else:
                can_toggle_this_role = True
        
        if can_toggle_this_role:
            builder.button(
                text=f"{prefix}{role.name}",
                callback_data=AdminUsersPanelNavigate(
                    action="toggle_role", 
                    item_id=target_user.id, 
                    role_id=role.id 
                ).pack()
            )
        else: 
            builder.button(
                text=f"{prefix}{role.name} (нет прав)", 
                callback_data=AdminUsersPanelNavigate(action="dummy_cant_toggle").pack() 
            )

    builder.adjust(1)
    builder.row(InlineKeyboardButton(
        text=users_texts["back_to_user_details"], 
        callback_data=AdminUsersPanelNavigate(action="view", item_id=target_user.id).pack()
    ))
    builder.row(get_back_to_admin_main_menu_button(services, locale))
    return builder.as_markup()

# --- Новая клавиатура для управления прямыми разрешениями пользователя ---
async def get_user_direct_perms_keyboard(
    target_user: 'DBUser', # Пользователь, чьи права редактируются
    services: 'BotServicesProvider',
    current_admin_tg_id: int, # Админ, который редактирует
    session: 'AsyncSession',
    all_system_permissions: List['DBPermission'], # Все разрешения в системе
    # Параметры из FSM для навигации:
    category_key: Optional[str] = None,
    entity_name: Optional[str] = None,
    page: int = 1,
    perms_per_page: int = 7,
    locale: Optional[str] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы
    if not locale:
        try:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == current_admin_tg_id))
            admin_user = result.scalar_one_or_none()
            if admin_user and admin_user.preferred_language_code:
                locale = admin_user.preferred_language_code
        except Exception:
            pass
        
        if not locale:
            locale = services.config.core.i18n.default_locale
    
    users_texts = get_users_mgmt_texts(services, locale)
    admin_texts = get_admin_texts(services, locale)
    texts = users_texts 
    
    user_direct_perm_ids: Set[int] = {perm.id for perm in target_user.direct_permissions if perm.id is not None}
    user_role_perm_ids: Set[int] = set()
    for role in target_user.roles:
        if role.permissions:
            user_role_perm_ids.update(p.id for p in role.permissions if p.id is not None)

    # Кнопка "Назад к деталям пользователя"
    builder.row(InlineKeyboardButton(
        text=texts["back_to_user_details"],
        callback_data=AdminUsersPanelNavigate(action="view", item_id=target_user.id).pack()
    ))

    # --- Уровень 1: Выбор основной категории разрешений (Ядро / Модули) ---
    if not category_key:
        builder.button(
            text=admin_texts["perm_category_core"], # Используем общие тексты для категорий
            callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key="core", page=1).pack()
        )
        module_perms_exist = any(not p.name.startswith("core.") for p in all_system_permissions)
        if module_perms_exist:
            builder.button(
                text=admin_texts["perm_category_modules"],
                callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key="module", page=1).pack()
            )
        builder.adjust(1)
        return builder.as_markup()

    # --- Уровень 2 и 3: Выбор подкатегории/модуля и отображение разрешений ---
    permissions_to_display_final: List['DBPermission'] = []
    
    if category_key == "core":
        CORE_PERM_GROUPS_MAP_USERS: Dict[str, str] = { # Локальные тексты, т.к. могут отличаться от ролей
            "users": admin_texts["perm_core_group_users"], 
            "roles": admin_texts["perm_core_group_roles"],
            "modules_core": admin_texts["perm_core_group_modules_core"], 
            "system": admin_texts["perm_core_group_system"],
            "settings_core": admin_texts["perm_core_group_settings_core"], 
            "other": admin_texts["perm_core_group_other"]
        }
        CORE_PERM_PREFIXES_MAP_USERS: Dict[str, str] = { # Аналогично
            "users": "core.users.", "roles": "core.roles.", "modules_core": "core.modules.",
            "system": "core.system.", "settings_core": "core.settings."
        }

        if not entity_name: # Показываем подкатегории ядра
            for group_key, group_display_name in CORE_PERM_GROUPS_MAP_USERS.items():
                prefix_to_check = CORE_PERM_PREFIXES_MAP_USERS.get(group_key)
                has_perms_in_group = False
                if prefix_to_check:
                    if any(p.name.startswith(prefix_to_check) for p in all_system_permissions): has_perms_in_group = True
                elif group_key == "other": 
                    known_prefixes = list(CORE_PERM_PREFIXES_MAP_USERS.values())
                    if any(p.name.startswith("core.") and not any(p.name.startswith(kp) for kp in known_prefixes) for p in all_system_permissions): has_perms_in_group = True
                if has_perms_in_group:
                    builder.button(text=group_display_name, callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key="core", entity_name=group_key, page=1).pack())
            builder.adjust(1)
            builder.row(InlineKeyboardButton(text=texts["back_to_direct_perm_categories"], callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id).pack()))
        else: # Показываем разрешения для выбранной подкатегории ядра
            if entity_name == "other":
                known_prefixes = list(CORE_PERM_PREFIXES_MAP_USERS.values())
                permissions_to_display_final = [p for p in all_system_permissions if p.name.startswith("core.") and not any(p.name.startswith(kp) for kp in known_prefixes)]
            elif entity_name in CORE_PERM_PREFIXES_MAP_USERS:
                prefix = CORE_PERM_PREFIXES_MAP_USERS[entity_name]
                permissions_to_display_final = [p for p in all_system_permissions if p.name.startswith(prefix)]
            builder.row(InlineKeyboardButton(text=texts["back_to_direct_perm_core_groups"], callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key="core").pack()))

    elif category_key == "module":
        if not services.modules: 
            builder.button(text="Ошибка: Загрузчик модулей недоступен.", callback_data="dummy_error_no_module_loader"); return builder.as_markup()
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
            if not sorted_module_names: builder.button(text=admin_texts["no_modules_with_perms"], callback_data="dummy_no_mod_perms_for_user")
            else:
                for mod_name in sorted_module_names:
                    builder.button(text=f"🧩 {module_display_names.get(mod_name, mod_name)}", callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key="module", entity_name=mod_name, page=1).pack())
            builder.adjust(1)
            builder.row(InlineKeyboardButton(text=texts["back_to_direct_perm_categories"], callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id).pack()))
        else: 
            permissions_to_display_final = module_permissions_map.get(entity_name, [])
            builder.row(InlineKeyboardButton(text=texts["back_to_direct_perm_module_list"], callback_data=AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key="module").pack()))
    
    if permissions_to_display_final:
        permissions_to_display_final.sort(key=lambda p: p.name)
        total_perms_in_list = len(permissions_to_display_final)
        total_perm_pages = (total_perms_in_list + perms_per_page - 1) // perms_per_page
        total_perm_pages = max(1, total_perm_pages)
        current_perm_page = max(1, min(page, total_perm_pages))
        start_idx = (current_perm_page - 1) * perms_per_page
        end_idx = start_idx + perms_per_page
        paginated_perms = permissions_to_display_final[start_idx:end_idx]

        if not paginated_perms and current_perm_page == 1:
            builder.button(text=admin_texts["no_permissions_in_group"], callback_data="dummy_no_perms_in_group_for_user")
        else:
            for perm in paginated_perms:
                if perm.id is None: continue
                status_prefix = texts["perm_status_none"] # ⬜
                is_direct = perm.id in user_direct_perm_ids
                is_via_role = perm.id in user_role_perm_ids

                if is_direct:
                    status_prefix = texts["perm_status_direct"] # ✅
                elif is_via_role: # Не прямое, но через роль
                    status_prefix = texts["perm_status_role"] # ☑️
                
                button_text = f"{status_prefix} {perm.name}"
                
                can_toggle_locally = not (is_via_role and not is_direct)

                if can_toggle_locally:
                    builder.button(
                        text=button_text,
                        callback_data=AdminUsersPanelNavigate(
                            action="toggle_direct_perm", 
                            item_id=target_user.id, 
                            permission_id=perm.id,
                            category_key=category_key, 
                            entity_name=entity_name, 
                            page=current_perm_page
                        ).pack()
                    )
                else: 
                    builder.button(
                        text=button_text,
                        callback_data=AdminUsersPanelNavigate(action="dummy_perm_via_role").pack()
                    )
            builder.adjust(1)

            if total_perm_pages > 1:
                pagination_row_perms = []
                nav_cb_data_base = AdminUsersPanelNavigate(action="direct_perms_nav", item_id=target_user.id, category_key=category_key, entity_name=entity_name)
                if current_perm_page > 1: pagination_row_perms.append(InlineKeyboardButton(text=admin_texts["pagination_prev"], callback_data=nav_cb_data_base.model_copy(update={"page": current_perm_page - 1}).pack()))
                pagination_row_perms.append(InlineKeyboardButton(text=f"{current_perm_page}/{total_perm_pages}", callback_data="dummy_direct_perm_page"))
                if current_perm_page < total_perm_pages: pagination_row_perms.append(InlineKeyboardButton(text=admin_texts["pagination_next"], callback_data=nav_cb_data_base.model_copy(update={"page": current_perm_page + 1}).pack()))
                if pagination_row_perms: builder.row(*pagination_row_perms)
    elif entity_name: 
        builder.button(text=admin_texts["no_permissions_in_group"], callback_data="dummy_no_perms_in_group_for_user_entity")

    builder.row(get_back_to_admin_main_menu_button(services, locale))
    return builder.as_markup()

