# core/admin/sys_info/__init__.py
from aiogram import Router

# Импортируем "конечный" роутер
from .handlers_sys_info import sys_info_router

# Создаем "собирающий" роутер для раздела (хотя здесь он включает только один)
section_sys_info_router = Router(name="sdb_admin_section_sys_info_router")
section_sys_info_router.include_router(sys_info_router)

__all__ = ["section_sys_info_router"]