# core/sys_modules/__init__.py
# Этот файл делает директорию 'sys_modules' пакетом Python.
# Сюда можно будет помещать внутренние системные модули ядра.

# Пример, если бы здесь был модуль 'internal_logger_viewer':
# from .internal_logger_viewer import setup_module as setup_logger_viewer_module
# from .internal_logger_viewer.handlers import logger_viewer_router

# __all__ = ["setup_logger_viewer_module", "logger_viewer_router"]