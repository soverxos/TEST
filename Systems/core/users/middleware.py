# SwiftDevBot/core/users/middleware.py
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as AiogramUser, Update 
from loguru import logger
from datetime import datetime, timezone 

from Systems.core.database.core_models import User as DBUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from Systems.core.ui.keyboards_core import TEXTS_CORE_KEYBOARDS_EN
from Systems.core.ui.callback_data_factories import CoreServiceAction


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from Systems.core.users.service import UserService 

MODULE_NAME_FOR_LOG = "UserStatusMiddleware"

class UserStatusMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update, 
        data: Dict[str, Any]
    ) -> Any:
        
        aiogram_event_user: Optional[AiogramUser] = data.get("event_from_user")
        if not aiogram_event_user:
            return await handler(event, data)

        user_tg_id = aiogram_event_user.id
        user_mention = f"@{aiogram_event_user.username}" if aiogram_event_user.username else f"ID:{user_tg_id}"
        
        services_provider: Optional['BotServicesProvider'] = data.get("services_provider")
        if not (services_provider and hasattr(services_provider, 'db') and hasattr(services_provider, 'user_service')):
            logger.critical(f"[{MODULE_NAME_FOR_LOG}] Необходимые сервисы (DBManager, UserService) не инициализированы "
                           f"или отсутствуют в data. Проверка/создание пользователя {user_mention} невозможно. Прерывание.")
            if event.message: await event.message.reply("Ошибка конфигурации сервисов бота. Пожалуйста, сообщите администратору.")
            elif event.callback_query: await event.callback_query.answer("Ошибка конфигурации сервисов.", show_alert=True)
            return None

        db_user: Optional[DBUser] = None
        user_service: 'UserService' = services_provider.user_service
        user_was_created_in_this_middleware_call = False # Флаг для этого вызова middleware

        try:
            async with services_provider.db.get_session() as session:
                stmt = select(DBUser).where(DBUser.telegram_id == user_tg_id)
                result = await session.execute(stmt)
                db_user = result.scalars().first()
        except Exception as e_get_user:
            logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка БД при первоначальном получении пользователя {user_mention}: {e_get_user}", exc_info=True)
            if event.message: await event.message.reply("Внутренняя ошибка сервера. Попробуйте позже.")
            elif event.callback_query: await event.callback_query.answer("Внутренняя ошибка сервера.", show_alert=True)
            return None

        is_owner_from_config = user_tg_id in services_provider.config.core.super_admins
        is_start_command = event.message and event.message.text and event.message.text.startswith("/start")
        callback_data = None
        if event.callback_query and event.callback_query.data:
            try:
                callback_data = CoreServiceAction.unpack(event.callback_query.data)
            except ValueError:
                callback_data = None
        is_confirm_registration_callback = callback_data is not None and callback_data.action == "confirm_registration"
        is_cancel_registration_callback = callback_data is not None and callback_data.action == "cancel_registration"

        if not db_user: 
            if is_start_command:
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} не найден в БД. Показываем приветствие и откладываем создание.")
                data['sdb_user'] = None
                data['user_was_just_created'] = False
                data['pending_registration_user'] = aiogram_event_user
                data['pending_registration_action'] = 'start'
                return await handler(event, data)
            if is_owner_from_config:
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Владелец {user_mention} не найден в БД. Создание пользователя (без задержки).")
                try:
                    processed_user, created_flag = await user_service.process_user_on_start(aiogram_event_user)
                    db_user = processed_user
                    if created_flag:
                        user_was_created_in_this_middleware_call = True
                    if not db_user:
                        logger.error(f"[{MODULE_NAME_FOR_LOG}] UserService.process_user_on_start не смог создать владельца {user_mention}.")
                        if event.message: await event.message.reply("Ошибка регистрации владельца. Обратитесь к администратору.")
                        elif event.callback_query: await event.callback_query.answer("Ошибка регистрации владельца.", show_alert=True)
                        return None
                except Exception as e_create_mw:
                    logger.error(f"[{MODULE_NAME_FOR_LOG}] Исключение при создании владельца {user_mention}: {e_create_mw}", exc_info=True)
                    if event.message: await event.message.reply("Критическая ошибка при обработке вашего профиля.")
                    elif event.callback_query: await event.callback_query.answer("Критическая ошибка профиля.", show_alert=True)
                    return None
            elif is_confirm_registration_callback:
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Подтверждение регистрации от {user_mention}, пользователь ещё не создан.")
                data['sdb_user'] = None
                data['pending_registration_user'] = aiogram_event_user
                data['pending_registration_action'] = 'confirm_registration'
                return await handler(event, data)
            elif is_cancel_registration_callback:
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} отменил регистрацию (middleware пропускает).")
                data['sdb_user'] = None
                return await handler(event, data)
            else: 
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} не найден в БД и это не /start/владелец. Отправка призыва к регистрации.")
                please_register_text = TEXTS_CORE_KEYBOARDS_EN.get("user_middleware_please_register", "Пожалуйста, используйте /start для начала работы с ботом.")
                # ... (отправка сообщения и return None)
                if event.message:
                    try: await event.message.reply(please_register_text)
                    except Exception as e_reply: logger.error(f"Не удалось отправить сообщение о регистр. {user_mention}: {e_reply}")
                elif event.callback_query:
                    try: await event.callback_query.answer(please_register_text, show_alert=True)
                    except Exception as e_answer: logger.error(f"Не удалось ответить на callback о регистр. {user_mention}: {e_answer}")
                return None 
        elif not is_start_command: 
            logger.trace(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} найден. Вызов process_user_on_start для обновления...")
            try:
                processed_user, _ = await user_service.process_user_on_start(aiogram_event_user) # Флаг created здесь не так важен
                if processed_user:
                    db_user = processed_user 
                else: 
                    logger.warning(f"[{MODULE_NAME_FOR_LOG}] process_user_on_start вернул None для существующего пользователя {user_mention} в middleware.")
            except Exception as e_update_mw:
                 logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка при обновлении данных существующего пользователя {user_mention} в middleware: {e_update_mw}", exc_info=True)
        
        if not db_user:
            logger.critical(f"[{MODULE_NAME_FOR_LOG}] db_user отсутствует после всех попыток получения/создания для {user_mention}. Прерывание.")
            return None

        # Проверки is_active и is_bot_blocked (без изменений)
        if not db_user.is_active:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} (DB ID: {db_user.id}) неактивен. Доступ запрещен.")
            if event.message:
                await event.message.reply("❌ Ваш аккаунт неактивен. Обратитесь к администратору для активации.")
            elif event.callback_query:
                await event.callback_query.answer("❌ Ваш аккаунт неактивен.", show_alert=True)
            return None

        if db_user.is_bot_blocked:
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} (DB ID: {db_user.id}) заблокирован в системе. Доступ запрещен.")
            if event.message:
                await event.message.reply("🚫 Вы заблокированы в системе. Обратитесь к администратору.")
            elif event.callback_query:
                await event.callback_query.answer("🚫 Вы заблокированы в системе.", show_alert=True)
            return None 
            
        logger.trace(f"[{MODULE_NAME_FOR_LOG}] Пользователь {user_mention} (DB ID: {db_user.id}) проверки прошел. Доступ разрешен.")
        data['sdb_user'] = db_user
        # --- ПЕРЕДАЕМ ФЛАГ О СОЗДАНИИ В ХЭНДЛЕР /start ---
        if is_start_command: # Только для команды /start передаем этот флаг
            data['user_was_just_created'] = user_was_created_in_this_middleware_call
            logger.debug(f"[{MODULE_NAME_FOR_LOG}] Для /start пользователя {user_mention} установлен флаг user_was_just_created = {user_was_created_in_this_middleware_call}")

        return await handler(event, data)