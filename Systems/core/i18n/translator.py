# core/i18n/translator.py

import gettext # Стандартная библиотека для i18n
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

# Импортируем настройки, чтобы знать путь к 'locales' и дефолтный язык
# Этот импорт может быть убран, если Translator будет получать эти данные извне
# from Systems.core.app_settings import settings as sdb_settings # Предположим, что настройки i18n там есть

class Translator:
    """
    Сервис для работы с переводами (локализацией) строк.
    Использует стандартный механизм gettext.
    """
    def __init__(
        self, 
        locales_dir: Path, 
        domain: str = "bot", # Имя домена переводов (соответствует имени .mo/.po файла)
        default_locale: str = "en", 
        available_locales: Optional[List[str]] = None
    ):
        """
        Инициализирует транслятор.

        Args:
            locales_dir: Путь к директории 'locales' (где лежат папки en/, ua/, etc.).
            domain: Имя домена переводов (обычно имя вашего .po/.mo файла, например, 'bot').
            default_locale: Язык по умолчанию, если перевод для языка пользователя не найден.
            available_locales: Список поддерживаемых языков (например, ['en', 'ua']).
                               Если None, попытается определить из папок в locales_dir.
        """
        self.locales_dir = locales_dir
        self.domain = domain
        self.default_locale = default_locale
        self._translations: Dict[str, gettext.GNUTranslations] = {} # Кэш загруженных переводов

        if available_locales:
            self.available_locales = available_locales
        else:
            # Пытаемся определить доступные языки по папкам в locales_dir
            self.available_locales = []
            if self.locales_dir.is_dir():
                for item in self.locales_dir.iterdir():
                    if item.is_dir() and (item / "LC_MESSAGES" / f"{self.domain}.mo").exists():
                        self.available_locales.append(item.name)
            if not self.available_locales:
                 logger.warning(f"Не найдены скомпилированные .mo файлы в {self.locales_dir} для домена '{self.domain}'. "
                                f"Локализация может не работать.")
            elif default_locale not in self.available_locales and self.available_locales:
                logger.warning(f"Язык по умолчанию '{default_locale}' не найден среди доступных: {self.available_locales}. "
                               f"Будет использован первый доступный язык или английский, если gettext не найдет ничего.")
        
        logger.info(f"Translator инициализирован. Locales dir: '{self.locales_dir}', Domain: '{self.domain}', "
                    f"Default: '{self.default_locale}', Available: {self.available_locales}")
        
        # Предзагрузка переводов (опционально, можно грузить по запросу)
        self.load_all_translations()


    def load_translation(self, locale: str) -> Optional[gettext.GNUTranslations]:
        """Загружает или возвращает из кэша объект перевода для указанного языка."""
        if locale in self._translations:
            return self._translations[locale]
        
        if locale not in self.available_locales:
            logger.trace(f"Язык '{locale}' не поддерживается или для него нет файлов перевода.")
            return None # Или можно вернуть перевод для default_locale

        try:
            # gettext.translation требует путь к директории, содержащей en/LC_MESSAGES, ua/LC_MESSAGES и т.д.
            # и список языков для поиска (fallback).
            translation = gettext.translation(
                domain=self.domain,
                localedir=str(self.locales_dir),
                languages=[locale, self.default_locale] # Порядок важен для fallback
            )
            self._translations[locale] = translation
            logger.debug(f"Переводы для языка '{locale}' успешно загружены.")
            return translation
        except FileNotFoundError:
            logger.warning(f"Файл перевода .mo для языка '{locale}' (домен '{self.domain}') не найден в '{self.locales_dir}'.")
            # Можно кэшировать None, чтобы не пытаться грузить снова
            self._translations[locale] = gettext.NullTranslations() # type: ignore # Используем NullTranslations как заглушку
            return self._translations[locale]
        except Exception as e:
            logger.error(f"Ошибка при загрузке перевода для языка '{locale}': {e}", exc_info=True)
            return None

    def load_all_translations(self) -> None:
        """Предзагружает все доступные переводы."""
        logger.info(f"Предзагрузка всех доступных переводов ({self.available_locales})...")
        for lang in self.available_locales:
            self.load_translation(lang)

    def gettext(self, message_key: str, locale: str, **kwargs: Any) -> str:
        """
        Получает переведенную строку по ключу для указанного языка.
        Поддерживает форматирование с kwargs.

        Пример ключа: "main_menu:button_profile" или просто "Profile Button Text"
        """
        translation = self._translations.get(locale)
        if not translation: # Если не загружен или NullTranslations
            # Пытаемся загрузить или используем дефолтный, если не удалось
            translation = self.load_translation(locale) or self._translations.get(self.default_locale)
            if not translation: # Если и дефолтный не загружен
                translation = self.load_translation(self.default_locale) or gettext.NullTranslations() # type: ignore
                self._translations[self.default_locale] = translation # Кэшируем NullTranslations для дефолта

        # gettext.gettext() используется объектом GNUTranslations
        translated_text = translation.gettext(message_key) # type: ignore

        try:
            # Применяем форматирование, если есть kwargs
            return translated_text.format(**kwargs) if kwargs else translated_text
        except (KeyError, IndexError) as e_format:
            logger.warning(f"Ошибка форматирования для ключа '{message_key}' (locale: {locale}): {e_format}. "
                           f"Переведенный текст: '{translated_text}', kwargs: {kwargs}")
            return translated_text # Возвращаем неформатированный текст в случае ошибки

    def ngettext(self, singular_key: str, plural_key: str, count: int, locale: str, **kwargs: Any) -> str:
        """
        Получает переведенную строку с учетом множественного числа.
        """
        translation = self._translations.get(locale)
        if not translation:
            translation = self.load_translation(locale) or self._translations.get(self.default_locale)
            if not translation:
                translation = self.load_translation(self.default_locale) or gettext.NullTranslations() # type: ignore
                self._translations[self.default_locale] = translation

        # ngettext ожидает msgid1, msgid2, n
        # Если мы используем ключи, то нам нужно как-то их передать.
        # Простой gettext.GNUTranslations.ngettext(msgid1, msgid2, n) не будет работать с нашими ключами.
        # Нам нужно, чтобы .po файлы содержали msgid и msgid_plural.
        # Для простоты, предположим, что ключи это и есть msgid/msgid_plural.
        translated_text = translation.ngettext(singular_key, plural_key, count) # type: ignore
        
        # Добавляем count в kwargs для форматирования, если его там нет
        format_kwargs = {**kwargs, 'count': count}
        try:
            return translated_text.format(**format_kwargs)
        except (KeyError, IndexError) as e_format:
            logger.warning(f"Ошибка форматирования ngettext для ключей '{singular_key}/{plural_key}' (locale: {locale}): {e_format}. "
                           f"Переведенный текст: '{translated_text}', kwargs: {format_kwargs}")
            return translated_text

    # Можно добавить методы для получения переводов для конкретного пользователя,
    # если язык пользователя известен сервису.
    # async def gettext_for_user(self, user_id: int, message_key: str, **kwargs) -> str:
    #     user_locale = await self._get_user_locale(user_id) # Нужен доступ к БД или кэшу с языком пользователя
    #     return self.gettext(message_key, user_locale, **kwargs)