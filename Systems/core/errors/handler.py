# core/errors/handler.py
"""
Централизованный обработчик ошибок
"""

import traceback
from typing import Optional, Dict, Any
from loguru import logger

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery, ErrorEvent
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter, TelegramBadRequest

from .exceptions import (
    SDBException, DatabaseError, ModuleError, PermissionError,
    ValidationError, RateLimitError, ConfigurationError,
    ExternalAPIError, CacheError, SecurityError
)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware для централизованной обработки ошибок
    """
    
    def __init__(self):
        super().__init__()
        self._logger = logger.bind(service="ErrorHandlerMiddleware")
    
    async def __call__(
        self,
        handler,
        event: Update,
        data: Dict
    ):
        """Обработка с перехватом исключений"""
        try:
            return await handler(event, data)
        except RateLimitError as e:
            return await self._handle_rate_limit_error(e, event)
        except PermissionError as e:
            return await self._handle_permission_error(e, event)
        except ValidationError as e:
            return await self._handle_validation_error(e, event)
        except DatabaseError as e:
            return await self._handle_database_error(e, event)
        except ModuleError as e:
            return await self._handle_module_error(e, event)
        except TelegramRetryAfter as e:
            return await self._handle_telegram_retry_after(e, event)
        except TelegramAPIError as e:
            return await self._handle_telegram_api_error(e, event)
        except SDBException as e:
            return await self._handle_sdb_exception(e, event)
        except Exception as e:
            return await self._handle_unexpected_error(e, event)
    
    async def _handle_rate_limit_error(self, error: RateLimitError, event: Update):
        """Обработка ошибки rate limit"""
        self._logger.warning(f"Rate limit error: {error.message}")
        message = f"⏳ Слишком много запросов. Подождите {error.retry_after} секунд."
        return await self._send_error_message(event, message)
    
    async def _handle_permission_error(self, error: PermissionError, event: Update):
        """Обработка ошибки прав доступа"""
        self._logger.warning(f"Permission error: {error.message} (permission: {error.permission})")
        message = f"❌ У вас нет прав для выполнения этого действия.\n{error.message}"
        return await self._send_error_message(event, message, show_alert=True)
    
    async def _handle_validation_error(self, error: ValidationError, event: Update):
        """Обработка ошибки валидации"""
        self._logger.warning(f"Validation error: {error.message} (field: {error.field})")
        message = f"❌ Ошибка валидации: {error.message}"
        return await self._send_error_message(event, message)
    
    async def _handle_database_error(self, error: DatabaseError, event: Update):
        """Обработка ошибки БД"""
        self._logger.error(f"Database error: {error.message}", exc_info=True)
        message = "❌ Произошла ошибка при работе с базой данных. Попробуйте позже."
        return await self._send_error_message(event, message)
    
    async def _handle_module_error(self, error: ModuleError, event: Update):
        """Обработка ошибки модуля"""
        self._logger.error(f"Module error in {error.module_name}: {error.message}", exc_info=True)
        message = f"❌ Ошибка модуля {error.module_name}: {error.message}"
        return await self._send_error_message(event, message)
    
    async def _handle_telegram_retry_after(self, error: TelegramRetryAfter, event: Update):
        """Обработка Telegram RetryAfter"""
        self._logger.warning(f"Telegram RetryAfter: {error.retry_after} seconds")
        # Не отправляем сообщение пользователю, просто логируем
        return None
    
    async def _handle_telegram_api_error(self, error: TelegramAPIError, event: Update):
        """Обработка ошибки Telegram API"""
        self._logger.error(f"Telegram API error: {error.message}", exc_info=True)
        
        # Специальная обработка для некоторых типов ошибок
        if isinstance(error, TelegramBadRequest):
            if "message is too long" in str(error).lower():
                message = "❌ Сообщение слишком длинное."
            elif "can't parse" in str(error).lower():
                message = "❌ Ошибка форматирования сообщения."
            else:
                message = "❌ Ошибка при отправке сообщения."
        else:
            message = "❌ Временная ошибка Telegram API. Попробуйте позже."
        
        return await self._send_error_message(event, message)
    
    async def _handle_sdb_exception(self, error: SDBException, event: Update):
        """Обработка кастомного исключения SDB"""
        self._logger.error(f"SDB Exception [{error.error_code}]: {error.message}", exc_info=True)
        message = f"❌ Ошибка: {error.message}"
        return await self._send_error_message(event, message)
    
    async def _handle_unexpected_error(self, error: Exception, event: Update):
        """Обработка неожиданных ошибок"""
        error_traceback = traceback.format_exc()
        self._logger.critical(
            f"Unexpected error: {type(error).__name__}: {error}",
            exc_info=True
        )
        
        # В продакшене не показываем детали пользователю
        message = "❌ Произошла неожиданная ошибка. Администратор уведомлен."
        return await self._send_error_message(event, message)
    
    async def _send_error_message(
        self, 
        event: Update, 
        message: str, 
        show_alert: bool = False
    ) -> Optional[Any]:
        """Отправляет сообщение об ошибке пользователю"""
        try:
            if event.message:
                await event.message.answer(message)
            elif event.callback_query:
                await event.callback_query.answer(message, show_alert=show_alert)
        except Exception as e:
            self._logger.error(f"Failed to send error message: {e}")
        return None


async def handle_error(event: ErrorEvent, exception: Exception):
    """
    Глобальный обработчик ошибок для aiogram
    """
    logger.error(
        f"Unhandled error in aiogram: {type(exception).__name__}: {exception}",
        exc_info=exception
    )

