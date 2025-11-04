# SwiftDevBot/core/ui/callback_data_factories.py
from typing import Optional, Literal, Union 
from aiogram.filters.callback_data import CallbackData

CORE_CALLBACK_PREFIX = "sdb_core"
ADMIN_CALLBACK_PREFIX = "sdb_admin" 

# --- Фабрики для навигации ядра ---
class CoreMenuNavigate(CallbackData, prefix=f"{CORE_CALLBACK_PREFIX}_nav"):
    target_menu: str 
    page: Optional[int] = None
    action: Optional[str] = None 
    # Добавим параметр для передачи данных, например, кода языка
    payload: Optional[str] = None 

class ModuleMenuEntry(CallbackData, prefix=f"{CORE_CALLBACK_PREFIX}_module_entry"):
    module_name: str

class CoreServiceAction(CallbackData, prefix=f"{CORE_CALLBACK_PREFIX}_service"):
    action: Literal[
        "delete_this_message", 
        "close_menu_silently",
        "confirm_registration", 
        "cancel_registration",
    ]

# --- Фабрики для Админ-панели ---
# ... (без изменений) ...
ADMIN_MAIN_MENU_PREFIX = "sdb_admin_main"
class AdminMainMenuNavigate(CallbackData, prefix=ADMIN_MAIN_MENU_PREFIX):
    target_section: str 

ADMIN_USERS_PREFIX = "sdb_admin_users"
class AdminUsersPanelNavigate(CallbackData, prefix=ADMIN_USERS_PREFIX):
    action: str 
    item_id: Optional[int] = None       
    page: Optional[int] = None          
    role_id: Optional[int] = None       
    permission_id: Optional[int] = None 
    
    category_key: Optional[str] = None 
    entity_name: Optional[str] = None  


ADMIN_ROLES_PREFIX = "sdb_admin_roles"
class AdminRolesPanelNavigate(CallbackData, prefix=ADMIN_ROLES_PREFIX):
    action: str 
    item_id: Optional[int] = None       
    permission_id: Optional[int] = None 
    category_key: Optional[str] = None  
    entity_name: Optional[str] = None   
    page: Optional[int] = None          

ADMIN_SYSINFO_PREFIX = "sdb_admin_sysinfo"
class AdminSysInfoPanelNavigate(CallbackData, prefix=ADMIN_SYSINFO_PREFIX):
    action: str 

ADMIN_MODULES_PREFIX = "sdb_admin_modules"
class AdminModulesPanelNavigate(CallbackData, prefix=ADMIN_MODULES_PREFIX):
    action: str 
    item_id: Optional[str] = None 
    page: Optional[int] = None

ADMIN_LOGS_PREFIX = "sdb_admin_logs"
class AdminLogsPanelNavigate(CallbackData, prefix=ADMIN_LOGS_PREFIX):
    action: str 
    item_id: Optional[str] = None 
    page: Optional[int] = None

# Новый callback data для просмотра логов
ADMIN_LOGS_VIEWER_PREFIX = "sdb_admin_logs_viewer"
class AdminLogsViewerNavigate(CallbackData, prefix=ADMIN_LOGS_VIEWER_PREFIX):
    action: str 
    payload: Optional[str] = None  # Для передачи имени файла

class AdminPanelNavigate(CallbackData, prefix=ADMIN_CALLBACK_PREFIX): 
    section: str 
    action: Optional[str] = None
    item_id: Optional[Union[int, str]] = None 
    page: Optional[int] = None
    role_id: Optional[int] = None 
    permission_name: Optional[str] = None