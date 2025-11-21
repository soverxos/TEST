from __future__ import annotations

from typing import Union, TYPE_CHECKING

from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

if TYPE_CHECKING:
    from aiogram.fsm.storage.redis import RedisStorage
    from Systems.core.cache.manager import CacheManager
    from Systems.core.app_settings import CacheSettings


async def build_fsm_storage(
    cache_manager: 'CacheManager',
    cache_settings: 'CacheSettings'
) -> Union[MemoryStorage, 'RedisStorage']:
    """
    Фабрика for FSM storage. Пытается использовать RedisStorage, если кеш
    настроен как redis и Redis клиент доступен; иначе — MemoryStorage.
    """
    _logger = logger.bind(service="FSMStorageFactory")

    storage: Union[MemoryStorage, 'RedisStorage']
    if cache_settings.type == "redis":
        _logger.debug("Попытка использовать RedisStorage для FSM.")
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            if not cache_manager.is_available():
                _logger.warning(
                    "CacheManager помечен как недоступный — используем MemoryStorage."
                )
            else:
                redis_client = await cache_manager.get_redis_client_instance()
                if redis_client:
                    storage = RedisStorage(redis=redis_client)
                    _logger.info("FSM Storage: используется RedisStorage.")
                    return storage
                _logger.warning(
                    "Redis клиент недоступен, несмотря на настройку redis CacheManager."
                )
        except ImportError:
            _logger.warning(
                "RedisStorage недоступен, не установлен пакет redis → используем MemoryStorage."
            )
        except Exception as exc:
            _logger.warning(
                f"Не удалось создать RedisStorage (redis_cache): {exc}. Используем MemoryStorage."
            )

    storage = MemoryStorage()
    _logger.info("FSM Storage: используется MemoryStorage.")
    return storage

