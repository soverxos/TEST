"""
Тесты для Rate Limiter
"""

import pytest
import time
from Systems.core.security.rate_limiter import RateLimiter, RateLimitMiddleware


class TestRateLimiter:
    """Тесты для класса RateLimiter"""
    
    def test_initialization(self):
        """Тест инициализации RateLimiter"""
        limiter = RateLimiter(default_limit=10, default_window=60)
        assert limiter.default_limit == 10
        assert limiter.default_window == 60
    
    def test_check_rate_limit_allowed(self):
        """Тест разрешенного запроса"""
        limiter = RateLimiter(default_limit=5, default_window=60)
        user_id = 123456
        
        # Первые 5 запросов должны быть разрешены
        for i in range(5):
            is_allowed, retry_after = limiter.check_rate_limit(user_id, "message")
            assert is_allowed is True
            assert retry_after == 0
    
    def test_check_rate_limit_exceeded(self):
        """Тест превышения лимита"""
        limiter = RateLimiter(default_limit=2, default_window=60)
        user_id = 123456
        
        # Первые 2 запроса разрешены
        assert limiter.check_rate_limit(user_id, "message")[0] is True
        assert limiter.check_rate_limit(user_id, "message")[0] is True
        
        # Третий запрос должен быть заблокирован
        is_allowed, retry_after = limiter.check_rate_limit(user_id, "message")
        assert is_allowed is False
        assert retry_after > 0
    
    def test_different_action_types(self):
        """Тест разных типов действий"""
        limiter = RateLimiter(default_limit=10, default_window=60)
        limiter.set_limit("command", limit=3, window=60)
        user_id = 123456
        
        # Команды имеют отдельный лимит
        assert limiter.check_rate_limit(user_id, "command")[0] is True
        assert limiter.check_rate_limit(user_id, "command")[0] is True
        assert limiter.check_rate_limit(user_id, "command")[0] is True
        assert limiter.check_rate_limit(user_id, "command")[0] is False
        
        # Сообщения имеют другой лимит
        assert limiter.check_rate_limit(user_id, "message")[0] is True
    
    def test_reset_user(self):
        """Тест сброса счетчика для пользователя"""
        limiter = RateLimiter(default_limit=2, default_window=60)
        user_id = 123456
        
        # Превышаем лимит
        limiter.check_rate_limit(user_id, "message")
        limiter.check_rate_limit(user_id, "message")
        assert limiter.check_rate_limit(user_id, "message")[0] is False
        
        # Сбрасываем
        limiter.reset_user(user_id)
        
        # Теперь запросы снова разрешены
        assert limiter.check_rate_limit(user_id, "message")[0] is True
    
    def test_get_user_stats(self):
        """Тест получения статистики пользователя"""
        limiter = RateLimiter(default_limit=10, default_window=60)
        user_id = 123456
        
        limiter.check_rate_limit(user_id, "message")
        limiter.check_rate_limit(user_id, "command")
        
        stats = limiter.get_user_stats(user_id)
        assert "message" in stats
        assert "command" in stats
        assert stats["message"]["count"] >= 1

