from aiogram import Dispatcher, Bot
from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider

from .handlers import router as handlers_router

async def setup_module(dp: Dispatcher, bot: Bot, services: 'BotServicesProvider'):
    """
    Setup Broadcast module.
    Ядро автоматически зарегистрирует UI точку входа на основе манифеста.
    """
    # Регистрируем обработчики
    dp.include_router(handlers_router)
    logger.info("[broadcast] Роутер успешно зарегистрирован")
    
    # Ядро автоматически зарегистрирует модуль в UI меню на основе манифеста
    logger.success("✅ Модуль 'broadcast' успешно настроен и готов к работе!")
