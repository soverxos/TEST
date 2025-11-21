# core/security/audit_logger.py
"""
Система аудит-логов безопасности
Записывает все действия модулей для мониторинга и анализа
"""

import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger
from datetime import datetime

class AuditEventType(Enum):
    """Типы событий аудита"""
    MODULE_LOAD = "module_load"
    MODULE_UNLOAD = "module_unload"
    COMMAND_EXECUTION = "command_execution"
    DATABASE_ACCESS = "database_access"
    FILE_ACCESS = "file_access"
    NETWORK_REQUEST = "network_request"
    SYSTEM_COMMAND = "system_command"
    USER_DATA_MODIFICATION = "user_data_modification"
    ADMIN_FUNCTION_ACCESS = "admin_function_access"
    SECURITY_VIOLATION = "security_violation"
    PERMISSION_CHECK = "permission_check"

class AuditSeverity(Enum):
    """Уровни серьезности событий"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Событие аудита"""
    event_id: str
    event_type: AuditEventType
    module_name: str
    user_id: Optional[int]
    timestamp: float
    severity: AuditSeverity
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class SecurityAuditLogger:
    """Логгер аудита безопасности"""
    
    def __init__(self, config):
        self.config = config
        self.audit_dir = config.core.project_data_path / "Security" / "audit_logs"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Буфер событий для батчевой записи
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 100
        self.buffer_timeout = 30  # секунд
        
        # Статистика событий
        self.event_stats = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_severity": {},
            "events_by_module": {},
            "violations_count": 0
        }
        
        logger.info(f"[Security] SecurityAuditLogger инициализирован. Директория аудита: {self.audit_dir}")
    
    def log_event(self, 
                  event_type: AuditEventType,
                  module_name: str,
                  details: Dict[str, Any],
                  user_id: Optional[int] = None,
                  severity: AuditSeverity = AuditSeverity.MEDIUM,
                  success: bool = True,
                  error_message: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None) -> str:
        """Записывает событие аудита"""
        
        event_id = self._generate_event_id()
        timestamp = time.time()
        
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            module_name=module_name,
            user_id=user_id,
            timestamp=timestamp,
            severity=severity,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        # Добавляем в буфер
        self.event_buffer.append(event)
        
        # Обновляем статистику
        self._update_stats(event)
        
        # Проверяем, нужно ли записать буфер
        if len(self.event_buffer) >= self.buffer_size:
            self._flush_buffer()
        
        logger.debug(f"[Security] Записано событие аудита: {event_type.value} от модуля {module_name}")
        return event_id
    
    def _generate_event_id(self) -> str:
        """Генерирует уникальный ID события"""
        timestamp = int(time.time() * 1000)
        return f"AUDIT_{timestamp}_{len(self.event_buffer)}"
    
    def _update_stats(self, event: AuditEvent):
        """Обновляет статистику событий"""
        self.event_stats["total_events"] += 1
        
        # По типам событий
        event_type = event.event_type.value
        self.event_stats["events_by_type"][event_type] = self.event_stats["events_by_type"].get(event_type, 0) + 1
        
        # По уровням серьезности
        severity = event.severity.value
        self.event_stats["events_by_severity"][severity] = self.event_stats["events_by_severity"].get(severity, 0) + 1
        
        # По модулям
        module_name = event.module_name
        self.event_stats["events_by_module"][module_name] = self.event_stats["events_by_module"].get(module_name, 0) + 1
        
        # Нарушения
        if event.event_type == AuditEventType.SECURITY_VIOLATION:
            self.event_stats["violations_count"] += 1
    
    def _flush_buffer(self):
        """Записывает буфер событий в файл"""
        if not self.event_buffer:
            return
        
        try:
            # Создаем файл для текущего дня
            today = datetime.now().strftime("%Y-%m-%d")
            audit_file = self.audit_dir / f"audit_{today}.jsonl"
            
            # Записываем события в формате JSONL
            with open(audit_file, 'a', encoding='utf-8') as f:
                for event in self.event_buffer:
                    event_dict = asdict(event)
                    # Конвертируем enum в строки
                    event_dict["event_type"] = event.event_type.value
                    event_dict["severity"] = event.severity.value
                    f.write(json.dumps(event_dict, ensure_ascii=False) + '\n')
            
            logger.debug(f"[Security] Записано {len(self.event_buffer)} событий аудита в {audit_file}")
            
            # Очищаем буфер
            self.event_buffer.clear()
            
        except Exception as e:
            logger.error(f"[Security] Ошибка записи буфера аудита: {e}")
    
    def log_module_load(self, module_name: str, module_path: str, signature_valid: bool, signer_id: Optional[str] = None):
        """Записывает загрузку модуля"""
        details = {
            "module_path": module_path,
            "signature_valid": signature_valid,
            "signer_id": signer_id
        }
        
        severity = AuditSeverity.HIGH if not signature_valid else AuditSeverity.MEDIUM
        
        return self.log_event(
            event_type=AuditEventType.MODULE_LOAD,
            module_name=module_name,
            details=details,
            severity=severity,
            success=signature_valid
        )
    
    def log_command_execution(self, module_name: str, command: str, user_id: int, success: bool = True, error_message: Optional[str] = None):
        """Записывает выполнение команды"""
        details = {
            "command": command,
            "user_id": user_id
        }
        
        return self.log_event(
            event_type=AuditEventType.COMMAND_EXECUTION,
            module_name=module_name,
            details=details,
            user_id=user_id,
            severity=AuditSeverity.MEDIUM,
            success=success,
            error_message=error_message
        )
    
    def log_database_access(self, module_name: str, operation: str, table: str, user_id: Optional[int] = None, success: bool = True):
        """Записывает доступ к базе данных"""
        details = {
            "operation": operation,
            "table": table
        }
        
        return self.log_event(
            event_type=AuditEventType.DATABASE_ACCESS,
            module_name=module_name,
            details=details,
            user_id=user_id,
            severity=AuditSeverity.MEDIUM,
            success=success
        )
    
    def log_security_violation(self, module_name: str, violation_type: str, details: Dict[str, Any], user_id: Optional[int] = None):
        """Записывает нарушение безопасности"""
        return self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            module_name=module_name,
            details={
                "violation_type": violation_type,
                **details
            },
            user_id=user_id,
            severity=AuditSeverity.HIGH,
            success=False
        )
    
    def get_events(self, 
                   module_name: Optional[str] = None,
                   event_type: Optional[AuditEventType] = None,
                   severity: Optional[AuditSeverity] = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   limit: int = 1000) -> List[AuditEvent]:
        """Возвращает события аудита с фильтрацией"""
        
        # Сначала записываем буфер
        self._flush_buffer()
        
        events = []
        
        try:
            # Получаем список файлов аудита
            audit_files = sorted(self.audit_dir.glob("audit_*.jsonl"), reverse=True)
            
            for audit_file in audit_files:
                if len(events) >= limit:
                    break
                
                with open(audit_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if len(events) >= limit:
                            break
                        
                        try:
                            event_data = json.loads(line.strip())
                            
                            # Применяем фильтры
                            if module_name and event_data.get("module_name") != module_name:
                                continue
                            
                            if event_type and event_data.get("event_type") != event_type.value:
                                continue
                            
                            if severity and event_data.get("severity") != severity.value:
                                continue
                            
                            if start_time and event_data.get("timestamp", 0) < start_time:
                                continue
                            
                            if end_time and event_data.get("timestamp", 0) > end_time:
                                continue
                            
                            # Создаем объект события
                            event = AuditEvent(
                                event_id=event_data["event_id"],
                                event_type=AuditEventType(event_data["event_type"]),
                                module_name=event_data["module_name"],
                                user_id=event_data.get("user_id"),
                                timestamp=event_data["timestamp"],
                                severity=AuditSeverity(event_data["severity"]),
                                details=event_data["details"],
                                ip_address=event_data.get("ip_address"),
                                user_agent=event_data.get("user_agent"),
                                success=event_data.get("success", True),
                                error_message=event_data.get("error_message")
                            )
                            
                            events.append(event)
                            
                        except Exception as e:
                            logger.error(f"[Security] Ошибка парсинга события аудита: {e}")
                            continue
        
        except Exception as e:
            logger.error(f"[Security] Ошибка получения событий аудита: {e}")
        
        return events
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику событий аудита"""
        # Записываем буфер перед получением статистики
        self._flush_buffer()
        
        return self.event_stats.copy()
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Очищает старые логи аудита"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            for audit_file in self.audit_dir.glob("audit_*.jsonl"):
                if audit_file.stat().st_mtime < cutoff_time:
                    audit_file.unlink()
                    logger.info(f"[Security] Удален старый файл аудита: {audit_file}")
        
        except Exception as e:
            logger.error(f"[Security] Ошибка очистки старых логов аудита: {e}")
    
    def force_flush(self):
        """Принудительно записывает буфер"""
        self._flush_buffer()
