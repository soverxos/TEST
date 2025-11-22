# SwiftDevBot/core/ui/handlers_core_ui.py
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart, Command, StateFilter 
from aiogram.fsm.context import FSMContext 
from aiogram.fsm.state import State, StatesGroup 
from aiogram.utils.markdown import hbold, hitalic, hcode 
import html # <--- ИМПОРТИРУЕМ СТАНДАРТНЫЙ МОДУЛЬ html
from loguru import logger
from aiogram.exceptions import TelegramBadRequest 
from aiogram.types import ReplyKeyboardRemove 

from .callback_data_factories import CoreMenuNavigate, ModuleMenuEntry, ModuleAction, CoreServiceAction 
from .keyboards_core import (
    get_main_menu_reply_keyboard,
    get_modules_list_keyboard, 
    get_welcome_confirmation_keyboard, 
    get_profile_menu_keyboard,         
    get_language_selection_keyboard, 
    TEXTS_CORE_KEYBOARDS_EN 
)
from Systems.core.database.core_models import User as DBUser 
from Systems.core.ui.registry_ui import ModuleUIEntry 
from sqlalchemy import select 
from Systems.core.i18n.translator import Translator
from Systems.core.module_loader import get_module_permission_to_check 

from typing import TYPE_CHECKING, Optional, List, Union, Dict
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession 

core_ui_router = Router(name="sdb_core_ui_handlers")
MODULE_NAME_FOR_LOG = "CoreUI"

# Глобальный кэш для translator
_translator_cache: Optional['Translator'] = None

def _get_translator_for_handler(services_provider: 'BotServicesProvider') -> 'Translator':
    """Получает или создает translator для использования в handlers"""
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

class FSMFeedback(StatesGroup):
    waiting_for_feedback_message = State()

async def show_main_menu_reply(
    message_or_query: Union[types.Message, types.CallbackQuery], 
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
    text_override: Optional[str] = None,
    state: Optional[FSMContext] = None 
):
    if state: 
        current_fsm_state = await state.get_state()
        if current_fsm_state is not None:
            logger.info(f"[{MODULE_NAME_FOR_LOG}] Сброс состояния FSM ({current_fsm_state}) перед показом главного reply-меню для пользователя {sdb_user.telegram_id}.")
            await state.clear()

    user_id = sdb_user.telegram_id
    
    # Перезагружаем пользователя из БД для получения актуального языка
    async with services_provider.db.get_session() as session:
        updated_user = await session.get(DBUser, sdb_user.id)
        if updated_user:
            sdb_user.preferred_language_code = updated_user.preferred_language_code
            user_display_name = updated_user.full_name
        else:
            user_display_name = sdb_user.full_name
    
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} ({user_display_name}) showing main reply menu.")
    
    # Получаем язык пользователя
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    
    # Получаем переводы
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    if text_override:
        text_to_send = text_override
    else:
        default_text = f"🏠 {hbold(t('main_menu_title'))}\n{t('main_menu_greeting', user_name=user_display_name)}"
        text_to_send = default_text
    
    keyboard = await get_main_menu_reply_keyboard(services_provider=services_provider, user_telegram_id=user_id, locale=user_locale)
    
    target_chat_id = message_or_query.chat.id if isinstance(message_or_query, types.Message) else message_or_query.message.chat.id # type: ignore

    if isinstance(message_or_query, types.CallbackQuery) and message_or_query.message:
        try:
            if message_or_query.message.reply_markup: 
                 await message_or_query.message.edit_reply_markup(reply_markup=None)
        except Exception as e_del_edit:
            logger.warning(f"Не удалось изменить/удалить старое сообщение перед показом reply menu: {e_del_edit}")
    
    await bot.send_message(target_chat_id, text_to_send, reply_markup=keyboard)
    
    if isinstance(message_or_query, types.CallbackQuery):
        await message_or_query.answer()


@core_ui_router.message(CommandStart())
async def handle_start_command(
    message: types.Message,
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: Optional[DBUser], 
    state: FSMContext, 
    user_was_just_created: Optional[bool] = False 
):
    user_tg = message.from_user 
    if not user_tg: return

    sdb_user_id = sdb_user.id if sdb_user else "N/A"
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_tg.id} (@{user_tg.username or 'N/A'}) вызвал /start. "
                f"SDB_User DB ID: {sdb_user_id}. Был только что создан (в middleware): {user_was_just_created}.")

    # Получаем язык пользователя
    user_locale = (
        (sdb_user.preferred_language_code if sdb_user else None)
        or message.from_user.language_code
        or services_provider.config.core.i18n.default_locale
    )
    
    # Получаем переводы
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    if not sdb_user:
        user_display_name = f"{user_tg.first_name} {user_tg.last_name or ''}".strip() or user_tg.username or str(user_tg.id)
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Новый пользователь {user_tg.id}. Показ приветственного сообщения.")
        welcome_title = t("welcome_message_title")
        welcome_body = t("welcome_message_body")
        full_welcome_text = f"{hbold(welcome_title)}\n\n{welcome_body}"
        welcome_keyboard = get_welcome_confirmation_keyboard(locale=user_locale, services_provider=services_provider)
        await message.answer(full_welcome_text, reply_markup=welcome_keyboard)
        return

    is_owner_from_config = sdb_user.telegram_id in services_provider.config.core.super_admins
    user_display_name = sdb_user.full_name 

    if is_owner_from_config or not user_was_just_created: 
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} ({'Владелец' if is_owner_from_config else 'существующий'}). Показ главного reply-меню.")
        await show_main_menu_reply(message, bot, services_provider, sdb_user, state=state) 
    else: 
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} новый. Показ приветственного сообщения.")
        welcome_title = t("welcome_message_title")
        welcome_body = t("welcome_message_body")
        full_welcome_text = f"{hbold(welcome_title)}\n\n{welcome_body}"
        welcome_keyboard = get_welcome_confirmation_keyboard(locale=user_locale, services_provider=services_provider)
        await message.answer(full_welcome_text, reply_markup=welcome_keyboard)


@core_ui_router.message(Command("help"))
async def handle_help_command(
    message: types.Message,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
):
    """Обработчик команды /help - показывает список доступных команд."""
    user_tg = message.from_user
    if not user_tg:
        return
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_tg.id} (@{user_tg.username or 'N/A'}) вызвал /help.")
    
    # Получаем язык пользователя
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    try:
        from Systems.core.bot_entrypoint import CORE_COMMANDS_DESCRIPTIONS
        
        # Собираем базовые команды
        help_text_parts = [
            f"{hbold(t('help_title'))}\n",
            f"{hbold(t('help_main_commands'))}\n"
        ]
        
        # Добавляем базовые команды
        for cmd_name, cmd_desc in CORE_COMMANDS_DESCRIPTIONS.items():
            if cmd_name != "help":  # Не показываем саму команду help в списке
                help_text_parts.append(f"/{cmd_name} - {cmd_desc}")
        
        # Собираем команды из модулей
        module_commands = []
        all_loaded_modules_info = services_provider.modules.get_loaded_modules_info(include_system=False, include_plugins=True)
        
        async with services_provider.db.get_session() as session:
            for module_info in all_loaded_modules_info:
                if module_info.manifest and module_info.manifest.commands:
                    for cmd_manifest in module_info.manifest.commands:
                        # Пропускаем админские команды, если у пользователя нет прав
                        if cmd_manifest.admin_only:
                            is_super_admin = sdb_user.telegram_id in services_provider.config.core.super_admins
                            if not is_super_admin:
                                # Проверяем, есть ли у пользователя права администратора через RBAC
                                has_admin_permission = await services_provider.rbac.user_has_permission(
                                    session, 
                                    sdb_user.telegram_id, 
                                    "core.view_admin_panel"
                                )
                                if not has_admin_permission:
                                    continue
                        
                        # Проверяем разрешения модуля для команды (если есть)
                        permission_to_check = get_module_permission_to_check(module_info.name, module_info.manifest)
                        if permission_to_check:
                            has_permission = await services_provider.rbac.user_has_permission(
                                session, sdb_user.telegram_id, permission_to_check
                            )
                            if not has_permission:
                                continue
                        
                        cmd_name = cmd_manifest.command.lstrip("/")
                        cmd_desc = cmd_manifest.description or "Без описания"
                        
                        # Избегаем дубликатов
                        if not any(cmd["name"] == cmd_name for cmd in module_commands):
                            module_commands.append({
                                "name": cmd_name,
                                "description": cmd_desc,
                                "module": module_info.name
                            })
        
        # Добавляем команды модулей, если они есть
        if module_commands:
            help_text_parts.append(f"\n{hbold(t('help_module_commands'))}\n")
            for cmd in module_commands:
                help_text_parts.append(f"/{cmd['name']} - {cmd['description']}")
        
        # Добавляем информацию о главном меню
        help_text_parts.append(f"\n{hitalic(t('help_tip_menu'))}")
        help_text_parts.append(f"{hitalic(t('help_tip_start'))}")
        
        help_text = "\n".join(help_text_parts)
        
        await message.answer(help_text)
        logger.debug(f"[{MODULE_NAME_FOR_LOG}] Команда /help успешно обработана для пользователя {user_tg.id}.")
        
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при обработке команды /help для пользователя {user_tg.id}: {e}", exc_info=True)
        await message.answer(
            f"{hbold('❌ Ошибка')}\n\n"
            f"Не удалось загрузить список команд. Попробуйте позже или обратитесь к администратору."
        )


@core_ui_router.message(Command("login"))
async def handle_login_command(
    message: types.Message,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
):
    """Обработчик команды /login - генерирует токен для входа в веб-панель."""
    user_tg = message.from_user
    if not user_tg:
        return
    
    try:
        # Импортируем JWT handler
        from Systems.web.auth.jwt_handler import get_jwt_handler
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from datetime import timedelta
        import os
        
        # Получаем роль пользователя
        # Сначала проверяем, является ли пользователь супер-админом из .env
        is_super_admin = sdb_user.telegram_id in services_provider.config.core.super_admins
        
        primary_role = None
        if is_super_admin:
            # Если пользователь в списке супер-админов, он автоматически админ
            primary_role = "admin"
            logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} определен как супер-админ из конфигурации.")
        elif sdb_user.roles:
            # Если не супер-админ, проверяем роли из БД
            role_names = [role.name for role in sdb_user.roles]
            if "Admin" in role_names:
                primary_role = "admin"  # lowercase для единообразия
            elif "Moderator" in role_names:
                primary_role = "moderator"
            elif role_names:
                primary_role = role_names[0].lower()
        
        # Получаем время жизни токена из переменной окружения (по умолчанию 60 минут)
        token_lifetime_minutes = int(os.environ.get("SDB_WEB_TOKEN_LIFETIME_MINUTES", "60"))
        
        # Создаем JWT токен
        jwt_handler = get_jwt_handler()
        login_token = await jwt_handler.create_access_token(
            user_id=sdb_user.telegram_id,
            username=sdb_user.username or sdb_user.full_name,
            role=primary_role or "user",  # lowercase по умолчанию
            expires_in=timedelta(minutes=token_lifetime_minutes)
        )
        
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Создан JWT токен для пользователя {sdb_user.telegram_id} с ролью: {primary_role or 'user'}")
        
        # Получаем URL веб-панели
        # Telegram не принимает localhost в кнопках, нужно использовать реальный домен/IP
        web_url = os.environ.get("SDB_WEB_URL")  # Можно задать явно в .env
        
        if not web_url:
            # Если не задан явно, пытаемся определить из настроек
            web_host = os.environ.get("SDB_WEB_HOST", "0.0.0.0")
            web_port = os.environ.get("SDB_WEB_PORT", "80")
            
            # Получаем реальный IP сервера (не localhost)
            import socket
            try:
                # Пытаемся получить внешний IP
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                
                # Если это localhost, используем IP из настроек или пытаемся определить
                if local_ip in ["127.0.0.1", "127.0.1.1"] or web_host in ["0.0.0.0", "127.0.0.1"]:
                    # Пытаемся получить IP из сетевого интерфейса
                    import subprocess
                    try:
                        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
                        if result.returncode == 0 and result.stdout.strip():
                            ips = result.stdout.strip().split()
                            if ips:
                                local_ip = ips[0]
                    except:
                        pass
                    
                    # Если всё равно localhost, используем IP из .env или отправляем токен текстом
                    if local_ip in ["127.0.0.1", "127.0.1.1"]:
                        # Отправляем токен текстом вместо кнопки
                        # Форматируем время жизни токена
                        if token_lifetime_minutes >= 60:
                            time_str = f"{token_lifetime_minutes // 60} час" + ("а" if token_lifetime_minutes // 60 > 1 else "")
                        else:
                            time_str = f"{token_lifetime_minutes} минут"
                        
                        login_text = (
                            f"{hbold('🌐 Вход в веб-панель')}\n\n"
                            f"Скопируйте ссылку ниже и откройте в браузере:\n\n"
                            f"{hcode(f'http://localhost:{web_port}/?token={login_token}')}\n\n"
                            f"{hitalic(f'Ссылка действительна {time_str}.')}"
                        )
                        await message.answer(login_text)
                        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} запросил вход в веб-панель. Токен отправлен текстом (localhost).")
                        return
                    
                web_url = f"http://{local_ip}:{web_port}" if web_port != "80" else f"http://{local_ip}"
            except Exception as e:
                logger.warning(f"[{MODULE_NAME_FOR_LOG}] Не удалось определить IP для URL: {e}. Используется текстовый формат.")
                # Отправляем токен текстом
                # Форматируем время жизни токена
                if token_lifetime_minutes >= 60:
                    time_str = f"{token_lifetime_minutes // 60} час" + ("а" if token_lifetime_minutes // 60 > 1 else "")
                else:
                    time_str = f"{token_lifetime_minutes} минут"
                
                login_text = (
                    f"{hbold('🌐 Вход в веб-панель')}\n\n"
                    f"Скопируйте ссылку ниже и откройте в браузере:\n\n"
                    f"{hcode(f'http://localhost:{web_port}/login?token={login_token}')}\n\n"
                    f"{hitalic(f'Ссылка действительна {time_str}.')}"
                )
                await message.answer(login_text)
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} запросил вход в веб-панель. Токен отправлен текстом (ошибка определения IP).")
                return
        
        # Use root path for better compatibility
        login_url = f"{web_url}/?token={login_token}"
        
        # Создаем кнопку с ссылкой
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть веб-панель", url=login_url)]
        ])
        
        # Отправляем сообщение
        # Форматируем время жизни токена
        if token_lifetime_minutes >= 60:
            time_str = f"{token_lifetime_minutes // 60} час" + ("а" if token_lifetime_minutes // 60 > 1 else "")
        else:
            time_str = f"{token_lifetime_minutes} минут"
        
        login_text = (
            f"{hbold('🌐 Вход в веб-панель')}\n\n"
            f"Нажмите на кнопку ниже, чтобы войти в веб-панель.\n"
            f"{hitalic(f'Ссылка действительна {time_str}.')}"
        )
        
        await message.answer(login_text, reply_markup=keyboard)
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} запросил вход в веб-панель. Токен создан.")
        
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при создании токена входа для пользователя {sdb_user.telegram_id}: {e}", exc_info=True)
        await message.answer(
            f"{hbold('❌ Ошибка')}\n\n"
            f"Не удалось создать ссылку для входа. Попробуйте позже."
        )


@core_ui_router.message(F.text.startswith("/"))
async def handle_module_command_fallback(
    message: types.Message,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser
):
    """
    Универсальный обработчик команд модулей.
    Показывает UI модуля, если команда найдена в манифесте модуля.
    Этот обработчик имеет низкий приоритет, поэтому модули могут переопределить его.
    """
    command_text = message.text
    if not command_text:
        return  # Не команда
    
    # Извлекаем имя команды (без /)
    command_name = command_text.split()[0].lstrip("/").split("@")[0]
    
    # Пропускаем команды ядра
    core_commands = ["start", "help", "login", "reset_password", "cancel_feedback"]
    if command_name in core_commands:
        return  # Это команда ядра, пропускаем
    
    # Ищем команду в манифестах модулей
    all_loaded_modules_info = services_provider.modules.get_loaded_modules_info(include_system=False, include_plugins=True)
    
    for module_info in all_loaded_modules_info:
        if not module_info.manifest or not module_info.manifest.commands:
            continue
        
        for cmd_manifest in module_info.manifest.commands:
            if cmd_manifest.command == command_name:
                # Найдена команда модуля - показываем UI модуля
                logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {sdb_user.telegram_id} called module command /{command_name}, showing module UI")
                
                # Проверяем права доступа
                async with services_provider.db.get_session() as session:
                    # Проверка admin_only
                    if cmd_manifest.admin_only:
                        is_super_admin = sdb_user.telegram_id in services_provider.config.core.super_admins
                        if not is_super_admin:
                            has_admin_permission = await services_provider.rbac.user_has_permission(
                                session, sdb_user.telegram_id, "core.view_admin_panel"
                            )
                            if not has_admin_permission:
                                await message.answer("❌ У вас нет прав администратора для этой команды")
                                return
                    
                    # Проверка разрешений модуля
                    permission_to_check = get_module_permission_to_check(module_info.name, module_info.manifest)
                    if permission_to_check:
                        has_permission = await services_provider.rbac.user_has_permission(
                            session, sdb_user.telegram_id, permission_to_check
                        )
                        if not has_permission:
                            await message.answer("❌ У вас нет прав для использования этой команды")
                            return
                
                # Показываем UI модуля через callback (симулируем нажатие на кнопку модуля)
                from .callback_data_factories import ModuleMenuEntry
                from aiogram.types import CallbackQuery
                
                # Создаем фиктивный callback query для показа UI модуля
                # Но лучше просто вызвать функцию показа UI модуля напрямую
                module_entry = services_provider.ui_registry.get_module_entry(module_info.name)
                if module_entry:
                    # Показываем UI модуля
                    from aiogram.types import InlineKeyboardButton
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    
                    icon = module_entry.icon or "🧩"
                    display_name = module_entry.display_name or module_info.name
                    description = module_entry.description or (module_info.manifest.description if module_info.manifest else "Модуль активен")
                    version = module_info.manifest.version if module_info.manifest else "N/A"
                    
                    # Получаем команды модуля
                    commands = []
                    async with services_provider.db.get_session() as session:
                        is_super_admin = sdb_user.telegram_id in services_provider.config.core.super_admins
                        for cmd in module_info.manifest.commands:
                            if cmd.admin_only:
                                if not is_super_admin:
                                    has_admin_permission = await services_provider.rbac.user_has_permission(
                                        session, sdb_user.telegram_id, "core.view_admin_panel"
                                    )
                                    if not has_admin_permission:
                                        continue
                            
                            if module_info.manifest.declared_permissions:
                                first_permission = module_info.manifest.declared_permissions[0]
                                has_permission = await services_provider.rbac.user_has_permission(
                                    session, sdb_user.telegram_id, first_permission.name
                                )
                                if not has_permission:
                                    continue
                            
                            commands.append(cmd)
                    
                    if commands:
                        text = (
                            f"{icon} **{display_name}**\n\n"
                            f"{description}\n\n"
                            f"📊 **Информация:**\n"
                            f"• Версия: {version}\n"
                            f"• Статус: {'✅ Активен' if module_info.is_loaded_successfully else '❌ Не загружен'}\n\n"
                            f"🎯 **Доступные действия:**\n"
                            f"Выберите действие из списка ниже:"
                        )
                    else:
                        text = (
                            f"{icon} **{display_name}**\n\n"
                            f"{description}\n\n"
                            f"📊 **Информация:**\n"
                            f"• Версия: {version}\n"
                            f"• Статус: {'✅ Активен' if module_info.is_loaded_successfully else '❌ Не загружен'}\n\n"
                            f"💡 Модуль не имеет доступных команд или у вас нет прав для их использования."
                        )
                    
                    builder = InlineKeyboardBuilder()
                    
                    if commands:
                        for cmd in commands:
                            cmd_icon = cmd.icon or "⚙️"
                            cmd_text = f"{cmd_icon} {cmd.description or cmd.command}"
                            builder.row(
                                InlineKeyboardButton(
                                    text=cmd_text,
                                    callback_data=ModuleAction(
                                        module_name=module_info.name,
                                        command=cmd.command,
                                        action="execute"
                                    ).pack()
                                )
                            )
                    
                    builder.row(
                        InlineKeyboardButton(
                            text="🔙 Назад к модулям",
                            callback_data=CoreMenuNavigate(target_menu="modules_list").pack()
                        )
                    )
                    keyboard = builder.as_markup()
                    
                    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
                    return
    
    # Команда не найдена в модулях - ничего не делаем (модуль может обработать её сам)


@core_ui_router.message(Command("reset_password"))
async def handle_reset_password_command(
    message: types.Message,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
):
    """Обработчик команды /reset_password - сброс облачного пароля."""
    user_tg = message.from_user
    if not user_tg:
        return
    
    try:
        from pathlib import Path
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Проверяем, существует ли облачный пароль
        config_dir = Path(__file__).parent.parent.parent.parent / "config"
        cloud_password_file = config_dir / f"cloud_password_{sdb_user.telegram_id}.txt"
        
        if not cloud_password_file.exists():
            await message.answer(
                f"{hbold('ℹ️ Облачный пароль не установлен')}\\n\\n"
                f"У вас ещё нет облачного пароля. Войдите в веб-панель через /login, "
                f"и система предложит вам создать новый пароль."
            )
            logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} попытался сбросить несуществующий пароль.")
            return
        
        # Создаем кнопки подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, сбросить",
                    callback_data=CoreServiceAction(action="confirm_reset_password").pack()
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=CoreServiceAction(action="cancel_reset_password").pack()
                )
            ]
        ])
        
        # Отправляем сообщение с подтверждением
        reset_text = (
            f"{hbold('🔐 Сброс облачного пароля')}\\n\\n"
            f"Вы уверены, что хотите сбросить облачный пароль?\\n\\n"
            f"{hitalic('После сброса вам нужно будет создать новый пароль при следующем входе в веб-панель.')}"
        )
        
        await message.answer(reset_text, reply_markup=keyboard)
        logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {sdb_user.telegram_id} запросил сброс облачного пароля.")
        
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при обработке команды /reset_password для пользователя {sdb_user.telegram_id}: {e}", exc_info=True)
        await message.answer(
            f"{hbold('❌ Ошибка')}\\n\\n"
            f"Не удалось обработать запрос на сброс пароля. Попробуйте позже."
        )


@core_ui_router.callback_query(CoreServiceAction.filter(F.action == "confirm_reset_password"))
async def cq_confirm_reset_password(
    query: types.CallbackQuery,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
):
    """Подтверждение сброса облачного пароля."""
    user_id = sdb_user.telegram_id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} подтвердил сброс облачного пароля.")
    
    try:
        from pathlib import Path
        import os
        
        # Удаляем файл с паролем
        config_dir = Path(__file__).parent.parent.parent.parent / "config"
        cloud_password_file = config_dir / f"cloud_password_{user_id}.txt"
        
        if cloud_password_file.exists():
            os.remove(cloud_password_file)
            logger.success(f"[{MODULE_NAME_FOR_LOG}] Облачный пароль для пользователя {user_id} успешно удалён.")
            
            success_text = (
                f"{hbold('✅ Пароль сброшен')}\\n\\n"
                f"Облачный пароль успешно удалён.\\n\\n"
                f"При следующем входе в веб-панель через /login "
                f"вам будет предложено создать новый пароль."
            )
            
            if query.message:
                try:
                    await query.message.edit_text(success_text)
                except Exception:
                    await bot.send_message(user_id, success_text)
            else:
                await bot.send_message(user_id, success_text)
                
            await query.answer("Пароль сброшен", show_alert=False)
        else:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Файл пароля для пользователя {user_id} не найден при попытке удаления.")
            await query.answer("Пароль уже был удалён", show_alert=True)
            
            if query.message:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                    
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при удалении облачного пароля для пользователя {user_id}: {e}", exc_info=True)
        await query.answer("Ошибка при сбросе пароля", show_alert=True)


@core_ui_router.callback_query(CoreServiceAction.filter(F.action == "cancel_reset_password"))
async def cq_cancel_reset_password(
    query: types.CallbackQuery,
    bot: Bot,
):
    """Отмена сброса облачного пароля."""
    user_id = query.from_user.id if query.from_user else 0
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} отменил сброс облачного пароля.")
    
    cancel_text = (
        f"{hbold('❌ Отменено')}\\n\\n"
        f"Сброс облачного пароля отменён. Ваш текущий пароль остался без изменений."
    )
    
    if query.message:
        try:
            await query.message.edit_text(cancel_text)
        except Exception:
            await bot.send_message(user_id, cancel_text)
    else:
        await bot.send_message(user_id, cancel_text)
        
    await query.answer()



@core_ui_router.callback_query(CoreServiceAction.filter(F.action == "confirm_registration"))
async def cq_confirm_registration_and_show_main_menu(
    query: types.CallbackQuery, 
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: Optional[DBUser],
    state: FSMContext 
):
    user_id = query.from_user.id
    user_full_name = query.from_user.full_name
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} подтвердил регистрацию, показ главного reply-меню.")

    if not sdb_user:
        try:
            sdb_user, created_flag = await services_provider.user_service.process_user_on_start(query.from_user)
            if not sdb_user:
                await query.answer("Ошибка создания профиля. Попробуйте снова.", show_alert=True)
                return
        except Exception as e_create:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Не удалось создать пользователя при подтверждении: {e_create}", exc_info=True)
            await query.answer("Ошибка создания профиля. Обратитесь к администратору.", show_alert=True)
            return
    
    if query.message:
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с приветствием: {e}")
            
    await show_main_menu_reply(query, bot, services_provider, sdb_user, 
                               text_override=f"Отлично, {hbold(user_full_name)}! Вот главное меню:",
                               state=state) 


@core_ui_router.callback_query(CoreServiceAction.filter(F.action == "cancel_registration"))
async def cq_cancel_registration(
    query: types.CallbackQuery, 
    bot: Bot, 
    services_provider: 'BotServicesProvider', 
    state: FSMContext 
):
    user_id = query.from_user.id 
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} отменил регистрацию/продолжение.")
    await state.clear() 
    
    texts = TEXTS_CORE_KEYBOARDS_EN
    cancel_text = texts.get("registration_cancelled_message", "Регистрация отменена.")

    if query.message:
        try:
            await query.message.delete()
        except Exception as e_delete:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Не удалось удалить сообщение после отмены регистрации (user: {user_id}): {e_delete}")
    
    await bot.send_message(user_id, cancel_text, reply_markup=ReplyKeyboardRemove())
    await query.answer()


# Обработчики текстовых сообщений для reply-кнопок
# Используем F.text с проверкой всех возможных переводов
@core_ui_router.message(F.text.in_([
    "🗂 Модули и функции",  # ru
    "🗂 Modules and Features",  # en
    "🗂 Модулі та функції",  # ua
]))
async def handle_text_modules_list(message: types.Message, services_provider: 'BotServicesProvider', sdb_user: DBUser):
    logger.info(f"Пользователь {sdb_user.telegram_id} нажал reply-кнопку 'Модули'")
    await send_modules_list_message(message.chat.id, message.bot, services_provider, sdb_user, page=1)

@core_ui_router.message(F.text.in_([
    "👤 Мой профиль",  # ru
    "👤 My Profile",  # en
    "👤 Мій профіль",  # ua
]))
async def handle_text_profile(message: types.Message, services_provider: 'BotServicesProvider', sdb_user: DBUser):
    logger.info(f"Пользователь {sdb_user.telegram_id} нажал reply-кнопку 'Профиль'")
    # Перезагружаем пользователя из БД для получения актуального языка
    async with services_provider.db.get_session() as session:
        updated_user = await session.get(DBUser, sdb_user.id)
        if updated_user:
            sdb_user.preferred_language_code = updated_user.preferred_language_code
    await send_profile_message(message.chat.id, message.bot, services_provider, sdb_user)

@core_ui_router.message(F.text.in_([
    "✍️ Связаться с нами",  # ru
    "✍️ Contact Us",  # en
    "✍️ Зв'язатися з нами",  # ua
]), StateFilter(None))
async def handle_text_feedback_start_fsm(
    message: types.Message, 
    services_provider: 'BotServicesProvider', 
    sdb_user: DBUser, 
    state: FSMContext
):
    logger.info(f"Пользователь {sdb_user.telegram_id} нажал reply-кнопку 'Обратная связь', вход в FSM.")
    
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    text = t("feedback_request")
    await state.set_state(FSMFeedback.waiting_for_feedback_message)
    await message.answer(text) 

@core_ui_router.message(StateFilter(FSMFeedback.waiting_for_feedback_message), F.text)
async def process_feedback_message(
    message: types.Message, 
    services_provider: 'BotServicesProvider', 
    sdb_user: DBUser, 
    state: FSMContext
):
    feedback_text = message.text
    user_id = sdb_user.telegram_id
    
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    # ИСПОЛЬЗУЕМ html.escape
    user_full_name_escaped = html.escape(sdb_user.full_name) 
    username_escaped = f"@{html.escape(sdb_user.username)}" if sdb_user.username else "(нет username)"
    
    logger.info(f"Получено сообщение обратной связи от {user_id} ({username_escaped}): '{feedback_text[:100]}...'")

    admin_message_header = (
        f"📬 {hbold('Новый отзыв от пользователя!')}\n\n"
        f"👤 От: {user_full_name_escaped}\n"
        f"🆔 Telegram ID: {hcode(str(user_id))}\n"
        f"🔗 Username: {username_escaped}\n"
        f"🕒 Время: {message.date.strftime('%Y-%m-%d %H:%M:%S %Z') if message.date else 'N/A'}\n"
    )
    admin_message_body = f"\n📝 {hbold('Текст отзыва:')}\n{html.escape(feedback_text)}" # ИСПОЛЬЗУЕМ html.escape
    full_admin_message = admin_message_header + admin_message_body
    
    sent_to_admins_count = 0
    if services_provider.config.core.super_admins:
        for admin_tg_id in services_provider.config.core.super_admins:
            try:
                await message.bot.send_message(admin_tg_id, full_admin_message)
                sent_to_admins_count += 1
            except Exception as e:
                logger.error(f"Не удалось отправить обратную связь админу {admin_tg_id}: {e}")
        if sent_to_admins_count > 0:
            logger.info(f"Отзыв успешно отправлен {sent_to_admins_count} супер-администраторам.")
        else:
            logger.warning("Отзыв не был отправлен ни одному супер-администратору (возможно, список пуст или произошли ошибки).")
    else:
        logger.warning("Список супер-администраторов пуст. Отзыв не будет отправлен.")
    
    await message.reply(t("feedback_thanks"))
    await show_main_menu_reply(message, message.bot, services_provider, sdb_user, text_override=t("main_menu_text"), state=state)

@core_ui_router.message(Command("cancel_feedback"), StateFilter(FSMFeedback.waiting_for_feedback_message))
async def cancel_feedback_fsm(
    message: types.Message, 
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
    state: FSMContext
):
    logger.info(f"Пользователь {sdb_user.telegram_id} отменил ввод обратной связи.")
    
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    await message.reply(t("feedback_cancelled"))
    await show_main_menu_reply(message, bot, services_provider, sdb_user, text_override=t("main_menu_text"), state=state)


@core_ui_router.message(F.text.in_([
    "🛠 Администрирование",  # ru
    "🛠 Administration",  # en
    "🛠 Адміністрування",  # ua
]))
async def handle_text_admin_panel(message: types.Message, services_provider: 'BotServicesProvider', sdb_user: DBUser, state: FSMContext): 
    logger.info(f"Пользователь {sdb_user.telegram_id} нажал reply-кнопку 'Админ-панель'")
    await state.clear() 
    from Systems.core.admin.entry.handlers_entry import send_admin_main_menu 
    await send_admin_main_menu(message, services_provider) 


@core_ui_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "main_reply"))
async def cq_nav_to_main_menu_reply(
    query: types.CallbackQuery, 
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
    state: FSMContext 
):
    await show_main_menu_reply(query, bot, services_provider, sdb_user, state=state) 


async def send_modules_list_message(
    chat_id: int, 
    bot: Bot, 
    services_provider: 'BotServicesProvider', 
    sdb_user: DBUser, 
    page: int = 1,
    message_to_edit: Optional[types.Message] = None 
):
    user_id = sdb_user.telegram_id
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    items_per_page = 5
    keyboard = await get_modules_list_keyboard(services_provider, user_id, page, items_per_page, locale=user_locale)
    
    num_module_buttons = 0; total_accessible_items = 0
    if keyboard.inline_keyboard: 
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data and button.callback_data.startswith(ModuleMenuEntry.__prefix__):
                    num_module_buttons +=1

    all_module_ui_entries_temp = services_provider.ui_registry.get_all_module_entries()
    if all_module_ui_entries_temp:
        async with services_provider.db.get_session() as session:
            for entry_temp in all_module_ui_entries_temp:
                if entry_temp.required_permission_to_view:
                    if await services_provider.rbac.user_has_permission(session, user_id, entry_temp.required_permission_to_view):
                        total_accessible_items +=1
                else: total_accessible_items +=1
    
    total_pages = (total_accessible_items + items_per_page - 1) // items_per_page
    total_pages = max(1, total_pages)

    if num_module_buttons == 0 and page == 1: 
        text = t("modules_list_no_modules")
    else: 
        text = t("modules_list_title_template", current_page=page, total_pages=total_pages)
    
    if message_to_edit: 
        try:
            if message_to_edit.text != text or message_to_edit.reply_markup != keyboard:
                await message_to_edit.edit_text(text, reply_markup=keyboard)
            return 
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.warning(f"Не удалось edit modules list (inline pagination): {e}")
            return
        except Exception as e:
            logger.error(f"Ошибка в send_modules_list_message (edit): {e}", exc_info=True)
            return
    
    await bot.send_message(chat_id, text, reply_markup=keyboard)


async def send_profile_message(
    chat_id: int, 
    bot: Bot, 
    services_provider: 'BotServicesProvider', 
    sdb_user: DBUser,
    message_to_edit: Optional[types.Message] = None
):
    # Перезагружаем пользователя из БД для получения актуального языка
    async with services_provider.db.get_session() as session:
        updated_user = await session.get(DBUser, sdb_user.id)
        if updated_user:
            sdb_user.preferred_language_code = updated_user.preferred_language_code
            # Обновляем также другие поля для отображения
            if not sdb_user.created_at and updated_user.created_at:
                sdb_user.created_at = updated_user.created_at
            if not sdb_user.username and updated_user.username:
                sdb_user.username = updated_user.username
            if not sdb_user.full_name and updated_user.full_name:
                sdb_user.full_name = updated_user.full_name
    
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    reg_date_str = sdb_user.created_at.strftime('%d.%m.%Y %H:%M') if sdb_user.created_at else t("profile_no_reg_date")
    username_str = f"@{sdb_user.username}" if sdb_user.username else t("profile_no_username")
    current_lang = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    
    # Получаем название языка из переводов
    lang_key = f"language_{current_lang}"
    lang_display_name = t(lang_key)

    profile_text = t("profile_info_template",
        user_id=str(sdb_user.telegram_id),
        full_name=sdb_user.full_name,
        username=username_str.replace("@", ""),
        registration_date=reg_date_str,
        current_language=lang_display_name
    )
    final_text = f"{hbold(t('profile_title'))}\n\n{profile_text}"
    keyboard = await get_profile_menu_keyboard(sdb_user, services_provider, locale=user_locale)
    
    if message_to_edit:
        try:
            if message_to_edit.text != final_text or message_to_edit.reply_markup != keyboard:
                await message_to_edit.edit_text(final_text, reply_markup=keyboard)
            return
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.warning(f"Не удалось edit profile (inline nav): {e}")
            return
        except Exception as e:
            logger.error(f"Ошибка в send_profile_message (edit): {e}", exc_info=True)
            return
            
    await bot.send_message(chat_id, final_text, reply_markup=keyboard)


@core_ui_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "modules_list"))
async def cq_nav_to_modules_list(
    query: types.CallbackQuery, 
    callback_data: CoreMenuNavigate, 
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser
):
    user_id = sdb_user.telegram_id
    page = callback_data.page if callback_data.page is not None else 1
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} requested modules list (inline nav), page: {page}")
    
    if query.message:
        await send_modules_list_message(query.message.chat.id, bot, services_provider, sdb_user, page, message_to_edit=query.message)
    await query.answer()


@core_ui_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "profile"))
async def cq_nav_to_profile( 
    query: types.CallbackQuery, 
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser 
):
    if query.message:
        await send_profile_message(query.message.chat.id, bot, services_provider, sdb_user, message_to_edit=query.message)
    await query.answer()


@core_ui_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "profile_change_lang_list"))
async def cq_profile_show_language_list(
    query: types.CallbackQuery,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser
):
    user_id = sdb_user.telegram_id
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} requested language selection list.")
    
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    i18n_settings = services_provider.config.core.i18n
    
    current_lang = sdb_user.preferred_language_code or i18n_settings.default_locale
    available_langs = i18n_settings.available_locales
    
    text = t("profile_select_language_title")
    keyboard = await get_language_selection_keyboard(current_lang, available_langs, services_provider=services_provider, locale=user_locale)
    
    if query.message:
        try:
            if query.message.text != text or query.message.reply_markup != keyboard: 
                await query.message.edit_text(text, reply_markup=keyboard)
            await query.answer()
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                 logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка edit_text в cq_profile_show_language_list: {e}")
            await query.answer() 
        except Exception as e:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка в cq_profile_show_language_list: {e}", exc_info=True)
            await query.answer("Ошибка отображения.")

@core_ui_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "profile_set_lang"))
async def cq_profile_set_language(
    query: types.CallbackQuery,
    callback_data: CoreMenuNavigate,
    bot: Bot, 
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser,
    translator: Translator 
):
    new_lang_code = callback_data.payload
    user_id = sdb_user.telegram_id
    
    if not new_lang_code or new_lang_code not in services_provider.config.core.i18n.available_locales:
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] User {user_id} попытался установить некорректный язык: {new_lang_code}")
        await query.answer("Выбран некорректный язык.", show_alert=True)
        if query.message: 
            await send_profile_message(query.message.chat.id, bot, services_provider, sdb_user, message_to_edit=query.message)
        return

    logger.info(f"[{MODULE_NAME_FOR_LOG}] User {user_id} устанавливает язык: {new_lang_code}")
    
    user_service = services_provider.user_service 
    language_updated = False
    async with services_provider.db.get_session() as session: 
        user_in_session = await session.get(DBUser, sdb_user.id) 
        if user_in_session:
            old_lang = user_in_session.preferred_language_code
            logger.debug(f"[{MODULE_NAME_FOR_LOG}] Текущий язык пользователя {user_id} в БД: {old_lang}, новый: {new_lang_code}")
            
            if await user_service.update_user_language(user_in_session, new_lang_code, session):
                try:
                    await session.commit()
                    # Обновляем объект из БД после commit
                    await session.refresh(user_in_session)
                    saved_lang = user_in_session.preferred_language_code
                    logger.info(f"[{MODULE_NAME_FOR_LOG}] После commit язык пользователя {user_id} в БД: {saved_lang}")
                    
                    # Обновляем объект sdb_user
                    sdb_user.preferred_language_code = saved_lang
                    language_updated = True
                    
                    logger.success(f"[{MODULE_NAME_FOR_LOG}] Язык для пользователя {user_id} успешно изменен на {new_lang_code} в БД (подтверждено: {saved_lang}).")
                    
                    # Получаем переводы для сообщения об успехе
                    user_locale = new_lang_code
                    translator = _get_translator_for_handler(services_provider)
                    def t(key: str, **kwargs) -> str:
                        return translator.gettext(key, user_locale, **kwargs)
                    
                    await query.answer(t("profile_language_changed").format(lang=new_lang_code.upper()), show_alert=False)
                except Exception as e_commit:
                    await session.rollback()
                    logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка commit при смене языка для {user_id}: {e_commit}", exc_info=True)
                    
                    # Получаем переводы для сообщения об ошибке
                    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
                    translator = _get_translator_for_handler(services_provider)
                    def t(key: str, **kwargs) -> str:
                        return translator.gettext(key, user_locale, **kwargs)
                    
                    await query.answer(t("profile_language_change_error"), show_alert=True)
            else:
                # Язык уже установлен
                logger.debug(f"[{MODULE_NAME_FOR_LOG}] Язык пользователя {user_id} уже установлен на {new_lang_code}")
                user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
                translator = _get_translator_for_handler(services_provider)
                def t(key: str, **kwargs) -> str:
                    return translator.gettext(key, user_locale, **kwargs)
                
                await query.answer(t("profile_language_already_set").format(lang=new_lang_code.upper()), show_alert=False)
        else: 
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_id} (DB ID: {sdb_user.id}) не найден в БД для обновления языка")
            user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
            translator = _get_translator_for_handler(services_provider)
            def t(key: str, **kwargs) -> str:
                return translator.gettext(key, user_locale, **kwargs)
            
            await query.answer(t("profile_language_user_not_found"), show_alert=True)
    
    # Обновляем профиль с новым языком только если язык был успешно изменен
    if query.message and language_updated:
        # Перезагружаем пользователя из БД для гарантии актуальных данных
        async with services_provider.db.get_session() as session:
            updated_user = await session.get(DBUser, sdb_user.id)
            if updated_user:
                final_lang = updated_user.preferred_language_code
                logger.debug(f"[{MODULE_NAME_FOR_LOG}] Финальная проверка: язык пользователя {user_id} в БД после перезагрузки: {final_lang}")
                sdb_user.preferred_language_code = final_lang
        await send_profile_message(query.message.chat.id, bot, services_provider, sdb_user, message_to_edit=query.message)
    elif query.message:
        # Если язык не был изменен, просто обновляем профиль с текущими данными
        await send_profile_message(query.message.chat.id, bot, services_provider, sdb_user, message_to_edit=query.message)
    

@core_ui_router.callback_query(CoreMenuNavigate.filter(F.target_menu == "feedback_fsm_start"))
async def cq_nav_to_feedback_fsm_start( 
    query: types.CallbackQuery, 
    bot: Bot, 
    services_provider: 'BotServicesProvider', 
    sdb_user: DBUser, 
    state: FSMContext
):
    user_id = query.from_user.id
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} запросил обратную связь (FSM через callback).")
    text = (
        "✍️ Пожалуйста, напишите ваше сообщение для обратной связи.\n"
        f"{hitalic('Для отмены введите /cancel_feedback')}"
    )
    await state.set_state(FSMFeedback.waiting_for_feedback_message)
    
    if query.message:
        try: 
            await query.message.edit_text(text, reply_markup=None) 
        except TelegramBadRequest as e:
             if "message is not modified" not in str(e).lower():
                logger.warning(f"Не удалось отредактировать сообщение перед вводом feedback (callback): {e}")
                await bot.send_message(user_id, text) 
        except Exception as e_edit_fb:
            logger.warning(f"Не удалось отредактировать сообщение перед вводом feedback (callback): {e_edit_fb}")
            await bot.send_message(user_id, text)
    else: 
        await bot.send_message(user_id, text)
    await query.answer()


@core_ui_router.callback_query(CoreServiceAction.filter(F.action == "delete_this_message"))
async def cq_service_action_delete_message(query: types.CallbackQuery):
    user_id = query.from_user.id
    message_id = query.message.message_id if query.message else "N/A"
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} requested to delete message_id: {message_id}")
    
    try:
        if query.message:
            await query.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
            await query.answer("Сообщение удалено.") 
        else:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Не найдено сообщение для удаления по запросу от user {user_id}.")
            await query.answer("Не найдено сообщение для удаления.")
    except TelegramBadRequest as e: 
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Не удалось удалить сообщение {message_id} для user {user_id}: {e} (возможно, уже удалено или нет прав).")
        await query.answer() 
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при удалении сообщения {message_id} для user {user_id}: {e}", exc_info=True)
        await query.answer("Ошибка при удалении сообщения.", show_alert=True)


@core_ui_router.callback_query(ModuleMenuEntry.filter())
async def cq_module_entry_default(
    query: types.CallbackQuery,
    callback_data: ModuleMenuEntry,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser
):
    """
    Универсальный обработчик для входа в модуль через UI.
    Этот обработчик работает как fallback, если модуль не зарегистрировал свой собственный обработчик.
    Модули могут переопределить этот обработчик, зарегистрировав свой с более высоким приоритетом.
    """
    user_id = sdb_user.telegram_id
    module_name = callback_data.module_name
    
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} requested entry to module '{module_name}'")
    
    # Получаем информацию о модуле из UIRegistry
    module_entry = services_provider.ui_registry.get_module_entry(module_name)
    if not module_entry:
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Module entry '{module_name}' not found in UIRegistry")
        await query.answer("❌ Модуль не найден", show_alert=True)
        return
    
    # Проверяем разрешения, если требуется
    if module_entry.required_permission_to_view:
        async with services_provider.db.get_session() as session:
            has_permission = await services_provider.rbac.user_has_permission(
                session, user_id, module_entry.required_permission_to_view
            )
            if not has_permission:
                await query.answer("❌ У вас нет доступа к этому модулю", show_alert=True)
                return
    
    # Получаем информацию о модуле из ModuleLoader
    module_info = services_provider.modules.get_module_info(module_name)
    if not module_info:
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Module info for '{module_name}' not found")
        await query.answer("❌ Информация о модуле не найдена", show_alert=True)
        return
    
    # Получаем язык пользователя
    user_locale = sdb_user.preferred_language_code or services_provider.config.core.i18n.default_locale
    translator = _get_translator_for_handler(services_provider)
    
    def t(key: str, **kwargs) -> str:
        return translator.gettext(key, user_locale, **kwargs)
    
    # Создаем базовое сообщение о модуле
    icon = module_entry.icon or "🧩"
    display_name = module_entry.display_name or module_name
    description = module_entry.description or (module_info.manifest.description if module_info.manifest else "Модуль активен")
    version = module_info.manifest.version if module_info.manifest else "N/A"
    
    # Получаем команды из манифеста
    commands = []
    if module_info.manifest and module_info.manifest.commands:
        async with services_provider.db.get_session() as session:
            is_super_admin = user_id in services_provider.config.core.super_admins
            for cmd_manifest in module_info.manifest.commands:
                # Проверяем права доступа к команде
                if cmd_manifest.admin_only:
                    if not is_super_admin:
                        has_admin_permission = await services_provider.rbac.user_has_permission(
                            session, user_id, "core.view_admin_panel"
                        )
                        if not has_admin_permission:
                            continue
                
                # Проверяем разрешения модуля для команды (если есть)
                permission_to_check = get_module_permission_to_check(module_info.name, module_info.manifest)
                if permission_to_check:
                    has_permission = await services_provider.rbac.user_has_permission(
                        session, user_id, permission_to_check
                    )
                    if not has_permission:
                        continue
                
                commands.append(cmd_manifest)
    
    # Формируем текст сообщения
    if commands:
        text = (
            f"{icon} **{display_name}**\n\n"
            f"{description}\n\n"
            f"📊 **Информация:**\n"
            f"• Версия: {version}\n"
            f"• Статус: {'✅ Активен' if module_info.is_loaded_successfully else '❌ Не загружен'}\n\n"
            f"🎯 **Доступные действия:**\n"
            f"Выберите действие из списка ниже:"
        )
    else:
        text = (
            f"{icon} **{display_name}**\n\n"
            f"{description}\n\n"
            f"📊 **Информация:**\n"
            f"• Версия: {version}\n"
            f"• Статус: {'✅ Активен' if module_info.is_loaded_successfully else '❌ Не загружен'}\n\n"
            f"💡 Модуль не имеет доступных команд или у вас нет прав для их использования."
        )
    
    # Создаем клавиатуру с кнопками команд
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    if commands:
        # Группируем команды по категориям
        commands_by_category: Dict[str, List] = {}
        commands_without_category = []
        
        for cmd in commands:
            category = cmd.category or "Общие"
            if category not in commands_by_category:
                commands_by_category[category] = []
            commands_by_category[category].append(cmd)
        
        # Добавляем команды по категориям
        for category, category_commands in sorted(commands_by_category.items()):
            for cmd in category_commands:
                cmd_icon = cmd.icon or "⚙️"
                cmd_text = f"{cmd_icon} {cmd.description or cmd.command}"
                builder.row(
                    InlineKeyboardButton(
                        text=cmd_text,
                        callback_data=ModuleAction(
                            module_name=module_name,
                            command=cmd.command,
                            action="execute"
                        ).pack()
                    )
                )
    
    # Кнопка "Назад к модулям"
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к модулям",
            callback_data=CoreMenuNavigate(target_menu="modules_list").pack()
        )
    )
    keyboard = builder.as_markup()
    
    # Отправляем или редактируем сообщение
    try:
        if query.message:
            await query.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка редактирования сообщения для модуля '{module_name}': {e}")
    except Exception as e:
        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при обработке входа в модуль '{module_name}': {e}", exc_info=True)
        await query.answer("❌ Ошибка при открытии модуля", show_alert=True)
        return
    
    await query.answer()


@core_ui_router.callback_query(ModuleAction.filter())
async def cq_module_action(
    query: types.CallbackQuery,
    callback_data: ModuleAction,
    bot: Bot,
    services_provider: 'BotServicesProvider',
    sdb_user: DBUser
):
    """
    Универсальный обработчик для действий модулей (команд).
    Выполняет команду модуля или показывает её интерфейс.
    """
    user_id = sdb_user.telegram_id
    module_name = callback_data.module_name
    command = callback_data.command
    action = callback_data.action or "execute"
    
    logger.debug(f"[{MODULE_NAME_FOR_LOG}] User {user_id} requested action '{action}' for command '{command}' in module '{module_name}'")
    
    # Получаем информацию о модуле
    module_info = services_provider.modules.get_module_info(module_name)
    if not module_info or not module_info.manifest:
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Module info or manifest for '{module_name}' not found")
        await query.answer("❌ Модуль не найден", show_alert=True)
        return
    
    # Находим команду в манифесте
    cmd_manifest = None
    for cmd in module_info.manifest.commands:
        if cmd.command == command:
            cmd_manifest = cmd
            break
    
    if not cmd_manifest:
        logger.warning(f"[{MODULE_NAME_FOR_LOG}] Command '{command}' not found in module '{module_name}' manifest")
        await query.answer("❌ Команда не найдена", show_alert=True)
        return
    
    # Проверяем права доступа
    async with services_provider.db.get_session() as session:
        # Проверка admin_only
        if cmd_manifest.admin_only:
            is_super_admin = user_id in services_provider.config.core.super_admins
            if not is_super_admin:
                has_admin_permission = await services_provider.rbac.user_has_permission(
                    session, user_id, "core.view_admin_panel"
                )
                if not has_admin_permission:
                    await query.answer("❌ У вас нет прав администратора для этой команды", show_alert=True)
                    return
        
        # Проверка разрешений модуля
        permission_to_check = get_module_permission_to_check(module_info.name, module_info.manifest)
        if permission_to_check:
            has_permission = await services_provider.rbac.user_has_permission(
                session, user_id, permission_to_check
            )
            if not has_permission:
                await query.answer("❌ У вас нет прав для использования этой команды", show_alert=True)
                return
    
    # Выполняем действие
    if action == "execute":
        # Пытаемся найти обработчик команды в модуле
        # Если модуль не имеет собственного обработчика, показываем базовое сообщение
        cmd_icon = cmd_manifest.icon or "⚙️"
        cmd_description = cmd_manifest.description or command
        
        text = (
            f"{cmd_icon} **{cmd_description}**\n\n"
            f"Команда `/{command}` выполнена.\n\n"
            f"💡 Эта команда не имеет собственного обработчика в модуле.\n"
            f"Используйте команду `/{command}` для полного функционала."
        )
        
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 Назад к модулю",
                callback_data=ModuleMenuEntry(module_name=module_name).pack()
            )
        )
        keyboard = builder.as_markup()
        
        try:
            if query.message:
                await query.message.edit_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.warning(f"[{MODULE_NAME_FOR_LOG}] Ошибка редактирования сообщения для команды '{command}': {e}")
        except Exception as e:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при выполнении команды '{command}': {e}", exc_info=True)
            await query.answer("❌ Ошибка при выполнении команды", show_alert=True)
            return
    
    await query.answer()