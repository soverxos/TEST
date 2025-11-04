# core/admin/__init__.py
from aiogram import Router
from loguru import logger

# Импортируем "собирающие" роутеры из каждого раздела
try:
    from .entry import section_entry_router # Импортируем собирающий роутер раздела
    logger.info("Admin submodule 'entry' (section router) loaded.")
except ImportError as e:
    section_entry_router = Router(name="sdb_admin_entry_stub_main") 
    logger.error(f"Failed to load admin submodule 'entry' (section router): {e}")

try:
    from .users import section_users_router # Импортируем собирающий роутер раздела
    logger.info("Admin submodule 'users' (section router) loaded.")
except ImportError as e:
    section_users_router = Router(name="sdb_admin_users_stub_main")
    logger.error(f"Failed to load admin submodule 'users' (section router): {e}")

try:
    from .roles import section_roles_router # Импортируем собирающий роутер раздела
    logger.info("Admin submodule 'roles' (section router) loaded.")
except ImportError as e:
    section_roles_router = Router(name="sdb_admin_roles_stub_main")
    logger.error(f"Failed to load admin submodule 'roles' (section router): {e}")

try:
    from .sys_info import section_sys_info_router # Импортируем собирающий роутер раздела
    logger.info("Admin submodule 'sys_info' (section router) loaded.")
except ImportError as e:
    section_sys_info_router = Router(name="sdb_admin_sys_info_stub_main")
    logger.error(f"Failed to load admin submodule 'sys_info' (section router): {e}")

try:
    from .modules_mgmt import section_modules_mgmt_router # Импортируем собирающий роутер раздела
    logger.info("Admin submodule 'modules_mgmt' (section router) loaded.")
except ImportError as e:
    section_modules_mgmt_router = Router(name="sdb_admin_modules_mgmt_stub_main")
    logger.error(f"Failed to load admin submodule 'modules_mgmt' (section router): {e}")

try:
    from .logs_viewer import section_logs_viewer_router # Импортируем собирающий роутер раздела
    logger.info("Admin submodule 'logs_viewer' (section router) loaded.")
except ImportError as e:
    section_logs_viewer_router = Router(name="sdb_admin_logs_viewer_stub_main")
    logger.error(f"Failed to load admin submodule 'logs_viewer' (section router): {e}")


# Главный роутер админ-панели
admin_router = Router(name="sdb_admin_top_level_router") # Даем ему уникальное имя

admin_router.include_router(section_entry_router)
admin_router.include_router(section_users_router)
admin_router.include_router(section_roles_router)
admin_router.include_router(section_sys_info_router)
admin_router.include_router(section_modules_mgmt_router)
admin_router.include_router(section_logs_viewer_router)

logger.success("Main admin_router composed from section routers.")

__all__ = ["admin_router"]