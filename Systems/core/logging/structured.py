# core/logging/structured.py
"""
Структурированное логирование в JSON формате
"""

import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from loguru import logger


class StructuredLogger:
    """
    Структурированный логгер с JSON выводом
    """
    
    def __init__(self, json_output: bool = False, indent: Optional[int] = None):
        self.json_output = json_output
        self.indent = indent
        self._setup_logger()
    
    def _setup_logger(self):
        """Настройка логгера"""
        if self.json_output:
            # Удаляем стандартный handler
            logger.remove()
            
            # Добавляем JSON handler
            logger.add(
                sys.stdout,
                format=self._json_formatter,
                serialize=True,
                level="DEBUG"
            )
    
    def _json_formatter(self, record: Dict[str, Any]) -> str:
        """Форматирует запись лога в JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record.get("name", ""),
            "function": record.get("function", ""),
            "line": record.get("line", 0),
        }
        
        # Добавляем дополнительные поля
        if "extra" in record:
            log_data.update(record["extra"])
        
        # Добавляем exception info если есть
        if "exception" in record:
            log_data["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"] else None,
                "value": str(record["exception"].value) if record["exception"] else None,
                "traceback": record["exception"].traceback if record["exception"] else None
            }
        
        return json.dumps(log_data, indent=self.indent, ensure_ascii=False)
    
    def bind(self, **kwargs):
        """Привязывает дополнительные поля к логгеру"""
        return logger.bind(**kwargs)


def setup_structured_logging(
    json_output: bool = False,
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    level: str = "INFO"
):
    """
    Настраивает структурированное логирование
    
    Args:
        json_output: Использовать JSON формат
        log_file: Путь к файлу логов (опционально)
        rotation: Ротация логов
        retention: Хранение логов
        level: Уровень логирования
    """
    logger.remove()
    
    if json_output:
        # JSON формат для консоли
        logger.add(
            sys.stdout,
            format=lambda record: json.dumps({
                "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record.get("name", ""),
                "function": record.get("function", ""),
                "line": record.get("line", 0),
                **record.get("extra", {})
            }, ensure_ascii=False),
            serialize=True,
            level=level
        )
    else:
        # Стандартный формат
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level
        )
    
    # Файловый лог (всегда JSON для структурированности)
    if log_file:
        logger.add(
            log_file,
            format=lambda record: json.dumps({
                "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record.get("name", ""),
                "function": record.get("function", ""),
                "line": record.get("line", 0),
                **record.get("extra", {})
            }, ensure_ascii=False),
            serialize=True,
            rotation=rotation,
            retention=retention,
            level="DEBUG"  # В файл пишем все
        )

