# core/cache/strategies.py
"""
Стратегии кэширования и инвалидация кэша
"""

import asyncio
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider


class CacheStrategy:
    """Базовый класс для стратегий кэширования"""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._logger = logger.bind(service="CacheStrategy")
    
    def get_key(self, prefix: str, *args, **kwargs) -> str:
        """Генерирует ключ кэша"""
        parts = [prefix]
        if args:
            parts.extend(str(arg) for arg in args)
        if kwargs:
            parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(parts)
    
    async def get_or_set(
        self,
        cache_manager,
        key: str,
        func: Callable,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Получить из кэша или выполнить функцию и сохранить"""
        raise NotImplementedError


class DefaultCacheStrategy(CacheStrategy):
    """Стандартная стратегия кэширования"""
    
    async def get_or_set(
        self,
        cache_manager,
        key: str,
        func: Callable,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Получить из кэша или выполнить функцию"""
        # Пытаемся получить из кэша
        cached_value = await cache_manager.get(key)
        if cached_value is not None:
            self._logger.debug(f"Cache hit: {key}")
            return cached_value
        
        # Кэш промах, выполняем функцию
        self._logger.debug(f"Cache miss: {key}")
        if asyncio.iscoroutinefunction(func):
            value = await func(*args, **kwargs)
        else:
            value = func(*args, **kwargs)
        
        # Сохраняем в кэш
        await cache_manager.set(key, value, ttl=ttl or self.ttl)
        return value


class WriteThroughCacheStrategy(CacheStrategy):
    """Стратегия Write-Through: запись в кэш и источник одновременно"""
    
    async def get_or_set(
        self,
        cache_manager,
        key: str,
        func: Callable,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Write-through кэширование"""
        # Всегда выполняем функцию
        if asyncio.iscoroutinefunction(func):
            value = await func(*args, **kwargs)
        else:
            value = func(*args, **kwargs)
        
        # Сохраняем в кэш
        await cache_manager.set(key, value, ttl=ttl or self.ttl)
        return value


class CacheInvalidator:
    """Класс для инвалидации кэша"""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self._logger = logger.bind(service="CacheInvalidator")
        # Регистр ключей по паттернам
        self._patterns: Dict[str, List[str]] = {}
    
    async def invalidate(self, key: str):
        """Инвалидировать конкретный ключ"""
        await self.cache_manager.delete(key)
        self._logger.debug(f"Cache invalidated: {key}")
    
    async def invalidate_pattern(self, pattern: str):
        """Инвалидировать все ключи по паттерну"""
        # Простая реализация - в реальности может потребоваться Redis SCAN
        if hasattr(self.cache_manager, 'delete_pattern'):
            await self.cache_manager.delete_pattern(pattern)
        else:
            self._logger.warning(f"Pattern invalidation not supported for {type(self.cache_manager)}")
    
    async def invalidate_by_prefix(self, prefix: str):
        """Инвалидировать все ключи с префиксом"""
        await self.invalidate_pattern(f"{prefix}*")
    
    def register_pattern(self, name: str, pattern: str):
        """Зарегистрировать паттерн для групповой инвалидации"""
        if name not in self._patterns:
            self._patterns[name] = []
        self._patterns[name].append(pattern)
    
    async def invalidate_by_registered_pattern(self, name: str):
        """Инвалидировать по зарегистрированному паттерну"""
        if name in self._patterns:
            for pattern in self._patterns[name]:
                await self.invalidate_pattern(pattern)


class CacheTagManager:
    """Управление тегами кэша для групповой инвалидации"""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self._logger = logger.bind(service="CacheTagManager")
        # Маппинг тегов на ключи: {tag: [key1, key2, ...]}
        self._tag_to_keys: Dict[str, List[str]] = {}
        # Маппинг ключей на теги: {key: [tag1, tag2, ...]}
        self._key_to_tags: Dict[str, List[str]] = {}
    
    async def tag_key(self, key: str, *tags: str):
        """Добавить теги к ключу"""
        if key not in self._key_to_tags:
            self._key_to_tags[key] = []
        
        for tag in tags:
            if tag not in self._tag_to_keys:
                self._tag_to_keys[tag] = []
            if key not in self._tag_to_keys[tag]:
                self._tag_to_keys[tag].append(key)
            if tag not in self._key_to_tags[key]:
                self._key_to_tags[key].append(tag)
    
    async def invalidate_by_tag(self, tag: str):
        """Инвалидировать все ключи с тегом"""
        if tag in self._tag_to_keys:
            for key in self._tag_to_keys[tag]:
                await self.cache_manager.delete(key)
                # Удаляем тег из маппинга
                if key in self._key_to_tags:
                    self._key_to_tags[key].remove(tag)
            del self._tag_to_keys[tag]
            self._logger.info(f"Invalidated {len(self._tag_to_keys[tag])} keys by tag: {tag}")
    
    async def invalidate_by_tags(self, *tags: str):
        """Инвалидировать по нескольким тегам"""
        for tag in tags:
            await self.invalidate_by_tag(tag)

