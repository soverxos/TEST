# SwiftDevBot/core/admin/users/__init__.py
from aiogram import Router
from loguru import logger

# --- ИСПРАВЛЕННЫЙ ИМПОРТ ---
# Импортируем фильтр из директории core/admin/, а не core/admin/users/
from ..filters_admin import can_view_admin_panel_filter # Используем .. для подъема на уровень выше

# Импортируем "конечные" роутеры из этого раздела
from .handlers_list import users_list_router
from .handlers_details import user_details_router
from .handlers_roles_assign import user_roles_assign_router
from .handlers_direct_perms import user_direct_perms_router

# Создаем один "собирающий" роутер для всего раздела "users"
section_users_router = Router(name="sdb_admin_section_users_router")

# Можно применить фильтр здесь, если он должен действовать на весь раздел users
# section_users_router.message.filter(can_view_admin_panel_filter)
# section_users_router.callback_query.filter(can_view_admin_panel_filter)
# Однако, если он уже применен к главному admin_router, это может быть избыточно,
# но не вредно. Лучше применять специфичные для раздела права здесь, если они есть.

section_users_router.include_router(users_list_router)
section_users_router.include_router(user_details_router)
section_users_router.include_router(user_roles_assign_router)
section_users_router.include_router(user_direct_perms_router)

__all__ = ["section_users_router"]