# core/admin/keyboards_admin_common.py
from aiogram import types 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder 
from Systems.core.ui.callback_data_factories import CoreMenuNavigate, AdminMainMenuNavigate

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from Systems.core.i18n.translator import Translator
    from sqlalchemy.ext.asyncio import AsyncSession
    from Systems.core.rbac.service import (
        PERMISSION_CORE_USERS_VIEW_LIST,
        PERMISSION_CORE_MODULES_VIEW_LIST,
        PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC,
        PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL,
        PERMISSION_CORE_ROLES_VIEW
    )

# Глобальный кэш для translator в админ-панели
_admin_translator_cache: Optional['Translator'] = None

def _get_admin_translator(services_provider: 'BotServicesProvider') -> 'Translator':
    """Получает или создает translator для использования в админ-панели"""
    global _admin_translator_cache
    if _admin_translator_cache is None:
        from Systems.core.i18n.translator import Translator
        _admin_translator_cache = Translator(
            locales_dir=services_provider.config.core.i18n.locales_dir,
            domain=services_provider.config.core.i18n.domain,
            default_locale=services_provider.config.core.i18n.default_locale,
            available_locales=services_provider.config.core.i18n.available_locales
        )
    return _admin_translator_cache

def get_admin_texts(services_provider: 'BotServicesProvider', locale: Optional[str] = None) -> dict:
    """Получает словарь переводов для админ-панели"""
    if not locale:
        locale = services_provider.config.core.i18n.default_locale
    
    translator = _get_admin_translator(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, locale, **kwargs)
    
    return {
        "admin_panel_title": t("admin_panel_title"),
        "admin_panel_select_section": t("admin_panel_select_section"),
        "admin_no_access": t("admin_no_access"),
        "admin_modules_in_development": t("admin_modules_in_development"),
        "back_to_main_menu_sdb": t("admin_back_to_main_menu_sdb"),
        "back_to_admin_menu_main": t("admin_back_to_admin_menu_main"),
        "pagination_prev": t("admin_pagination_prev"),
        "pagination_next": t("admin_pagination_next"),
        "confirm_yes": t("admin_confirm_yes"),
        "confirm_no": t("admin_confirm_no"),
        "close_message": t("admin_close_message"),
        "error_general": t("admin_error_general"),
        "access_denied": t("admin_access_denied"),
        "not_found_generic": t("admin_not_found_generic"),
        "system_info": t("admin_system_info"),
        "manage_modules": t("admin_manage_modules"),
        "manage_users": t("admin_manage_users"),
        "manage_roles": t("admin_manage_roles"),
        "perm_category_core": t("admin_perm_category_core"),
        "perm_category_modules": t("admin_perm_category_modules"),
        "perm_core_group_users": t("admin_perm_core_group_users"),
        "perm_core_group_roles": t("admin_perm_core_group_roles"),
        "perm_core_group_modules_core": t("admin_perm_core_group_modules_core"),
        "perm_core_group_system": t("admin_perm_core_group_system"),
        "perm_core_group_settings_core": t("admin_perm_core_group_settings_core"),
        "perm_core_group_other": t("admin_perm_core_group_other"),
        "back_to_perm_categories": t("admin_back_to_perm_categories"),
        "back_to_core_perm_groups": t("admin_back_to_core_perm_groups"),
        "back_to_module_list_for_perms": t("admin_back_to_module_list_for_perms"),
        "no_modules_with_perms": t("admin_no_modules_with_perms"),
        "no_permissions_in_group": t("admin_no_permissions_in_group"),
        "fsm_enter_role_name": t("admin_fsm_enter_role_name"),
        "fsm_role_name_empty": t("admin_fsm_role_name_empty"),
        "fsm_role_name_taken": t("admin_fsm_role_name_taken"),
        "fsm_enter_role_description": t("admin_fsm_enter_role_description"),
        "fsm_command_skip_description": t("admin_fsm_command_skip_description"),
        "fsm_command_cancel_role_creation": t("admin_fsm_command_cancel_role_creation"),
        "fsm_role_created_successfully": t("admin_fsm_role_created_successfully"),
        "fsm_role_creation_cancelled": t("admin_fsm_role_creation_cancelled"),
        "fsm_edit_role_title": t("admin_fsm_edit_role_title"),
        "fsm_edit_role_name_not_allowed": t("admin_fsm_edit_role_name_not_allowed"),
        "fsm_enter_new_role_description": t("admin_fsm_enter_new_role_description"),
        "fsm_enter_new_role_name": t("admin_fsm_enter_new_role_name"),
        "fsm_command_skip_name": t("admin_fsm_command_skip_name"),
        "fsm_command_cancel_role_edit": t("admin_fsm_command_cancel_role_edit"),
        "fsm_role_updated_successfully": t("admin_fsm_role_updated_successfully"),
        "fsm_role_update_cancelled": t("admin_fsm_role_update_cancelled"),
        "delete_role_confirm_text": t("admin_delete_role_confirm_text"),
        "role_is_standard_cant_delete": t("admin_role_is_standard_cant_delete"),
        "role_delete_failed": t("admin_role_delete_failed"),
        "role_deleted_successfully": t("admin_role_deleted_successfully"),
    }

# Старый словарь для обратной совместимости (deprecated, будет удален)
ADMIN_COMMON_TEXTS = {
    "back_to_main_menu_sdb": "🏠 Главное меню SDB",
    "back_to_admin_menu_main": "⬅️ Админ-панель (Главная)",
    "pagination_prev": "⬅️ Пред.",
    "pagination_next": "След. ➡️",
    "confirm_yes": "✅ Да",
    "confirm_no": "❌ Нет",
    "close_message": "❌ Закрыть это сообщение",
    "error_general": "Произошла ошибка. Попробуйте позже.",
    "access_denied": "У вас нет прав для этого действия.",
    "not_found_generic": "Запрошенный элемент не найден.",
    
    # Тексты для кнопок главного меню админки - более четкие и логично сгруппированные
    "system_info": "ℹ️ Информация о системе",
    "manage_modules": "🧩 Управление модулями", 
    "manage_users": "👥 Управление пользователями",
    "manage_roles": "🛡️ Управление ролями",

    # Тексты для категорий и групп разрешений (добавлены)
    "perm_category_core": "Разрешения Ядра",
    "perm_category_modules": "Разрешения Модулей",
    "perm_core_group_users": "Пользователи (Ядро)",
    "perm_core_group_roles": "Роли (Ядро)",
    "perm_core_group_modules_core": "Управление модулями (Ядро)", # Изменено для ясности
    "perm_core_group_system": "Система (Ядро)",
    "perm_core_group_settings_core": "Настройки Ядра",
    "perm_core_group_other": "Прочие (Ядро)",
    "back_to_perm_categories": "⬅️ К категориям разрешений",
    "back_to_core_perm_groups": "⬅️ К группам Ядра",
    "back_to_module_list_for_perms": "⬅️ К списку модулей (для прав)",
    "no_modules_with_perms": "Нет модулей с объявлениями прав",
    "no_permissions_in_group": "В этой группе нет разрешений",

    # Тексты для FSM (добавлены)
    "fsm_enter_role_name": "Введите имя новой роли:",
    "fsm_role_name_empty": "Имя роли не может быть пустым.",
    "fsm_role_name_taken": "Роль с именем \"{role_name}\" уже существует.",
    "fsm_enter_role_description": "Введите описание для роли {role_name}:",
    "fsm_command_skip_description": "/skip_description - Пропустить",
    "fsm_command_cancel_role_creation": "/cancel_role_creation - Отменить создание",
    "fsm_role_created_successfully": "Роль \"{role_name}\" успешно создана!",
    "fsm_role_creation_cancelled": "Создание роли отменено.",
    
    "fsm_edit_role_title": "Редактирование роли: {role_name}",
    "fsm_edit_role_name_not_allowed": "Имя стандартной роли {role_name} изменять нельзя.",
    "fsm_enter_new_role_description": "Введите новое описание для роли {role_name} (текущее: {current_description}):",
    "fsm_enter_new_role_name": "Введите новое имя для роли (текущее: {current_name}):",
    "fsm_command_skip_name": "/skip_name - Оставить как есть",
    "fsm_command_cancel_role_edit": "/cancel_role_edit - Отменить редактирование",
    "fsm_role_updated_successfully": "Роль \"{role_name}\" успешно обновлена!",
    "fsm_role_update_cancelled": "Редактирование роли отменено.",

    "delete_role_confirm_text": "Вы уверены, что хотите удалить роль {role_name}?\n{warning_if_users}\nЭто действие необратимо!",
    "role_is_standard_cant_delete": "Стандартную роль \"{role_name}\" удалять нельзя.",
    "role_delete_failed": "Не удалось удалить роль \"{role_name}\".",
    "role_deleted_successfully": "Роль \"{role_name}\" успешно удалена.",
}

def get_back_to_admin_main_menu_button(services_provider: Optional['BotServicesProvider'] = None, locale: Optional[str] = None) -> InlineKeyboardButton:
    """Создает кнопку возврата в главное меню админ-панели с переводами"""
    if services_provider:
        texts = get_admin_texts(services_provider, locale)
        text = texts["back_to_admin_menu_main"]
    else:
        text = ADMIN_COMMON_TEXTS["back_to_admin_menu_main"]
    return InlineKeyboardButton(
        text=text,
        callback_data=AdminMainMenuNavigate(target_section="main_admin").pack()
    )

def get_back_to_sdb_main_menu_button(services_provider: Optional['BotServicesProvider'] = None, locale: Optional[str] = None) -> InlineKeyboardButton:
    """Создает кнопку возврата в главное меню SDB с переводами"""
    if services_provider:
        texts = get_admin_texts(services_provider, locale)
        text = texts["back_to_main_menu_sdb"]
    else:
        text = ADMIN_COMMON_TEXTS["back_to_main_menu_sdb"]
    return InlineKeyboardButton(
        text=text,
        callback_data=CoreMenuNavigate(target_menu="main").pack()
    )

async def get_admin_main_menu_keyboard( 
    services: 'BotServicesProvider',
    user_tg_id: int,
    session: 'AsyncSession',
    locale: Optional[str] = None
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем язык пользователя из БД, если не передан
    if not locale:
        try:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == user_tg_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                locale = db_user.preferred_language_code
        except Exception:
            pass
        
        if not locale:
            locale = services.config.core.i18n.default_locale
    
    texts = get_admin_texts(services, locale) 

    rbac = services.rbac
    user_is_owner_from_config = user_tg_id in services.config.core.super_admins

    from Systems.core.rbac.service import (
        PERMISSION_CORE_USERS_VIEW_LIST,
        PERMISSION_CORE_MODULES_VIEW_LIST,
        PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC,
        PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL,
        PERMISSION_CORE_ROLES_VIEW
    )
    
    # БЛОК 1: УПРАВЛЕНИЕ СИСТЕМОЙ (приоритетные функции)
    system_buttons = []
    
    # Информация о системе
    if user_is_owner_from_config or \
       await rbac.user_has_permission(session, user_tg_id, PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC) or \
       await rbac.user_has_permission(session, user_tg_id, PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL):
        system_buttons.append((texts["system_info"], AdminMainMenuNavigate(target_section="sys_info")))

    # Управление модулями (важная функция)
    if user_is_owner_from_config or \
       await rbac.user_has_permission(session, user_tg_id, PERMISSION_CORE_MODULES_VIEW_LIST):
        system_buttons.append((texts["manage_modules"], AdminMainMenuNavigate(target_section="modules")))
    
    # БЛОК 2: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    user_management_buttons = []
    
    # Управление пользователями
    if user_is_owner_from_config or \
       await rbac.user_has_permission(session, user_tg_id, PERMISSION_CORE_USERS_VIEW_LIST):
        user_management_buttons.append((texts["manage_users"], AdminMainMenuNavigate(target_section="users")))
    
    # Управление ролями
    if user_is_owner_from_config or \
       await rbac.user_has_permission(session, user_tg_id, PERMISSION_CORE_ROLES_VIEW): 
        user_management_buttons.append((texts["manage_roles"], AdminMainMenuNavigate(target_section="roles")))

    # Добавляем кнопки группами для лучшей организации
    for text, callback_data in system_buttons:
        builder.button(text=text, callback_data=callback_data.pack())
    
    for text, callback_data in user_management_buttons:
        builder.button(text=text, callback_data=callback_data.pack())
    
    # Структура: системные функции сверху, пользовательские снизу, по одной в ряд для читаемости
    if builder.export(): 
        builder.adjust(1)

    # Кнопка возврата в главное меню всегда внизу
    builder.row(get_back_to_sdb_main_menu_button(services, locale)) 
    return builder.as_markup()