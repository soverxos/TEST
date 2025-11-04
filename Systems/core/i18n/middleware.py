# core/i18n/middleware.py

from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as AiogramUser # User из aiogram.types

# Импортируем наш Translator и AppSettings (для дефолтного языка и списка доступных)
from .translator import Translator
from Systems.core.app_settings import settings as sdb_settings # Глобальные настройки
from Systems.core.database.core_models import User as DBUser # Наша модель User из БД
from sqlalchemy.ext.asyncio import AsyncSession # Для работы с БД

# Для доступа к BotServicesProvider из workflow_data диспетчера (если он там есть)
# from Systems.core.services_provider import BotServicesProvider


class I18nMiddleware(BaseMiddleware):
    """
    Middleware для определения языка пользователя и предоставления
    инструментов локализации (gettext) в хэндлеры.
    """
    def __init__(self, translator: Translator):
        super().__init__()
        self.translator = translator
        self.default_locale = translator.default_locale
        self.available_locales = translator.available_locales
        # logger здесь можно получить из data, если BotServicesProvider его передает, или создать свой

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject, # Это может быть Message, CallbackQuery, etc.
        data: Dict[str, Any]   # Словарь данных, передаваемый в хэндлер
    ) -> Any:
        
        # Получаем объект пользователя Telegram, если он есть в событии
        aiogram_event_user: Optional[AiogramUser] = data.get("event_from_user")
        
        user_locale: str = self.default_locale # По умолчанию язык системы

        if aiogram_event_user:
            # Пытаемся получить язык пользователя из нашей БД
            # Для этого нужен доступ к DBManager или сессии
            # Предположим, что BotServicesProvider (services) доступен в data
            services = data.get("services_provider") # Имя ключа зависит от того, как мы его положили в Dispatcher
            
            db_user: Optional[DBUser] = None
            if services and hasattr(services, 'db'):
                try:
                    async with services.db.get_session() as session: # type: AsyncSession
                        # Ищем пользователя по telegram_id
                        from sqlalchemy import select # Ленивый импорт
                        stmt = select(DBUser).where(DBUser.telegram_id == aiogram_event_user.id)
                        result = await session.execute(stmt)
                        db_user = result.scalars().first()
                        
                        if db_user and db_user.preferred_language_code and db_user.preferred_language_code in self.available_locales:
                            user_locale = db_user.preferred_language_code
                        elif db_user and not db_user.preferred_language_code:
                            # Если у пользователя в БД нет языка, но есть язык в Telegram и он поддерживается
                            if aiogram_event_user.language_code and aiogram_event_user.language_code in self.available_locales:
                                user_locale = aiogram_event_user.language_code
                                # Можно обновить язык в БД для этого пользователя
                                # db_user.preferred_language_code = user_locale
                                # await session.commit() # ОСТОРОЖНО: commit в middleware
                        elif not db_user: # Если пользователя нет в БД
                            if aiogram_event_user.language_code and aiogram_event_user.language_code in self.available_locales:
                                user_locale = aiogram_event_user.language_code
                except Exception as e:
                    # logger.error(f"Ошибка получения языка пользователя из БД для TG ID {aiogram_event_user.id}: {e}")
                    # Используем логгер из data, если он там есть
                    data.get("logger", logger).error(f"I18nMiddleware: Ошибка БД при получении языка для TG ID {aiogram_event_user.id}: {e}")
                    # Продолжаем с default_locale или языком из Telegram, если он был определен ранее
            else: # Если services или services.db недоступны
                 data.get("logger", logger).warning("I18nMiddleware: BotServicesProvider или DBManager не найдены в data. Язык из БД не будет загружен.")
                 # Пытаемся использовать язык из Telegram API, если он поддерживается
                 if aiogram_event_user.language_code and aiogram_event_user.language_code in self.available_locales:
                     user_locale = aiogram_event_user.language_code
        
        # Сохраняем определенный язык в data для доступа в хэндлерах
        data["user_locale"] = user_locale
        
        # Предоставляем хэндлерам удобные функции для перевода
        # Они будут использовать user_locale, сохраненный в data
        # Это обертки, чтобы не передавать locale каждый раз
        data["gettext"] = lambda message_key, **kwargs: self.translator.gettext(message_key, user_locale, **kwargs)
        data["ngettext"] = lambda singular_key, plural_key, count, **kwargs: self.translator.ngettext(singular_key, plural_key, count, user_locale, **kwargs)
        
        # Также можно передать сам объект translator, если это удобнее
        data["translator"] = self.translator 
        
        # data.get("logger", logger).debug(f"I18nMiddleware: Установлен язык '{user_locale}' для TG ID {aiogram_event_user.id if aiogram_event_user else 'N/A'}.")
        
        return await handler(event, data)