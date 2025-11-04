# core/admin/modules_mgmt/__init__.py
from aiogram import Router

from .handlers_modules import modules_mgmt_router # Роутер из handlers_modules.py

section_modules_mgmt_router = Router(name="sdb_admin_section_modules_mgmt_router")
section_modules_mgmt_router.include_router(modules_mgmt_router)

__all__ = ["section_modules_mgmt_router"]