# core/module_loader/migrations.py
"""
Система миграций БД для модулей
"""

import importlib
from pathlib import Path
from typing import List, Optional, Dict
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from alembic import config as alembic_config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from Systems.core.module_loader import ModuleInfo


class ModuleMigrationManager:
    """
    Менеджер миграций для модулей
    """
    
    def __init__(self, services_provider: 'BotServicesProvider'):
        self.services = services_provider
        self._logger = logger.bind(service="ModuleMigrationManager")
        self._migration_paths: Dict[str, Path] = {}
    
    def register_module_migrations(self, module_name: str, migrations_path: Path):
        """Регистрирует путь к миграциям модуля"""
        if migrations_path.exists() and migrations_path.is_dir():
            self._migration_paths[module_name] = migrations_path
            self._logger.info(f"Зарегистрированы миграции для модуля {module_name}: {migrations_path}")
        else:
            self._logger.warning(f"Путь к миграциям не существует: {migrations_path}")
    
    async def run_module_migrations(
        self,
        module_name: str,
        target_revision: str = "head"
    ) -> bool:
        """
        Выполняет миграции для модуля
        
        Args:
            module_name: Имя модуля
            target_revision: Целевая ревизия (по умолчанию "head")
        
        Returns:
            True если миграции выполнены успешно
        """
        if module_name not in self._migration_paths:
            self._logger.warning(f"Миграции для модуля {module_name} не зарегистрированы")
            return False
        
        migrations_path = self._migration_paths[module_name]
        
        try:
            # Создаем временную конфигурацию Alembic для модуля
            module_alembic_cfg = alembic_config.Config()
            module_alembic_cfg.set_main_option("script_location", str(migrations_path))
            
            # Получаем URL БД из сервисов
            db_url = self.services.db.get_database_url()
            module_alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            
            # Выполняем миграции
            from alembic import command
            command.upgrade(module_alembic_cfg, target_revision)
            
            self._logger.success(f"Миграции модуля {module_name} выполнены до ревизии {target_revision}")
            return True
        
        except Exception as e:
            self._logger.error(f"Ошибка при выполнении миграций модуля {module_name}: {e}", exc_info=True)
            return False
    
    async def get_module_migration_status(self, module_name: str) -> Dict:
        """
        Получает статус миграций модуля
        
        Returns:
            Словарь с информацией о миграциях
        """
        if module_name not in self._migration_paths:
            return {
                "registered": False,
                "current_revision": None,
                "head_revision": None
            }
        
        try:
            migrations_path = self._migration_paths[module_name]
            script = ScriptDirectory.from_config(
                alembic_config.Config().set_main_option("script_location", str(migrations_path))
            )
            
            head_revision = script.get_current_head()
            
            # Получаем текущую ревизию из БД
            async with self.services.db.get_session() as session:
                context = MigrationContext.configure(await session.connection())
                current_revision = context.get_current_revision()
            
            return {
                "registered": True,
                "current_revision": current_revision,
                "head_revision": head_revision,
                "is_up_to_date": current_revision == head_revision
            }
        
        except Exception as e:
            self._logger.error(f"Ошибка при получении статуса миграций модуля {module_name}: {e}")
            return {
                "registered": True,
                "error": str(e)
            }
    
    async def run_all_module_migrations(self) -> Dict[str, bool]:
        """
        Выполняет миграции для всех зарегистрированных модулей
        
        Returns:
            Словарь {module_name: success}
        """
        results = {}
        for module_name in self._migration_paths.keys():
            results[module_name] = await self.run_module_migrations(module_name)
        return results

