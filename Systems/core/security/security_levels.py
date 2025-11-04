# core/security/security_levels.py
"""
Система уровней безопасности для пользователей
Позволяет настраивать различные уровни защиты
"""

import json
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from loguru import logger

class SecurityLevel(Enum):
    """Уровни безопасности"""
    PARANOID = "paranoid"      # Максимальная защита
    STRICT = "strict"         # Строгая защита
    MODERATE = "moderate"     # Умеренная защита
    PERMISSIVE = "permissive" # Минимальная защита (только для разработки)

class SecurityPolicy(Enum):
    """Политики безопасности"""
    ALLOW_SIGNED_ONLY = "allow_signed_only"           # Только подписанные модули
    REQUIRE_REPUTATION = "require_reputation"          # Требовать минимальную репутацию
    SANDBOX_ALL_MODULES = "sandbox_all_modules"        # Все модули в sandbox
    AUDIT_ALL_ACTIONS = "audit_all_actions"           # Аудит всех действий
    BLOCK_SUSPICIOUS = "block_suspicious"             # Блокировать подозрительные модули
    REQUIRE_APPROVAL = "require_approval"             # Требовать одобрение администратора

@dataclass
class SecurityConfiguration:
    """Конфигурация безопасности"""
    level: SecurityLevel
    policies: Set[SecurityPolicy]
    min_reputation_score: float
    allowed_developers: Set[str]
    blocked_modules: Set[str]
    trusted_signers: Set[str]
    max_risk_score: float
    auto_approve_verified: bool

class SecurityLevelManager:
    """Менеджер уровней безопасности"""
    
    def __init__(self, config):
        self.config = config
        self.security_dir = config.core.project_data_path / "Security" / "levels"
        self.security_dir.mkdir(parents=True, exist_ok=True)
        
        # Предустановленные конфигурации безопасности
        self.default_configurations = {
            SecurityLevel.PARANOID: SecurityConfiguration(
                level=SecurityLevel.PARANOID,
                policies={
                    SecurityPolicy.ALLOW_SIGNED_ONLY,
                    SecurityPolicy.REQUIRE_REPUTATION,
                    SecurityPolicy.SANDBOX_ALL_MODULES,
                    SecurityPolicy.AUDIT_ALL_ACTIONS,
                    SecurityPolicy.BLOCK_SUSPICIOUS,
                    SecurityPolicy.REQUIRE_APPROVAL
                },
                min_reputation_score=80.0,
                allowed_developers=set(),
                blocked_modules=set(),
                trusted_signers={"sdb_core_team"},
                max_risk_score=10.0,
                auto_approve_verified=False
            ),
            
            SecurityLevel.STRICT: SecurityConfiguration(
                level=SecurityLevel.STRICT,
                policies={
                    SecurityPolicy.ALLOW_SIGNED_ONLY,
                    SecurityPolicy.REQUIRE_REPUTATION,
                    SecurityPolicy.SANDBOX_ALL_MODULES,
                    SecurityPolicy.AUDIT_ALL_ACTIONS,
                    SecurityPolicy.BLOCK_SUSPICIOUS
                },
                min_reputation_score=60.0,
                allowed_developers=set(),
                blocked_modules=set(),
                trusted_signers={"sdb_core_team"},
                max_risk_score=30.0,
                auto_approve_verified=True
            ),
            
            SecurityLevel.MODERATE: SecurityConfiguration(
                level=SecurityLevel.MODERATE,
                policies={
                    SecurityPolicy.REQUIRE_REPUTATION,
                    SecurityPolicy.SANDBOX_ALL_MODULES,
                    SecurityPolicy.AUDIT_ALL_ACTIONS
                },
                min_reputation_score=40.0,
                allowed_developers=set(),
                blocked_modules=set(),
                trusted_signers={"sdb_core_team"},
                max_risk_score=50.0,
                auto_approve_verified=True
            ),
            
            SecurityLevel.PERMISSIVE: SecurityConfiguration(
                level=SecurityLevel.PERMISSIVE,
                policies={
                    SecurityPolicy.AUDIT_ALL_ACTIONS
                },
                min_reputation_score=0.0,
                allowed_developers=set(),
                blocked_modules=set(),
                trusted_signers=set(),
                max_risk_score=100.0,
                auto_approve_verified=True
            )
        }
        
        # Текущая конфигурация безопасности
        self.current_config = self._load_security_configuration()
        
        logger.info(f"[Security] SecurityLevelManager инициализирован с уровнем {self.current_config.level.value}")
    
    def _load_security_configuration(self) -> SecurityConfiguration:
        """Загружает конфигурацию безопасности"""
        config_file = self.security_dir / "security_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return SecurityConfiguration(
                    level=SecurityLevel(data["level"]),
                    policies={SecurityPolicy(policy) for policy in data["policies"]},
                    min_reputation_score=data["min_reputation_score"],
                    allowed_developers=set(data["allowed_developers"]),
                    blocked_modules=set(data["blocked_modules"]),
                    trusted_signers=set(data["trusted_signers"]),
                    max_risk_score=data["max_risk_score"],
                    auto_approve_verified=data["auto_approve_verified"]
                )
            except Exception as e:
                logger.error(f"[Security] Ошибка загрузки конфигурации безопасности: {e}")
        
        # Возвращаем конфигурацию по умолчанию
        return self.default_configurations[SecurityLevel.MODERATE]
    
    def _save_security_configuration(self):
        """Сохраняет конфигурацию безопасности"""
        config_file = self.security_dir / "security_config.json"
        
        try:
            data = {
                "level": self.current_config.level.value,
                "policies": [policy.value for policy in self.current_config.policies],
                "min_reputation_score": self.current_config.min_reputation_score,
                "allowed_developers": list(self.current_config.allowed_developers),
                "blocked_modules": list(self.current_config.blocked_modules),
                "trusted_signers": list(self.current_config.trusted_signers),
                "max_risk_score": self.current_config.max_risk_score,
                "auto_approve_verified": self.current_config.auto_approve_verified
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"[Security] Ошибка сохранения конфигурации безопасности: {e}")
    
    def set_security_level(self, level: SecurityLevel) -> bool:
        """Устанавливает уровень безопасности"""
        try:
            self.current_config = self.default_configurations[level].__class__(
                level=level,
                policies=self.default_configurations[level].policies.copy(),
                min_reputation_score=self.default_configurations[level].min_reputation_score,
                allowed_developers=self.default_configurations[level].allowed_developers.copy(),
                blocked_modules=self.default_configurations[level].blocked_modules.copy(),
                trusted_signers=self.default_configurations[level].trusted_signers.copy(),
                max_risk_score=self.default_configurations[level].max_risk_score,
                auto_approve_verified=self.default_configurations[level].auto_approve_verified
            )
            
            self._save_security_configuration()
            logger.info(f"[Security] Установлен уровень безопасности: {level.value}")
            return True
            
        except Exception as e:
            logger.error(f"[Security] Ошибка установки уровня безопасности {level.value}: {e}")
            return False
    
    def get_current_configuration(self) -> SecurityConfiguration:
        """Возвращает текущую конфигурацию безопасности"""
        return self.current_config
    
    def add_policy(self, policy: SecurityPolicy) -> bool:
        """Добавляет политику безопасности"""
        try:
            self.current_config.policies.add(policy)
            self._save_security_configuration()
            logger.info(f"[Security] Добавлена политика безопасности: {policy.value}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка добавления политики {policy.value}: {e}")
            return False
    
    def remove_policy(self, policy: SecurityPolicy) -> bool:
        """Удаляет политику безопасности"""
        try:
            self.current_config.policies.discard(policy)
            self._save_security_configuration()
            logger.info(f"[Security] Удалена политика безопасности: {policy.value}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка удаления политики {policy.value}: {e}")
            return False
    
    def add_trusted_signer(self, signer_id: str) -> bool:
        """Добавляет доверенного подписанта"""
        try:
            self.current_config.trusted_signers.add(signer_id)
            self._save_security_configuration()
            logger.info(f"[Security] Добавлен доверенный подписант: {signer_id}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка добавления доверенного подписанта {signer_id}: {e}")
            return False
    
    def remove_trusted_signer(self, signer_id: str) -> bool:
        """Удаляет доверенного подписанта"""
        try:
            self.current_config.trusted_signers.discard(signer_id)
            self._save_security_configuration()
            logger.info(f"[Security] Удален доверенный подписант: {signer_id}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка удаления доверенного подписанта {signer_id}: {e}")
            return False
    
    def block_module(self, module_name: str) -> bool:
        """Блокирует модуль"""
        try:
            self.current_config.blocked_modules.add(module_name)
            self._save_security_configuration()
            logger.info(f"[Security] Заблокирован модуль: {module_name}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка блокировки модуля {module_name}: {e}")
            return False
    
    def unblock_module(self, module_name: str) -> bool:
        """Разблокирует модуль"""
        try:
            self.current_config.blocked_modules.discard(module_name)
            self._save_security_configuration()
            logger.info(f"[Security] Разблокирован модуль: {module_name}")
            return True
        except Exception as e:
            logger.error(f"[Security] Ошибка разблокировки модуля {module_name}: {e}")
            return False
    
    def is_module_allowed(self, module_name: str, 
                         signature_valid: bool = False,
                         reputation_score: float = 0.0,
                         risk_score: float = 0.0,
                         developer_id: str = "unknown") -> Tuple[bool, str]:
        """Проверяет, разрешен ли модуль для загрузки"""
        
        # Проверяем блокировку
        if module_name in self.current_config.blocked_modules:
            return False, f"Модуль {module_name} заблокирован администратором"
        
        # Проверяем политику подписанных модулей
        if SecurityPolicy.ALLOW_SIGNED_ONLY in self.current_config.policies:
            if not signature_valid:
                return False, f"Модуль {module_name} не подписан, требуется подпись"
        
        # Проверяем политику репутации
        if SecurityPolicy.REQUIRE_REPUTATION in self.current_config.policies:
            if reputation_score < self.current_config.min_reputation_score:
                return False, f"Репутация модуля {module_name} слишком низкая ({reputation_score:.1f} < {self.current_config.min_reputation_score})"
        
        # Проверяем политику блокировки подозрительных
        if SecurityPolicy.BLOCK_SUSPICIOUS in self.current_config.policies:
            if risk_score > self.current_config.max_risk_score:
                return False, f"Риск модуля {module_name} слишком высокий ({risk_score:.1f} > {self.current_config.max_risk_score})"
        
        # Проверяем доверенных разработчиков
        if self.current_config.allowed_developers and developer_id not in self.current_config.allowed_developers:
            return False, f"Разработчик {developer_id} не в списке разрешенных"
        
        return True, "Модуль разрешен для загрузки"
    
    def get_security_summary(self) -> Dict[str, any]:
        """Возвращает сводку по безопасности"""
        return {
            "current_level": self.current_config.level.value,
            "active_policies": [policy.value for policy in self.current_config.policies],
            "min_reputation_score": self.current_config.min_reputation_score,
            "max_risk_score": self.current_config.max_risk_score,
            "trusted_signers_count": len(self.current_config.trusted_signers),
            "blocked_modules_count": len(self.current_config.blocked_modules),
            "allowed_developers_count": len(self.current_config.allowed_developers),
            "auto_approve_verified": self.current_config.auto_approve_verified
        }
