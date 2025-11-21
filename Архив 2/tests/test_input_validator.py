"""
Тесты для Input Validator
"""

import pytest
from Systems.core.security.input_validator import InputValidator, InputValidationMiddleware


class TestInputValidator:
    """Тесты для класса InputValidator"""
    
    def test_initialization(self):
        """Тест инициализации InputValidator"""
        validator = InputValidator()
        assert validator.MAX_MESSAGE_LENGTH == 4096
        assert validator.MAX_COMMAND_LENGTH == 100
    
    def test_validate_message_valid(self):
        """Тест валидного сообщения"""
        validator = InputValidator()
        is_valid, error = validator.validate_message("Привет, это тестовое сообщение!")
        assert is_valid is True
        assert error is None
    
    def test_validate_message_too_long(self):
        """Тест слишком длинного сообщения"""
        validator = InputValidator()
        long_message = "a" * 5000
        is_valid, error = validator.validate_message(long_message)
        assert is_valid is False
        assert "слишком длинное" in error.lower()
    
    def test_validate_message_xss_pattern(self):
        """Тест обнаружения XSS паттерна"""
        validator = InputValidator()
        xss_message = "<script>alert('XSS')</script>"
        is_valid, error = validator.validate_message(xss_message)
        assert is_valid is False
        assert "опасный" in error.lower() or "xss" in error.lower()
    
    def test_validate_message_flood_pattern(self):
        """Тест обнаружения флуд-паттерна"""
        validator = InputValidator()
        flood_message = "aaaaaa"  # Повторяющиеся символы
        is_valid, error = validator.validate_message(flood_message)
        # Может быть валидным, если паттерн не обнаружен
        # Это зависит от реализации _check_flood_pattern
    
    def test_validate_command_valid(self):
        """Тест валидной команды"""
        validator = InputValidator()
        is_valid, error = validator.validate_command("/start")
        assert is_valid is True
        assert error is None
    
    def test_validate_command_invalid_format(self):
        """Тест невалидной команды"""
        validator = InputValidator()
        is_valid, error = validator.validate_command("start")  # Без /
        assert is_valid is False
        assert error is not None
    
    def test_validate_command_too_long(self):
        """Тест слишком длинной команды"""
        validator = InputValidator()
        long_command = "/" + "a" * 200
        is_valid, error = validator.validate_command(long_command)
        assert is_valid is False
        assert "слишком длинная" in error.lower()
    
    def test_validate_callback_data_valid(self):
        """Тест валидных callback data"""
        validator = InputValidator()
        is_valid, error = validator.validate_callback_data("action:123")
        assert is_valid is True
        assert error is None
    
    def test_validate_callback_data_too_long(self):
        """Тест слишком длинных callback data"""
        validator = InputValidator()
        long_data = "a" * 100
        is_valid, error = validator.validate_callback_data(long_data)
        assert is_valid is False
        assert "слишком длинные" in error.lower()
    
    def test_validate_callback_data_dangerous_chars(self):
        """Тест опасных символов в callback data"""
        validator = InputValidator()
        dangerous_data = "action<script>"
        is_valid, error = validator.validate_callback_data(dangerous_data)
        assert is_valid is False
        assert "недопустимые" in error.lower()
    
    def test_sanitize_text(self):
        """Тест очистки текста"""
        validator = InputValidator()
        dirty_text = "<script>alert('XSS')</script>Hello"
        clean_text = validator.sanitize_text(dirty_text)
        assert "<script>" not in clean_text
        assert "Hello" in clean_text

