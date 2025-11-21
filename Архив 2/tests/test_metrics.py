"""
Тесты для Metrics Collector
"""

import pytest
from Systems.core.monitoring.metrics import MetricsCollector


class TestMetricsCollector:
    """Тесты для MetricsCollector"""
    
    def test_initialization(self):
        """Тест инициализации MetricsCollector"""
        collector = MetricsCollector()
        assert collector._counters == {}
        assert collector._gauges == {}
        assert collector._histograms == {}
    
    def test_increment_counter(self):
        """Тест увеличения счетчика"""
        collector = MetricsCollector()
        collector.increment_counter("test_counter")
        assert collector._counters["test_counter"] == 1
        
        collector.increment_counter("test_counter", value=5)
        assert collector._counters["test_counter"] == 6
    
    def test_increment_counter_with_labels(self):
        """Тест счетчика с метками"""
        collector = MetricsCollector()
        collector.increment_counter("test_counter", labels={"type": "test"})
        key = collector._format_key("test_counter", {"type": "test"})
        assert collector._counters[key] == 1
    
    def test_set_gauge(self):
        """Тест установки gauge"""
        collector = MetricsCollector()
        collector.set_gauge("test_gauge", 42.5)
        assert collector._gauges["test_gauge"] == 42.5
        
        collector.set_gauge("test_gauge", 100.0)
        assert collector._gauges["test_gauge"] == 100.0
    
    def test_record_histogram(self):
        """Тест записи в гистограмму"""
        collector = MetricsCollector()
        collector.record_histogram("test_histogram", 1.5)
        collector.record_histogram("test_histogram", 2.5)
        collector.record_histogram("test_histogram", 3.5)
        
        assert len(collector._histograms["test_histogram"]) == 3
        assert collector._histograms["test_histogram"] == [1.5, 2.5, 3.5]
    
    def test_get_prometheus_format(self):
        """Тест формата Prometheus"""
        collector = MetricsCollector()
        collector.increment_counter("test_counter")
        collector.set_gauge("test_gauge", 42.0)
        collector.record_histogram("test_histogram", 1.0)
        
        prometheus_output = collector.get_prometheus_format()
        assert "test_counter" in prometheus_output
        assert "test_gauge" in prometheus_output
        assert "test_histogram" in prometheus_output
        assert "# TYPE" in prometheus_output
    
    def test_get_metrics_dict(self):
        """Тест получения метрик в виде словаря"""
        collector = MetricsCollector()
        collector.increment_counter("test_counter")
        collector.set_gauge("test_gauge", 42.0)
        collector.record_histogram("test_histogram", 1.0)
        
        metrics_dict = collector.get_metrics_dict()
        assert "counters" in metrics_dict
        assert "gauges" in metrics_dict
        assert "histograms" in metrics_dict
        assert "test_counter" in metrics_dict["counters"]
        assert "test_gauge" in metrics_dict["gauges"]

