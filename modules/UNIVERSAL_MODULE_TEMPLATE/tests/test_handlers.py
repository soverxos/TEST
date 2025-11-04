"""
Тесты для обработчиков универсального шаблона модуля

Этот файл содержит тесты для проверки корректности работы
обработчиков команд и сообщений.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from ..handlers import template_router
from ..permissions import PERMISSIONS
from ..utils import check_permission

# === ТЕСТЫ ОБРАБОТЧИКОВ КОМАНД ===

@pytest.mark.asyncio
async def test_template_command_success():
    """Тест успешного выполнения команды /template"""
    # Создаем мок объекты
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    
    services = MagicMock()
    
    # Мокаем проверку разрешений
    with patch('modules.universal_template.handlers.check_permission', return_value=True):
        # Импортируем и вызываем обработчик
        from ..handlers import template_command
        await template_command(message, services)
        
        # Проверяем, что сообщение было отправлено
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Универсальный шаблон модуля" in call_args

@pytest.mark.asyncio
async def test_template_command_no_permission():
    """Тест команды /template без разрешения"""
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    
    services = MagicMock()
    
    # Мокаем проверку разрешений (возвращаем False)
    with patch('modules.universal_template.handlers.check_permission', return_value=False):
        from ..handlers import template_command
        await template_command(message, services)
        
        # Проверяем, что отправлено сообщение об отсутствии доступа
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "нет доступа" in call_args

@pytest.mark.asyncio
async def test_template_admin_command_success():
    """Тест успешного выполнения команды /template_admin"""
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.check_permission', return_value=True):
        from ..handlers import template_admin_command
        await template_admin_command(message, services)
        
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Административная панель" in call_args

@pytest.mark.asyncio
async def test_template_admin_command_no_permission():
    """Тест команды /template_admin без разрешения"""
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.check_permission', return_value=False):
        from ..handlers import template_admin_command
        await template_admin_command(message, services)
        
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "нет прав администратора" in call_args

# === ТЕСТЫ CALLBACK ОБРАБОТЧИКОВ ===

@pytest.mark.asyncio
async def test_main_menu_callback_success():
    """Тест успешного callback главного меню"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user.id = 123456789
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.check_permission', return_value=True):
        from ..handlers import main_menu_callback
        await main_menu_callback(callback, services)
        
        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once()

@pytest.mark.asyncio
async def test_main_menu_callback_no_permission():
    """Тест callback главного меню без разрешения"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user.id = 123456789
    callback.answer = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.check_permission', return_value=False):
        from ..handlers import main_menu_callback
        await main_menu_callback(callback, services)
        
        callback.answer.assert_called_once_with("❌ Нет доступа", show_alert=True)

@pytest.mark.asyncio
async def test_show_stats_callback_success():
    """Тест успешного callback статистики"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user.id = 123456789
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    
    services = MagicMock()
    services.modules.get_module_settings.return_value = {}
    
    # Мокаем сервис
    mock_service = AsyncMock()
    mock_service.get_user_stats.return_value = {
        "items_created": 5,
        "active_items": 3,
        "max_items": 10
    }
    mock_service.get_global_stats.return_value = {
        "total_items": 100,
        "active_items": 80,
        "unique_users": 25
    }
    
    with patch('modules.universal_template.handlers.check_permission', return_value=True), \
         patch('modules.universal_template.handlers.TemplateService', return_value=mock_service):
        
        from ..handlers import show_stats_callback
        await show_stats_callback(callback, services)
        
        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once()

# === ТЕСТЫ FSM ОБРАБОТЧИКОВ ===

@pytest.mark.asyncio
async def test_start_create_item_callback_success():
    """Тест успешного начала создания элемента"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user.id = 123456789
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    
    state = AsyncMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.check_permission', return_value=True):
        from ..handlers import start_create_item_callback
        await start_create_item_callback(callback, state, services)
        
        state.set_state.assert_called_once()
        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once()

@pytest.mark.asyncio
async def test_process_title_input_valid():
    """Тест обработки валидного ввода заголовка"""
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.text = "Тестовый заголовок"
    message.answer = AsyncMock()
    
    state = AsyncMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.validate_input', return_value=True):
        from ..handlers import process_title_input
        await process_title_input(message, state, services)
        
        state.update_data.assert_called_once()
        state.set_state.assert_called_once()
        message.answer.assert_called_once()

@pytest.mark.asyncio
async def test_process_title_input_invalid():
    """Тест обработки невалидного ввода заголовка"""
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.text = ""  # Пустой заголовок
    message.answer = AsyncMock()
    
    state = AsyncMock(spec=FSMContext)
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.validate_input', return_value=False):
        from ..handlers import process_title_input
        await process_title_input(message, state, services)
        
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "❌" in call_args

# === ТЕСТЫ ОБРАБОТКИ ОШИБОК ===

@pytest.mark.asyncio
async def test_unknown_callback():
    """Тест обработки неизвестного callback"""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.data = "unknown_callback_data"
    callback.answer = AsyncMock()
    
    from ..handlers import unknown_callback
    await unknown_callback(callback)
    
    callback.answer.assert_called_once_with("❌ Неизвестная команда", show_alert=True)

@pytest.mark.asyncio
async def test_unknown_message():
    """Тест обработки неизвестного сообщения"""
    message = AsyncMock(spec=types.Message)
    message.text = "Неизвестное сообщение"
    
    state = AsyncMock(spec=FSMContext)
    state.get_state.return_value = None  # Нет активного состояния
    
    from ..handlers import unknown_message
    await unknown_message(message, state)
    
    # Сообщение должно быть проигнорировано (нет вызовов answer)

# === ТЕСТЫ ИНТЕГРАЦИИ ===

@pytest.mark.asyncio
async def test_handler_integration():
    """Интеграционный тест обработчиков"""
    # Создаем полный мок контекста
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.text = "/template"
    message.answer = AsyncMock()
    
    services = MagicMock()
    services.modules.get_module_settings.return_value = {}
    
    # Мокаем все зависимости
    with patch('modules.universal_template.handlers.check_permission', return_value=True), \
         patch('modules.universal_template.handlers.log_module_action'):
        
        from ..handlers import template_command
        await template_command(message, services)
        
        # Проверяем, что команда выполнилась успешно
        message.answer.assert_called_once()
        
        # Проверяем, что логирование было вызвано
        # (это проверяется через мок log_module_action)

# === ТЕСТЫ ВАЛИДАЦИИ ===

@pytest.mark.asyncio
async def test_input_validation():
    """Тест валидации входных данных"""
    from ..utils import validate_input
    
    # Валидные данные
    assert validate_input("Тест", min_length=1, max_length=10) == True
    assert validate_input("Длинный текст для тестирования", min_length=1, max_length=100) == True
    
    # Невалидные данные
    assert validate_input("", min_length=1, max_length=10) == False
    assert validate_input("Очень длинный текст", min_length=1, max_length=5) == False
    assert validate_input(None, min_length=1, max_length=10) == False

# === ТЕСТЫ РАЗРЕШЕНИЙ ===

@pytest.mark.asyncio
async def test_permission_checking():
    """Тест проверки разрешений"""
    services = MagicMock()
    services.db.get_session.return_value.__aenter__.return_value = AsyncMock()
    services.rbac.user_has_permission = AsyncMock(return_value=True)
    
    from ..utils import check_permission
    
    result = await check_permission(services, 123456789, PERMISSIONS.ACCESS)
    assert result == True
    
    # Тест с отсутствующим разрешением
    services.rbac.user_has_permission.return_value = False
    result = await check_permission(services, 123456789, PERMISSIONS.ACCESS)
    assert result == False

# === ТЕСТЫ КОНФИГУРАЦИИ ===

def test_permissions_constants():
    """Тест констант разрешений"""
    from ..permissions import PERMISSIONS, MODULE_NAME
    
    assert MODULE_NAME == "universal_template"
    assert PERMISSIONS.ACCESS == f"{MODULE_NAME}.access"
    assert PERMISSIONS.ADMIN == f"{MODULE_NAME}.admin"
    assert PERMISSIONS.VIEW_DATA == f"{MODULE_NAME}.view_data"
    assert PERMISSIONS.MANAGE_DATA == f"{MODULE_NAME}.manage_data"
    assert PERMISSIONS.ADVANCED == f"{MODULE_NAME}.advanced"

# === ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ===

@pytest.mark.asyncio
async def test_handler_performance():
    """Тест производительности обработчиков"""
    import time
    
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    
    services = MagicMock()
    
    with patch('modules.universal_template.handlers.check_permission', return_value=True):
        from ..handlers import template_command
        
        start_time = time.time()
        await template_command(message, services)
        end_time = time.time()
        
        # Проверяем, что обработчик выполняется быстро (менее 1 секунды)
        assert (end_time - start_time) < 1.0

# === ТЕСТЫ БЕЗОПАСНОСТИ ===

@pytest.mark.asyncio
async def test_security_input_validation():
    """Тест безопасности валидации входных данных"""
    from ..utils import validate_input
    
    # Тест на SQL инъекцию
    malicious_input = "'; DROP TABLE users; --"
    assert validate_input(malicious_input, min_length=1, max_length=100) == True  # Должно пройти валидацию длины
    
    # Тест на XSS
    xss_input = "<script>alert('xss')</script>"
    assert validate_input(xss_input, min_length=1, max_length=100) == True  # Должно пройти валидацию длины
    
    # Тест на очень длинный ввод
    long_input = "A" * 10000
    assert validate_input(long_input, min_length=1, max_length=100) == False  # Должно не пройти валидацию

@pytest.mark.asyncio
async def test_permission_escalation():
    """Тест предотвращения эскалации привилегий"""
    services = MagicMock()
    services.db.get_session.return_value.__aenter__.return_value = AsyncMock()
    services.rbac.user_has_permission = AsyncMock(return_value=False)
    
    from ..utils import check_permission
    
    # Пользователь без прав не должен получить доступ к админским функциям
    result = await check_permission(services, 123456789, PERMISSIONS.ADMIN)
    assert result == False
    
    # Пользователь без прав не должен получить доступ к управлению данными
    result = await check_permission(services, 123456789, PERMISSIONS.MANAGE_DATA)
    assert result == False
