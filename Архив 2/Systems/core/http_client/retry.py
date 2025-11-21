# core/http_client/retry.py
"""
Retry механизм и Circuit Breaker для внешних API
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
from loguru import logger

import aiohttp
from aiohttp import ClientError, ClientResponseError


class CircuitState(Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Цепь разомкнута, запросы блокируются
    HALF_OPEN = "half_open"  # Тестовый режим


class CircuitBreaker:
    """
    Circuit Breaker для защиты от нестабильных сервисов
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Args:
            failure_threshold: Количество ошибок до открытия цепи
            recovery_timeout: Время в секундах до попытки восстановления
            expected_exception: Тип исключения, которое считается ошибкой
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        self._logger = logger.bind(service="CircuitBreaker")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Выполняет функцию через circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self._logger.info("Circuit breaker переходит в HALF_OPEN состояние")
            else:
                raise Exception(f"Circuit breaker OPEN. Повторите через {self.recovery_timeout} секунд")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Асинхронная версия call"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self._logger.info("Circuit breaker переходит в HALF_OPEN состояние")
            else:
                raise Exception(f"Circuit breaker OPEN. Повторите через {self.recovery_timeout} секунд")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Обработка успешного запроса"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Нужно несколько успешных запросов
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self._logger.info("Circuit breaker восстановлен (CLOSED)")
    
    def _on_failure(self):
        """Обработка ошибки"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self._logger.warning("Circuit breaker снова открыт после неудачной попытки восстановления")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._logger.error(
                f"Circuit breaker открыт после {self.failure_count} ошибок. "
                f"Будут блокироваться запросы на {self.recovery_timeout} секунд"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Проверяет, можно ли попытаться восстановить соединение"""
        if not self.last_failure_time:
            return True
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout
    
    def reset(self):
        """Принудительный сброс circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self._logger.info("Circuit breaker принудительно сброшен")


class RetryConfig:
    """Конфигурация для retry механизма"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: tuple = (ClientError, ClientResponseError)
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    **kwargs
) -> Any:
    """
    Выполняет функцию с повторными попытками и экспоненциальной задержкой
    
    Args:
        func: Асинхронная функция для выполнения
        config: Конфигурация retry
        circuit_breaker: Опциональный circuit breaker
        *args, **kwargs: Аргументы для функции
    
    Returns:
        Результат выполнения функции
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            if circuit_breaker:
                result = await circuit_breaker.call_async(func, *args, **kwargs)
            else:
                result = await func(*args, **kwargs)
            return result
        
        except config.retry_on as e:
            last_exception = e
            
            if attempt == config.max_attempts - 1:
                # Последняя попытка, выбрасываем исключение
                logger.error(f"Все {config.max_attempts} попытки исчерпаны. Последняя ошибка: {e}")
                raise
            
            # Вычисляем задержку
            delay = min(
                config.initial_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random() * 0.5)
            
            logger.warning(
                f"Попытка {attempt + 1}/{config.max_attempts} не удалась: {e}. "
                f"Повтор через {delay:.2f} секунд"
            )
            
            await asyncio.sleep(delay)
        
        except Exception as e:
            # Неожиданное исключение, не повторяем
            logger.error(f"Неожиданное исключение в retry: {e}")
            raise
    
    # Не должно достичь сюда, но на всякий случай
    if last_exception:
        raise last_exception
    raise Exception("Retry механизм завершился неожиданно")

