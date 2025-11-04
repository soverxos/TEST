# SwiftDevBot/core/users/service.py
from typing import TYPE_CHECKING, Optional, Tuple, List 
from aiogram import types as aiogram_types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, orm 
from sqlalchemy.orm import attributes as orm_attributes 
from loguru import logger
from sqlalchemy.exc import IntegrityError 
from datetime import datetime, timezone 

from Systems.core.database.core_models import User as DBUser, Role as DBRole 
from Systems.core.rbac.service import DEFAULT_ROLE_USER 

if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from Systems.core.app_settings import I18nSettings 
    from Systems.core.rbac.service import RBACService 


class UserService:
    def __init__(self, services_provider: 'BotServicesProvider'):
        self._services = services_provider
        self._logger = logger.bind(service="UserService")
        self._logger.info("UserService инициализирован.")

    async def _get_user_by_telegram_id(self, telegram_id: int, session: AsyncSession, load_roles: bool = False, load_direct_perms: bool = False) -> Optional[DBUser]:
        self._logger.trace(f"Запрос пользователя из БД. TG ID: {telegram_id}, загрузка ролей: {load_roles}, прямых прав: {load_direct_perms}")
        stmt = select(DBUser).where(DBUser.telegram_id == telegram_id)
        options_to_load = []
        if load_roles:
            options_to_load.append(orm.selectinload(DBUser.roles).selectinload(DBRole.permissions))
        if load_direct_perms:
            options_to_load.append(orm.selectinload(DBUser.direct_permissions))
        
        if options_to_load:
            stmt = stmt.options(*options_to_load)
            
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            roles_loaded_str = "не запрошено"
            if load_roles:
                is_roles_relationship_loaded = orm_attributes.instance_state(user).has_identity and \
                                            'roles' in orm_attributes.instance_state(user).committed_state
                
                roles_loaded_str = "загружены" if is_roles_relationship_loaded and user.roles is not None else "НЕ загружены"
                if is_roles_relationship_loaded and user.roles is not None:
                     self._logger.trace(f"User roles data (count): {len(user.roles)}")
                elif not is_roles_relationship_loaded:
                    self._logger.trace(f"Атрибут 'roles' не был загружен для пользователя {telegram_id}, хотя load_roles=True.")

            self._logger.trace(f"Пользователь {telegram_id} найден в БД (DB ID: {user.id}). Роли: {roles_loaded_str}")
        else:
            self._logger.trace(f"Пользователь {telegram_id} не найден в БД.")
        return user

    async def _update_existing_user_data(
        self,
        db_user: DBUser,
        tg_user: aiogram_types.User,
        current_lang_code: str
        ) -> bool: # Возвращает True, если были значимые изменения данных (кроме last_activity_at)
        updated_fields_log: dict = {}
        data_changed_meaningfully = False # Флаг для изменений, кроме last_activity

        if db_user.username != tg_user.username:
            updated_fields_log['username'] = (db_user.username, tg_user.username)
            db_user.username = tg_user.username
            db_user.username_lower = tg_user.username.lower() if tg_user.username else None 
            data_changed_meaningfully = True
        if db_user.first_name != tg_user.first_name:
            updated_fields_log['first_name'] = (db_user.first_name, tg_user.first_name)
            db_user.first_name = tg_user.first_name
            data_changed_meaningfully = True
        if db_user.last_name != tg_user.last_name:
            updated_fields_log['last_name'] = (db_user.last_name, tg_user.last_name)
            db_user.last_name = tg_user.last_name
            data_changed_meaningfully = True
        if db_user.preferred_language_code != current_lang_code:
            updated_fields_log['preferred_language_code'] = (db_user.preferred_language_code, current_lang_code)
            db_user.preferred_language_code = current_lang_code
            data_changed_meaningfully = True
        
        is_owner_check = tg_user.id in self._services.config.core.super_admins

        if is_owner_check:
            if not db_user.is_active:
                db_user.is_active = True; data_changed_meaningfully = True
                updated_fields_log['is_active (owner override)'] = (False, True)
            # Убираем автоматическую разблокировку для владельцев
            # if db_user.is_bot_blocked:
            #     db_user.is_bot_blocked = False; data_changed_meaningfully = True
            #     updated_fields_log['is_bot_blocked (owner override)'] = (True, False)
        else:
            # Убираем автоматическую разблокировку при активности пользователя
            # if db_user.is_bot_blocked:
            #     updated_fields_log['is_bot_blocked (user active)'] = (db_user.is_bot_blocked, False)
            #     db_user.is_bot_blocked = False
            #     data_changed_meaningfully = True
            if not db_user.is_active:
                updated_fields_log['is_active (user active)'] = (db_user.is_active, True)
                db_user.is_active = True
                data_changed_meaningfully = True

        # Обновляем last_activity_at только для активных и незаблокированных пользователей
        if db_user.is_active and not db_user.is_bot_blocked:
            db_user.last_activity_at = datetime.now(timezone.utc)
        elif not db_user.is_active:
            self._logger.debug(f"Не обновляем last_activity_at для неактивного пользователя TG ID: {tg_user.id}")
        elif db_user.is_bot_blocked:
            self._logger.debug(f"Не обновляем last_activity_at для заблокированного пользователя TG ID: {tg_user.id}")
        
        if data_changed_meaningfully:
            self._logger.info(f"Данные пользователя TG ID: {tg_user.id} (DB ID: {db_user.id}) будут обновлены: {updated_fields_log}")
        
        return data_changed_meaningfully

    async def process_user_on_start(self, tg_user: aiogram_types.User) -> Tuple[Optional[DBUser], bool]:
        """
        Обрабатывает пользователя при старте или любом другом событии.
        Создает нового пользователя или обновляет существующего.
        Возвращает кортеж (DBUser, user_was_created_bool).
        """
        self._logger.info(f"UserService.process_user_on_start для TG ID: {tg_user.id} (@{tg_user.username or 'N/A'})")
        
        is_owner = tg_user.id in self._services.config.core.super_admins
        if is_owner:
            self._logger.info(f"Пользователь {tg_user.id} идентифицирован как Владелец системы.")

        user_was_created = False # Инициализируем флаг

        async with self._services.db.get_session() as session:
            try:
                db_user = await self._get_user_by_telegram_id(tg_user.id, session, load_roles=True) # Загружаем с ролями
                
                data_actually_changed_in_db = False # Флаг для реальных изменений, требующих коммита

                i18n_settings: Optional["I18nSettings"] = getattr(self._services.config.core, 'i18n', None)
                available_locales = getattr(i18n_settings, 'available_locales', ['en', 'ua']) if i18n_settings else ['en', 'ua']
                default_locale = getattr(i18n_settings, 'default_locale', 'en') if i18n_settings else 'en'
                current_lang_code = tg_user.language_code if tg_user.language_code and tg_user.language_code in available_locales else default_locale
                self._logger.trace(f"Определен язык '{current_lang_code}' для пользователя {tg_user.id}.")

                if not db_user:
                    self._logger.info(f"Пользователь TG ID: {tg_user.id} не найден. Создание нового пользователя.")
                    db_user = DBUser(
                        telegram_id=tg_user.id, username=tg_user.username,
                        username_lower=tg_user.username.lower() if tg_user.username else None,
                        first_name=tg_user.first_name, last_name=tg_user.last_name,
                        preferred_language_code=current_lang_code,
                        is_active=True, is_bot_blocked=False,
                        last_activity_at=datetime.now(timezone.utc) 
                    )
                    session.add(db_user) 
                    user_was_created = True # Устанавливаем флаг
                    data_actually_changed_in_db = True
                    self._logger.info(f"Новый пользователь TG ID: {tg_user.id} подготовлен к созданию.")
                else:
                    self._logger.info(f"Пользователь TG ID: {tg_user.id} (DB ID: {db_user.id}) найден. Обновление данных...")
                    if await self._update_existing_user_data(db_user, tg_user, current_lang_code):
                        data_actually_changed_in_db = True
                    # last_activity_at обновляется в _update_existing_user_data, и если только оно изменилось,
                    # то data_actually_changed_in_db может быть False, но сессия все равно будет dirty.
                    if db_user not in session.dirty and db_user not in session.new :
                        session.add(db_user) # Добавляем в сессию для отслеживания, если не там
                    self._logger.info(f"Данные пользователя TG ID: {tg_user.id} отслеживаются сессией (изменения: {data_actually_changed_in_db}).")
                
                # Управление ролями
                rbac_service: Optional["RBACService"] = getattr(self._services, 'rbac', None)
                if rbac_service:
                    if user_was_created: 
                        await session.flush([db_user]) # Получаем ID
                        self._logger.info(f"Новый пользователь TG ID: {tg_user.id} получил DB ID: {db_user.id} после flush.")
                        if is_owner:
                            # Супер-админы из .env автоматически получают роль SuperAdmin
                            if await rbac_service.assign_role_to_user(session, db_user, "SuperAdmin"):
                                self._logger.info(f"Супер-администратору {tg_user.id} автоматически назначена роль 'SuperAdmin'.")
                                data_actually_changed_in_db = True
                        else:
                            if await rbac_service.assign_role_to_user(session, db_user, DEFAULT_ROLE_USER):
                                data_actually_changed_in_db = True
                    elif db_user: # Существующий
                        if is_owner:
                            # Супер-админы из .env должны иметь роль SuperAdmin
                            user_role_names = {r.name for r in db_user.roles} if db_user.roles else set()
                            if "SuperAdmin" not in user_role_names:
                                # Назначаем роль SuperAdmin если её нет
                                if await rbac_service.assign_role_to_user(session, db_user, "SuperAdmin"):
                                    self._logger.info(f"Супер-администратору {tg_user.id} автоматически назначена роль 'SuperAdmin'.")
                                    data_actually_changed_in_db = True
                            # Удаляем другие роли если они есть (SuperAdmin достаточна)
                            roles_to_remove = user_role_names - {"SuperAdmin"}
                            for role_name in roles_to_remove:
                                if await rbac_service.remove_role_from_user(session, db_user, role_name):
                                    self._logger.info(f"Роль '{role_name}' удалена у супер-администратора {tg_user.id} (оставлена роль 'SuperAdmin').")
                                    data_actually_changed_in_db = True
                        elif not db_user.roles: # Обычный юзер без ролей - даем User
                            if await rbac_service.assign_role_to_user(session, db_user, DEFAULT_ROLE_USER):
                                data_actually_changed_in_db = True
                
                # Коммит только если были реальные изменения или сессия "грязная"
                # (обновление last_activity_at делает сессию грязной)
                if data_actually_changed_in_db or (session.new or session.dirty or session.deleted): 
                    self._logger.info(f"UserService: ПЕРЕД session.commit() для TG ID {tg_user.id}. "
                                     f"Data changed: {data_actually_changed_in_db}, Dirty: {session.dirty}, New: {session.new}")
                    await session.commit()
                    self._logger.success(f"UserService: ПОСЛЕ session.commit() для TG ID {tg_user.id}.")
                    if db_user: # Обновляем объект из БД
                        await session.refresh(db_user, attribute_names=['id', 'roles', 'direct_permissions', 'last_activity_at', 'is_active', 'is_bot_blocked'])
                        logger.debug(f"Пользователь {db_user.id} обновлен из БД после коммита в UserService.")
                else:
                    self._logger.trace(f"Нет фактических изменений в сессии для TG ID {tg_user.id} в UserService. Коммит не требуется.")
                
                return db_user, user_was_created

            except IntegrityError as ie: # Обработка гонки (пользователь создан между SELECT и INSERT)
                await session.rollback()
                self._logger.error(f"Ошибка IntegrityError при обработке TG ID {tg_user.id}. {ie.orig if hasattr(ie, 'orig') else ie}", exc_info=True)
                self._logger.info(f"Повторная попытка получения пользователя TG ID {tg_user.id} после IntegrityError.")
                db_user_retry = await self._get_user_by_telegram_id(tg_user.id, session, load_roles=True)
                if db_user_retry:
                    self._logger.info(f"Пользователь TG ID {tg_user.id} найден при повторной попытке. Обновляем данные.")
                    meaningful_data_updated_on_retry = await self._update_existing_user_data(db_user_retry, tg_user, current_lang_code)
                    
                    # Логика ролей при ретрае (убедимся, что владелец имеет роль Admin, а юзер с ролью User)
                    if rbac_service:
                        if is_owner:
                            # Супер-админы из .env должны иметь роль SuperAdmin
                            user_role_names_retry = {r.name for r in db_user_retry.roles} if db_user_retry.roles else set()
                            if "SuperAdmin" not in user_role_names_retry:
                                if await rbac_service.assign_role_to_user(session, db_user_retry, "SuperAdmin"):
                                    self._logger.info(f"Супер-администратору {tg_user.id} автоматически назначена роль 'SuperAdmin' (retry).")
                            # Удаляем другие роли если они есть (SuperAdmin достаточна)
                            roles_to_remove_retry = user_role_names_retry - {"SuperAdmin"}
                            for role_name in roles_to_remove_retry:
                                if await rbac_service.remove_role_from_user(session, db_user_retry, role_name):
                                    self._logger.info(f"Роль '{role_name}' удалена у супер-администратора {tg_user.id} (retry).")
                        elif not db_user_retry.roles: # Если это не владелец и у него нет ролей
                             await rbac_service.assign_role_to_user(session, db_user_retry, DEFAULT_ROLE_USER)
                    
                    if meaningful_data_updated_on_retry or (session.new or session.dirty or session.deleted):
                        self._logger.info(f"UserService (retry): ПЕРЕД session.commit() для TG ID {tg_user.id}.")
                        await session.commit()
                        self._logger.success(f"UserService (retry): ПОСЛЕ session.commit() для TG ID {tg_user.id}.")
                        await session.refresh(db_user_retry, attribute_names=['id', 'roles', 'direct_permissions', 'last_activity_at', 'is_active', 'is_bot_blocked'])
                    return db_user_retry, False # False, т.к. он уже существовал на момент ретрая
                self._logger.error(f"Пользователь TG ID {tg_user.id} не найден даже после IntegrityError и повторной попытки.")
                return None, False
            except Exception as e: 
                self._logger.error(f"Непредвиденная ошибка ({type(e).__name__}) при обработке TG ID {tg_user.id} в UserService: {e}", exc_info=True)
                if hasattr(session, 'is_active') and session.is_active: 
                    await session.rollback()
                return None, False
        
        self._logger.error(f"Выход из process_user_on_start для TG ID {tg_user.id} без явного возврата.")
        return None, False
    
    async def update_user_language(self, user: DBUser, language_code: str, session: AsyncSession) -> bool:
        if user.preferred_language_code != language_code:
            user.preferred_language_code = language_code
            if user not in session.dirty and user not in session.new : session.add(user) 
            self._logger.info(f"Язык для пользователя {user.telegram_id} (DB ID: {user.id}) изменен на '{language_code}' (добавлен в сессию).")
            return True
        return False

    async def set_user_active_status(self, user: DBUser, is_active: bool, session: AsyncSession) -> bool:
        if user.telegram_id in self._services.config.core.super_admins:
            self._logger.warning(f"Попытка изменить статус активности Владельца ({user.telegram_id}). Действие запрещено.")
            return False 

        if user.is_active != is_active:
            user.is_active = is_active
            if user not in session.dirty and user not in session.new : session.add(user)
            self._logger.info(f"Статус активности для пользователя {user.telegram_id} (DB ID: {user.id}) изменен на {is_active} (добавлен в сессию).")
            return True
        return False

    async def set_user_bot_blocked_status(self, user: DBUser, is_bot_blocked: bool, session: AsyncSession) -> bool:
        if user.telegram_id in self._services.config.core.super_admins:
            self._logger.warning(f"Попытка изменить статус блокировки Владельца ({user.telegram_id}). Действие запрещено.")
            return False 

        if user.is_bot_blocked != is_bot_blocked:
            user.is_bot_blocked = is_bot_blocked
            if user not in session.dirty and user not in session.new : session.add(user)
            self._logger.info(f"Статус блокировки бота для пользователя {user.telegram_id} (DB ID: {user.id}) изменен на {is_bot_blocked} (добавлен в сессию).")
            return True
        return False

    async def get_user_by_telegram_id(
        self, 
        session: AsyncSession, 
        telegram_id: int, 
        load_roles: bool = True,
        load_direct_perms: bool = False
    ) -> Optional[DBUser]:
        """
        Получить пользователя по Telegram ID.
        
        Args:
            session: Database session
            telegram_id: Telegram user ID
            load_roles: Загружать ли роли пользователя
            load_direct_perms: Загружать ли прямые разрешения
            
        Returns:
            User object or None if not found
        """
        return await self._get_user_by_telegram_id(
            telegram_id=telegram_id,
            session=session,
            load_roles=load_roles,
            load_direct_perms=load_direct_perms
        )