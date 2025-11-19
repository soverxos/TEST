"""
Тесты для Health Checker
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from Systems.core.monitoring.health import HealthChecker, HealthStatus


class TestHealthStatus:
    """Тесты для HealthStatus"""
    
    def test_health_status_creation(self):
        """Тест создания HealthStatus"""
        status = HealthStatus(
            name="test",
            status="healthy",
            message="Test message",
            details={"key": "value"}
        )
        assert status.name == "test"
        assert status.status == "healthy"
        assert status.message == "Test message"
        assert status.details == {"key": "value"}
    
    def test_health_status_to_dict(self):
        """Тест конвертации в словарь"""
        status = HealthStatus(
            name="test",
            status="healthy",
            message="Test message"
        )
        status_dict = status.to_dict()
        assert status_dict["name"] == "test"
        assert status_dict["status"] == "healthy"
        assert status_dict["message"] == "Test message"
        assert "timestamp" in status_dict


class TestHealthChecker:
    """Тесты для HealthChecker"""
    
    @pytest.fixture
    def mock_services(self):
        """Мок для BotServicesProvider"""
        services = MagicMock()
        services.db = MagicMock()
        services.cache = MagicMock()
        services.bot = MagicMock()
        services.modules = MagicMock()
        return services
    
    @pytest.mark.asyncio
    async def test_check_database_healthy(self, mock_services):
        """Тест проверки БД (здоровое состояние)"""
        checker = HealthChecker(mock_services)
        
        # Мокаем успешное подключение к БД
        mock_session = AsyncMock()
        mock_services.db.get_session.return_value.__aenter__.return_value = mock_session
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        status = await checker.check_database()
        assert status.status == "healthy"
        assert "База данных доступна" in status.message
    
    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self, mock_services):
        """Тест проверки БД (нездоровое состояние)"""
        checker = HealthChecker(mock_services)
        
        # Мокаем ошибку подключения
        mock_services.db.get_session.side_effect = Exception("Connection failed")
        
        status = await checker.check_database()
        assert status.status == "unhealthy"
        assert "Ошибка" in status.message
    
    @pytest.mark.asyncio
    async def test_check_cache_healthy(self, mock_services):
        """Тест проверки кэша (здоровое состояние)"""
        checker = HealthChecker(mock_services)
        
        mock_services.cache.is_available.return_value = True
        mock_services.cache.set = AsyncMock()
        mock_services.cache.get = AsyncMock(return_value="test")
        mock_services.cache.delete = AsyncMock()
        
        status = await checker.check_cache()
        assert status.status == "healthy"
        assert "Кэш работает" in status.message
    
    @pytest.mark.asyncio
    async def test_check_cache_unavailable(self, mock_services):
        """Тест проверки кэша (недоступен)"""
        checker = HealthChecker(mock_services)
        
        mock_services.cache.is_available.return_value = False
        
        status = await checker.check_cache()
        assert status.status == "unhealthy"
        assert "недоступен" in status.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_all(self, mock_services):
        """Тест проверки всех компонентов"""
        checker = HealthChecker(mock_services)
        
        # Мокаем все проверки как успешные
        with patch.object(checker, 'check_database', return_value=HealthStatus("database", "healthy", "")), \
             patch.object(checker, 'check_cache', return_value=HealthStatus("cache", "healthy", "")), \
             patch.object(checker, 'check_telegram_api', return_value=HealthStatus("telegram_api", "healthy", "")), \
             patch.object(checker, 'check_modules', return_value=HealthStatus("modules", "healthy", "")):
            
            result = await checker.check_all()
            assert result["status"] == "healthy"
            assert "checks" in result
            assert len(result["checks"]) == 4

