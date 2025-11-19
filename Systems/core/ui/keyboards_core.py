# SwiftDevBot/core/ui/keyboards_core.py

from typing import List, Dict, Optional, TYPE_CHECKING, Callable
# Используем нужные типы для Reply клавиатур
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton 
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder # Добавляем ReplyKeyboardBuilder
from loguru import logger 

from .callback_data_factories import CoreMenuNavigate, ModuleMenuEntry, CoreServiceAction
from Systems.core.rbac.service import PERMISSION_CORE_VIEW_ADMIN_PANEL 
from Systems.core.database.core_models import User as DBUser

if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from Systems.core.ui.registry_ui import ModuleUIEntry
    from sqlalchemy.ext.asyncio import AsyncSession

# Глобальный кэш для translator (создается один раз)
_translator_cache: Optional['Translator'] = None

def _get_translator(services_provider: 'BotServicesProvider') -> 'Translator':
    """Получает или создает translator для использования в клавиатурах"""
    global _translator_cache
    if _translator_cache is None:
        from Systems.core.i18n.translator import Translator
        _translator_cache = Translator(
            locales_dir=services_provider.config.core.i18n.locales_dir,
            domain=services_provider.config.core.i18n.domain,
            default_locale=services_provider.config.core.i18n.default_locale,
            available_locales=services_provider.config.core.i18n.available_locales
        )
    return _translator_cache 

# Обновляем тексты для кнопок, чтобы они были командами или уникальными фразами
TEXTS_CORE_KEYBOARDS_EN = {
    # Для Reply Keyboard (главное меню) - более интуитивные тексты
    "main_menu_reply_modules": "🗂 Модули и функции", # Более описательное название
    "main_menu_reply_profile": "👤 Мой профиль",
    "main_menu_reply_feedback": "✍️ Связаться с нами", # Более дружелюбное название
    "main_menu_reply_admin_panel": "🛠 Администрирование",

    # Для Inline Keyboard (остальные меню)
    "main_menu_inline_modules": "🗂 Modules", # Оставим старые для инлайн, если понадобятся
    "main_menu_inline_profile": "👤 Profile",
    "main_menu_inline_feedback": "✍️ Feedback",
    "main_menu_inline_admin_panel": "🛠 Admin Panel",

    "modules_list_no_modules": "🤷 No modules available",
    "modules_list_title_template": "Available Modules (Page {current_page}/{total_pages}):",
    "pagination_prev": "⬅️ Prev",
    "pagination_next": "Next ➡️",
    "navigation_back_to_main": "🏠 Main Menu", # Может быть и для инлайн, и для reply (как /start)
    "service_delete_message": "❌ Close this menu",
    "confirm_yes": "✅ Yes",
    "confirm_no": "❌ No",
    "welcome_message_title": "🎉 Добро пожаловать в SwiftDevBot!",
    "welcome_message_body": (
        "Я — ваш модульный Telegram-помощник, созданный для расширения функциональности и автоматизации задач.\n\n"
        "🔍 **Что я могу?**\n"
        "Мои возможности зависят от подключенных модулей. Это могут быть инструменты для разработки, утилиты, информационные сервисы и многое другое.\n\n"
        "🔒 **Конфиденциальность:**\n"
        "Я обрабатываю только те данные, которые необходимы для моей работы и работы активных модулей. "
        "Мы ценим вашу приватность. Для получения более подробной информации вы всегда можете обратиться к администратору бота.\n\n"
        "Нажимая «Продолжить», вы соглашаетесь с тем, что бот будет обрабатывать ваши сообщения для предоставления своих функций."
    ),
    "welcome_button_continue": "✅ Продолжить",
    "welcome_button_cancel": "❌ Отмена",
    "registration_cancelled_message": "Очень жаль, что вы передумали. Если надумаете снова, просто напишите /start.",
    "user_middleware_please_register": (
        "👋 Похоже, вы еще не знакомы со мной! "
        "Чтобы начать, пожалуйста, нажмите /start или введите команду /start."
    ),
    "profile_title": "👤 Ваш профиль",
    "profile_info_template": (
        "🆔 Ваш Telegram ID: {user_id}\n"
        "📝 Имя: {full_name}\n"
        "👤 Username: @{username}\n"
        "📅 Дата регистрации: {registration_date}\n"
        "🗣 Язык интерфейса: {current_language}"
    ),
    "profile_no_username": "не указан",
    "profile_no_reg_date": "неизвестно",
    "profile_button_change_language": "🌐 Сменить язык", # Это будет инлайн кнопка в профиле
    "profile_select_language_title": "Выберите язык интерфейса:",
}

# --- НОВАЯ ФУНКЦИЯ ДЛЯ REPLY KEYBOARD ГЛАВНОГО МЕНЮ ---
async def get_main_menu_reply_keyboard( 
    services_provider: 'BotServicesProvider', 
    user_telegram_id: int,
    locale: Optional[str] = None
) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder() # Используем ReplyKeyboardBuilder
    
    # Получаем язык пользователя
    if not locale:
        # Пытаемся получить язык из БД
        try:
            async with services_provider.db.get_session() as session:
                from Systems.core.database.core_models import User as DBUser
                from sqlalchemy import select
                result = await session.execute(select(DBUser).where(DBUser.telegram_id == user_telegram_id))
                db_user = result.scalar_one_or_none()
                if db_user and db_user.preferred_language_code:
                    locale = db_user.preferred_language_code
        except Exception:
            pass
        
        # Если язык не найден, используем дефолтный
        if not locale:
            locale = services_provider.config.core.i18n.default_locale
    
    # Получаем переводы через translator
    translator = _get_translator(services_provider)
    
    # Используем переводы вместо TEXTS_CORE_KEYBOARDS_EN
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, locale, **kwargs)
    
    texts = {
        "main_menu_reply_modules": t("main_menu_reply_modules"),
        "main_menu_reply_profile": t("main_menu_reply_profile"),
        "main_menu_reply_feedback": t("main_menu_reply_feedback"),
        "main_menu_reply_admin_panel": t("main_menu_reply_admin_panel"),
    } 
    
    # Основные функции - первый ряд
    builder.button(text=texts["main_menu_reply_modules"])
    builder.button(text=texts["main_menu_reply_profile"])
    
    show_admin_button = False
    is_super_admin = user_telegram_id in services_provider.config.core.super_admins
    
    if is_super_admin:
        show_admin_button = True
    else:
        try:
            async with services_provider.db.get_session() as session: 
                if await services_provider.rbac.user_has_permission(session, user_telegram_id, PERMISSION_CORE_VIEW_ADMIN_PANEL):
                    show_admin_button = True
        except Exception as e: 
            logger.error(f"[MainMenuReplyKeyboard] Ошибка проверки разрешения '{PERMISSION_CORE_VIEW_ADMIN_PANEL}' для {user_telegram_id}: {e}")
    
    # Логически группируем кнопки:
    # Ряд 1: Основные функции (Модули, Профиль) 
    # Ряд 2: Административные функции (Админ-панель) или служебные (Обратная связь)
    if show_admin_button:
        # Для админов: Админ-панель в отдельном ряду как важная функция
        builder.button(text=texts["main_menu_reply_admin_panel"])
        
        # Обратная связь для супер-админов менее важна (они сами получают отзывы)
        # Но для обычных админов оставляем доступной
        if not is_super_admin:
            builder.button(text=texts["main_menu_reply_feedback"])
            # Расположение для обычных админов: [Модули][Профиль] / [Админ-панель][Обратная связь]
            builder.adjust(2, 2)
        else:
            # Расположение для супер-админов: [Модули][Профиль] / [Админ-панель]
            builder.adjust(2, 1)
    else:
        # Для обычных пользователей: Обратная связь в отдельном ряду
        builder.button(text=texts["main_menu_reply_feedback"])
        # Расположение: [Модули][Профиль] / [Обратная связь]
        builder.adjust(2, 1)
    
    return builder.as_markup(
        resize_keyboard=True, 
        input_field_placeholder="Выберите действие из меню..." # Подсказка в поле ввода
    )# Старая функция для инлайн-клавиатуры главного меню (может пригодиться для других случаев или если захотите вернуть)
async def get_main_menu_inline_keyboard( # Переименовал для ясности
    services_provider: 'BotServicesProvider', 
    user_telegram_id: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    texts = TEXTS_CORE_KEYBOARDS_EN 
    
    builder.button(
        text=texts["main_menu_inline_modules"], # Используем тексты для инлайн
        callback_data=CoreMenuNavigate(target_menu="modules_list", page=1).pack()
    )
    builder.button(
        text=texts["main_menu_inline_profile"],
        callback_data=CoreMenuNavigate(target_menu="profile").pack()
    )
    # ... (логика кнопки админки как была) ...
    show_admin_button = False
    if user_telegram_id in services_provider.config.core.super_admins:
        show_admin_button = True
    else:
        try:
            async with services_provider.db.get_session() as session: 
                if await services_provider.rbac.user_has_permission(session, user_telegram_id, PERMISSION_CORE_VIEW_ADMIN_PANEL):
                    show_admin_button = True
        except Exception as e:
            logger.debug(f"Ошибка проверки прав доступа к админ-панели для пользователя {user_telegram_id}: {e}")
            
    if show_admin_button:
        builder.button(
            text=texts["main_menu_inline_admin_panel"],
            callback_data=CoreMenuNavigate(target_menu="admin_panel_main").pack()
        )
    builder.button(
        text=texts["main_menu_inline_feedback"],
        callback_data=CoreMenuNavigate(target_menu="feedback").pack()
    )
    builder.adjust(2) 
    return builder.as_markup()


async def get_modules_list_keyboard( # Остается инлайн
    services_provider: 'BotServicesProvider',
    user_telegram_id: int, 
    current_page: int = 1,
    items_per_page: int = 5,
    locale: Optional[str] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем язык пользователя
    if not locale:
        try:
            async with services_provider.db.get_session() as session:
                from sqlalchemy import select
                result = await session.execute(select(DBUser).where(DBUser.telegram_id == user_telegram_id))
                db_user = result.scalar_one_or_none()
                if db_user and db_user.preferred_language_code:
                    locale = db_user.preferred_language_code
        except Exception:
            pass
        
        if not locale:
            locale = services_provider.config.core.i18n.default_locale
    
    translator = _get_translator(services_provider)
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, locale, **kwargs)
    
    texts = {
        "modules_list_no_modules": t("modules_list_no_modules"),
        "pagination_prev": t("pagination_prev"),
        "pagination_next": t("pagination_next"),
        "navigation_back_to_main": t("navigation_back_to_main"),
    }
    
    all_module_ui_entries: List['ModuleUIEntry'] = services_provider.ui_registry.get_all_module_entries()
    
    accessible_module_entries: List['ModuleUIEntry'] = []
    if all_module_ui_entries:
        async with services_provider.db.get_session() as session: 
            for entry in all_module_ui_entries:
                if entry.required_permission_to_view:
                    if await services_provider.rbac.user_has_permission(session, user_telegram_id, entry.required_permission_to_view):
                        accessible_module_entries.append(entry)
                else:
                    accessible_module_entries.append(entry)

    if not accessible_module_entries:
        builder.button(
            text=texts["modules_list_no_modules"],
            callback_data="core:dummy_no_modules"
        )
    else:
        # ... (логика пагинации и кнопок модулей без изменений) ...
        total_items = len(accessible_module_entries)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        current_page = max(1, min(current_page, total_pages if total_pages > 0 else 1))

        start_index = (current_page - 1) * items_per_page
        end_index = start_index + items_per_page
        paginated_entries = accessible_module_entries[start_index:end_index]

        for entry in paginated_entries:
            button_text = f"{entry.icon} {entry.display_name}" if entry.icon else entry.display_name
            builder.button(
                text=button_text,
                callback_data=entry.entry_callback_data
            )
        builder.adjust(1)

        if total_pages > 1:
            pagination_buttons_row: List[InlineKeyboardButton] = []
            if current_page > 1:
                pagination_buttons_row.append(InlineKeyboardButton(text=texts["pagination_prev"], callback_data=CoreMenuNavigate(target_menu="modules_list", page=current_page - 1).pack()))
            pagination_buttons_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="core:dummy_page_indicator"))
            if current_page < total_pages:
                pagination_buttons_row.append(InlineKeyboardButton(text=texts["pagination_next"], callback_data=CoreMenuNavigate(target_menu="modules_list", page=current_page + 1).pack()))
            if pagination_buttons_row:
                 builder.row(*pagination_buttons_row)
    builder.row(
        InlineKeyboardButton(
            text=texts["navigation_back_to_main"], 
            callback_data=CoreMenuNavigate(target_menu="main_reply").pack() # <--- ИЗМЕНЕНО: возврат к reply-меню
        )
    )
    return builder.as_markup()


def get_welcome_confirmation_keyboard(locale: Optional[str] = None, services_provider: Optional['BotServicesProvider'] = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения регистрации с переводами"""
    builder = InlineKeyboardBuilder()
    
    # Если services_provider передан, используем переводы
    if services_provider:
        if not locale:
            locale = services_provider.config.core.i18n.default_locale
        translator = _get_translator(services_provider)
        def t(key: str, **kwargs) -> str:
            return translator.gettext(key, locale, **kwargs)
        texts = {
            "welcome_button_continue": t("welcome_button_continue"),
            "welcome_button_cancel": t("welcome_button_cancel"),
        }
    else:
        # Fallback на старые тексты, если services_provider не передан
        texts = TEXTS_CORE_KEYBOARDS_EN
    
    builder.button(
        text=texts["welcome_button_continue"],
        callback_data=CoreServiceAction(action="confirm_registration").pack()
    )
    builder.button(
        text=texts["welcome_button_cancel"],
        callback_data=CoreServiceAction(action="cancel_registration").pack()
    )
    builder.adjust(2)
    return builder.as_markup()

async def get_profile_menu_keyboard( # Остается инлайн
    db_user: DBUser, 
    services_provider: 'BotServicesProvider',
    locale: Optional[str] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем язык пользователя
    if not locale:
        locale = db_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    
    translator = _get_translator(services_provider)
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, locale, **kwargs)
    
    texts = {
        "profile_button_change_language": t("profile_button_change_language"),
        "navigation_back_to_main": t("navigation_back_to_main"),
    }
    
    available_langs = services_provider.config.core.i18n.available_locales
    if len(available_langs) > 1:
        builder.button(
            text=texts["profile_button_change_language"],
            callback_data=CoreMenuNavigate(target_menu="profile_change_lang_list").pack()
        )
    if not builder.export():
        builder.button(text="Нет доступных действий в профиле", callback_data="core_profile:dummy_no_actions")
    builder.row(
        InlineKeyboardButton(
            text=texts["navigation_back_to_main"],
            callback_data=CoreMenuNavigate(target_menu="main_reply").pack() # <--- ИЗМЕНЕНО: возврат к reply-меню
        )
    )
    builder.adjust(1)
    return builder.as_markup()

async def get_language_selection_keyboard( # Остается инлайн
    current_lang_code: Optional[str],
    available_locales: List[str],
    services_provider: Optional['BotServicesProvider'] = None,
    locale: Optional[str] = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем переводы для названий языков
    if services_provider:
        if not locale:
            locale = current_lang_code or services_provider.config.core.i18n.default_locale
        translator = _get_translator(services_provider)
        
        for lang_code in available_locales:
            prefix = "✅ " if lang_code == current_lang_code else "▫️ "
            lang_key = f"language_{lang_code}"
            display_name = translator.gettext(lang_key, locale) if lang_key in translator._translations.get(locale, {}) else lang_code.upper()
            builder.button(
                text=f"{prefix}{display_name}",
                callback_data=CoreMenuNavigate(target_menu="profile_set_lang", payload=lang_code).pack()
            )
    else:
        # Fallback без переводов
        for lang_code in available_locales:
            prefix = "✅ " if lang_code == current_lang_code else "▫️ "
            display_name = lang_code.upper() 
            builder.button(
                text=f"{prefix}{display_name}",
                callback_data=CoreMenuNavigate(target_menu="profile_set_lang", payload=lang_code).pack()
            )
    builder.adjust(1) 
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в профиль", 
            callback_data=CoreMenuNavigate(target_menu="profile").pack()
        )
    )
    return builder.as_markup()

# ... (get_confirm_action_keyboard, get_close_button_keyboard без изменений, т.к. они инлайн)
def get_confirm_action_keyboard(
    confirm_callback_data: str,
    cancel_callback_data: str,
    confirm_text_key: str = "confirm_yes",
    cancel_text_key: str = "confirm_no"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    texts = TEXTS_CORE_KEYBOARDS_EN
    
    builder.button(text=texts[confirm_text_key], callback_data=confirm_callback_data)
    builder.button(text=texts[cancel_text_key], callback_data=cancel_callback_data)
    builder.adjust(2)
    return builder.as_markup()

def get_close_button_keyboard(
    close_text_key: str = "service_delete_message"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    texts = TEXTS_CORE_KEYBOARDS_EN
    builder.button(
        text=texts[close_text_key],
        callback_data=CoreServiceAction(action="delete_this_message").pack()
    )
    return builder.as_markup()