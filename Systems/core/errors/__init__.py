# core/errors/__init__.py
"""
Модуль обработки ошибок
"""

from .exceptions import (
    SDBException,
    DatabaseError,
    ModuleError,
    PermissionError,
    ValidationError,
    RateLimitError,
    ConfigurationError,
    ExternalAPIError,
    CacheError,
    SecurityError
)

from .handler import ErrorHandlerMiddleware, handle_error

__all__ = [
    "SDBException",
    "DatabaseError",
    "ModuleError",
    "PermissionError",
    "ValidationError",
    "RateLimitError",
    "ConfigurationError",
    "ExternalAPIError",
    "CacheError",
    "SecurityError",
    "ErrorHandlerMiddleware",
    "handle_error"
]

