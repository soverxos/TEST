# core/bot_entrypoint.py

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone

from loguru import logger as global_logger

if not (hasattr(global_logger, '_core') and hasattr(global_logger._core, 'handlers') and global_logger._core.handlers):
    try:
        global_logger.remove()
        global_logger.add(sys.stderr, level="DEBUG")
        print("!!! [SDB bot_entrypoint WARNING] Loguru handlers был пуст или недоступен, добавлен stderr по умолчанию. !!!", file=sys.stderr)
    except Exception as e_loguru_init_fallback_entry:
        print(f"!!! [SDB bot_entrypoint CRITICAL] Loguru handlers пуст и не удалось добавить stderr: {e_loguru_init_fallback_entry} !!!", file=sys.stderr)


from aiogram import Bot, Dispatcher, __version__ as aiogram_version
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
# <--- ИЗМЕНЕНИЕ: УДАЛЕН ИМПОРТ RedisStorage ОТСЮДА ---
# from aiogram.fsm.storage.redis import RedisStorage
from aiogram.exceptions import TelegramRetryAfter

from Systems.core.app_settings import settings
from Systems.core.services_provider import BotServicesProvider
from Systems.core.module_loader import ModuleLoader
from Systems.core.ui.handlers_core_ui import core_ui_router
from Systems.core.i18n.middleware import I18nMiddleware
from Systems.core.i18n.translator import Translator
from Systems.core.users.middleware import UserStatusMiddleware
from Systems.core.logging_manager import LoggingManager

if TYPE_CHECKING:
    from aiogram.fsm.storage.redis import RedisStorage # <--- ИЗМЕНЕНИЕ: Импорт для type hinting

PID_FILENAME = "sdb_bot.pid"
CORE_COMMANDS_DESCRIPTIONS = {
    "start": "🚀 Запустить бота / Показать главное меню",
    "help": "❓ Помощь и список команд бота",
    "login": "🌐 Войти в веб-панель",
}

try:
    from Systems.core.admin import admin_router
    ADMIN_ROUTER_AVAILABLE = True
    global_logger.info("Главный админ-роутер (Systems.core.admin.admin_router) успешно импортирован.")
except ImportError:
    admin_router = None
    ADMIN_ROUTER_AVAILABLE = False
    global_logger.info("Главный админ-роутер не найден или не может быть импортирован. Админ-панель будет неактивна.")


async def _setup_bot_commands(bot: Bot, services: 'BotServicesProvider', admin_router_available: bool):
    module_name_for_log = "CoreBotSetup"
    global_logger.debug(f"[{module_name_for_log}] Начало установки команд бота в Telegram...")

    final_commands_dict: Dict[str, str] = {}

    for cmd_name, cmd_desc in CORE_COMMANDS_DESCRIPTIONS.items():
        if cmd_name not in final_commands_dict:
            final_commands_dict[cmd_name] = cmd_desc
    global_logger.trace(f"[{module_name_for_log}] Добавлены базовые команды ядра: {list(CORE_COMMANDS_DESCRIPTIONS.keys())}")

    all_loaded_plugin_modules_info = services.modules.get_loaded_modules_info(include_system=False, include_plugins=True)
    for module_info in all_loaded_plugin_modules_info:
        if module_info.manifest and module_info.manifest.commands:
            global_logger.trace(f"[{module_name_for_log}] Проверка команд для плагина: {module_info.name}")
            for cmd_manifest in module_info.manifest.commands:
                if not cmd_manifest.admin_only:
                    if cmd_manifest.command not in final_commands_dict:
                        final_commands_dict[cmd_manifest.command] = cmd_manifest.description

    # Команда /admin убрана из глобального списка команд по соображениям безопасности
    # Доступ к админ-панели осуществляется только через кнопку в главном меню
    # и скрытую команду /admin_cp для супер-администраторов
    if admin_router_available:
        global_logger.trace(f"[{module_name_for_log}] Админ-роутер доступен, но команда /admin не добавлена в глобальный список команд (безопасность)")

    final_bot_commands = [
        BotCommand(command=name, description=desc) for name, desc in final_commands_dict.items()
    ]

    if final_bot_commands:
        try:
            await bot.set_my_commands(final_bot_commands)
            global_logger.success(f"[{module_name_for_log}] Установлено {len(final_bot_commands)} команд бота в Telegram: "
                                  f"{[cmd.command for cmd in final_bot_commands]}")
        except Exception as e:
            global_logger.error(f"[{module_name_for_log}] Ошибка при установке команд бота: {e}", exc_info=True)
    else:
        global_logger.warning(f"[{module_name_for_log}] Нет команд для установки в Telegram.")


async def run_sdb_bot() -> int:
    # Загружаем .env файл в переменные окружения
    from dotenv import load_dotenv
    load_dotenv('.env')
    
    from Systems.core.app_settings import load_app_settings
    settings = load_app_settings()
    
    current_process_start_time = datetime.now(timezone.utc)
    sdb_version = settings.core.sdb_version

    logging_manager = LoggingManager(app_settings=settings)
    await logging_manager.initialize_logging()

    global_logger.info(f"Система логирования инициализирована. "
                       f"Уровень консольного лога: {settings.core.log_level.upper()} (может быть переопределен SDB_CLI_DEBUG_MODE_FOR_LOGGING). "
                       f"Уровень файлового лога всегда DEBUG (или TRACE, если так задано в LoggingManager).")

    global_logger.info(f"🚀 Запуск SwiftDevBot (SDB) v{sdb_version} в {current_process_start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}...")
    global_logger.info(f"🐍 Используется Python v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    global_logger.info(f"🤖 Используется Aiogram v{aiogram_version}")
    global_logger.debug(f"Каталог запуска (CWD): {Path.cwd()}")
    global_logger.debug(f"Корень проекта: {settings.core.project_data_path.parent}")
    global_logger.debug(f"Директория данных проекта: {settings.core.project_data_path}")

    pid_file_actual_path = settings.core.project_data_path / PID_FILENAME
    bot: Optional[Bot] = None
    services: Optional[BotServicesProvider] = None
    exit_code_internal = 1

    if pid_file_actual_path.exists():
        try:
            old_pid = int(pid_file_actual_path.read_text().strip())
            if sys.platform != "win32":
                os.kill(old_pid, 0)
                global_logger.error(f"Обнаружен активный PID-файл ({pid_file_actual_path}) для работающего процесса PID {old_pid}. "
                                   f"Новый запуск SDB (PID: {os.getpid()}) не может быть выполнен. Остановите предыдущий экземпляр.")
                if logging_manager: await logging_manager.shutdown_logging()
                return 1
        except (OSError, ValueError):
            global_logger.info(f"Удаление устаревшего или некорректного PID-файла: {pid_file_actual_path}")
            pid_file_actual_path.unlink(missing_ok=True)
        except Exception as e_pid_precheck:
             global_logger.warning(f"Ошибка при предварительной проверке PID-файла: {e_pid_precheck}")

    try:
        pid_file_actual_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pid_file_actual_path, "w") as f:
            f.write(str(os.getpid()))
        global_logger.info(f"PID {os.getpid()} записан в {pid_file_actual_path}")
    except Exception as e_pid_write:
        global_logger.error(f"Не удалось создать/записать PID-файл {pid_file_actual_path}: {e_pid_write}. "
                           "Бот продолжит работу, но управление через PID-файл может быть нарушено.")
    try:
        services = BotServicesProvider(settings=settings)
        await services.setup_services()
        global_logger.success("✅ BotServicesProvider и все его базовые сервисы успешно инициализированы.")

        # Проверка наличия токена непосредственно перед созданием бота
        if not services.config.telegram.token:
            global_logger.critical("BOT_TOKEN отсутствует. Укажите токен в .env или YAML перед запуском бота.")
            if logging_manager:
                await logging_manager.shutdown_logging()
            return 1

        bot = Bot(
            token=services.config.telegram.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        me = await bot.get_me()
        global_logger.info(f"🤖 Экземпляр Telegram Bot успешно создан: @{me.username} (ID: {me.id})")

        # <--- ИЗМЕНЕНИЕ: УСЛОВНЫЙ ИМПОРТ И СОЗДАНИЕ ХРАНИЛИЩА ---
        storage: Union[MemoryStorage, "RedisStorage"]

        if services.config.cache.type == "redis" and services.cache.is_available():
            try:
                # Импортируем RedisStorage только здесь
                from aiogram.fsm.storage.redis import RedisStorage
                
                redis_client_instance = await services.cache.get_redis_client_instance()
                if redis_client_instance:
                    storage = RedisStorage(redis=redis_client_instance)
                    global_logger.info("FSM Storage: используется RedisStorage.")
                else:
                    global_logger.warning("Redis сконфигурирован, но клиент Redis недоступен для FSM. Используется MemoryStorage.")
                    storage = MemoryStorage()
            except ImportError:
                global_logger.critical("Выбран тип кэша/FSM 'redis', но библиотека 'redis' не установлена! Установите ее: pip install redis")
                global_logger.warning("FSM Storage: Фоллбэк на MemoryStorage из-за отсутствия библиотеки redis.")
                storage = MemoryStorage()
        else:
            storage = MemoryStorage()
            if services.config.cache.type == "redis":
                global_logger.warning("Redis был выбран для кэша, но CacheManager недоступен. Используется MemoryStorage для FSM.")
            global_logger.info("FSM Storage: используется MemoryStorage.")
        # <--- КОНЕЦ ИЗМЕНЕНИЯ ---

        dp = Dispatcher(storage=storage, services_provider=services)
        global_logger.info("🚦 Dispatcher и FSM Storage инициализированы.")

        translator = Translator(
            locales_dir=settings.core.i18n.locales_dir,
            domain=settings.core.i18n.domain,
            default_locale=settings.core.i18n.default_locale,
            available_locales=settings.core.i18n.available_locales
        )
        dp.update.outer_middleware(I18nMiddleware(translator))
        global_logger.info("I18nMiddleware зарегистрирован для всех Update.")

        dp.update.outer_middleware(UserStatusMiddleware())
        global_logger.info("UserStatusMiddleware зарегистрирован для всех Update.")

        dp.include_router(core_ui_router)
        global_logger.info(f"Базовый UI-роутер ядра '{core_ui_router.name}' зарегистрирован.")

        if ADMIN_ROUTER_AVAILABLE and admin_router:
            try:
                dp.include_router(admin_router)
                global_logger.critical(f"✅ Главный админ-роутер '{admin_router.name}' успешно зарегистрирован")
            except Exception as e:
                global_logger.critical(f"❌ Ошибка при регистрации админ-роутера: {e}", exc_info=True)
        else:
            global_logger.critical(f"❌ Админ-роутер не зарегистрирован: ADMIN_ROUTER_AVAILABLE={ADMIN_ROUTER_AVAILABLE}, admin_router={'существует' if admin_router else 'отсутствует'}")

        module_loader: ModuleLoader = services.modules
        await module_loader.initialize_and_setup_modules(dp=dp, bot=bot)

        num_enabled_plugins = len(module_loader.enabled_plugin_names)
        num_loaded_plugins = sum(1 for mi in module_loader.get_loaded_modules_info(include_system=False, include_plugins=True) if mi.is_enabled)

        global_logger.info(
            f"🧩 Загрузка плагинов из 'Modules/': {num_loaded_plugins} из {num_enabled_plugins} активных успешно загружено."
        )
        if num_loaded_plugins < num_enabled_plugins:
            global_logger.warning("⚠️ Не все активные плагины были успешно загружены. Смотрите логи выше.")

        global_logger.debug("Все роутеры (ядра, системные, плагины) зарегистрированы в Dispatcher.")

        if settings.core.setup_bot_commands_on_startup:
            await _setup_bot_commands(bot, services, admin_router_available=ADMIN_ROUTER_AVAILABLE)
        else:
            global_logger.info("Автоматическая установка команд бота отключена в настройках.")

        @dp.startup()
        async def on_bot_startup():
            nonlocal sdb_version
            bot_info = await bot.get_me()
            services.logger.info(f"🚀 Инициализация SDB Core - Dispatcher startup для @{bot_info.username}...")
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                services.logger.info("Webhook удален, ожидающие обновления сброшены.")
            except Exception as e_startup_hook:
                services.logger.error(f"Ошибка на этапе startup диспетчера: {e_startup_hook}", exc_info=True)

            services.logger.success(f"⚡ SDB Core v{sdb_version} - Система активирована! @{bot_info.username} готов к работе!")
            if services.config.core.super_admins and services.config.core.enable_startup_shutdown_notifications:
                for admin_id in services.config.core.super_admins:
                    try:
                        await bot.send_message(admin_id, f"🚀 **SDB Core v{sdb_version}**\n\n⚡ Система активирована\n🔧 Модули загружены\n🌐 API подключен\n\n@{bot_info.username} готов к работе! 🎯")
                    except Exception as e_send:
                        services.logger.warning(f"Не удалось отправить уведомление о запуске админу {admin_id}: {e_send}")
            elif not services.config.core.enable_startup_shutdown_notifications:
                services.logger.info("🔕 Уведомления о запуске/остановке отключены в настройках.")

        @dp.shutdown()
        async def on_bot_shutdown():
            nonlocal logging_manager
            bot_info = await bot.get_me()
            services.logger.info(f"🔄 SDB Core shutdown - Начало деактивации системы @{bot_info.username}...")

            if services and services.config.core.super_admins and services.config.core.enable_startup_shutdown_notifications:
                for admin_id in services.config.core.super_admins:
                    try:
                        await bot.send_message(admin_id, f"🔄 **SDB Core v{sdb_version}**\n\n⏳ Система деактивируется\n🛡️ Завершение процессов\n💾 Сохранение данных\n\n@{bot_info.username} переходит в режим ожидания...")
                    except Exception as e_send:
                         services.logger.warning(f"Не удалось отправить уведомление об остановке админу {admin_id}: {e_send}")
            elif services and not services.config.core.enable_startup_shutdown_notifications:
                services.logger.info("🔕 Уведомления о запуске/остановке отключены в настройках.")

            if logging_manager:
                await logging_manager.shutdown_logging()

            if pid_file_actual_path.exists():
                try:
                    pid_in_file = int(pid_file_actual_path.read_text().strip())
                    if pid_in_file == os.getpid():
                        pid_file_actual_path.unlink(missing_ok=True)
                        global_logger.info(f"PID-файл {pid_file_actual_path} удален при штатной остановке (on_bot_shutdown).")
                    else:
                         global_logger.info(f"PID-файл {pid_file_actual_path} (PID: {pid_in_file}) не принадлежит текущему процессу (PID: {os.getpid()}). Удаление пропущено в on_bot_shutdown.")
                except Exception as e_unlink_pid_shutdown:
                    global_logger.error(f"Не удалось удалить PID-файл {pid_file_actual_path} в on_bot_shutdown: {e_unlink_pid_shutdown}")

            global_logger.info(f"✅ SDB Core shutdown завершен для @{bot_info.username} (сервисы будут закрыты в finally).")

        bot_username_for_log = (await bot.get_me()).username
        global_logger.info(f"🌐 SDB Core - Запуск Telegram Bot Polling для @{bot_username_for_log}...")

        await dp.start_polling(bot)
        exit_code_internal = 0

    except (KeyboardInterrupt, SystemExit) as e_exit:
        global_logger.info(f"🚨 Получен сигнал остановки ({type(e_exit).__name__}). Поллинг прерывается...")
        exit_code_internal = 0
    except Exception as e_main_run:
        global_logger.critical(f"❌ КРИТИЧЕСКАЯ ОШИБКА в основной функции run_sdb_bot: {e_main_run}", exc_info=True)
        exit_code_internal = 1
    finally:
        global_logger.info("Блок finally в run_sdb_bot.")

        if bot:
            try:
                global_logger.info("Закрытие сессии бота будет обработано Aiogram при завершении Dispatcher.start_polling.")
            except TelegramRetryAfter as e_retry:
                global_logger.warning(f"TelegramRetryAfter при попытке закрыть сессию бота (или уже во время ее закрытия Aiogram): {e_retry}")
            except Exception as e_bot_close:
                global_logger.warning(f"Предупреждение при операциях с объектом бота в finally: {type(e_bot_close).__name__} - {e_bot_close}", exc_info=True)

        if services:
            try:
                await services.close_services()
                global_logger.info("Все сервисы BotServicesProvider корректно остановлены в блоке finally.")
            except Exception as e_services_close:
                global_logger.error(f"Ошибка при закрытии сервисов в блоке finally: {e_services_close}", exc_info=True)

        if logging_manager and logging_manager._is_initialized:
            await logging_manager.shutdown_logging()

        if pid_file_actual_path.exists():
            try:
                pid_in_file = int(pid_file_actual_path.read_text().strip())
                if pid_in_file == os.getpid():
                    pid_file_actual_path.unlink(missing_ok=True)
                    global_logger.info(f"PID-файл {pid_file_actual_path} удален/проверен в блоке finally.")
            except Exception as e_final_pid_unlink:
                global_logger.warning(f"Не удалось окончательно удалить/проверить PID-файл {pid_file_actual_path}: {e_final_pid_unlink}")

        bot_name_display = getattr(bot, 'id', 'N/A') if bot else 'N/A'
        if bot and hasattr(bot, 'username') and bot.username:
            bot_name_display = f"@{bot.username} (ID: {bot.id})"

        global_logger.info(f"🎯 SDB Core завершен ({bot_name_display}) - Код выхода: {exit_code_internal}")
        return exit_code_internal