# core/admin/roles/handlers_crud_fsm.py
from typing import List
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, StateFilter 
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup 
from aiogram.utils.markdown import hbold, hcode, hitalic
from aiogram.utils.keyboard import InlineKeyboardBuilder 
from loguru import logger
from sqlalchemy import select, func as sql_func
from aiogram.exceptions import TelegramBadRequest # <--- ИСПРАВЛЕН ИМПОРТ

from Systems.core.ui.callback_data_factories import AdminRolesPanelNavigate
from .keyboards_roles import get_admin_roles_list_keyboard_local, ROLES_MGMT_TEXTS, get_roles_mgmt_texts
from Systems.core.admin.keyboards_admin_common import ADMIN_COMMON_TEXTS, get_admin_texts 
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from Systems.core.rbac.service import PERMISSION_CORE_ROLES_CREATE, PERMISSION_CORE_ROLES_EDIT, PERMISSION_CORE_ROLES_DELETE, DEFAULT_ROLES_DEFINITIONS
from Systems.core.database.core_models import Role as DBRole, UserRole


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider
    from sqlalchemy.ext.asyncio import AsyncSession


role_crud_fsm_router = Router(name="sdb_admin_role_crud_fsm_handlers")
MODULE_NAME_FOR_LOG = "AdminRoleCRUD"

#role_crud_fsm_router.callback_query.filter(can_view_admin_panel_filter)
#role_crud_fsm_router.message.filter(can_view_admin_panel_filter)

class FSMAdminCreateRole(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()

class FSMAdminEditRole(StatesGroup): 
    waiting_for_new_name = State()
    waiting_for_new_description = State()

@role_crud_fsm_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "create_start"))
async def cq_admin_role_create_start_fsm( 
    query: types.CallbackQuery,
    state: FSMContext,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} инициировал создание новой роли (FSM).")

    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_CREATE):
                await query.answer(admin_texts["access_denied"], show_alert=True)
                return
    
    await state.set_state(FSMAdminCreateRole.waiting_for_name)
    
    text = (f"{admin_texts.get('fsm_enter_role_name', 'Введите имя роли:')}\n\n"
            f"{hitalic(admin_texts.get('fsm_command_cancel_role_creation', '/cancel_role_creation - Отменить'))}")
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=None) 
        except TelegramBadRequest as e: # Используем импортированный TelegramBadRequest
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Не удалось отредактировать сообщение для FSM (create_start): {e}. Отправка нового.")
            await query.bot.send_message(query.from_user.id, text) 
        except Exception as e_fatal:
            logger.error(f"Критическая ошибка в cq_admin_role_create_start_fsm при edit/send: {e_fatal}")
            await query.answer(admin_texts["error_general"], show_alert=True)
    else: 
        await query.bot.send_message(query.from_user.id, text) 
    await query.answer()


@role_crud_fsm_router.message(StateFilter(FSMAdminCreateRole.waiting_for_name), F.text)
async def process_fsm_role_name_crud( 
    message: types.Message, 
    state: FSMContext, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = message.from_user.id
    role_name = message.text.strip() if message.text else ""

    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)

    if not role_name:
        await message.reply(admin_texts.get('fsm_role_name_empty', 'Имя роли не может быть пустым.'))
        return

    async with services_provider.db.get_session() as session:
        existing_role = await services_provider.rbac._get_role_by_name(session, role_name) 
        if existing_role:
            await message.reply(admin_texts.get('fsm_role_name_taken','Роль с именем "{role_name}" уже существует.').format(role_name=hcode(role_name)))
            return
            
    await state.update_data(new_role_name=role_name)
    await state.set_state(FSMAdminCreateRole.waiting_for_description)
    
    text = (f"{admin_texts.get('fsm_enter_role_description','Введите описание для роли {role_name}:').format(role_name=hcode(role_name))}\n\n"
            f"{hitalic(admin_texts.get('fsm_command_skip_description','/skip_description - Пропустить'))} или {hitalic(admin_texts.get('fsm_command_cancel_role_creation','/cancel_role_creation - Отменить'))}")
    await message.answer(text)


@role_crud_fsm_router.message(StateFilter(FSMAdminCreateRole.waiting_for_description), F.text)
async def process_fsm_role_description_crud( 
    message: types.Message, 
    state: FSMContext, 
    services_provider: 'BotServicesProvider',
    bot: Bot 
):
    admin_user_id = message.from_user.id
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    roles_texts = get_roles_mgmt_texts(services_provider, user_locale)
    
    if message.text and message.text.lower() == "/skip_description": 
        role_description = None
    else:
        role_description = message.text.strip() if message.text else None

    user_data = await state.get_data()
    role_name = user_data.get("new_role_name")

    if not role_name: 
        logger.error(f"[{MODULE_NAME_FOR_LOG}] FSM: Не найдено имя роли в состоянии при получении описания.")
        await message.answer(admin_texts["error_general"])
        await state.clear()
        from .handlers_list import cq_admin_roles_list_entry 
        chat_id_for_reply = message.chat.id
        dummy_message_for_cb = types.Message(message_id=0, chat=types.Chat(id=chat_id_for_reply, type="private"), date=0) 
        await cq_admin_roles_list_entry(
            types.CallbackQuery(id="dummy_fsm_error_cb", from_user=message.from_user, chat_instance=str(chat_id_for_reply), data="dummy", message=dummy_message_for_cb), 
            AdminRolesPanelNavigate(action="list"), services_provider
        )
        return

    async with services_provider.db.get_session() as session:
        created_role = await services_provider.rbac.get_or_create_role(session, role_name, role_description)
        if created_role:
            try:
                await session.commit()
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} успешно создал роль: '{role_name}'.")
                await message.answer(admin_texts.get('fsm_role_created_successfully','Роль "{role_name}" успешно создана!').format(role_name=hcode(role_name)))
            except Exception as e_commit:
                await session.rollback()
                logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка commit при создании роли '{role_name}': {e_commit}", exc_info=True)
                await message.answer(admin_texts.get("admin_error_saving_role", admin_texts["admin_error_saving"]))
        else:
            await message.answer(admin_texts.get("admin_error_saving_role", admin_texts["admin_error_saving"]))
        
        await state.clear()
        
        # Отправляем обновленный список ролей
        from Systems.core.database.core_models import Role as DBRole
        
        async with services_provider.db.get_session() as session:
            all_roles: List[DBRole] = await services_provider.rbac.get_all_roles(session)
            text = f"{roles_texts['role_list_title']}\n{roles_texts['role_list_select_action']}"
            keyboard = await get_admin_roles_list_keyboard_local(all_roles, services_provider, message.from_user.id, session, locale=user_locale)
            
            await message.bot.send_message(message.chat.id, text, reply_markup=keyboard)

@role_crud_fsm_router.message(Command("cancel_role_creation"), StateFilter(FSMAdminCreateRole))
async def cancel_create_role_fsm_command(
    message: types.Message, 
    state: FSMContext, 
    services_provider: 'BotServicesProvider', 
    bot: Bot
):
    admin_user_id = message.from_user.id
    
    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)
    
    current_fsm_state = await state.get_state()
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} отменил создание роли из состояния {current_fsm_state} командой.")
    await state.clear()
    await message.answer(admin_texts.get('fsm_role_creation_cancelled', "Создание роли отменено."))
    
    from .handlers_list import cq_admin_roles_list_entry
    chat_id_for_reply = message.chat.id
    dummy_message_for_cb = types.Message(message_id=0, chat=types.Chat(id=chat_id_for_reply, type="private"), date=0)
    await cq_admin_roles_list_entry(
        types.CallbackQuery(id="dummy_fsm_cancel_cb", from_user=message.from_user, chat_instance=str(chat_id_for_reply), data="dummy", message=dummy_message_for_cb), 
        AdminRolesPanelNavigate(action="list"), services_provider
    )

@role_crud_fsm_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "edit_start"))
async def cq_admin_role_edit_start_fsm( 
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate,
    state: FSMContext,
    services_provider: 'BotServicesProvider'
):
    from Systems.core.database.core_models import Role as DBRole
    admin_user_id = query.from_user.id
    role_id_to_edit = callback_data.item_id

    # Получаем язык пользователя
    user_locale = services_provider.config.core.i18n.default_locale
    try:
        async with services_provider.db.get_session() as session:
            from Systems.core.database.core_models import User as DBUser
            from sqlalchemy import select
            result = await session.execute(select(DBUser).where(DBUser.telegram_id == admin_user_id))
            db_user = result.scalar_one_or_none()
            if db_user and db_user.preferred_language_code:
                user_locale = db_user.preferred_language_code
    except Exception:
        pass
    
    admin_texts = get_admin_texts(services_provider, user_locale)

    if role_id_to_edit is None or not str(role_id_to_edit).isdigit(): 
        await query.answer(admin_texts["admin_error_role_id_invalid"], show_alert=True); return
    
    role_id_to_edit = int(str(role_id_to_edit)) 

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} инициировал редактирование роли ID: {role_id_to_edit} (FSM).")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_EDIT):
                await query.answer(admin_texts["access_denied"], show_alert=True); return
        
        role_to_edit = await session.get(DBRole, role_id_to_edit)
        if not role_to_edit:
            await query.answer(admin_texts["not_found_generic"], show_alert=True); return

        await state.update_data(
            editing_role_id=role_to_edit.id,
            current_role_name=role_to_edit.name,
            current_role_description=role_to_edit.description or "" 
        )

        title_text = admin_texts.get('fsm_edit_role_title','Редактирование роли: {role_name}').format(role_name=hcode(role_to_edit.name))
        
        if role_to_edit.name in DEFAULT_ROLES_DEFINITIONS:
            await state.set_state(FSMAdminEditRole.waiting_for_new_description)
            prompt_text = (f"{title_text}\n"
                           f"{admin_texts.get('fsm_edit_role_name_not_allowed','Имя стандартной роли {role_name} изменять нельзя.').format(role_name=hcode(role_to_edit.name))}\n\n"
                           f"{admin_texts.get('fsm_enter_new_role_description','Введите новое описание для роли {role_name} (текущее: {current_description}):').format(role_name=hcode(role_to_edit.name), current_description=hitalic(role_to_edit.description or 'пусто'))}\n\n"
                           f"{hitalic(admin_texts.get('fsm_command_skip_description','/skip_description - Пропустить'))} или {hitalic(admin_texts.get('fsm_command_cancel_role_edit','/cancel_role_edit - Отменить'))}")
        else:
            await state.set_state(FSMAdminEditRole.waiting_for_new_name)
            prompt_text = (f"{title_text}\n"
                           f"{admin_texts.get('fsm_enter_new_role_name','Введите новое имя для роли (текущее: {current_name}):').format(current_name=hcode(role_to_edit.name))}\n\n"
                           f"{hitalic(ADMIN_COMMON_TEXTS.get('fsm_command_skip_name','/skip_name - Оставить как есть'))} или {hitalic(ADMIN_COMMON_TEXTS.get('fsm_command_cancel_role_edit','/cancel_role_edit - Отменить'))}")
    
    if query.message:
        try:
            await query.message.edit_text(prompt_text, reply_markup=None) 
        except TelegramBadRequest as e: # Используем импортированный TelegramBadRequest
            logger.warning(f"[{MODULE_NAME_FOR_LOG}] Не удалось отредактировать сообщение для FSM (edit_start): {e}. Отправка нового.")
            await query.bot.send_message(query.from_user.id, prompt_text) 
    else:
        await query.bot.send_message(query.from_user.id, prompt_text) 
    await query.answer()


@role_crud_fsm_router.message(StateFilter(FSMAdminEditRole.waiting_for_new_name), F.text)
async def process_fsm_edit_role_name_crud( 
    message: types.Message, 
    state: FSMContext, 
    services_provider: 'BotServicesProvider'
):
    admin_user_id = message.from_user.id
    new_role_name_input = message.text.strip() if message.text else ""
    
    user_data = await state.get_data()
    current_role_name = user_data.get("current_role_name")
    role_id = user_data.get("editing_role_id")

    final_role_name = current_role_name 

    if new_role_name_input.lower() == "/skip_name":
        logger.info(f"[{MODULE_NAME_FOR_LOG}] FSM Edit Role: Пользователь {admin_user_id} пропустил изменение имени для роли ID {role_id}.")
    elif not new_role_name_input:
        await message.reply(ADMIN_COMMON_TEXTS.get('fsm_role_name_empty', 'Имя роли не может быть пустым.'))
        return
    elif new_role_name_input != current_role_name:
        async with services_provider.db.get_session() as session:
            existing_role_with_new_name = await services_provider.rbac._get_role_by_name(session, new_role_name_input)
            if existing_role_with_new_name and existing_role_with_new_name.id != role_id:
                await message.reply(ADMIN_COMMON_TEXTS.get('fsm_role_name_taken','Роль с именем "{role_name}" уже существует.').format(role_name=hcode(new_role_name_input)))
                return
        final_role_name = new_role_name_input
        logger.info(f"[{MODULE_NAME_FOR_LOG}] FSM Edit Role: Пользователь {admin_user_id} ввел новое имя '{final_role_name}' для роли ID {role_id}.")
    
    await state.update_data(edited_role_name=final_role_name) 
    await state.set_state(FSMAdminEditRole.waiting_for_new_description)
    
    current_description = user_data.get("current_role_description", "пусто")
    text = (f"{ADMIN_COMMON_TEXTS.get('fsm_enter_new_role_description','Введите новое описание для роли {role_name} (текущее: {current_description}):').format(role_name=hcode(final_role_name), current_description=hitalic(current_description))}\n\n"
            f"{hitalic(ADMIN_COMMON_TEXTS.get('fsm_command_skip_description','/skip_description - Пропустить'))} или {hitalic(ADMIN_COMMON_TEXTS.get('fsm_command_cancel_role_edit','/cancel_role_edit - Отменить'))}")
    await message.answer(text)


@role_crud_fsm_router.message(StateFilter(FSMAdminEditRole.waiting_for_new_description), F.text)
async def process_fsm_edit_role_description_crud( 
    message: types.Message, 
    state: FSMContext, 
    services_provider: 'BotServicesProvider',
    bot: Bot
):
    from Systems.core.database.core_models import Role as DBRole
    admin_user_id = message.from_user.id
    new_role_description_input = message.text.strip() if message.text else None

    user_data = await state.get_data()
    role_id = user_data.get("editing_role_id")
    final_role_name = user_data.get("edited_role_name", user_data.get("current_role_name")) 
    current_role_description = user_data.get("current_role_description")

    final_role_description = current_role_description 
    if new_role_description_input and new_role_description_input.lower() == "/skip_description":
        final_role_description = current_role_description if current_role_description is not None else None 
        logger.info(f"[{MODULE_NAME_FOR_LOG}] FSM Edit Role: Пользователь {admin_user_id} пропустил изменение описания для роли ID {role_id}.")
    elif new_role_description_input is not None: 
        final_role_description = new_role_description_input if new_role_description_input else None 
        logger.info(f"[{MODULE_NAME_FOR_LOG}] FSM Edit Role: Пользователь {admin_user_id} ввел новое описание для роли ID {role_id}.")

    if role_id is None or final_role_name is None: 
        logger.error(f"[{MODULE_NAME_FOR_LOG}] FSM Edit: Отсутствует ID роли или имя в состоянии.")
        await message.answer(ADMIN_COMMON_TEXTS["error_general"])
        await state.clear()
        return

    async with services_provider.db.get_session() as session:
        role_to_update = await session.get(DBRole, role_id)
        if not role_to_update:
            await message.answer(ADMIN_COMMON_TEXTS["not_found_generic"])
            await state.clear()
            return
        
        made_changes = False
        if role_to_update.name != final_role_name and role_to_update.name not in DEFAULT_ROLES_DEFINITIONS:
            if final_role_name != user_data.get("current_role_name"): 
                existing_role_check = await services_provider.rbac._get_role_by_name(session, final_role_name)
                if existing_role_check and existing_role_check.id != role_id:
                    await message.reply(ADMIN_COMMON_TEXTS.get('fsm_role_name_taken','Роль с именем "{role_name}" уже существует.').format(role_name=hcode(final_role_name)))
                    await state.set_state(FSMAdminEditRole.waiting_for_new_name)
                    current_name_for_prompt = user_data.get("current_role_name")
                    title_text = ADMIN_COMMON_TEXTS.get('fsm_edit_role_title','Редактирование роли: {role_name}').format(role_name=hcode(current_name_for_prompt))
                    prompt_text = (f"{title_text}\n"
                                   f"{ADMIN_COMMON_TEXTS.get('fsm_enter_new_role_name','Введите новое имя для роли (текущее: {current_name}):').format(current_name=hcode(current_name_for_prompt))}\n\n"
                                   f"{hitalic(ADMIN_COMMON_TEXTS.get('fsm_command_skip_name','/skip_name - Оставить как есть'))} или {hitalic(ADMIN_COMMON_TEXTS.get('fsm_command_cancel_role_edit','/cancel_role_edit - Отменить'))}")
                    await message.answer(prompt_text)
                    return
            role_to_update.name = final_role_name
            made_changes = True
        elif role_to_update.name != final_role_name and role_to_update.name in DEFAULT_ROLES_DEFINITIONS:
            logger.warning(f"Попытка изменить имя стандартной роли '{role_to_update.name}' на '{final_role_name}'. Имя не будет изменено.")
        
        if role_to_update.description != final_role_description:
            role_to_update.description = final_role_description
            made_changes = True
        
        if made_changes:
            session.add(role_to_update)
            try:
                await session.commit()
                logger.info(f"[{MODULE_NAME_FOR_LOG}] Роль ID {role_id} успешно обновлена. Имя: '{role_to_update.name}', описание: '{role_to_update.description}'.")
                await message.answer(ADMIN_COMMON_TEXTS.get('fsm_role_updated_successfully','Роль "{role_name}" успешно обновлена!').format(role_name=hcode(role_to_update.name)))
            except Exception as e_commit:
                await session.rollback()
                logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка commit при обновлении роли ID {role_id}: {e_commit}", exc_info=True)
                await message.answer("Ошибка сохранения изменений роли.")
        else:
            await message.answer("Нет изменений для сохранения.")

        await state.clear()
        
        # Отправляем обновленный список ролей
        from .keyboards_roles import get_admin_roles_list_keyboard_local, ROLES_MGMT_TEXTS
        from Systems.core.rbac.service import PERMISSION_CORE_ROLES_VIEW
        from Systems.core.database.core_models import Role as DBRole
        from sqlalchemy import select, func as sql_func
        
        async with services_provider.db.get_session() as session:
            # Проверяем права
            has_perm = await services_provider.rbac.user_has_permission(session, message.from_user.id, PERMISSION_CORE_ROLES_VIEW)
            if not has_perm:
                await message.answer("У вас нет прав для просмотра списка ролей.")
                return
            
            # Получаем список ролей
            roles_query = select(DBRole).order_by(DBRole.name)
            roles_result = await session.execute(roles_query)
            all_roles = list(roles_result.scalars().all())
            
            # Формируем текст и клавиатуру
            text = ROLES_MGMT_TEXTS["role_list_title"]
            keyboard = await get_admin_roles_list_keyboard_local(all_roles, services_provider, message.from_user.id, session)
            
            await message.answer(text, reply_markup=keyboard)

@role_crud_fsm_router.message(Command("cancel_role_edit"), StateFilter(FSMAdminEditRole))
async def cancel_edit_role_fsm_command_crud( 
    message: types.Message, 
    state: FSMContext, 
    services_provider: 'BotServicesProvider', 
    bot: Bot
):
    admin_user_id = message.from_user.id
    current_fsm_state = await state.get_state()
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} отменил редактирование роли из состояния {current_fsm_state} командой.")
    await state.clear()
    await message.answer(ADMIN_COMMON_TEXTS.get('fsm_role_update_cancelled', "Редактирование роли отменено."))
    
    from .handlers_list import cq_admin_roles_list_entry
    chat_id_for_reply = message.chat.id
    dummy_message_for_cb = types.Message(message_id=0, chat=types.Chat(id=chat_id_for_reply, type="private"), date=0)
    await cq_admin_roles_list_entry(
        types.CallbackQuery(id="dummy_fsm_cancel_edit_cb", from_user=message.from_user, chat_instance=str(chat_id_for_reply), data="dummy", message=dummy_message_for_cb), 
        AdminRolesPanelNavigate(action="list"), services_provider
    )

@role_crud_fsm_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "delete_confirm"))
async def cq_admin_role_delete_confirm_crud( 
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate,
    services_provider: 'BotServicesProvider'
):
    from Systems.core.database.core_models import Role as DBRole
    admin_user_id = query.from_user.id
    role_id_to_delete = callback_data.item_id

    if role_id_to_delete is None or not str(role_id_to_delete).isdigit():
        await query.answer("Ошибка: ID роли для удаления не указан или некорректен.", show_alert=True); return
    
    role_id_to_delete = int(str(role_id_to_delete))

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил подтверждение удаления роли ID: {role_id_to_delete}.")

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_DELETE):
                await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return

        role_to_delete = await session.get(DBRole, role_id_to_delete)
        if not role_to_delete:
            await query.answer(ADMIN_COMMON_TEXTS["not_found_generic"], show_alert=True); return

        if role_to_delete.name in DEFAULT_ROLES_DEFINITIONS:
            await query.answer(ADMIN_COMMON_TEXTS.get('role_is_standard_cant_delete','Стандартную роль "{role_name}" удалять нельзя.').format(role_name=hcode(role_to_delete.name)), show_alert=True); return
        
        user_role_count_stmt = select(sql_func.count(UserRole.id)).where(UserRole.role_id == role_id_to_delete)
        user_role_count_res = await session.execute(user_role_count_stmt)
        user_count_with_role = user_role_count_res.scalar_one()

        warning_text = ""
        if user_count_with_role > 0:
            text_with_warning = (f"🚫 {hbold('Удаление невозможно!')}\n"
                                 f"Роль {hcode(role_to_delete.name)} назначена {hbold(str(user_count_with_role))} пользователю(ям).\n"
                                 f"Сначала снимите эту роль со всех пользователей.")
            builder = InlineKeyboardBuilder()
            builder.button(text=ROLES_MGMT_TEXTS.get('back_to_role_details', "Назад"), 
                           callback_data=AdminRolesPanelNavigate(action="view", item_id=role_id_to_delete).pack())
            if query.message: await query.message.edit_text(text_with_warning, reply_markup=builder.as_markup())
            await query.answer(f"Роль используется {user_count_with_role} пользователями.", show_alert=True)
            return

        text = ADMIN_COMMON_TEXTS.get('delete_role_confirm_text','Вы уверены, что хотите удалить роль {role_name}?\n{warning_if_users}\nЭто действие необратимо!').format(role_name=hbold(role_to_delete.name), warning_if_users=warning_text)
        
        from Systems.core.ui.keyboards_core import get_confirm_action_keyboard 
        keyboard = get_confirm_action_keyboard(
            confirm_callback_data=AdminRolesPanelNavigate(action="delete_execute", item_id=role_id_to_delete).pack(),
            cancel_callback_data=AdminRolesPanelNavigate(action="view", item_id=role_id_to_delete).pack() 
        )
        if query.message:
            await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()


@role_crud_fsm_router.callback_query(AdminRolesPanelNavigate.filter(F.action == "delete_execute"))
async def cq_admin_role_delete_execute_crud( 
    query: types.CallbackQuery,
    callback_data: AdminRolesPanelNavigate,
    services_provider: 'BotServicesProvider',
    bot: Bot
):
    from Systems.core.database.core_models import Role as DBRole
    from sqlalchemy import select, func as sql_func
    from Systems.core.database.core_models import UserRole
    admin_user_id = query.from_user.id
    role_id_to_delete = callback_data.item_id

    if role_id_to_delete is None or not str(role_id_to_delete).isdigit():
        await query.answer("Ошибка: ID роли для удаления не указан или некорректен.", show_alert=True); return
    
    role_id_to_delete = int(str(role_id_to_delete))

    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} подтвердил удаление роли ID: {role_id_to_delete}.")
    
    default_fail_text = ADMIN_COMMON_TEXTS.get('role_delete_failed','Не удалось удалить роль "{role_name}".')
    alert_text = default_fail_text.format(role_name="ID:"+str(role_id_to_delete)) 

    async with services_provider.db.get_session() as session:
        if not services_provider.config.core.super_admins or admin_user_id not in services_provider.config.core.super_admins:
            if not await services_provider.rbac.user_has_permission(session, admin_user_id, PERMISSION_CORE_ROLES_DELETE):
                await query.answer(ADMIN_COMMON_TEXTS["access_denied"], show_alert=True); return

        role_to_delete = await session.get(DBRole, role_id_to_delete) 
        if not role_to_delete:
            alert_text = ADMIN_COMMON_TEXTS["not_found_generic"]
        elif role_to_delete.name in DEFAULT_ROLES_DEFINITIONS:
            alert_text = ADMIN_COMMON_TEXTS.get('role_is_standard_cant_delete','Стандартную роль "{role_name}" удалять нельзя.').format(role_name=hcode(role_to_delete.name))
        else:
            user_role_count_stmt = select(sql_func.count(UserRole.id)).where(UserRole.role_id == role_id_to_delete)
            user_role_count_res = await session.execute(user_role_count_stmt)
            if user_role_count_res.scalar_one() > 0:
                alert_text = "Невозможно удалить роль, так как она все еще назначена пользователям."
            else:
                role_name_deleted = role_to_delete.name
                if await services_provider.rbac.delete_role(session, role_id_to_delete): 
                    try:
                        await session.commit()
                        alert_text = ADMIN_COMMON_TEXTS.get('role_deleted_successfully','Роль "{role_name}" успешно удалена.').format(role_name=hcode(role_name_deleted))
                        logger.info(f"[{MODULE_NAME_FOR_LOG}] {alert_text}")
                    except Exception as e_commit:
                        await session.rollback()
                        logger.error(f"[{MODULE_NAME_FOR_LOG}] Ошибка commit при удалении роли: {e_commit}", exc_info=True)
                        alert_text = "Ошибка сохранения удаления роли."
                else: 
                    alert_text = default_fail_text.format(role_name=hcode(role_name_deleted))
        
        # Отправляем обновленный список ролей
        from .keyboards_roles import get_admin_roles_list_keyboard_local, ROLES_MGMT_TEXTS
        from Systems.core.rbac.service import PERMISSION_CORE_ROLES_VIEW
        from Systems.core.database.core_models import Role as DBRole
        from sqlalchemy import select, func as sql_func
        
        async with services_provider.db.get_session() as session:
            # Проверяем права
            has_perm = await services_provider.rbac.user_has_permission(session, query.from_user.id, PERMISSION_CORE_ROLES_VIEW)
            if not has_perm:
                await query.bot.send_message(query.from_user.id, "У вас нет прав для просмотра списка ролей.")
                return
            
            # Получаем список ролей
            roles_query = select(DBRole).order_by(DBRole.name)
            roles_result = await session.execute(roles_query)
            all_roles = list(roles_result.scalars().all())
            
            # Формируем текст и клавиатуру
            text = ROLES_MGMT_TEXTS["role_list_title"]
            keyboard = await get_admin_roles_list_keyboard_local(all_roles, services_provider, query.from_user.id, session)
            
            await query.bot.send_message(query.from_user.id, text, reply_markup=keyboard)

    await query.answer(alert_text, show_alert=True)