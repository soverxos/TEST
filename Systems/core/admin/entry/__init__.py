# core/admin/entry/__init__.py
from aiogram import Router

# Импортируем "конечный" роутер
from .handlers_entry import admin_entry_router

# Создаем "собирающий" роутер для раздела
section_entry_router = Router(name="sdb_admin_section_entry_router")
section_entry_router.include_router(admin_entry_router)

__all__ = ["section_entry_router"]