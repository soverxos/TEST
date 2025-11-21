# core/errors/exceptions.py
"""
Кастомные исключения для SwiftDevBot
"""


class SDBException(Exception):
    """Базовое исключение SwiftDevBot"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(SDBException):
    """Ошибка базы данных"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "DATABASE_ERROR", details)


class ModuleError(SDBException):
    """Ошибка модуля"""
    def __init__(self, message: str, module_name: str = None, details: dict = None):
        super().__init__(message, "MODULE_ERROR", details)
        self.module_name = module_name


class PermissionError(SDBException):
    """Ошибка прав доступа"""
    def __init__(self, message: str, permission: str = None, details: dict = None):
        super().__init__(message, "PERMISSION_ERROR", details)
        self.permission = permission


class ValidationError(SDBException):
    """Ошибка валидации"""
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class RateLimitError(SDBException):
    """Ошибка превышения rate limit"""
    def __init__(self, message: str, retry_after: int = 0, details: dict = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.retry_after = retry_after


class ConfigurationError(SDBException):
    """Ошибка конфигурации"""
    def __init__(self, message: str, config_key: str = None, details: dict = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key


class ExternalAPIError(SDBException):
    """Ошибка внешнего API"""
    def __init__(self, message: str, api_name: str = None, status_code: int = None, details: dict = None):
        super().__init__(message, "EXTERNAL_API_ERROR", details)
        self.api_name = api_name
        self.status_code = status_code


class CacheError(SDBException):
    """Ошибка кэша"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "CACHE_ERROR", details)


class SecurityError(SDBException):
    """Ошибка безопасности"""
    def __init__(self, message: str, threat_type: str = None, details: dict = None):
        super().__init__(message, "SECURITY_ERROR", details)
        self.threat_type = threat_type

