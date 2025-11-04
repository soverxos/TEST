# core/admin/filters_admin.py

from aiogram import types
from loguru import logger

# Используем основное разрешение для доступа к админ-панели
from Systems.core.rbac.service import PERMISSION_CORE_VIEW_ADMIN_PANEL 

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider

MODULE_NAME_FOR_LOG = "AdminFilters"

async def can_view_admin_panel_filter(event: types.TelegramObject, services_provider: 'BotServicesProvider') -> bool:
    """
    Проверяет, имеет ли пользователь доступ к основным разделам админ-панели.
    Доступ разрешен, если:
    1. Пользователь находится в списке super_admins из конфигурации.
    2. Пользователь имеет разрешение PERMISSION_CORE_VIEW_ADMIN_PANEL.
    """
    user = getattr(event, 'from_user', None) 
    if not user: 
        logger.trace(f"[{MODULE_NAME_FOR_LOG}] Событие без 'from_user', доступ к админ-панели не релевантен или запрещен.")
        return False

    user_id = user.id
    user_mention = f"@{user.username}" if user.username else f"ID:{user.id}"

    if user_id in services_provider.config.core.super_admins:
        logger.trace(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} имеет доступ к админ-панели (super_admin из config).")
        return True
    try:
        async with services_provider.db.get_session() as session:
            has_permission = await services_provider.rbac.user_has_permission(
                session, user_id, PERMISSION_CORE_VIEW_ADMIN_PANEL
            )
            if has_permission:
                logger.trace(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} имеет разрешение '{PERMISSION_CORE_VIEW_ADMIN_PANEL}' (доступ разрешен).")
                return True
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка проверки разрешения '{PERMISSION_CORE_VIEW_ADMIN_PANEL}' для {user_mention} в БД: {e}", exc_info=True)
        return False 
    
    logger.warning(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} "
                   f"попытался получить доступ к админ-панели без разрешения '{PERMISSION_CORE_VIEW_ADMIN_PANEL}'.")
    return False
