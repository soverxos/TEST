# core/monitoring/health.py
"""
Health check endpoints для мониторинга
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider


class HealthStatus:
    """Статус здоровья компонента"""
    
    def __init__(self, name: str, status: str, message: str = "", details: Dict = None):
        self.name = name
        self.status = status  # "healthy", "degraded", "unhealthy"
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    """
    Проверка здоровья системы и компонентов
    """
    
    def __init__(self, services_provider: Optional['BotServicesProvider'] = None):
        self.services = services_provider
        self._logger = logger.bind(service="HealthChecker")
    
    async def check_database(self) -> HealthStatus:
        """Проверка состояния базы данных"""
        try:
            if not self.services or not hasattr(self.services, 'db'):
                return HealthStatus(
                    "database",
                    "unhealthy",
                    "DBManager не инициализирован"
                )
            
            start_time = datetime.now()
            async with self.services.db.get_session() as session:
                # Простой запрос для проверки соединения
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if duration > 1.0:
                return HealthStatus(
                    "database",
                    "degraded",
                    f"Медленный ответ БД: {duration:.2f}s",
                    {"response_time": duration}
                )
            
            return HealthStatus(
                "database",
                "healthy",
                "База данных доступна",
                {"response_time": duration}
            )
        
        except Exception as e:
            self._logger.error(f"Database health check failed: {e}")
            return HealthStatus(
                "database",
                "unhealthy",
                f"Ошибка подключения: {str(e)}"
            )
    
    async def check_cache(self) -> HealthStatus:
        """Проверка состояния кэша"""
        try:
            if not self.services or not hasattr(self.services, 'cache'):
                return HealthStatus(
                    "cache",
                    "unhealthy",
                    "CacheManager не инициализирован"
                )
            
            if not self.services.cache.is_available():
                return HealthStatus(
                    "cache",
                    "unhealthy",
                    "Кэш недоступен"
                )
            
            # Тест записи/чтения
            test_key = "__health_check__"
            test_value = "test"
            
            start_time = datetime.now()
            await self.services.cache.set(test_key, test_value, ttl=10)
            cached_value = await self.services.cache.get(test_key)
            await self.services.cache.delete(test_key)
            duration = (datetime.now() - start_time).total_seconds()
            
            if cached_value != test_value:
                return HealthStatus(
                    "cache",
                    "degraded",
                    "Кэш возвращает неверные данные"
                )
            
            return HealthStatus(
                "cache",
                "healthy",
                "Кэш работает корректно",
                {"response_time": duration}
            )
        
        except Exception as e:
            self._logger.error(f"Cache health check failed: {e}")
            return HealthStatus(
                "cache",
                "unhealthy",
                f"Ошибка кэша: {str(e)}"
            )
    
    async def check_telegram_api(self) -> HealthStatus:
        """Проверка доступности Telegram API"""
        try:
            if not self.services or not hasattr(self.services, 'bot'):
                return HealthStatus(
                    "telegram_api",
                    "unhealthy",
                    "Bot не инициализирован"
                )
            
            start_time = datetime.now()
            bot_info = await self.services.bot.get_me()
            duration = (datetime.now() - start_time).total_seconds()
            
            return HealthStatus(
                "telegram_api",
                "healthy",
                f"Telegram API доступен (@{bot_info.username})",
                {
                    "bot_id": bot_info.id,
                    "bot_username": bot_info.username,
                    "response_time": duration
                }
            )
        
        except Exception as e:
            self._logger.error(f"Telegram API health check failed: {e}")
            return HealthStatus(
                "telegram_api",
                "unhealthy",
                f"Ошибка Telegram API: {str(e)}"
            )
    
    async def check_modules(self) -> HealthStatus:
        """Проверка состояния модулей"""
        try:
            if not self.services or not hasattr(self.services, 'modules'):
                return HealthStatus(
                    "modules",
                    "unhealthy",
                    "ModuleLoader не инициализирован"
                )
            
            module_loader = self.services.modules
            all_modules = module_loader.get_all_modules_info()
            loaded_modules = [
                m for m in all_modules 
                if m.is_enabled and m.is_loaded_successfully
            ]
            failed_modules = [
                m for m in all_modules 
                if m.is_enabled and not m.is_loaded_successfully and m.error
            ]
            
            total = len(all_modules)
            loaded = len(loaded_modules)
            failed = len(failed_modules)
            
            if failed > 0:
                status = "degraded" if loaded > 0 else "unhealthy"
                message = f"{failed} модулей не загружены"
            else:
                status = "healthy"
                message = f"Все модули загружены ({loaded}/{total})"
            
            return HealthStatus(
                "modules",
                status,
                message,
                {
                    "total": total,
                    "loaded": loaded,
                    "failed": failed,
                    "failed_modules": [m.name for m in failed_modules]
                }
            )
        
        except Exception as e:
            self._logger.error(f"Modules health check failed: {e}")
            return HealthStatus(
                "modules",
                "unhealthy",
                f"Ошибка проверки модулей: {str(e)}"
            )
    
    async def check_all(self) -> Dict:
        """
        Выполняет все проверки здоровья
        
        Returns:
            Словарь с результатами всех проверок
        """
        check_tasks = [
            ("database", self.check_database()),
            ("cache", self.check_cache()),
            ("telegram_api", self.check_telegram_api()),
            ("modules", self.check_modules()),
        ]

        checks = await asyncio.gather(
            *(task for _, task in check_tasks),
            return_exceptions=True
        )

        results = {}
        overall_status = "healthy"

        for (component_name, _), check in zip(check_tasks, checks):
            if isinstance(check, Exception):
                self._logger.error(f"Health check exception for {component_name}: {check}")
                check = HealthStatus(
                    component_name,
                    "unhealthy",
                    f"Ошибка проверки {component_name}: {str(check)}",
                    {"error": str(check)}
                )

            if isinstance(check, HealthStatus):
                results[component_name] = check.to_dict()

                # Определяем общий статус
                if check.status == "unhealthy":
                    overall_status = "unhealthy"
                elif check.status == "degraded" and overall_status == "healthy":
                    overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": results
        }
    
    async def get_health_summary(self) -> Dict:
        """Краткая сводка о здоровье системы"""
        health_data = await self.check_all()
        
        return {
            "status": health_data["status"],
            "timestamp": health_data["timestamp"],
            "checks_count": len(health_data["checks"]),
            "healthy_count": sum(
                1 for c in health_data["checks"].values() 
                if c["status"] == "healthy"
            ),
            "degraded_count": sum(
                1 for c in health_data["checks"].values() 
                if c["status"] == "degraded"
            ),
            "unhealthy_count": sum(
                1 for c in health_data["checks"].values() 
                if c["status"] == "unhealthy"
            )
        }

