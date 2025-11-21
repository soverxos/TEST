# core/security/reputation_system.py
"""
Система репутации модулей и разработчиков
Оценивает надежность и безопасность модулей
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from datetime import datetime, timedelta

class ReputationLevel(Enum):
    """Уровни репутации"""
    UNTRUSTED = "untrusted"    # 0-20
    SUSPICIOUS = "suspicious"  # 21-40
    NEUTRAL = "neutral"        # 41-60
    TRUSTED = "trusted"        # 61-80
    VERIFIED = "verified"      # 81-100

class ReputationFactor(Enum):
    """Факторы репутации"""
    SIGNATURE_VALID = "signature_valid"
    CODE_QUALITY = "code_quality"
    SECURITY_SCAN = "security_scan"
    USER_FEEDBACK = "user_feedback"
    TIME_ACTIVE = "time_active"
    VIOLATIONS = "violations"
    UPDATES_FREQUENCY = "updates_frequency"

@dataclass
class ReputationScore:
    """Оценка репутации"""
    module_name: str
    developer_id: str
    total_score: float
    level: ReputationLevel
    factors: Dict[ReputationFactor, float]
    last_updated: float
    confidence: float  # Уверенность в оценке (0-1)

@dataclass
class DeveloperProfile:
    """Профиль разработчика"""
    developer_id: str
    name: str
    email: Optional[str]
    reputation_score: float
    reputation_level: ReputationLevel
    modules_count: int
    total_downloads: int
    verified: bool
    join_date: float
    last_activity: float

class ModuleReputationSystem:
    """Система репутации модулей"""
    
    def __init__(self, config):
        self.config = config
        self.reputation_dir = config.core.project_data_path / "Security" / "reputation"
        self.reputation_dir.mkdir(parents=True, exist_ok=True)
        
        # Веса факторов репутации
        self.factor_weights = {
            ReputationFactor.SIGNATURE_VALID: 0.25,
            ReputationFactor.CODE_QUALITY: 0.20,
            ReputationFactor.SECURITY_SCAN: 0.20,
            ReputationFactor.USER_FEEDBACK: 0.15,
            ReputationFactor.TIME_ACTIVE: 0.10,
            ReputationFactor.VIOLATIONS: -0.20,  # Отрицательный вес
            ReputationFactor.UPDATES_FREQUENCY: 0.10
        }
        
        # Кэш оценок репутации
        self.reputation_cache: Dict[str, ReputationScore] = {}
        
        # Профили разработчиков
        self.developer_profiles: Dict[str, DeveloperProfile] = {}
        
        # Загружаем существующие данные
        self._load_reputation_data()
        
        logger.info(f"[Security] ModuleReputationSystem инициализирован. Загружено {len(self.reputation_cache)} оценок репутации")
    
    def _load_reputation_data(self):
        """Загружает данные репутации из файлов"""
        try:
            # Загружаем оценки модулей
            modules_file = self.reputation_dir / "module_reputations.json"
            if modules_file.exists():
                with open(modules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for module_name, score_data in data.items():
                        self.reputation_cache[module_name] = ReputationScore(**score_data)
            
            # Загружаем профили разработчиков
            developers_file = self.reputation_dir / "developer_profiles.json"
            if developers_file.exists():
                with open(developers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for dev_id, profile_data in data.items():
                        self.developer_profiles[dev_id] = DeveloperProfile(**profile_data)
        
        except Exception as e:
            logger.error(f"[Security] Ошибка загрузки данных репутации: {e}")
    
    def _save_reputation_data(self):
        """Сохраняет данные репутации в файлы"""
        try:
            # Сохраняем оценки модулей
            modules_file = self.reputation_dir / "module_reputations.json"
            modules_data = {}
            for module_name, score in self.reputation_cache.items():
                modules_data[module_name] = {
                    "module_name": score.module_name,
                    "developer_id": score.developer_id,
                    "total_score": score.total_score,
                    "level": score.level.value,
                    "factors": {factor.value: value for factor, value in score.factors.items()},
                    "last_updated": score.last_updated,
                    "confidence": score.confidence
                }
            
            with open(modules_file, 'w', encoding='utf-8') as f:
                json.dump(modules_data, f, indent=2, ensure_ascii=False)
            
            # Сохраняем профили разработчиков
            developers_file = self.reputation_dir / "developer_profiles.json"
            developers_data = {}
            for dev_id, profile in self.developer_profiles.items():
                developers_data[dev_id] = {
                    "developer_id": profile.developer_id,
                    "name": profile.name,
                    "email": profile.email,
                    "reputation_score": profile.reputation_score,
                    "reputation_level": profile.reputation_level.value,
                    "modules_count": profile.modules_count,
                    "total_downloads": profile.total_downloads,
                    "verified": profile.verified,
                    "join_date": profile.join_date,
                    "last_activity": profile.last_activity
                }
            
            with open(developers_file, 'w', encoding='utf-8') as f:
                json.dump(developers_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"[Security] Ошибка сохранения данных репутации: {e}")
    
    def calculate_reputation_score(self, module_name: str, developer_id: str, 
                                 signature_valid: bool = False,
                                 code_quality_score: float = 0.5,
                                 security_scan_score: float = 0.5,
                                 user_feedback_score: float = 0.5,
                                 time_active_days: int = 0,
                                 violations_count: int = 0,
                                 updates_count: int = 0) -> ReputationScore:
        """Вычисляет оценку репутации модуля"""
        
        factors = {}
        
        # Подпись модуля
        factors[ReputationFactor.SIGNATURE_VALID] = 1.0 if signature_valid else 0.0
        
        # Качество кода
        factors[ReputationFactor.CODE_QUALITY] = max(0.0, min(1.0, code_quality_score))
        
        # Результат сканирования безопасности
        factors[ReputationFactor.SECURITY_SCAN] = max(0.0, min(1.0, security_scan_score))
        
        # Отзывы пользователей
        factors[ReputationFactor.USER_FEEDBACK] = max(0.0, min(1.0, user_feedback_score))
        
        # Время активности (нормализованное)
        factors[ReputationFactor.TIME_ACTIVE] = min(1.0, time_active_days / 365.0)  # Максимум за год
        
        # Нарушения (отрицательный фактор)
        factors[ReputationFactor.VIOLATIONS] = max(0.0, 1.0 - (violations_count * 0.1))
        
        # Частота обновлений
        factors[ReputationFactor.UPDATES_FREQUENCY] = min(1.0, updates_count / 12.0)  # Максимум 12 обновлений в год
        
        # Вычисляем общий балл
        total_score = 0.0
        total_weight = 0.0
        
        for factor, weight in self.factor_weights.items():
            if factor in factors:
                total_score += factors[factor] * abs(weight)
                total_weight += abs(weight)
        
        if total_weight > 0:
            total_score = (total_score / total_weight) * 100  # Нормализуем до 0-100
        
        # Определяем уровень репутации
        if total_score >= 81:
            level = ReputationLevel.VERIFIED
        elif total_score >= 61:
            level = ReputationLevel.TRUSTED
        elif total_score >= 41:
            level = ReputationLevel.NEUTRAL
        elif total_score >= 21:
            level = ReputationLevel.SUSPICIOUS
        else:
            level = ReputationLevel.UNTRUSTED
        
        # Вычисляем уверенность в оценке
        confidence = min(1.0, (time_active_days / 30.0) + 0.1)  # Больше времени = больше уверенности
        
        score = ReputationScore(
            module_name=module_name,
            developer_id=developer_id,
            total_score=total_score,
            level=level,
            factors=factors,
            last_updated=time.time(),
            confidence=confidence
        )
        
        # Сохраняем в кэш
        self.reputation_cache[module_name] = score
        
        logger.debug(f"[Security] Вычислена репутация модуля {module_name}: {total_score:.1f} ({level.value})")
        return score
    
    def get_module_reputation(self, module_name: str) -> Optional[ReputationScore]:
        """Возвращает репутацию модуля"""
        return self.reputation_cache.get(module_name)
    
    def update_module_reputation(self, module_name: str, **kwargs) -> ReputationScore:
        """Обновляет репутацию модуля"""
        current_score = self.reputation_cache.get(module_name)
        
        if current_score:
            # Обновляем существующую оценку
            developer_id = current_score.developer_id
        else:
            # Создаем новую оценку
            developer_id = kwargs.get("developer_id", "unknown")
        
        new_score = self.calculate_reputation_score(module_name, developer_id, **kwargs)
        
        # Сохраняем данные
        self._save_reputation_data()
        
        return new_score
    
    def register_developer(self, developer_id: str, name: str, email: Optional[str] = None) -> DeveloperProfile:
        """Регистрирует нового разработчика"""
        profile = DeveloperProfile(
            developer_id=developer_id,
            name=name,
            email=email,
            reputation_score=50.0,  # Начальная репутация
            reputation_level=ReputationLevel.NEUTRAL,
            modules_count=0,
            total_downloads=0,
            verified=False,
            join_date=time.time(),
            last_activity=time.time()
        )
        
        self.developer_profiles[developer_id] = profile
        self._save_reputation_data()
        
        logger.info(f"[Security] Зарегистрирован новый разработчик: {developer_id}")
        return profile
    
    def get_developer_profile(self, developer_id: str) -> Optional[DeveloperProfile]:
        """Возвращает профиль разработчика"""
        return self.developer_profiles.get(developer_id)
    
    def update_developer_activity(self, developer_id: str):
        """Обновляет активность разработчика"""
        if developer_id in self.developer_profiles:
            self.developer_profiles[developer_id].last_activity = time.time()
            self._save_reputation_data()
    
    def get_reputation_statistics(self) -> Dict[str, any]:
        """Возвращает статистику репутации"""
        stats = {
            "total_modules": len(self.reputation_cache),
            "total_developers": len(self.developer_profiles),
            "reputation_distribution": {},
            "average_reputation": 0.0,
            "verified_modules": 0,
            "untrusted_modules": 0
        }
        
        if self.reputation_cache:
            total_score = 0.0
            
            for score in self.reputation_cache.values():
                level = score.level.value
                stats["reputation_distribution"][level] = stats["reputation_distribution"].get(level, 0) + 1
                
                total_score += score.total_score
                
                if score.level == ReputationLevel.VERIFIED:
                    stats["verified_modules"] += 1
                elif score.level == ReputationLevel.UNTRUSTED:
                    stats["untrusted_modules"] += 1
            
            stats["average_reputation"] = total_score / len(self.reputation_cache)
        
        return stats
    
    def get_top_modules(self, limit: int = 10) -> List[Tuple[str, ReputationScore]]:
        """Возвращает топ модулей по репутации"""
        sorted_modules = sorted(
            self.reputation_cache.items(),
            key=lambda x: x[1].total_score,
            reverse=True
        )
        
        return sorted_modules[:limit]
    
    def get_suspicious_modules(self) -> List[Tuple[str, ReputationScore]]:
        """Возвращает подозрительные модули"""
        suspicious = []
        
        for module_name, score in self.reputation_cache.items():
            if score.level in [ReputationLevel.SUSPICIOUS, ReputationLevel.UNTRUSTED]:
                suspicious.append((module_name, score))
        
        return sorted(suspicious, key=lambda x: x[1].total_score)
