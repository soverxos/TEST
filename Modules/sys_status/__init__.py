# Точка входа для модуля sys_status

from aiogram import Dispatcher, Bot, Router
from loguru import logger

# Импортируем нужные компоненты из нашего модуля
from .handlers import sys_status_router
from .permissions import MODULE_NAME, PERM_VIEW_SYS_STATUS

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.services_provider import BotServicesProvider
    from core.module_loader import ModuleInfo

async def setup_module(dp: Dispatcher, bot: Bot, services: 'BotServicesProvider'):
    """
    Обязательная функция для инициализации модуля ядром SDB.
    """
    module_info = services.modules.get_module_info(MODULE_NAME)
    
    if not module_info or not module_info.manifest:
        logger.error(f"Не удалось получить манифест для модуля '{MODULE_NAME}'. Модуль не будет настроен.")
        return

    display_name = module_info.manifest.display_name
    version = module_info.manifest.version
    logger.info(f"[{MODULE_NAME}] Настройка модуля: '{display_name}' v{version}...")

    # 1. Регистрация хэндлеров
    dp.include_router(sys_status_router)
    logger.info(f"[{MODULE_NAME}] Роутер '{sys_status_router.name}' успешно зарегистрирован.")

    # 2. Регистрация UI-точки входа в ядре
    from core.ui.callback_data_factories import ModuleMenuEntry 

    entry_cb_data = ModuleMenuEntry(module_name=MODULE_NAME).pack()
    icon = "📊" # Можно взять из манифеста
    description = module_info.manifest.description

    services.ui_registry.register_module_entry(
        module_name=MODULE_NAME, 
        display_name=display_name,
        entry_callback_data=entry_cb_data, 
        icon=icon,
        description=description,
        # Указываем, что кнопку в меню "Модули" увидят только те, у кого есть это право
        required_permission_to_view=PERM_VIEW_SYS_STATUS 
    )
    logger.info(f"[{MODULE_NAME}] UI-точка входа для модуля '{display_name}' зарегистрирована.")

    logger.success(f"✅ Модуль '{MODULE_NAME}' ({display_name}) успешно настроен.")