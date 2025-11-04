# core/admin/logs_viewer/__init__.py
from aiogram import Router

from .handlers_logs import logs_viewer_router 

section_logs_viewer_router = Router(name="sdb_admin_section_logs_viewer_router")
section_logs_viewer_router.include_router(logs_viewer_router)

__all__ = ["section_logs_viewer_router"]