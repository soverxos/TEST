"""
Утилиты для универсального шаблона модуля

Этот файл содержит вспомогательные функции, которые могут
использоваться в различных частях модуля.
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from loguru import logger

from .permissions import MODULE_NAME, check_permission_hierarchy

async def check_permission(services, user_id: int, permission: str) -> bool:
    """
    Проверка разрешения пользователя через RBAC систему
    
    Args:
        services: Провайдер сервисов SDB
        user_id: Telegram ID пользователя
        permission: Требуемое разрешение
        
    Returns:
        True если разрешение есть, False если нет
    """
    try:
        async with services.db.get_session() as session:
            has_permission = await services.rbac.user_has_permission(
                session, user_id, permission
            )
            
            # Логируем проверку разрешения
            logger.debug(f"[{MODULE_NAME}] Проверка разрешения '{permission}' для пользователя {user_id}: {has_permission}")
            
            return has_permission
            
    except Exception as e:
        logger.error(f"[{MODULE_NAME}] Ошибка проверки разрешения '{permission}' для пользователя {user_id}: {e}")
        return False

def format_user_info(user_data: Dict[str, Any]) -> str:
    """
    Форматирование информации о пользователе для отображения
    
    Args:
        user_data: Данные пользователя
        
    Returns:
        Отформатированная строка с информацией о пользователе
    """
    name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')
    username = user_data.get('username', '')
    
    if name and last_name:
        full_name = f"{name} {last_name}"
    elif name:
        full_name = name
    elif username:
        full_name = f"@{username}"
    else:
        full_name = f"User_{user_data.get('id', 'Unknown')}"
    
    return f"👤 **{full_name}**"

def validate_input(data: str, min_length: int = 1, max_length: int = 1000) -> bool:
    """
    Валидация входных данных
    
    Args:
        data: Входные данные
        min_length: Минимальная длина
        max_length: Максимальная длина
        
    Returns:
        True если данные валидны, False если нет
    """
    if not isinstance(data, str):
        return False
    
    data = data.strip()
    
    if len(data) < min_length:
        return False
    
    if len(data) > max_length:
        return False
    
    return True

def validate_email(email: str) -> bool:
    """
    Валидация email адреса
    
    Args:
        email: Email для проверки
        
    Returns:
        True если email валиден, False если нет
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """
    Валидация номера телефона
    
    Args:
        phone: Номер телефона для проверки
        
    Returns:
        True если номер валиден, False если нет
    """
    # Убираем все символы кроме цифр
    phone_clean = re.sub(r'\D', '', phone)
    
    # Проверяем длину (от 10 до 15 цифр)
    if len(phone_clean) < 10 or len(phone_clean) > 15:
        return False
    
    return True

def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматирование даты и времени
    
    Args:
        dt: Объект datetime
        format_str: Строка формата
        
    Returns:
        Отформатированная дата и время
    """
    if dt is None:
        return "Не указано"
    
    return dt.strftime(format_str)

def get_current_timestamp() -> datetime:
    """
    Получение текущего времени в UTC
    
    Returns:
        Текущее время в UTC
    """
    return datetime.now(timezone.utc)

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезка текста до указанной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def parse_command_args(text: str) -> List[str]:
    """
    Парсинг аргументов команды
    
    Args:
        text: Текст команды с аргументами
        
    Returns:
        Список аргументов
    """
    # Разбиваем по пробелам, но учитываем кавычки
    import shlex
    try:
        return shlex.split(text)
    except ValueError:
        # Если не удалось распарсить, разбиваем по пробелам
        return text.split()

def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов Markdown
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    # Символы, которые нужно экранировать в Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def format_file_size(size_bytes: int) -> str:
    """
    Форматирование размера файла в читаемый вид
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированный размер
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def generate_unique_id() -> str:
    """
    Генерация уникального ID
    
    Returns:
        Уникальный ID
    """
    import uuid
    return str(uuid.uuid4())

def safe_get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Безопасное получение значения из вложенного словаря
    
    Args:
        data: Словарь данных
        keys: Список ключей для навигации
        default: Значение по умолчанию
        
    Returns:
        Значение или default
    """
    try:
        current = data
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default

def log_module_action(services, action: str, user_id: int, details: Dict[str, Any] = None):
    """
    Логирование действий модуля в аудит
    
    Args:
        services: Провайдер сервисов SDB
        action: Действие пользователя
        user_id: ID пользователя
        details: Дополнительные детали
    """
    if hasattr(services, 'audit_logger'):
        from core.security.audit_logger import AuditEventType
        services.audit_logger.log_event(
            event_type=AuditEventType.COMMAND_EXECUTION,
            module_name=MODULE_NAME,
            details={
                "action": action,
                **(details or {})
            },
            user_id=user_id
        )
