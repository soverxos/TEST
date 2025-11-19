# core/monitoring/metrics.py
"""
Prometheus метрики для мониторинга
"""

import time
from typing import Dict, Optional, Any
from collections import defaultdict
from datetime import datetime
from loguru import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider


class MetricsCollector:
    """
    Сборщик метрик для экспорта в Prometheus
    """
    
    def __init__(self):
        self._logger = logger.bind(service="MetricsCollector")
        
        # Счетчики
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Метрики времени выполнения
        self._histograms: Dict[str, list] = defaultdict(list)
        
        # Gauge метрики (текущие значения)
        self._gauges: Dict[str, float] = defaultdict(float)
        
        # Метки времени последнего обновления
        self._last_update: Dict[str, datetime] = {}
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: int = 1):
        """Увеличить счетчик"""
        key = self._format_key(name, labels)
        self._counters[key] += value
        self._last_update[key] = datetime.now()
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Записать значение в гистограмму"""
        key = self._format_key(name, labels)
        self._histograms[key].append(value)
        # Храним только последние 1000 значений
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]
        self._last_update[key] = datetime.now()
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Установить значение gauge"""
        key = self._format_key(name, labels)
        self._gauges[key] = value
        self._last_update[key] = datetime.now()
    
    def _format_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Форматирует ключ метрики с лейблами"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_prometheus_format(self) -> str:
        """
        Возвращает метрики в формате Prometheus
        """
        lines = []
        
        # Counters
        for key, value in self._counters.items():
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")
        
        # Gauges
        for key, value in self._gauges.items():
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")
        
        # Histograms (как summary)
        for key, values in self._histograms.items():
            if values:
                lines.append(f"# TYPE {key.split('{')[0]} summary")
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {sum(values)}")
                lines.append(f"{key}_avg {sum(values) / len(values)}")
                if values:
                    sorted_values = sorted(values)
                    lines.append(f"{key}_min {sorted_values[0]}")
                    lines.append(f"{key}_max {sorted_values[-1]}")
        
        return "\n".join(lines) + "\n"
    
    def get_metrics_dict(self) -> Dict:
        """Возвращает метрики в виде словаря"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0
                }
                for k, v in self._histograms.items()
            }
        }


class MetricsMiddleware:
    """
    Middleware для автоматического сбора метрик
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._logger = logger.bind(service="MetricsMiddleware")
    
    async def __call__(self, handler, event, data: Dict):
        """Сбор метрик для каждого события"""
        start_time = time.time()
        
        # Определяем тип события
        event_type = "unknown"
        if hasattr(event, 'message') and event.message:
            event_type = "message"
        elif hasattr(event, 'callback_query') and event.callback_query:
            event_type = "callback"
        elif hasattr(event, 'inline_query') and event.inline_query:
            event_type = "inline_query"
        
        # Увеличиваем счетчик событий
        self.metrics.increment_counter(
            "sdb_events_total",
            labels={"type": event_type}
        )
        
        try:
            result = await handler(event, data)
            
            # Успешная обработка
            self.metrics.increment_counter(
                "sdb_events_success_total",
                labels={"type": event_type}
            )
            
            return result
        
        except Exception as e:
            # Ошибка обработки
            self.metrics.increment_counter(
                "sdb_events_error_total",
                labels={"type": event_type, "error": type(e).__name__}
            )
            raise
        
        finally:
            # Записываем время выполнения
            duration = time.time() - start_time
            self.metrics.record_histogram(
                "sdb_event_duration_seconds",
                duration,
                labels={"type": event_type}
            )


# Глобальный экземпляр сборщика метрик
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Получить глобальный экземпляр сборщика метрик"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector

