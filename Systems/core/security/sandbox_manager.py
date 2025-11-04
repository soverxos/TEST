# core/security/sandbox_manager.py
"""
Система sandbox для модулей
Обеспечивает изоляцию и ограничение прав модулей
"""

import os
import sys
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import importlib.util

class SecurityLevel(Enum):
    """Уровни безопасности модулей"""
    PARANOID = "paranoid"      # Максимальная изоляция
    STRICT = "strict"         # Строгие ограничения
    MODERATE = "moderate"     # Умеренные ограничения
    PERMISSIVE = "permissive" # Минимальные ограничения (только для разработки)

@dataclass
class ModulePermissions:
    """Разрешения модуля"""
    can_access_database: bool = False
    can_access_cache: bool = False
    can_access_filesystem: bool = False
    can_make_network_requests: bool = False
    can_execute_system_commands: bool = False
    can_modify_user_data: bool = False
    can_access_admin_functions: bool = False
    max_memory_mb: int = 50
    max_execution_time_seconds: int = 30

@dataclass
class SandboxViolation:
    """Нарушение sandbox"""
    module_name: str
    violation_type: str
    details: str
    timestamp: float
    severity: str  # "low", "medium", "high", "critical"

class ModuleSandboxManager:
    """Менеджер sandbox для модулей"""
    
    def __init__(self, config):
        self.config = config
        self.sandbox_dir = config.core.project_data_path / "Security" / "sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Уровни безопасности и соответствующие разрешения
        self.security_levels = {
            SecurityLevel.PARANOID: ModulePermissions(
                can_access_database=False,
                can_access_cache=False,
                can_access_filesystem=False,
                can_make_network_requests=False,
                can_execute_system_commands=False,
                can_modify_user_data=False,
                can_access_admin_functions=False,
                max_memory_mb=10,
                max_execution_time_seconds=10
            ),
            SecurityLevel.STRICT: ModulePermissions(
                can_access_database=True,
                can_access_cache=True,
                can_access_filesystem=False,
                can_make_network_requests=False,
                can_execute_system_commands=False,
                can_modify_user_data=True,
                can_access_admin_functions=False,
                max_memory_mb=25,
                max_execution_time_seconds=20
            ),
            SecurityLevel.MODERATE: ModulePermissions(
                can_access_database=True,
                can_access_cache=True,
                can_access_filesystem=True,
                can_make_network_requests=True,
                can_execute_system_commands=False,
                can_modify_user_data=True,
                can_access_admin_functions=False,
                max_memory_mb=50,
                max_execution_time_seconds=30
            ),
            SecurityLevel.PERMISSIVE: ModulePermissions(
                can_access_database=True,
                can_access_cache=True,
                can_access_filesystem=True,
                can_make_network_requests=True,
                can_execute_system_commands=True,
                can_modify_user_data=True,
                can_access_admin_functions=True,
                max_memory_mb=100,
                max_execution_time_seconds=60
            )
        }
        
        # Активные sandbox'ы модулей
        self.active_sandboxes: Dict[str, Dict] = {}
        
        # История нарушений
        self.violations: List[SandboxViolation] = []
        
        logger.info(f"[Security] ModuleSandboxManager инициализирован с {len(self.security_levels)} уровнями безопасности")
    
    def create_sandbox(self, module_name: str, security_level: SecurityLevel) -> bool:
        """Создает sandbox для модуля"""
        try:
            if module_name in self.active_sandboxes:
                logger.warning(f"[Security] Sandbox для модуля {module_name} уже существует")
                return True
            
            permissions = self.security_levels[security_level]
            
            # Создаем изолированную директорию для модуля
            module_sandbox_dir = self.sandbox_dir / module_name
            module_sandbox_dir.mkdir(exist_ok=True)
            
            # Создаем виртуальную файловую систему
            self._create_virtual_filesystem(module_sandbox_dir, permissions)
            
            # Сохраняем информацию о sandbox
            sandbox_info = {
                "module_name": module_name,
                "security_level": security_level.value,
                "permissions": permissions.__dict__,
                "sandbox_dir": str(module_sandbox_dir),
                "created_at": os.time.time(),
                "violations": []
            }
            
            self.active_sandboxes[module_name] = sandbox_info
            
            logger.info(f"[Security] Создан sandbox для модуля {module_name} с уровнем {security_level.value}")
            return True
            
        except Exception as e:
            logger.error(f"[Security] Ошибка создания sandbox для модуля {module_name}: {e}")
            return False
    
    def _create_virtual_filesystem(self, sandbox_dir: Path, permissions: ModulePermissions):
        """Создает виртуальную файловую систему для модуля"""
        # Создаем директории для различных типов доступа
        if permissions.can_access_filesystem:
            # Ограниченный доступ к файловой системе
            (sandbox_dir / "files").mkdir(exist_ok=True)
            (sandbox_dir / "temp").mkdir(exist_ok=True)
        
        if permissions.can_access_database:
            # Виртуальная БД (только для чтения в строгом режиме)
            (sandbox_dir / "db").mkdir(exist_ok=True)
        
        if permissions.can_access_cache:
            # Изолированный кэш
            (sandbox_dir / "cache").mkdir(exist_ok=True)
    
    def check_permission(self, module_name: str, permission_type: str, **kwargs) -> bool:
        """Проверяет разрешение модуля на выполнение действия"""
        try:
            if module_name not in self.active_sandboxes:
                logger.warning(f"[Security] Sandbox для модуля {module_name} не найден")
                return False
            
            sandbox_info = self.active_sandboxes[module_name]
            permissions = ModulePermissions(**sandbox_info["permissions"])
            
            # Проверяем конкретное разрешение
            permission_map = {
                "database": permissions.can_access_database,
                "cache": permissions.can_access_cache,
                "filesystem": permissions.can_access_filesystem,
                "network": permissions.can_make_network_requests,
                "system_commands": permissions.can_execute_system_commands,
                "user_data": permissions.can_modify_user_data,
                "admin_functions": permissions.can_access_admin_functions
            }
            
            has_permission = permission_map.get(permission_type, False)
            
            if not has_permission:
                # Записываем нарушение
                violation = SandboxViolation(
                    module_name=module_name,
                    violation_type=f"permission_denied_{permission_type}",
                    details=f"Попытка доступа к {permission_type} без разрешения",
                    timestamp=os.time.time(),
                    severity="medium"
                )
                self._record_violation(violation)
            
            return has_permission
            
        except Exception as e:
            logger.error(f"[Security] Ошибка проверки разрешения для модуля {module_name}: {e}")
            return False
    
    def _record_violation(self, violation: SandboxViolation):
        """Записывает нарушение sandbox"""
        self.violations.append(violation)
        
        # Добавляем в информацию о sandbox
        if violation.module_name in self.active_sandboxes:
            self.active_sandboxes[violation.module_name]["violations"].append(violation.__dict__)
        
        logger.warning(f"[Security] Нарушение sandbox: {violation.module_name} - {violation.violation_type} ({violation.severity})")
    
    def get_module_permissions(self, module_name: str) -> Optional[ModulePermissions]:
        """Возвращает разрешения модуля"""
        if module_name not in self.active_sandboxes:
            return None
        
        sandbox_info = self.active_sandboxes[module_name]
        return ModulePermissions(**sandbox_info["permissions"])
    
    def update_security_level(self, module_name: str, new_level: SecurityLevel) -> bool:
        """Обновляет уровень безопасности модуля"""
        try:
            if module_name not in self.active_sandboxes:
                logger.error(f"[Security] Sandbox для модуля {module_name} не найден")
                return False
            
            # Обновляем разрешения
            new_permissions = self.security_levels[new_level]
            self.active_sandboxes[module_name]["security_level"] = new_level.value
            self.active_sandboxes[module_name]["permissions"] = new_permissions.__dict__
            
            logger.info(f"[Security] Обновлен уровень безопасности модуля {module_name} на {new_level.value}")
            return True
            
        except Exception as e:
            logger.error(f"[Security] Ошибка обновления уровня безопасности модуля {module_name}: {e}")
            return False
    
    def destroy_sandbox(self, module_name: str) -> bool:
        """Уничтожает sandbox модуля"""
        try:
            if module_name not in self.active_sandboxes:
                return True
            
            # Удаляем директорию sandbox
            sandbox_info = self.active_sandboxes[module_name]
            sandbox_dir = Path(sandbox_info["sandbox_dir"])
            
            if sandbox_dir.exists():
                shutil.rmtree(sandbox_dir)
            
            # Удаляем из активных sandbox'ов
            del self.active_sandboxes[module_name]
            
            logger.info(f"[Security] Уничтожен sandbox модуля {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"[Security] Ошибка уничтожения sandbox модуля {module_name}: {e}")
            return False
    
    def get_violations(self, module_name: Optional[str] = None) -> List[SandboxViolation]:
        """Возвращает список нарушений"""
        if module_name:
            return [v for v in self.violations if v.module_name == module_name]
        return self.violations.copy()
    
    def get_sandbox_status(self, module_name: str) -> Optional[Dict]:
        """Возвращает статус sandbox модуля"""
        return self.active_sandboxes.get(module_name)
    
    def list_active_sandboxes(self) -> Dict[str, Dict]:
        """Возвращает список активных sandbox'ов"""
        return self.active_sandboxes.copy()
