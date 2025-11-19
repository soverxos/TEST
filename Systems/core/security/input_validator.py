# core/security/input_validator.py
"""
Валидация входных данных на уровне middleware
"""

import re
from typing import Optional, Dict, Any, List, Callable, Tuple
from loguru import logger

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message
from aiogram.filters import Command

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider


class InputValidator:
    """
    Класс для валидации входных данных
    """
    
    # Паттерны для обнаружения потенциально опасного контента
    DANGEROUS_PATTERNS = [
        (r'<script[^>]*>.*?</script>', 'XSS скрипт'),
        (r'javascript:', 'JavaScript протокол'),
        (r'on\w+\s*=', 'HTML событие'),
        (r'data:text/html', 'HTML data URI'),
        (r'eval\s*\(', 'eval функция'),
        (r'exec\s*\(', 'exec функция'),
        (r'__import__', 'динамический импорт'),
    ]
    
    # Максимальные длины
    MAX_MESSAGE_LENGTH = 4096  # Лимит Telegram
    MAX_COMMAND_LENGTH = 100
    MAX_CALLBACK_DATA_LENGTH = 64
    
    def __init__(self):
        self._logger = logger.bind(service="InputValidator")
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), description)
            for pattern, description in self.DANGEROUS_PATTERNS
        ]
    
    def validate_message(self, text: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Валидирует текст сообщения
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not text:
            return True, None
        
        # Проверка длины
        if len(text) > self.MAX_MESSAGE_LENGTH:
            return False, f"Сообщение слишком длинное (максимум {self.MAX_MESSAGE_LENGTH} символов)"
        
        # Проверка на опасные паттерны
        for pattern, description in self._compiled_patterns:
            if pattern.search(text):
                self._logger.warning(f"Обнаружен опасный паттерн в сообщении: {description}")
                return False, f"Обнаружен потенциально опасный контент: {description}"
        
        # Проверка на слишком много упоминаний (спам)
        mention_count = text.count('@')
        if mention_count > 10:
            return False, "Слишком много упоминаний в сообщении"
        
        # Проверка на повторяющиеся символы (флуд)
        if self._check_flood_pattern(text):
            return False, "Обнаружен паттерн флуда в сообщении"
        
        return True, None
    
    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Валидирует команду"""
        if not command:
            return False, "Пустая команда"
        
        if len(command) > self.MAX_COMMAND_LENGTH:
            return False, f"Команда слишком длинная (максимум {self.MAX_COMMAND_LENGTH} символов)"
        
        # Команда должна начинаться с /
        if not command.startswith('/'):
            return False, "Команда должна начинаться с /"
        
        # Проверка на валидные символы
        if not re.match(r'^/[a-zA-Z0-9_]+(\s+.*)?$', command):
            return False, "Недопустимые символы в команде"
        
        return True, None
    
    def validate_callback_data(self, callback_data: str) -> Tuple[bool, Optional[str]]:
        """Валидирует callback data"""
        if not callback_data:
            return False, "Пустые callback данные"
        
        if len(callback_data) > self.MAX_CALLBACK_DATA_LENGTH:
            return False, f"Callback data слишком длинные (максимум {self.MAX_CALLBACK_DATA_LENGTH} символов)"
        
        # Проверка на опасные символы
        if re.search(r'[<>"\']', callback_data):
            return False, "Недопустимые символы в callback data"
        
        return True, None
    
    def _check_flood_pattern(self, text: str, threshold: int = 5) -> bool:
        """Проверяет на паттерн флуда (повторяющиеся символы)"""
        if len(text) < threshold * 2:
            return False
        
        # Проверяем повторяющиеся символы
        for i in range(len(text) - threshold):
            char = text[i]
            if text[i:i+threshold] == char * threshold:
                return True
        
        return False
    
    def sanitize_text(self, text: str) -> str:
        """Очищает текст от потенциально опасных элементов"""
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        # Экранируем специальные символы
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        return text


class InputValidationMiddleware(BaseMiddleware):
    """
    Middleware для валидации входных данных
    """
    
    def __init__(self, validator: Optional[InputValidator] = None):
        super().__init__()
        self.validator = validator or InputValidator()
        self._logger = logger.bind(service="InputValidationMiddleware")
        # Пользователи, которые не должны валидироваться
        self._exempt_users: set = set()
    
    def exempt_user(self, user_id: int):
        """Добавить пользователя в исключения"""
        self._exempt_users.add(user_id)
    
    async def __call__(
        self,
        handler,
        event: Update,
        data: Dict
    ):
        """Валидация входных данных"""
        
        user = data.get("event_from_user")
        if user and user.id in self._exempt_users:
            return await handler(event, data)
        
        # Валидация сообщений
        if event.message and event.message.text:
            is_valid, error_msg = self.validator.validate_message(event.message.text)
            if not is_valid:
                self._logger.warning(
                    f"Валидация не пройдена для пользователя {user.id if user else 'unknown'}: {error_msg}"
                )
                try:
                    await event.message.answer(
                        f"❌ Ошибка валидации: {error_msg}\n"
                        f"Пожалуйста, проверьте ваше сообщение и попробуйте снова."
                    )
                except Exception as e:
                    self._logger.error(f"Ошибка при отправке сообщения об ошибке валидации: {e}")
                return None
        
        # Валидация команд
        if event.message and event.message.text and event.message.text.startswith('/'):
            is_valid, error_msg = self.validator.validate_command(event.message.text)
            if not is_valid:
                self._logger.warning(f"Невалидная команда от {user.id if user else 'unknown'}: {error_msg}")
                try:
                    await event.message.answer(f"❌ Невалидная команда: {error_msg}")
                except Exception:
                    pass
                return None
        
        # Валидация callback query
        if event.callback_query and event.callback_query.data:
            is_valid, error_msg = self.validator.validate_callback_data(event.callback_query.data)
            if not is_valid:
                self._logger.warning(f"Невалидные callback data от {user.id if user else 'unknown'}: {error_msg}")
                try:
                    await event.callback_query.answer("❌ Ошибка валидации данных", show_alert=True)
                except Exception:
                    pass
                return None
        
        return await handler(event, data)

