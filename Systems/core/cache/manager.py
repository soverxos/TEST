# core/cache/manager.py

import asyncio
import json
import time
from typing import Optional, Any, Union, TYPE_CHECKING
from abc import ABC, abstractmethod

# Условные импорты для Redis с правильной типизацией
# Условные импорты для Redis с правильной типизацией
try:
    import redis.asyncio as redis_async
    REDIS_PY_AVAILABLE = True
except ImportError:
    redis_async = None # type: ignore
    REDIS_PY_AVAILABLE = False

if TYPE_CHECKING:
    from redis.asyncio.client import Redis as AsyncRedisClient
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
else:
    if REDIS_PY_AVAILABLE:
        from redis.asyncio.client import Redis as AsyncRedisClient
        from redis.exceptions import RedisError, ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
    else:
        AsyncRedisClient = Any # type: ignore
        RedisError = Exception # type: ignore
        RedisConnectionError = Exception # type: ignore
        RedisTimeoutError = asyncio.TimeoutError # Фоллбэк на asyncio.TimeoutError

# Условные импорты для cachetools
try:
    from cachetools import TTLCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    TTLCache = dict # type: ignore
    CACHETOOLS_AVAILABLE = False

from loguru import logger

if TYPE_CHECKING:
    from Systems.core.app_settings import CacheSettings

class BaseCache(ABC):
    @abstractmethod
    async def initialize(self) -> None: pass
    @abstractmethod
    async def dispose(self) -> None: pass
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: raise NotImplementedError
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None: raise NotImplementedError
    @abstractmethod
    async def delete(self, key: str) -> bool: raise NotImplementedError
    @abstractmethod
    async def exists(self, key: str) -> bool: raise NotImplementedError
    @abstractmethod
    async def clear(self) -> None: raise NotImplementedError

class MemoryCache(BaseCache):
    def __init__(self, maxsize: int = 1024, default_ttl: int = 300):
        self._default_ttl = default_ttl
        if CACHETOOLS_AVAILABLE and TTLCache:
            self._cache: Union[Any, dict] = TTLCache(maxsize=maxsize, ttl=default_ttl)  # type: ignore
            self._uses_cachetools = True
        else:
            logger.warning("Библиотека 'cachetools' не найдена. Используется простая ручная реализация MemoryCache с TTL.")
            self._cache = {} 
            self._maxsize = maxsize
            self._uses_cachetools = False
        logger.info(f"MemoryCache инициализирован (использует cachetools: {self._uses_cachetools}, default TTL: {default_ttl}s).")

    async def initialize(self) -> None: logger.debug("MemoryCache.initialize() - операция не требуется.")
    async def dispose(self) -> None: await self.clear(); logger.debug("MemoryCache.dispose() - кэш очищен.")

    async def get(self, key: str) -> Optional[Any]:
        if self._uses_cachetools and isinstance(self._cache, TTLCache):
            try: return self._cache[key]
            except KeyError: return None
        elif isinstance(self._cache, dict):
            item = self._cache.get(key)
            if item:
                value, expiry_timestamp = item
                if time.time() < expiry_timestamp: return value
                else: 
                    # Явно удаляем просроченный ключ
                    await self.delete(key) 
            return None
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        effective_ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        if self._uses_cachetools and isinstance(self._cache, TTLCache):
            if ttl_seconds is not None and ttl_seconds != self._cache.ttl: # type: ignore
                 # TTLCache имеет общий TTL, но можно хранить время истечения отдельно, если очень нужно.
                 # Пока оставляем как есть - используем общий TTL.
                 logger.trace(f"MemoryCache (TTLCache) использует общий TTL ({self._cache.ttl} сек) для всех ключей.") # type: ignore
            self._cache[key] = value
        elif isinstance(self._cache, dict):
            if len(self._cache) >= self._maxsize and key not in self._cache:
                # Простая LRU-подобная логика: удаляем самый старый (первый добавленный)
                # Это не настоящий LRU, но для простой реализации сойдет.
                try:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    logger.trace(f"MemoryCache достиг maxsize, удален ключ (FIFO-like): {oldest_key}")
                except StopIteration: pass # Пустой словарь
            self._cache[key] = (value, time.time() + effective_ttl)

    async def delete(self, key: str) -> bool:
        if key in self._cache: 
            del self._cache[key]
            return True
        return False

    async def exists(self, key: str) -> bool: 
        # Для TTLCache проверка на существование автоматически учитывает TTL
        # Для ручной реализации get() также проверяет TTL
        return await self.get(key) is not None

    async def clear(self) -> None: 
        self._cache.clear()
        logger.info("MemoryCache очищен.")


class RedisCache(BaseCache):
    def __init__(self, redis_url: str):
        if not REDIS_PY_AVAILABLE:
            msg = "Библиотека 'redis' (с поддержкой asyncio) не установлена. `pip install redis`. RedisCache не будет работать."
            logger.critical(msg)
            raise ImportError(msg)
        self.redis_url = redis_url
        self._redis_client: Optional[Any] = None  # type: ignore
        logger.info(f"RedisCache инициализирован для URL: {self.redis_url} (используя redis.asyncio)")

    async def initialize(self) -> None:
        logger.debug(f"RedisCache: Попытка инициализации для URL: {self.redis_url}")
        if not redis_async:
            logger.critical("RedisCache.initialize: redis.asyncio не импортирован!")
            raise ImportError("redis.asyncio не доступен")

        try:
            logger.debug(f"RedisCache: Вызов redis.asyncio.from_url('{self.redis_url}')")
            self._redis_client = redis_async.from_url(  # type: ignore
                self.redis_url, 
                decode_responses=False, # Важно для pickle
                socket_timeout=5,
                socket_connect_timeout=5,
                # health_check_interval=30 # Опционально
            )
            logger.debug(f"RedisCache: redis.asyncio.from_url выполнен. Клиент: {type(self._redis_client)}")
            
            if self._redis_client:
                logger.debug("RedisCache: Попытка PING...")
                await self._redis_client.ping()
                logger.success(f"Успешное подключение и PING к Redis: {self.redis_url}")
            else:
                # Эта ветка маловероятна, так как from_url обычно либо падает, либо возвращает клиент
                logger.error(f"RedisCache: redis.asyncio.from_url вернул None для {self.redis_url}")
                self._redis_client = None 
                raise RedisConnectionError("Не удалось создать клиент Redis (from_url вернул None)")

        except (asyncio.TimeoutError, RedisTimeoutError) as te: 
            logger.error(f"RedisCache: Таймаут при подключении/пинге к Redis ({self.redis_url}): {te}", exc_info=False) # exc_info=False т.к. таймаут - это ожидаемое
            self._redis_client = None
            raise
        except RedisConnectionError as ce: 
            logger.error(f"RedisCache: Ошибка соединения Redis ({self.redis_url}): {ce}", exc_info=True)
            self._redis_client = None
            raise
        except RedisError as re: 
            logger.error(f"RedisCache: Общая ошибка Redis при подключении/пинге ({self.redis_url}): {re}", exc_info=True)
            self._redis_client = None
            raise
        except Exception as e: 
            logger.error(f"RedisCache: Непредвиденная ошибка при инициализации Redis ({self.redis_url}): {type(e).__name__} - {e}", exc_info=True)
            self._redis_client = None
            raise

    async def dispose(self) -> None:
        if self._redis_client:
            logger.info(f"RedisCache: Закрытие соединения с Redis ({self.redis_url})...")
            try:
                await self._redis_client.close()
                # Для redis-py 4.2+ можно также закрыть пул соединений, если он не общий
                # и если это необходимо (обычно close() клиента достаточно)
                if hasattr(self._redis_client, 'connection_pool') and hasattr(self._redis_client.connection_pool, 'disconnect'):
                     await self._redis_client.connection_pool.disconnect()
                logger.info(f"Соединение с Redis ({self.redis_url}) успешно закрыто.")
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединения с Redis ({self.redis_url}): {e}", exc_info=True)
            finally:
                self._redis_client = None

    async def get(self, key: str) -> Optional[Any]:
        if not self._redis_client: return None
        try:
            json_value = await self._redis_client.get(key)
            if json_value: 
                # Безопасная десериализация через JSON вместо pickle
                return json.loads(json_value.decode('utf-8'))
            return None
        except RedisError as e: logger.error(f"RedisCache: Ошибка Redis при GET для ключа '{key}': {e}"); return None
        except (json.JSONDecodeError, UnicodeDecodeError) as e: logger.error(f"RedisCache: Ошибка десериализации для ключа '{key}': {e}"); return None
        except Exception as e_unexp: logger.error(f"RedisCache: Неожиданная ошибка GET для ключа '{key}': {e_unexp}"); return None


    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if not self._redis_client: return
        try:
            # Безопасная сериализация через JSON вместо pickle
            json_value = json.dumps(value, ensure_ascii=False, default=str)
            await self._redis_client.set(key, json_value, ex=ttl_seconds)
        except (TypeError, ValueError) as e: logger.error(f"RedisCache: Ошибка сериализации для ключа '{key}': {e}")
        except RedisError as e_redis: logger.error(f"RedisCache: Ошибка Redis при SET для ключа '{key}': {e_redis}")
        except Exception as e_unexp: logger.error(f"RedisCache: Неожиданная ошибка SET для ключа '{key}': {e_unexp}")


    async def delete(self, key: str) -> bool:
        if not self._redis_client: return False
        try: 
            deleted_count = await self._redis_client.delete(key)
            return deleted_count > 0
        except RedisError as e: logger.error(f"RedisCache: Ошибка Redis при DELETE для ключа '{key}': {e}"); return False
        except Exception as e_unexp: logger.error(f"RedisCache: Неожиданная ошибка DELETE для ключа '{key}': {e_unexp}"); return False


    async def exists(self, key: str) -> bool:
        if not self._redis_client: return False
        try: 
            exists_count = await self._redis_client.exists(key)
            return exists_count > 0
        except RedisError as e: logger.error(f"RedisCache: Ошибка Redis при EXISTS для ключа '{key}': {e}"); return False
        except Exception as e_unexp: logger.error(f"RedisCache: Неожиданная ошибка EXISTS для ключа '{key}': {e_unexp}"); return False


    async def clear(self) -> None:
        if not self._redis_client: return
        try:
            logger.warning(f"RedisCache: Выполняется команда FLUSHDB для Redis ({self.redis_url})!")
            await self._redis_client.flushdb()
            logger.info(f"RedisCache: FLUSHDB для Redis ({self.redis_url}) выполнен.")
        except RedisError as e: logger.error(f"RedisCache: Ошибка Redis при FLUSHDB: {e}")
        except Exception as e_unexp: logger.error(f"RedisCache: Неожиданная ошибка FLUSHDB: {e_unexp}")


    def get_client_instance(self) -> Optional[Any]:  # type: ignore
        return self._redis_client


class CacheManager:
    def __init__(self, cache_settings: 'CacheSettings'):
        self._settings = cache_settings
        self._cache_backend: Optional[BaseCache] = None
        self._is_initialized_successfully = False
        logger.info(f"CacheManager инициализирован. Сконфигурированный тип кэша: {self._settings.type}")

    async def initialize(self) -> None:
        if self._is_initialized_successfully:
            logger.debug(f"CacheManager (бэкенд: {self._settings.type}) уже был успешно инициализирован.")
            return
        self._is_initialized_successfully = False # Сбрасываем флаг перед новой попыткой

        if self._settings.type == "redis":
            if not self._settings.redis_url:
                logger.error("Тип кэша 'redis', но redis_url не указан в настройках. Кэш не будет инициализирован.")
                return
            if not REDIS_PY_AVAILABLE:
                logger.critical("Библиотека 'redis' (для asyncio) не установлена, но выбран тип кэша 'redis'. Кэш не будет работать.")
                return
            try:
                self._cache_backend = RedisCache(redis_url=str(self._settings.redis_url))
            except ImportError as e_imp_redis: 
                logger.critical(f"CacheManager: Не удалось создать RedisCache (ImportError): {e_imp_redis}")
                return 
        elif self._settings.type == "memory":
            self._cache_backend = MemoryCache() 
        else:
            logger.warning(f"Неизвестный тип кэша: '{self._settings.type}'. Кэш не будет доступен.")
            return

        if self._cache_backend:
            try:
                await self._cache_backend.initialize()
                # Дополнительная проверка для Redis, что клиент действительно создался
                if isinstance(self._cache_backend, RedisCache) and self._cache_backend.get_client_instance() is None:
                    logger.error(f"CacheManager: RedisCache.initialize() завершился, но клиент Redis остался None. Инициализация не удалась.")
                    self._cache_backend = None # Сбрасываем, чтобы is_available() вернул False
                else:
                    self._is_initialized_successfully = True
                    logger.success(f"Бэкенд кэша '{self._settings.type}' успешно инициализирован.")
            except Exception as e_init_backend: 
                logger.error(f"Ошибка инициализации бэкенда кэша '{self._settings.type}': {type(e_init_backend).__name__} - {e_init_backend}", exc_info=False)
                self._cache_backend = None 
    
    async def dispose(self) -> None:
        if self._cache_backend: 
            try: await self._cache_backend.dispose()
            except Exception as e: logger.error(f"Ошибка при освобождении ресурсов кэша '{self._settings.type}': {e}", exc_info=True)
        self._is_initialized_successfully = False 
        self._cache_backend = None 
        logger.info(f"Ресурсы CacheManager для бэкенда '{self._settings.type}' освобождены (или попытка освобождения).")


    def is_available(self) -> bool:
        return self._cache_backend is not None and self._is_initialized_successfully

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if not self.is_available() or self._cache_backend is None:
            logger.trace(f"Кэш недоступен. get('{key}') вернет default ({default}).")
            return default
        return await self._cache_backend.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if not self.is_available() or self._cache_backend is None:
            logger.trace(f"Кэш недоступен. set('{key}', ...) не будет выполнено.")
            return
        await self._cache_backend.set(key, value, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> bool:
        if not self.is_available() or self._cache_backend is None:
            logger.trace(f"Кэш недоступен. delete('{key}') вернет False.")
            return False
        return await self._cache_backend.delete(key)

    async def exists(self, key: str) -> bool:
        if not self.is_available() or self._cache_backend is None:
            logger.trace(f"Кэш недоступен. exists('{key}') вернет False.")
            return False
        return await self._cache_backend.exists(key)

    async def clear_all_cache(self) -> None:
        if not self.is_available() or self._cache_backend is None:
            logger.trace(f"Кэш недоступен. clear_all_cache() не будет выполнено.")
            return
        logger.warning(f"Запрошена полная очистка кэша для бэкенда '{self._settings.type}'.")
        await self._cache_backend.clear()

    async def get_redis_client_instance(self) -> Optional[Any]:  # type: ignore
        if self.is_available() and isinstance(self._cache_backend, RedisCache):
            return self._cache_backend.get_client_instance()
        logger.debug("Запрошен экземпляр Redis клиента, но RedisCache не используется или не инициализирован.")
        return None