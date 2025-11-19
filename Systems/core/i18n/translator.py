# core/i18n/translator.py

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

class Translator:
    """
    Сервис для работы с переводами (локализацией) строк.
    Использует YAML файлы для хранения переводов.
    Формат: key = value в YAML файлах.
    """
    def __init__(
        self, 
        locales_dir: Path, 
        domain: str = "bot", # Имя домена переводов (не используется для YAML, но оставлено для совместимости)
        default_locale: str = "ru", 
        available_locales: Optional[List[str]] = None
    ):
        """
        Инициализирует транслятор.

        Args:
            locales_dir: Путь к директории 'locales' (где лежат файлы en.yaml, ua.yaml, ru.yaml).
            domain: Имя домена переводов (не используется для YAML, оставлено для совместимости).
            default_locale: Язык по умолчанию, если перевод для языка пользователя не найден.
            available_locales: Список поддерживаемых языков (например, ['en', 'ua', 'ru']).
                               Если None, попытается определить из YAML файлов в locales_dir.
        """
        self.locales_dir = locales_dir
        self.domain = domain
        self.default_locale = default_locale
        self._translations: Dict[str, Dict[str, str]] = {} # Кэш загруженных переводов: {locale: {key: value}}

        if available_locales:
            self.available_locales = available_locales
        else:
            # Пытаемся определить доступные языки по YAML файлам в locales_dir
            self.available_locales = []
            if self.locales_dir.is_dir():
                for item in self.locales_dir.iterdir():
                    if item.is_file() and item.suffix == ".yaml":
                        locale_name = item.stem  # Имя файла без расширения (en, ua, ru)
                        self.available_locales.append(locale_name)
            if not self.available_locales:
                 logger.warning(f"Не найдены YAML файлы переводов в {self.locales_dir}. "
                                f"Локализация может не работать.")
            elif default_locale not in self.available_locales and self.available_locales:
                logger.warning(f"Язык по умолчанию '{default_locale}' не найден среди доступных: {self.available_locales}. "
                               f"Будет использован первый доступный язык.")
        
        logger.info(f"Translator инициализирован. Locales dir: '{self.locales_dir}', Domain: '{self.domain}', "
                    f"Default: '{self.default_locale}', Available: {self.available_locales}")
        
        # Предзагрузка переводов
        self.load_all_translations()


    def load_translation(self, locale: str) -> Optional[Dict[str, str]]:
        """Загружает или возвращает из кэша словарь переводов для указанного языка."""
        if locale in self._translations:
            return self._translations[locale]
        
        if locale not in self.available_locales:
            logger.trace(f"Язык '{locale}' не поддерживается или для него нет файлов перевода.")
            return None

        try:
            # Загружаем YAML файл с переводами
            yaml_file = self.locales_dir / f"{locale}.yaml"
            if not yaml_file.exists():
                logger.warning(f"Файл перевода '{yaml_file}' не найден.")
                # Пытаемся загрузить дефолтный язык
                if locale != self.default_locale:
                    return self.load_translation(self.default_locale)
                return None
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                translations = yaml.safe_load(f) or {}
            
            # Конвертируем формат "key = value" в словарь, если нужно
            # Если YAML уже в формате словаря, используем его как есть
            if isinstance(translations, dict):
                self._translations[locale] = translations
                logger.debug(f"Переводы для языка '{locale}' успешно загружены ({len(translations)} ключей).")
                return translations
            else:
                logger.warning(f"Неверный формат файла перевода '{yaml_file}'. Ожидается словарь.")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке перевода для языка '{locale}': {e}", exc_info=True)
            # Пытаемся загрузить дефолтный язык при ошибке
            if locale != self.default_locale:
                return self.load_translation(self.default_locale)
            return None

    def load_all_translations(self) -> None:
        """Предзагружает все доступные переводы."""
        logger.info(f"Предзагрузка всех доступных переводов ({self.available_locales})...")
        for lang in self.available_locales:
            self.load_translation(lang)
        logger.info(f"Загружено переводов для {len(self._translations)} языков.")

    def gettext(self, message_key: str, locale: str, **kwargs: Any) -> str:
        """
        Получает переведенную строку по ключу для указанного языка.
        Поддерживает форматирование с kwargs.

        Args:
            message_key: Ключ перевода (например, "main_menu_title")
            locale: Код языка (например, "en", "ua", "ru")
            **kwargs: Параметры для форматирования строки

        Returns:
            Переведенная строка или сам ключ, если перевод не найден
        """
        # Загружаем переводы для указанного языка
        translations = self._translations.get(locale)
        if not translations:
            translations = self.load_translation(locale)
        
        # Если перевод не найден, пытаемся использовать дефолтный язык
        if not translations or message_key not in translations:
            if locale != self.default_locale:
                default_translations = self._translations.get(self.default_locale)
                if not default_translations:
                    default_translations = self.load_translation(self.default_locale)
                if default_translations and message_key in default_translations:
                    translations = default_translations
                    logger.trace(f"Использован перевод из дефолтного языка '{self.default_locale}' для ключа '{message_key}'")
        
        # Получаем переведенный текст
        if translations and message_key in translations:
            translated_text = translations[message_key]
        else:
            # Если перевод не найден, возвращаем ключ
            logger.warning(f"Перевод не найден для ключа '{message_key}' (locale: {locale}). Возвращается ключ.")
            translated_text = message_key

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
        
        Args:
            singular_key: Ключ для единственного числа
            plural_key: Ключ для множественного числа
            count: Количество для определения формы
            locale: Код языка
            **kwargs: Параметры для форматирования строки
            
        Returns:
            Переведенная строка с учетом числа
        """
        # Для простоты используем singular_key если count == 1, иначе plural_key
        # В будущем можно добавить поддержку правил множественного числа для разных языков
        key_to_use = singular_key if count == 1 else plural_key
        
        # Добавляем count в kwargs для форматирования
        format_kwargs = {**kwargs, 'count': count}
        
        return self.gettext(key_to_use, locale, **format_kwargs)

    # Можно добавить методы для получения переводов для конкретного пользователя,
    # если язык пользователя известен сервису.
    # async def gettext_for_user(self, user_id: int, message_key: str, **kwargs) -> str:
    #     user_locale = await self._get_user_locale(user_id) # Нужен доступ к БД или кэшу с языком пользователя
    #     return self.gettext(message_key, user_locale, **kwargs)