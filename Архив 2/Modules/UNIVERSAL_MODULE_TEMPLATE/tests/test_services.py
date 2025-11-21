"""
Тесты для сервисов универсального шаблона модуля

Этот файл содержит тесты для проверки корректности работы
бизнес-логики и сервисов модуля.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ..services import TemplateService
from ..models import TemplateModel, UserData

# === ТЕСТЫ СОЗДАНИЯ ЭЛЕМЕНТОВ ===

@pytest.mark.asyncio
async def test_create_item_success():
    """Тест успешного создания элемента"""
    # Создаем мок объекты
    services = MagicMock()
    settings = {"max_items_per_user": 10}
    
    # Мокаем сессию БД
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем запросы к БД
    mock_session.execute.return_value.scalar.return_value = 5  # Текущее количество элементов
    
    # Мокаем создание элемента
    new_item = TemplateModel(
        id=1,
        user_id=123456789,
        title="Тестовый элемент",
        description="Описание",
        priority=50
    )
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    
    # Создаем сервис
    template_service = TemplateService(services, settings)
    
    # Мокаем метод обновления статистики
    with patch.object(template_service, '_update_user_stats', new_callable=AsyncMock):
        result = await template_service.create_item(
            user_id=123456789,
            title="Тестовый элемент",
            description="Описание",
            priority=50
        )
        
        # Проверяем, что элемент был создан
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_item_limit_exceeded():
    """Тест создания элемента при превышении лимита"""
    services = MagicMock()
    settings = {"max_items_per_user": 5}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем превышение лимита
    mock_session.execute.return_value.scalar.return_value = 10  # Превышает лимит
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.create_item(
        user_id=123456789,
        title="Тестовый элемент",
        description="Описание",
        priority=50
    )
    
    # Проверяем, что элемент не был создан
    assert result is None

@pytest.mark.asyncio
async def test_create_item_database_error():
    """Тест создания элемента при ошибке БД"""
    services = MagicMock()
    settings = {"max_items_per_user": 10}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем ошибку БД
    mock_session.execute.side_effect = Exception("Database error")
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.create_item(
        user_id=123456789,
        title="Тестовый элемент",
        description="Описание",
        priority=50
    )
    
    # Проверяем, что элемент не был создан из-за ошибки
    assert result is None

# === ТЕСТЫ ПОЛУЧЕНИЯ ЭЛЕМЕНТОВ ===

@pytest.mark.asyncio
async def test_get_user_items_success():
    """Тест успешного получения элементов пользователя"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем элементы пользователя
    mock_items = [
        TemplateModel(id=1, user_id=123456789, title="Элемент 1", priority=50),
        TemplateModel(id=2, user_id=123456789, title="Элемент 2", priority=30)
    ]
    mock_session.execute.return_value.scalars.return_value.all.return_value = mock_items
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.get_user_items(123456789)
    
    # Проверяем, что элементы получены
    assert len(result) == 2
    assert result[0].title == "Элемент 1"
    assert result[1].title == "Элемент 2"

@pytest.mark.asyncio
async def test_get_user_items_empty():
    """Тест получения элементов для пользователя без элементов"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем пустой результат
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.get_user_items(123456789)
    
    # Проверяем, что результат пустой
    assert len(result) == 0

@pytest.mark.asyncio
async def test_get_item_by_id_success():
    """Тест успешного получения элемента по ID"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем элемент
    mock_item = TemplateModel(id=1, user_id=123456789, title="Тестовый элемент")
    mock_session.execute.return_value.scalars.return_value.first.return_value = mock_item
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.get_item_by_id(1, 123456789)
    
    # Проверяем, что элемент найден
    assert result is not None
    assert result.id == 1
    assert result.title == "Тестовый элемент"

@pytest.mark.asyncio
async def test_get_item_by_id_not_found():
    """Тест получения несуществующего элемента"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем отсутствие элемента
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.get_item_by_id(999, 123456789)
    
    # Проверяем, что элемент не найден
    assert result is None

# === ТЕСТЫ ОБНОВЛЕНИЯ ЭЛЕМЕНТОВ ===

@pytest.mark.asyncio
async def test_update_item_success():
    """Тест успешного обновления элемента"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем существующий элемент
    mock_item = TemplateModel(id=1, user_id=123456789, title="Старый заголовок")
    
    template_service = TemplateService(services, settings)
    
    # Мокаем метод получения элемента
    with patch.object(template_service, 'get_item_by_id', return_value=mock_item):
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        result = await template_service.update_item(
            item_id=1,
            user_id=123456789,
            title="Новый заголовок",
            description="Новое описание"
        )
        
        # Проверяем, что обновление прошло успешно
        assert result == True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_item_not_found():
    """Тест обновления несуществующего элемента"""
    services = MagicMock()
    settings = {}
    
    template_service = TemplateService(services, settings)
    
    # Мокаем отсутствие элемента
    with patch.object(template_service, 'get_item_by_id', return_value=None):
        result = await template_service.update_item(
            item_id=999,
            user_id=123456789,
            title="Новый заголовок"
        )
        
        # Проверяем, что обновление не прошло
        assert result == False

@pytest.mark.asyncio
async def test_update_item_no_changes():
    """Тест обновления элемента без изменений"""
    services = MagicMock()
    settings = {}
    
    mock_item = TemplateModel(id=1, user_id=123456789, title="Заголовок")
    
    template_service = TemplateService(services, settings)
    
    with patch.object(template_service, 'get_item_by_id', return_value=mock_item):
        result = await template_service.update_item(
            item_id=1,
            user_id=123456789
            # Нет изменений
        )
        
        # Проверяем, что обновление не прошло из-за отсутствия изменений
        assert result == False

# === ТЕСТЫ УДАЛЕНИЯ ЭЛЕМЕНТОВ ===

@pytest.mark.asyncio
async def test_delete_item_success():
    """Тест успешного удаления элемента"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    mock_item = TemplateModel(id=1, user_id=123456789, title="Элемент для удаления")
    
    template_service = TemplateService(services, settings)
    
    with patch.object(template_service, 'get_item_by_id', return_value=mock_item):
        mock_session.execute.return_value.rowcount = 1
        mock_session.commit = AsyncMock()
        
        result = await template_service.delete_item(1, 123456789)
        
        # Проверяем, что удаление прошло успешно
        assert result == True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_item_not_found():
    """Тест удаления несуществующего элемента"""
    services = MagicMock()
    settings = {}
    
    template_service = TemplateService(services, settings)
    
    with patch.object(template_service, 'get_item_by_id', return_value=None):
        result = await template_service.delete_item(999, 123456789)
        
        # Проверяем, что удаление не прошло
        assert result == False

# === ТЕСТЫ СТАТИСТИКИ ===

@pytest.mark.asyncio
async def test_get_user_stats_success():
    """Тест успешного получения статистики пользователя"""
    services = MagicMock()
    settings = {"max_items_per_user": 10}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем данные пользователя
    mock_user_data = UserData(
        id=1,
        user_id=123456789,
        items_created=5,
        last_activity=datetime.now(timezone.utc)
    )
    
    template_service = TemplateService(services, settings)
    
    # Мокаем методы получения данных
    with patch.object(template_service, '_get_or_create_user_data', return_value=mock_user_data):
        mock_session.execute.return_value.scalar.return_value = 3  # Активные элементы
        mock_session.execute.return_value.scalar.return_value = 1  # Публичные элементы
        
        result = await template_service.get_user_stats(123456789)
        
        # Проверяем структуру статистики
        assert "user_id" in result
        assert "items_created" in result
        assert "active_items" in result
        assert "public_items" in result
        assert "max_items" in result
        assert "can_create_more" in result
        
        assert result["user_id"] == 123456789
        assert result["max_items"] == 10

@pytest.mark.asyncio
async def test_get_global_stats_success():
    """Тест успешного получения глобальной статистики"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем глобальную статистику
    mock_session.execute.return_value.scalar.side_effect = [100, 80, 25]  # total, active, unique
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.get_global_stats()
    
    # Проверяем структуру глобальной статистики
    assert "total_items" in result
    assert "active_items" in result
    assert "unique_users" in result
    assert "module_version" in result
    
    assert result["total_items"] == 100
    assert result["active_items"] == 80
    assert result["unique_users"] == 25

# === ТЕСТЫ ОБРАБОТКИ ДАННЫХ ===

@pytest.mark.asyncio
async def test_process_data_success():
    """Тест успешной обработки данных"""
    services = MagicMock()
    settings = {}
    
    # Мокаем аудит логгер
    services.audit_logger = MagicMock()
    services.audit_logger.log_event = AsyncMock()
    
    template_service = TemplateService(services, settings)
    
    result = await template_service.process_data("тестовые данные")
    
    # Проверяем результат обработки
    assert result == "Обработано: ТЕСТОВЫЕ ДАННЫЕ"
    
    # Проверяем, что событие было залогировано
    services.audit_logger.log_event.assert_called_once()

# === ТЕСТЫ ВСПОМОГАТЕЛЬНЫХ МЕТОДОВ ===

@pytest.mark.asyncio
async def test_get_or_create_user_data_existing():
    """Тест получения существующих данных пользователя"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем существующие данные
    existing_data = UserData(id=1, user_id=123456789, items_created=5)
    mock_session.execute.return_value.scalars.return_value.first.return_value = existing_data
    
    template_service = TemplateService(services, settings)
    
    result = await template_service._get_or_create_user_data(mock_session, 123456789)
    
    # Проверяем, что возвращены существующие данные
    assert result == existing_data
    assert result.items_created == 5

@pytest.mark.asyncio
async def test_get_or_create_user_data_new():
    """Тест создания новых данных пользователя"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем отсутствие данных
    mock_session.execute.return_value.scalars.return_value.first.return_value = None
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    
    template_service = TemplateService(services, settings)
    
    result = await template_service._get_or_create_user_data(mock_session, 123456789)
    
    # Проверяем, что созданы новые данные
    assert result is not None
    assert result.user_id == 123456789
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()

@pytest.mark.asyncio
async def test_update_user_stats():
    """Тест обновления статистики пользователя"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    mock_user_data = UserData(id=1, user_id=123456789, items_created=5)
    
    template_service = TemplateService(services, settings)
    
    with patch.object(template_service, '_get_or_create_user_data', return_value=mock_user_data):
        mock_session.flush = AsyncMock()
        
        await template_service._update_user_stats(mock_session, 123456789)
        
        # Проверяем, что счетчик увеличился
        assert mock_user_data.items_created == 6
        mock_session.flush.assert_called_once()

# === ТЕСТЫ ОБРАБОТКИ ОШИБОК ===

@pytest.mark.asyncio
async def test_service_database_error():
    """Тест обработки ошибок БД в сервисе"""
    services = MagicMock()
    settings = {}
    
    # Мокаем ошибку БД
    services.db.get_session.side_effect = Exception("Database connection error")
    
    template_service = TemplateService(services, settings)
    
    # Тестируем различные методы на обработку ошибок
    result = await template_service.get_user_items(123456789)
    assert result == []
    
    result = await template_service.get_item_by_id(1, 123456789)
    assert result is None
    
    result = await template_service.update_item(1, 123456789, title="Новый заголовок")
    assert result == False
    
    result = await template_service.delete_item(1, 123456789)
    assert result == False

@pytest.mark.asyncio
async def test_service_initialization():
    """Тест инициализации сервиса"""
    services = MagicMock()
    settings = {
        "max_items_per_user": 15,
        "debug_mode": True,
        "notification_enabled": False
    }
    
    template_service = TemplateService(services, settings)
    
    # Проверяем, что настройки применились
    assert template_service.max_items_per_user == 15
    assert template_service.debug_mode == True
    assert template_service.notification_enabled == False

# === ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ===

@pytest.mark.asyncio
async def test_service_performance():
    """Тест производительности сервиса"""
    import time
    
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    # Мокаем быстрые операции
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    
    template_service = TemplateService(services, settings)
    
    start_time = time.time()
    await template_service.get_user_items(123456789)
    end_time = time.time()
    
    # Проверяем, что операция выполняется быстро
    assert (end_time - start_time) < 1.0

# === ТЕСТЫ БЕЗОПАСНОСТИ ===

@pytest.mark.asyncio
async def test_service_security():
    """Тест безопасности сервиса"""
    services = MagicMock()
    settings = {}
    
    mock_session = AsyncMock()
    services.db.get_session.return_value.__aenter__.return_value = mock_session
    
    template_service = TemplateService(services, settings)
    
    # Тест на SQL инъекцию через параметры
    malicious_title = "'; DROP TABLE users; --"
    
    with patch.object(template_service, 'get_item_by_id', return_value=None):
        result = await template_service.update_item(
            item_id=1,
            user_id=123456789,
            title=malicious_title
        )
        
        # Проверяем, что элемент не найден (безопасность)
        assert result == False
    
    # Тест на доступ к чужим данным
    result = await template_service.get_item_by_id(1, 999999)  # Другой пользователь
    
    # Проверяем, что доступ ограничен
    assert result is None
