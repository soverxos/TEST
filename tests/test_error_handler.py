"""
Тесты для Error Handler
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from Systems.core.errors.exceptions import (
    RateLimitError,
    PermissionError,
    ValidationError,
    DatabaseError,
    ModuleError
)
from Systems.core.errors.handler import ErrorHandlerMiddleware


class TestCustomExceptions:
    """Тесты для кастомных исключений"""
    
    def test_rate_limit_error(self):
        """Тест RateLimitError"""
        error = RateLimitError("Too many requests", retry_after=60)
        assert error.message == "Too many requests"
        assert error.error_code == "RATE_LIMIT_ERROR"
        assert error.retry_after == 60
    
    def test_permission_error(self):
        """Тест PermissionError"""
        error = PermissionError("Access denied", permission="module.action")
        assert error.message == "Access denied"
        assert error.error_code == "PERMISSION_ERROR"
        assert error.permission == "module.action"
    
    def test_validation_error(self):
        """Тест ValidationError"""
        error = ValidationError("Invalid input", field="username")
        assert error.message == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field == "username"
    
    def test_database_error(self):
        """Тест DatabaseError"""
        error = DatabaseError("Connection failed")
        assert error.message == "Connection failed"
        assert error.error_code == "DATABASE_ERROR"
    
    def test_module_error(self):
        """Тест ModuleError"""
        error = ModuleError("Module failed", module_name="test_module")
        assert error.message == "Module failed"
        assert error.error_code == "MODULE_ERROR"
        assert error.module_name == "test_module"

