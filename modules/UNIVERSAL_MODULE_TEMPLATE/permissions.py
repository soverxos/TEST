"""
Определения разрешений для универсального шаблона модуля

Этот файл содержит все разрешения, которые использует модуль.
Разрешения определяют, какие действия может выполнять пользователь.

Структура разрешений:
- Базовые разрешения (доступ к модулю)
- Функциональные разрешения (конкретные действия)
- Административные разрешения (управление модулем)
"""

MODULE_NAME = "universal_template"

class PERMISSIONS:
    """
    Константы разрешений модуля
    
    Используйте эти константы для проверки прав доступа в коде.
    Имена разрешений должны совпадать с теми, что указаны в manifest.yaml
    """
    
    # === БАЗОВЫЕ РАЗРЕШЕНИЯ ===
    ACCESS_USER_FEATURES = f"{MODULE_NAME}.access_user_features"
    """Базовый доступ пользователя к функциям модуля (автоназначение для роли User)"""
    
    ACCESS = f"{MODULE_NAME}.access"
    """Базовый доступ к модулю - возможность видеть главное меню"""
    
    VIEW_DATA = f"{MODULE_NAME}.view_data"
    """Просмотр данных модуля - чтение информации"""
    
    # === ФУНКЦИОНАЛЬНЫЕ РАЗРЕШЕНИЯ ===
    MANAGE_DATA = f"{MODULE_NAME}.manage_data"
    """Управление данными - создание, редактирование, удаление"""
    
    ADVANCED = f"{MODULE_NAME}.advanced"
    """Продвинутые функции - доступ к расширенным возможностям"""
    
    # === АДМИНИСТРАТИВНЫЕ РАЗРЕШЕНИЯ ===
    ADMIN = f"{MODULE_NAME}.admin"
    """Административные функции - полное управление модулем"""

# Список всех разрешений для удобства
ALL_PERMISSIONS = [
    PERMISSIONS.ACCESS_USER_FEATURES,
    PERMISSIONS.ACCESS,
    PERMISSIONS.VIEW_DATA,
    PERMISSIONS.MANAGE_DATA,
    PERMISSIONS.ADVANCED,
    PERMISSIONS.ADMIN
]

# Группировка разрешений по уровням доступа
PERMISSION_GROUPS = {
    "basic": [PERMISSIONS.ACCESS_USER_FEATURES, PERMISSIONS.ACCESS, PERMISSIONS.VIEW_DATA],
    "functional": [PERMISSIONS.MANAGE_DATA, PERMISSIONS.ADVANCED],
    "admin": [PERMISSIONS.ADMIN]
}

def get_permission_description(permission: str) -> str:
    """
    Возвращает описание разрешения
    
    Args:
        permission: Имя разрешения
        
    Returns:
        Описание разрешения или пустая строка
    """
    descriptions = {
        PERMISSIONS.ACCESS_USER_FEATURES: "Базовый доступ пользователя к функциям модуля",
        PERMISSIONS.ACCESS: "Базовый доступ к модулю",
        PERMISSIONS.VIEW_DATA: "Просмотр данных модуля",
        PERMISSIONS.MANAGE_DATA: "Управление данными модуля",
        PERMISSIONS.ADVANCED: "Продвинутые функции модуля",
        PERMISSIONS.ADMIN: "Административные функции модуля"
    }
    
    return descriptions.get(permission, "")

def check_permission_hierarchy(user_permissions: list, required_permission: str) -> bool:
    """
    Проверяет разрешение с учетом иерархии
    
    Например, если у пользователя есть ADMIN разрешение,
    то у него автоматически есть все остальные разрешения.
    
    Args:
        user_permissions: Список разрешений пользователя
        required_permission: Требуемое разрешение
        
    Returns:
        True если разрешение есть, False если нет
    """
    # Если есть админское разрешение - доступ ко всему
    if PERMISSIONS.ADMIN in user_permissions:
        return True
    
    # Если есть продвинутое разрешение - доступ к базовым и функциональным
    if PERMISSIONS.ADVANCED in user_permissions:
        if required_permission in PERMISSION_GROUPS["basic"] + PERMISSION_GROUPS["functional"]:
            return True
    
    # Если есть функциональное разрешение - доступ к базовым
    if PERMISSIONS.MANAGE_DATA in user_permissions:
        if required_permission in PERMISSION_GROUPS["basic"]:
            return True
    
    # Прямая проверка разрешения
    return required_permission in user_permissions
