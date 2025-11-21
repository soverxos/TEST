"""
Универсальный шаблон модуля для SwiftDevBot

Этот модуль демонстрирует все возможности системы модулей SDB:
- Обработка команд и сообщений
- FSM (Finite State Machine) диалоги
- Работа с разрешениями и RBAC
- Интеграция с базой данных
- Система настроек модуля
- UI компоненты (клавиатуры, callback data)
- Аудит и логирование
- Обработка ошибок

Используйте этот шаблон как основу для создания собственных модулей.
"""

from aiogram import Dispatcher, Bot
from loguru import logger
from typing import TYPE_CHECKING

# Импорты компонентов модуля
from .handlers import template_router
from .permissions import MODULE_NAME, PERMISSIONS
from .services import TemplateService

if TYPE_CHECKING:
    from core.services_provider import BotServicesProvider

async def setup_module(dp: Dispatcher, bot: Bot, services: 'BotServicesProvider'):
    """
    Обязательная функция для инициализации модуля ядром SDB.
    
    Эта функция вызывается автоматически при загрузке модуля.
    Здесь происходит:
    - Регистрация обработчиков
    - Инициализация сервисов
    - Регистрация UI компонентов
    - Проверка настроек
    
    Args:
        dp: Dispatcher aiogram для регистрации обработчиков
        bot: Bot instance для работы с Telegram API
        services: Провайдер сервисов SDB (БД, кэш, RBAC и т.д.)
    """
    # Получаем информацию о модуле
    module_info = services.modules.get_module_info(MODULE_NAME)
    
    if not module_info or not module_info.manifest:
        logger.error(f"Не удалось получить манифест для модуля '{MODULE_NAME}'. Модуль не будет настроен.")
        return

    # Получаем настройки модуля
    settings = services.modules.get_module_settings(MODULE_NAME) or {}
    
    # Проверяем, включен ли модуль
    if not settings.get('enabled', True):
        logger.info(f"Модуль '{MODULE_NAME}' отключен в настройках")
        return

    display_name = module_info.manifest.display_name
    version = module_info.manifest.version
    logger.info(f"[{MODULE_NAME}] Настройка модуля: '{display_name}' v{version}...")

    # 1. Инициализируем сервисы модуля
    template_service = TemplateService(services, settings)
    logger.info(f"[{MODULE_NAME}] Сервисы модуля инициализированы")

    # 2. Регистрируем обработчики команд и сообщений
    dp.include_router(template_router)
    logger.info(f"[{MODULE_NAME}] Роутер '{template_router.name}' успешно зарегистрирован")

    # 3. Регистрируем UI точку входа в главном меню
    from core.ui.callback_data_factories import ModuleMenuEntry 
    
    entry_cb_data = ModuleMenuEntry(module_name=MODULE_NAME).pack()
    icon = "🔧"  # Можно взять из манифеста
    description = module_info.manifest.description

    services.ui_registry.register_module_entry(
        module_name=MODULE_NAME, 
        display_name=display_name,
        entry_callback_data=entry_cb_data, 
        icon=icon,
        description=description,
        # Указываем, что кнопку в меню "Модули" увидят только те, у кого есть это право
        required_permission_to_view=PERMISSIONS.ACCESS 
    )
    logger.info(f"[{MODULE_NAME}] UI-точка входа для модуля '{display_name}' зарегистрирована")

    # 4. Создаем таблицы БД для модуля (если есть модели)
    if module_info.manifest.model_definitions:
        try:
            # Импортируем модели для регистрации в SQLAlchemy
            from . import models  # noqa: F401
            
            # Создаем таблицы
            await services.db.create_specific_module_tables([
                models.TemplateModel,
                models.UserData
            ])
            logger.info(f"[{MODULE_NAME}] Таблицы БД созданы/обновлены")
        except Exception as e:
            logger.error(f"[{MODULE_NAME}] Ошибка создания таблиц БД: {e}")

    # 5. Логируем успешную инициализацию в аудит
    if hasattr(services, 'audit_logger'):
        from core.security.audit_logger import AuditEventType
        services.audit_logger.log_event(
            event_type=AuditEventType.MODULE_LOAD,
            module_name=MODULE_NAME,
            details={
                "version": version,
                "display_name": display_name,
                "settings": settings
            }
        )

    logger.success(f"✅ Модуль '{MODULE_NAME}' ({display_name}) успешно настроен и готов к работе!")
