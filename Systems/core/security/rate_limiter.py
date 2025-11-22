# core/security/rate_limiter.py
"""
Rate Limiting Middleware для защиты от флуда и DDoS атак
"""

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from aiogram.exceptions import TelegramRetryAfter

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider


class RateLimiter:
    """
    Класс для управления rate limiting с использованием sliding window алгоритма
    """
    
    def __init__(self, default_limit: int = 10, default_window: int = 60):
        """
        Args:
            default_limit: Количество запросов по умолчанию
            default_window: Окно времени в секундах
        """
        self.default_limit = default_limit
        self.default_window = default_window
        # Структура: {user_id: [(timestamp, action_type), ...]}
        self._requests: Dict[int, list] = defaultdict(list)
        # Настройки для разных типов действий
        self._limits: Dict[str, Tuple[int, int]] = {
            "message": (self.default_limit, self.default_window),
            "callback": (20, 60),
            "command": (5, 60),
            "inline_query": (30, 60),
        }
        self._logger = logger.bind(service="RateLimiter")
    
    def set_limit(self, action_type: str, limit: int, window: int):
        """Установить лимит для типа действия"""
        self._limits[action_type] = (limit, window)
        self._logger.info(f"Установлен лимит для {action_type}: {limit} запросов за {window} секунд")
    
    def check_rate_limit(
        self, 
        user_id: int, 
        action_type: str = "message",
        custom_limit: Optional[int] = None,
        custom_window: Optional[int] = None
    ) -> Tuple[bool, int]:
        """
        Проверяет rate limit для пользователя
        
        Returns:
            Tuple[bool, int]: (is_allowed, retry_after)
                - is_allowed: разрешен ли запрос
                - retry_after: через сколько секунд можно повторить (если не разрешен)
        """
        current_time = time.time()
        limit, window = self._limits.get(action_type, (self.default_limit, self.default_window))
        
        if custom_limit is not None:
            limit = custom_limit
        if custom_window is not None:
            window = custom_window
        
        # Очищаем старые записи (старше окна)
        user_requests = self._requests[user_id]
        cutoff_time = current_time - window
        self._requests[user_id] = [
            req_time for req_time in user_requests 
            if req_time[0] > cutoff_time
        ]
        
        # Проверяем количество запросов
        request_count = len(self._requests[user_id])
        
        if request_count >= limit:
            # Вычисляем время до следующего разрешенного запроса
            oldest_request_time = min(req[0] for req in self._requests[user_id]) if self._requests[user_id] else current_time
            retry_after = int(window - (current_time - oldest_request_time)) + 1
            return False, retry_after
        
        # Добавляем текущий запрос
        self._requests[user_id].append((current_time, action_type))
        return True, 0
    
    def reset_user(self, user_id: int):
        """Сбросить счетчик для пользователя"""
        if user_id in self._requests:
            del self._requests[user_id]
            self._logger.debug(f"Счетчик rate limit сброшен для пользователя {user_id}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Получить статистику для пользователя"""
        current_time = time.time()
        user_requests = self._requests.get(user_id, [])
        
        stats = {}
        for action_type, (limit, window) in self._limits.items():
            cutoff_time = current_time - window
            action_requests = [
                req_time for req_time in user_requests 
                if req_time[0] > cutoff_time and req_time[1] == action_type
            ]
            stats[action_type] = {
                "count": len(action_requests),
                "limit": limit,
                "remaining": max(0, limit - len(action_requests))
            }
        
        return stats


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов от пользователей
    """
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        super().__init__()
        self.rate_limiter = rate_limiter or RateLimiter()
        self._logger = logger.bind(service="RateLimitMiddleware")
        # Исключения - пользователи, которые не должны ограничиваться
        self._exempt_users: set = set()
    
    def exempt_user(self, user_id: int):
        """Добавить пользователя в исключения"""
        self._exempt_users.add(user_id)
        self._logger.debug(f"Пользователь {user_id} добавлен в исключения rate limit")
    
    def remove_exemption(self, user_id: int):
        """Убрать пользователя из исключений"""
        self._exempt_users.discard(user_id)
    
    def _get_action_type(self, event: Update) -> str:
        """Определяет тип действия из события"""
        if event.message:
            if event.message.text and event.message.text.startswith("/"):
                return "command"
            return "message"
        elif event.callback_query:
            return "callback"
        elif event.inline_query:
            return "inline_query"
        return "message"
    
    async def __call__(
        self,
        handler,
        event: Update,
        data: Dict
    ):
        """Обработка события с проверкой rate limit"""
        
        # Получаем пользователя из события
        user = data.get("event_from_user")
        if not user:
            # Если нет пользователя, пропускаем проверку
            return await handler(event, data)
        
        user_id = user.id
        
        # Проверяем исключения (супер-админы и т.д.)
        services_provider = data.get("services_provider")
        if services_provider:
            if user_id in services_provider.config.core.super_admins:
                return await handler(event, data)
        
        if user_id in self._exempt_users:
            return await handler(event, data)
        
        # Определяем тип действия
        action_type = self._get_action_type(event)
        
        # Проверяем rate limit
        is_allowed, retry_after = self.rate_limiter.check_rate_limit(
            user_id=user_id,
            action_type=action_type
        )
        
        if not is_allowed:
            self._logger.warning(
                f"Rate limit превышен для пользователя {user_id} "
                f"(действие: {action_type}, повторить через {retry_after} сек)"
            )
            
            # Отправляем сообщение пользователю
            error_message = (
                f"⏳ Слишком много запросов. "
                f"Пожалуйста, подождите {retry_after} секунд перед следующим запросом."
            )
            
            try:
                if event.message:
                    await event.message.answer(error_message)
                elif event.callback_query:
                    await event.callback_query.answer(
                        f"Подождите {retry_after} сек",
                        show_alert=True
                    )
            except Exception as e:
                self._logger.error(f"Ошибка при отправке сообщения о rate limit: {e}")
            
            return None  # Прерываем обработку
        
        # Если все в порядке, продолжаем обработку
        return await handler(event, data)

