# core/events/dispatcher.py

import asyncio
from collections import defaultdict
from typing import Callable, Any, Coroutine, List, Dict, Optional, Union, TYPE_CHECKING # Добавил Optional, Union
from loguru import logger

if TYPE_CHECKING:
    # Более строгий тип для обработчика события, если это необходимо.
    # EventHandler = Callable[..., Coroutine[Any, Any, None]]
    pass


class EventDispatcher:
    """
    Простая асинхронная шина событий для SwiftDevBot.
    Позволяет различным компонентам системы (ядру, модулям) публиковать события
    и подписываться на них, не имея прямых зависимостей друг от друга.
    """

    def __init__(self):
        # Словарь, где ключ - строковое имя (тип) события,
        # значение - список асинхронных функций-обработчиков (корутин).
        self._listeners: Dict[str, List[Callable[..., Coroutine[Any, Any, None]]]] = defaultdict(list)
        self._logger = logger.bind(service="EventDispatcher")
        self._logger.info("EventDispatcher инициализирован.")

    def subscribe(self, event_type: str, handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """
        Подписывает асинхронный обработчик на указанный тип события.

        Args:
            event_type: Имя (тип) события, на которое осуществляется подписка.
                        Рекомендуется использовать префиксы (например, "sdb:core:startup", "module_name:user_registered").
            handler: Асинхронная функция-обработчик (корутина), которая будет вызвана при публикации события.
                     Обработчик должен принимать те же позиционные (*args) и именованные (**kwargs) аргументы,
                     что и передаются в метод publish().

        Raises:
            TypeError: Если переданный обработчик не является асинхронной функцией (корутиной).
        """
        if not asyncio.iscoroutinefunction(handler):
            err_msg = (f"Обработчик '{handler.__qualname__}' для события '{event_type}' должен быть "
                       f"асинхронной функцией (определенной с 'async def').")
            self._logger.error(err_msg)
            raise TypeError(err_msg) # Делаем проверку строже

        self._listeners[event_type].append(handler)
        self._logger.debug(f"Обработчик '{handler.__qualname__}' успешно подписан на событие '{event_type}'.")

    def unsubscribe(self, event_type: str, handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """
        Отписывает указанный обработчик от указанного типа события.

        Args:
            event_type: Имя (тип) события.
            handler: Функция-обработчик, которую необходимо отписать.
        """
        try:
            self._listeners[event_type].remove(handler)
            self._logger.debug(f"Обработчик '{handler.__qualname__}' успешно отписан от события '{event_type}'.")
        except ValueError: # Обработчик не найден в списке для данного события
            self._logger.warning(f"Попытка отписать необъявленный обработчик '{handler.__qualname__}' "
                                 f"от события '{event_type}'. Обработчик не найден.")
        except KeyError: # Такого типа события вообще нет в _listeners
            self._logger.warning(f"Попытка отписаться от несуществующего типа события '{event_type}'.")

    async def publish(self, event_type: str, *args: Any, **kwargs: Any) -> List[Union[Any, Exception]]:
        """
        Асинхронно публикует событие, вызывая всех подписанных на него обработчиков.

        Обработчики для одного события запускаются конкурентно с использованием `asyncio.gather()`.
        Если какой-либо обработчик вызывает исключение, это исключение будет поймано,
        залогировано, и вместо результата этого обработчика в возвращаемом списке будет объект исключения.
        Остальные обработчики продолжат выполняться.

        Args:
            event_type: Имя (тип) публикуемого события.
            *args: Позиционные аргументы, которые будут переданы каждому обработчику.
            **kwargs: Именованные аргументы, которые будут переданы каждому обработчику.

        Returns:
            Список результатов выполнения каждого обработчика.
            Если обработчик вернул значение, оно будет в списке.
            Если обработчик вызвал исключение, в списке на его месте будет объект этого исключения.
            Если подписчиков на событие нет, возвращается пустой список.
        """
        if event_type not in self._listeners or not self._listeners[event_type]:
            self._logger.trace(f"Нет подписчиков для события '{event_type}'. Публикация пропущена.")
            return []

        handlers_to_call = self._listeners[event_type]
        # Формируем строку с аргументами для лога, чтобы не показывать слишком много данных
        args_repr = f"{len(args)} positional"
        kwargs_repr = f"{len(kwargs)} keyword"
        
        self._logger.info(f"Публикация события '{event_type}' для {len(handlers_to_call)} подписчиков. "
                          f"Аргументы: ({args_repr}), ({kwargs_repr}).")

        # Создаем список корутин для вызова
        tasks = [handler(*args, **kwargs) for handler in handlers_to_call]
        
        # Запускаем все обработчики конкурентно и собираем результаты или исключения
        results: List[Union[Any, Exception]] = await asyncio.gather(*tasks, return_exceptions=True)

        # Логируем ошибки, если они произошли в обработчиках
        for i, result_or_exc in enumerate(results):
            if isinstance(result_or_exc, Exception):
                failed_handler_name = handlers_to_call[i].__qualname__
                self._logger.error(
                    f"Ошибка в обработчике события '{failed_handler_name}' при обработке события '{event_type}': "
                    f"{type(result_or_exc).__name__}('{result_or_exc}')",
                    exc_info=result_or_exc # Для полного трейсбека исключения
                )
        
        return results

    def get_listeners_count(self, event_type: Optional[str] = None) -> Union[int, Dict[str, int]]:
        """
        Возвращает количество подписчиков.
        Если `event_type` указан, возвращает количество для этого события.
        Если `event_type` не указан (None), возвращает словарь {event_type: count} для всех событий.
        """
        if event_type:
            return len(self._listeners.get(event_type, []))
        else:
            return {etype: len(handler_list) for etype, handler_list in self._listeners.items() if handler_list}

    async def dispose(self) -> None: # Сделаем async, если в будущем понадобится асинхронная очистка
        """Очищает всех подписчиков. Полезно при остановке или перезагрузке системы."""
        self._listeners.clear()
        self._logger.info("EventDispatcher очищен (все подписчики и списки событий удалены).")