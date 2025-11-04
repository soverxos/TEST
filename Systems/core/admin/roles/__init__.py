# core/admin/roles/__init__.py
from aiogram import Router

# Импортируем "конечные" роутеры из этого раздела
from .handlers_list import roles_list_router
from .handlers_details import role_details_router
from .handlers_role_perms import role_permissions_router
from .handlers_crud_fsm import role_crud_fsm_router

# Создаем один "собирающий" роутер для всего раздела "roles"
section_roles_router = Router(name="sdb_admin_section_roles_router")

section_roles_router.include_router(roles_list_router)
section_roles_router.include_router(role_details_router)
section_roles_router.include_router(role_permissions_router)
section_roles_router.include_router(role_crud_fsm_router)

# Экспортируем только собирающий роутер с правильным именем
__all__ = ["section_roles_router"]