# core/admin/modules_mgmt/handlers_modules.py
from aiogram import Router, types, F
from loguru import logger
from typing import List, Dict, Any, Optional

from Systems.core.ui.callback_data_factories import AdminModulesPanelNavigate, AdminMainMenuNavigate
from Systems.core.admin.filters_admin import can_view_admin_panel_filter
from .keyboards_modules import get_modules_list_keyboard, get_module_details_keyboard, get_module_actions_keyboard

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Systems.core.services_provider import BotServicesProvider

modules_mgmt_router = Router(name="sdb_admin_modules_mgmt_handlers")
MODULE_NAME_FOR_LOG = "AdminModulesMgmt"

modules_mgmt_router.callback_query.filter(can_view_admin_panel_filter)

@modules_mgmt_router.callback_query(AdminMainMenuNavigate.filter(F.target_section == "modules"))
async def cq_admin_modules_start(
    query: types.CallbackQuery,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил управление модулями.")
    
    # Получаем список модулей
    modules_info = await _get_modules_info(services_provider)
    
    text = "🔧 **Управление модулями**\n\n"
    if modules_info:
        enabled_count = sum(1 for m in modules_info if m['is_enabled'])
        total_count = len(modules_info)
        text += f"📊 Всего модулей: {total_count}\n"
        text += f"✅ Включено: {enabled_count}\n"
        text += f"❌ Отключено: {total_count - enabled_count}\n\n"
        text += "Выберите модуль для управления:"
    else:
        text += "❌ Модули не найдены"
    
    keyboard = await get_modules_list_keyboard(modules_info)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения модулей: {e}")
            await query.answer("Ошибка при обновлении интерфейса", show_alert=True)
    
    await query.answer()

@modules_mgmt_router.callback_query(AdminModulesPanelNavigate.filter(F.action == "list"))
async def cq_admin_modules_list(
    query: types.CallbackQuery,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил список модулей.")
    
    # Повторяем логику из cq_admin_modules_start
    modules_info = await _get_modules_info(services_provider)
    
    text = "🔧 **Управление модулями**\n\n"
    if modules_info:
        enabled_count = sum(1 for m in modules_info if m['is_enabled'])
        total_count = len(modules_info)
        text += f"📊 Всего модулей: {total_count}\n"
        text += f"✅ Включено: {enabled_count}\n"
        text += f"❌ Отключено: {total_count - enabled_count}\n\n"
        text += "Выберите модуль для управления:"
    else:
        text += "❌ Модули не найдены"
    
    keyboard = await get_modules_list_keyboard(modules_info)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка при обновлении списка модулей: {e}")
            await query.answer("Ошибка при обновлении интерфейса", show_alert=True)
    
    await query.answer()

@modules_mgmt_router.callback_query(AdminModulesPanelNavigate.filter(F.action == "view"))
async def cq_admin_module_view(
    query: types.CallbackQuery,
    callback_data: AdminModulesPanelNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    module_name = callback_data.item_id
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил просмотр модуля {module_name}")
    
    # Получаем информацию о модуле
    module_info = await _get_module_info(services_provider, module_name)
    
    if not module_info:
        await query.answer("Модуль не найден", show_alert=True)
        return
    
    text = f"📦 **Модуль: {module_name}**\n\n"
    text += f"📋 Описание: {module_info.get('description', 'Нет описания')}\n"
    text += f"📅 Версия: {module_info.get('version', 'Не указана')}\n"
    text += f"👨‍💻 Автор: {module_info.get('author', 'Не указан')}\n"
    text += f"🔗 Сайт: {module_info.get('website', 'Не указан')}\n"
    text += f"📧 Email: {module_info.get('email', 'Не указан')}\n"
    text += f"📄 Лицензия: {module_info.get('license', 'Не указана')}\n\n"
    text += f"✅ Статус: {'Включен' if module_info['is_enabled'] else 'Отключен'}\n"
    
    if module_info.get('error'):
        text += f"❌ Ошибка: {module_info['error']}\n"
    
    keyboard = await get_module_details_keyboard(module_name, module_info['is_enabled'])
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о модуле: {e}")
            await query.answer("Ошибка при обновлении интерфейса", show_alert=True)
    
    await query.answer()

@modules_mgmt_router.callback_query(AdminModulesPanelNavigate.filter(F.action == "toggle"))
async def cq_admin_module_toggle(
    query: types.CallbackQuery,
    callback_data: AdminModulesPanelNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    module_name = callback_data.item_id
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил переключение модуля {module_name}")
    
    # Получаем текущий статус модуля
    module_info = await _get_module_info(services_provider, module_name)
    
    if not module_info:
        await query.answer("Модуль не найден", show_alert=True)
        return
    
    current_status = module_info['is_enabled']
    new_status = not current_status
    
    # Выполняем переключение
    success = await _toggle_module(services_provider, module_name, new_status)
    
    if success:
        status_text = "включен" if new_status else "отключен"
        await query.answer(f"Модуль {module_name} {status_text}")
        
        # Обновляем интерфейс
        await cq_admin_module_view(query, callback_data, services_provider)
    else:
        await query.answer("Ошибка при переключении модуля", show_alert=True)

@modules_mgmt_router.callback_query(AdminModulesPanelNavigate.filter(F.action == "actions"))
async def cq_admin_module_actions(
    query: types.CallbackQuery,
    callback_data: AdminModulesPanelNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    module_name = callback_data.item_id
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил действия с модулем {module_name}")
    
    # Получаем информацию о модуле
    module_info = await _get_module_info(services_provider, module_name)
    
    if not module_info:
        await query.answer("Модуль не найден", show_alert=True)
        return
    
    text = f"🔧 **Действия с модулем: {module_name}**\n\n"
    text += "Выберите действие:"
    
    keyboard = await get_module_actions_keyboard(module_name, module_info['is_enabled'])
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка при обновлении действий модуля: {e}")
            await query.answer("Ошибка при обновлении интерфейса", show_alert=True)
    
    await query.answer()

@modules_mgmt_router.callback_query(AdminModulesPanelNavigate.filter(F.action == "clean_tables"))
async def cq_admin_module_clean_tables(
    query: types.CallbackQuery,
    callback_data: AdminModulesPanelNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    module_name = callback_data.item_id
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} запросил очистку таблиц модуля {module_name}")
    
    # Запрашиваем подтверждение
    text = f"⚠️ **Внимание!**\n\n"
    text += f"Вы собираетесь очистить таблицы модуля '{module_name}'.\n"
    text += "Это действие необратимо и удалит все данные модуля.\n\n"
    text += "Продолжить?"
    
    keyboard = await get_module_clean_tables_confirm_keyboard(module_name)
    
    if query.message:
        try:
            await query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка при запросе подтверждения очистки: {e}")
            await query.answer("Ошибка при обновлении интерфейса", show_alert=True)
    
    await query.answer()

@modules_mgmt_router.callback_query(AdminModulesPanelNavigate.filter(F.action == "clean_tables_confirm"))
async def cq_admin_module_clean_tables_confirm(
    query: types.CallbackQuery,
    callback_data: AdminModulesPanelNavigate,
    services_provider: 'BotServicesProvider'
):
    admin_user_id = query.from_user.id
    module_name = callback_data.item_id
    
    logger.info(f"[{MODULE_NAME_FOR_LOG}] Администратор {admin_user_id} подтвердил очистку таблиц модуля {module_name}")
    
    # Выполняем очистку таблиц
    success = await _clean_module_tables(services_provider, module_name)
    
    if success:
        await query.answer("Таблицы модуля очищены")
        # Возвращаемся к списку модулей
        await cq_admin_modules_list(query, services_provider)
    else:
        await query.answer("Ошибка при очистке таблиц", show_alert=True)

# Вспомогательные функции
async def _get_modules_info(services_provider: 'BotServicesProvider') -> List[Dict[str, Any]]:
    """Получить информацию о всех модулях"""
    try:
        module_loader = services_provider.module_loader
        all_modules = module_loader.get_all_modules_info()
        
        modules_info = []
        for module_info in all_modules:
            modules_info.append({
                'name': module_info.name,
                'description': module_info.manifest.description if module_info.manifest else 'Нет описания',
                'version': module_info.manifest.version if module_info.manifest else 'Не указана',
                'author': module_info.manifest.author if module_info.manifest else 'Не указан',
                'website': module_info.manifest.website if module_info.manifest else 'Не указан',
                'email': module_info.manifest.email if module_info.manifest else 'Не указан',
                'license': module_info.manifest.license if module_info.manifest else 'Не указана',
                'is_enabled': module_info.is_enabled,
                'error': module_info.error,
                'is_system_module': module_info.is_system_module
            })
        
        return modules_info
    except Exception as e:
        logger.error(f"Ошибка при получении информации о модулях: {e}")
        return []

async def _get_module_info(services_provider: 'BotServicesProvider', module_name: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о конкретном модуле"""
    try:
        module_loader = services_provider.module_loader
        module_info = module_loader.get_module_info(module_name)
        
        if not module_info:
            return None
        
        return {
            'name': module_info.name,
            'description': module_info.manifest.description if module_info.manifest else 'Нет описания',
            'version': module_info.manifest.version if module_info.manifest else 'Не указана',
            'author': module_info.manifest.author if module_info.manifest else 'Не указан',
            'website': module_info.manifest.website if module_info.manifest else 'Не указан',
            'email': module_info.manifest.email if module_info.manifest else 'Не указан',
            'license': module_info.manifest.license if module_info.manifest else 'Не указана',
            'is_enabled': module_info.is_enabled,
            'error': module_info.error,
            'is_system_module': module_info.is_system_module
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о модуле {module_name}: {e}")
        return None

async def _toggle_module(services_provider: 'BotServicesProvider', module_name: str, enable: bool) -> bool:
    """Включить или отключить модуль"""
    try:
        # Используем CLI команды для управления модулями - безопасная версия
        import subprocess
        import sys
        import shlex
        
        action = "enable" if enable else "disable"
        # Безопасная проверка имени модуля
        if not module_name.replace('_', '').replace('-', '').isalnum():
            logger.error(f"Недопустимые символы в имени модуля: {module_name}")
            return False
            
        cmd = [sys.executable, "sdb", "module", action, module_name]
        
        # Безопасный запуск с ограничением времени выполнения
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        
        if result.returncode == 0:
            logger.info(f"Модуль {module_name} успешно {action}d")
            return True
        else:
            logger.error(f"Ошибка при {action} модуля {module_name}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при переключении модуля {module_name}: {e}")
        return False

async def _clean_module_tables(services_provider: 'BotServicesProvider', module_name: str) -> bool:
    """Очистить таблицы модуля"""
    try:
        import subprocess
        import sys
        
        # Безопасная проверка имени модуля
        if not module_name.replace('_', '').replace('-', '').isalnum():
            logger.error(f"Недопустимые символы в имени модуля: {module_name}")
            return False
            
        cmd = [sys.executable, "sdb", "module", "clean-tables", module_name]
        
        # Безопасный запуск с ограничением времени выполнения
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        
        if result.returncode == 0:
            logger.info(f"Таблицы модуля {module_name} успешно очищены")
            return True
        else:
            logger.error(f"Ошибка при очистке таблиц модуля {module_name}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при очистке таблиц модуля {module_name}: {e}")
        return False

async def get_module_clean_tables_confirm_keyboard(module_name: str):
    """Клавиатура для подтверждения очистки таблиц"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    # Кнопка подтверждения
    builder.button(
        text="✅ Да, очистить",
        callback_data=AdminModulesPanelNavigate(action="clean_tables_confirm", item_id=module_name).pack()
    )
    
    # Кнопка отмены
    builder.button(
        text="❌ Отмена",
        callback_data=AdminModulesPanelNavigate(action="view", item_id=module_name).pack()
    )
    
    builder.adjust(2)
    return builder.as_markup()