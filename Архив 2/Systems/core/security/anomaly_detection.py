# core/security/anomaly_detection.py
"""
Система детекции аномального поведения модулей
Мониторит активность и выявляет подозрительные паттерны
"""

import time
import json
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
from loguru import logger
from datetime import datetime, timedelta

class AnomalyType(Enum):
    """Типы аномалий"""
    FREQUENT_COMMANDS = "frequent_commands"           # Слишком частые команды
    UNUSUAL_PATTERNS = "unusual_patterns"            # Необычные паттерны использования
    SUSPICIOUS_TIMING = "suspicious_timing"          # Подозрительное время активности
    RESOURCE_ABUSE = "resource_abuse"                # Злоупотребление ресурсами
    DATA_EXFILTRATION = "data_exfiltration"          # Подозрение на утечку данных
    PRIVILEGE_ESCALATION = "privilege_escalation"    # Попытки повышения привилегий
    NETWORK_ANOMALY = "network_anomaly"              # Аномальная сетевая активность
    FILE_ACCESS_ANOMALY = "file_access_anomaly"      # Аномальный доступ к файлам

class AnomalySeverity(Enum):
    """Уровни серьезности аномалий"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AnomalyDetection:
    """Обнаруженная аномалия"""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    module_name: str
    user_id: Optional[int]
    timestamp: float
    description: str
    evidence: Dict[str, any]
    confidence: float  # Уверенность в обнаружении (0-1)
    auto_blocked: bool = False

@dataclass
class BehaviorPattern:
    """Паттерн поведения"""
    module_name: str
    user_id: Optional[int]
    pattern_type: str
    frequency: int
    time_window: int  # секунды
    last_seen: float

class AnomalyDetector:
    """Детектор аномального поведения"""
    
    def __init__(self, config):
        self.config = config
        self.anomaly_dir = config.core.project_data_path / "Security" / "anomaly_detection"
        self.anomaly_dir.mkdir(parents=True, exist_ok=True)
        
        # Пороги для детекции аномалий
        self.thresholds = {
            "max_commands_per_minute": 30,
            "max_commands_per_hour": 500,
            "max_file_access_per_minute": 20,
            "max_network_requests_per_minute": 10,
            "max_database_queries_per_minute": 100,
            "suspicious_hours": [0, 1, 2, 3, 4, 5],  # Ночные часы
            "unusual_pattern_threshold": 0.7
        }
        
        # История активности модулей
        self.activity_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Паттерны поведения
        self.behavior_patterns: Dict[str, List[BehaviorPattern]] = defaultdict(list)
        
        # Обнаруженные аномалии
        self.detected_anomalies: List[AnomalyDetection] = []
        
        # Статистика
        self.stats = {
            "total_anomalies": 0,
            "anomalies_by_type": defaultdict(int),
            "anomalies_by_severity": defaultdict(int),
            "auto_blocked_modules": set()
        }
        
        logger.info(f"[Security] AnomalyDetector инициализирован с {len(self.thresholds)} порогами")
    
    def analyze_activity(self, 
                        module_name: str,
                        activity_type: str,
                        user_id: Optional[int] = None,
                        details: Optional[Dict] = None) -> List[AnomalyDetection]:
        """Анализирует активность модуля на предмет аномалий"""
        
        timestamp = time.time()
        activity_key = f"{module_name}:{user_id or 'system'}"
        
        # Записываем активность
        activity_record = {
            "timestamp": timestamp,
            "activity_type": activity_type,
            "module_name": module_name,
            "user_id": user_id,
            "details": details or {}
        }
        
        self.activity_history[activity_key].append(activity_record)
        
        # Анализируем на аномалии
        anomalies = []
        
        # Проверяем частоту команд
        command_anomalies = self._detect_frequent_commands(activity_key, timestamp)
        anomalies.extend(command_anomalies)
        
        # Проверяем подозрительное время
        timing_anomalies = self._detect_suspicious_timing(activity_key, timestamp)
        anomalies.extend(timing_anomalies)
        
        # Проверяем необычные паттерны
        pattern_anomalies = self._detect_unusual_patterns(activity_key, activity_record)
        anomalies.extend(pattern_anomalies)
        
        # Проверяем злоупотребление ресурсами
        resource_anomalies = self._detect_resource_abuse(activity_key, activity_record)
        anomalies.extend(resource_anomalies)
        
        # Обновляем статистику
        for anomaly in anomalies:
            self._update_stats(anomaly)
        
        return anomalies
    
    def _detect_frequent_commands(self, activity_key: str, timestamp: float) -> List[AnomalyDetection]:
        """Детектирует слишком частые команды"""
        anomalies = []
        
        # Анализируем последние записи
        recent_activities = [
            activity for activity in self.activity_history[activity_key]
            if timestamp - activity["timestamp"] <= 60  # Последняя минута
        ]
        
        command_count = len([a for a in recent_activities if a["activity_type"] == "command"])
        
        if command_count > self.thresholds["max_commands_per_minute"]:
            anomaly = AnomalyDetection(
                anomaly_id=f"freq_cmd_{int(timestamp)}",
                anomaly_type=AnomalyType.FREQUENT_COMMANDS,
                severity=AnomalySeverity.HIGH,
                module_name=activity_key.split(":")[0],
                user_id=int(activity_key.split(":")[1]) if activity_key.split(":")[1] != "system" else None,
                timestamp=timestamp,
                description=f"Слишком частые команды: {command_count} за минуту",
                evidence={
                    "command_count": command_count,
                    "threshold": self.thresholds["max_commands_per_minute"],
                    "time_window": "1 minute"
                },
                confidence=min(1.0, command_count / self.thresholds["max_commands_per_minute"])
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_suspicious_timing(self, activity_key: str, timestamp: float) -> List[AnomalyDetection]:
        """Детектирует подозрительное время активности"""
        anomalies = []
        
        current_hour = datetime.fromtimestamp(timestamp).hour
        
        if current_hour in self.thresholds["suspicious_hours"]:
            anomaly = AnomalyDetection(
                anomaly_id=f"susp_timing_{int(timestamp)}",
                anomaly_type=AnomalyType.SUSPICIOUS_TIMING,
                severity=AnomalySeverity.MEDIUM,
                module_name=activity_key.split(":")[0],
                user_id=int(activity_key.split(":")[1]) if activity_key.split(":")[1] != "system" else None,
                timestamp=timestamp,
                description=f"Активность в подозрительное время: {current_hour}:00",
                evidence={
                    "hour": current_hour,
                    "suspicious_hours": self.thresholds["suspicious_hours"]
                },
                confidence=0.6
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_unusual_patterns(self, activity_key: str, activity_record: Dict) -> List[AnomalyDetection]:
        """Детектирует необычные паттерны поведения"""
        anomalies = []
        
        module_name = activity_record["module_name"]
        activity_type = activity_record["activity_type"]
        
        # Анализируем историю активности модуля
        module_activities = [
            activity for activity in self.activity_history[activity_key]
            if activity["module_name"] == module_name
        ]
        
        # Подсчитываем частоту различных типов активности
        activity_counts = defaultdict(int)
        for activity in module_activities[-100:]:  # Последние 100 записей
            activity_counts[activity["activity_type"]] += 1
        
        total_activities = sum(activity_counts.values())
        if total_activities > 0:
            current_activity_ratio = activity_counts[activity_type] / total_activities
            
            # Если текущий тип активности встречается слишком редко
            if current_activity_ratio < 0.1 and total_activities > 10:
                anomaly = AnomalyDetection(
                    anomaly_id=f"unusual_pattern_{int(time.time())}",
                    anomaly_type=AnomalyType.UNUSUAL_PATTERNS,
                    severity=AnomalySeverity.MEDIUM,
                    module_name=module_name,
                    user_id=activity_record["user_id"],
                    timestamp=activity_record["timestamp"],
                    description=f"Необычный паттерн активности: {activity_type}",
                    evidence={
                        "activity_type": activity_type,
                        "ratio": current_activity_ratio,
                        "total_activities": total_activities,
                        "activity_counts": dict(activity_counts)
                    },
                    confidence=0.7
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_resource_abuse(self, activity_key: str, activity_record: Dict) -> List[AnomalyDetection]:
        """Детектирует злоупотребление ресурсами"""
        anomalies = []
        
        timestamp = activity_record["timestamp"]
        activity_type = activity_record["activity_type"]
        
        # Анализируем последние записи для подсчета ресурсов
        recent_activities = [
            activity for activity in self.activity_history[activity_key]
            if timestamp - activity["timestamp"] <= 60  # Последняя минута
        ]
        
        # Проверяем различные типы ресурсов
        resource_checks = {
            "file_access": ("file_access", self.thresholds["max_file_access_per_minute"]),
            "network_request": ("network_request", self.thresholds["max_network_requests_per_minute"]),
            "database_query": ("database_query", self.thresholds["max_database_queries_per_minute"])
        }
        
        for resource_type, (check_type, threshold) in resource_checks.items():
            count = len([a for a in recent_activities if a["activity_type"] == check_type])
            
            if count > threshold:
                anomaly = AnomalyDetection(
                    anomaly_id=f"resource_abuse_{resource_type}_{int(timestamp)}",
                    anomaly_type=AnomalyType.RESOURCE_ABUSE,
                    severity=AnomalySeverity.HIGH,
                    module_name=activity_key.split(":")[0],
                    user_id=int(activity_key.split(":")[1]) if activity_key.split(":")[1] != "system" else None,
                    timestamp=timestamp,
                    description=f"Злоупотребление ресурсами {resource_type}: {count} за минуту",
                    evidence={
                        "resource_type": resource_type,
                        "count": count,
                        "threshold": threshold,
                        "time_window": "1 minute"
                    },
                    confidence=min(1.0, count / threshold)
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _update_stats(self, anomaly: AnomalyDetection):
        """Обновляет статистику аномалий"""
        self.stats["total_anomalies"] += 1
        self.stats["anomalies_by_type"][anomaly.anomaly_type.value] += 1
        self.stats["anomalies_by_severity"][anomaly.severity.value] += 1
        
        if anomaly.auto_blocked:
            self.stats["auto_blocked_modules"].add(anomaly.module_name)
        
        self.detected_anomalies.append(anomaly)
    
    def should_block_module(self, module_name: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Определяет, нужно ли заблокировать модуль"""
        activity_key = f"{module_name}:{user_id or 'system'}"
        
        # Проверяем последние аномалии для этого модуля
        recent_anomalies = [
            anomaly for anomaly in self.detected_anomalies
            if anomaly.module_name == module_name and 
               time.time() - anomaly.timestamp <= 3600  # Последний час
        ]
        
        # Блокируем если есть критические аномалии
        critical_anomalies = [a for a in recent_anomalies if a.severity == AnomalySeverity.CRITICAL]
        if critical_anomalies:
            return True, f"Критические аномалии обнаружены: {len(critical_anomalies)}"
        
        # Блокируем если много высоких аномалий
        high_anomalies = [a for a in recent_anomalies if a.severity == AnomalySeverity.HIGH]
        if len(high_anomalies) >= 3:
            return True, f"Слишком много высоких аномалий: {len(high_anomalies)}"
        
        # Блокируем если модуль уже был заблокирован
        if module_name in self.stats["auto_blocked_modules"]:
            return True, "Модуль был автоматически заблокирован ранее"
        
        return False, "Модуль разрешен"
    
    def get_anomaly_statistics(self) -> Dict[str, any]:
        """Возвращает статистику аномалий"""
        return {
            "total_anomalies": self.stats["total_anomalies"],
            "anomalies_by_type": dict(self.stats["anomalies_by_type"]),
            "anomalies_by_severity": dict(self.stats["anomalies_by_severity"]),
            "auto_blocked_modules": list(self.stats["auto_blocked_modules"]),
            "active_modules": len(self.activity_history),
            "thresholds": self.thresholds
        }
    
    def get_recent_anomalies(self, hours: int = 24) -> List[AnomalyDetection]:
        """Возвращает недавние аномалии"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            anomaly for anomaly in self.detected_anomalies
            if anomaly.timestamp >= cutoff_time
        ]
    
    def clear_old_data(self, days_to_keep: int = 30):
        """Очищает старые данные"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        # Очищаем историю активности
        for activity_key in list(self.activity_history.keys()):
            activities = self.activity_history[activity_key]
            # Удаляем старые записи
            while activities and activities[0]["timestamp"] < cutoff_time:
                activities.popleft()
            
            # Удаляем пустые ключи
            if not activities:
                del self.activity_history[activity_key]
        
        # Очищаем старые аномалии
        self.detected_anomalies = [
            anomaly for anomaly in self.detected_anomalies
            if anomaly.timestamp >= cutoff_time
        ]
        
        logger.info(f"[Security] Очищены данные аномалий старше {days_to_keep} дней")
