"""
Примеры интеграции универсального шаблона модуля

Этот файл содержит примеры того, как интегрировать модуль
с другими компонентами системы SDB и внешними сервисами.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from aiogram import Router, types, F
from aiogram.filters import Command
from loguru import logger

from .services import TemplateService
from .utils import check_permission, log_module_action
from .permissions import PERMISSIONS

# === ПРИМЕР 1: ИНТЕГРАЦИЯ С СИСТЕМОЙ УВЕДОМЛЕНИЙ ===

integration_router = Router(name="integration_examples")

@integration_router.message(Command("notification_integration"))
async def notification_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой уведомлений
    
    Этот пример показывает, как отправлять уведомления
    пользователям через различные каналы.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ Нет прав администратора")
        return
    
    # Получаем настройки модуля
    settings = services.modules.get_module_settings("my_module") or {}
    notifications_enabled = settings.get('notification_enabled', True)
    
    if not notifications_enabled:
        await message.answer("❌ Уведомления отключены в настройках модуля")
        return
    
    # Пример отправки уведомления
    notification_data = {
        "type": "module_action",
        "module": "my_module",
        "action": "notification_test",
        "user_id": message.from_user.id,
        "message": "Тестовое уведомление из модуля",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Отправляем уведомление через систему событий
        if hasattr(services, 'events'):
            await services.events.emit("notification_send", notification_data)
        
        # Логируем в аудит
        log_module_action(
            services,
            "notification_sent",
            message.from_user.id,
            {"notification_type": "test"}
        )
        
        await message.answer(
            "✅ **Уведомление отправлено**\n\n"
            "Тестовое уведомление было отправлено через систему событий."
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")
        await message.answer("❌ Ошибка отправки уведомления")

# === ПРИМЕР 2: ИНТЕГРАЦИЯ С СИСТЕМОЙ БЭКАПОВ ===

@integration_router.message(Command("backup_integration"))
async def backup_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой бэкапов
    
    Этот пример показывает, как создавать и восстанавливать
    бэкапы данных модуля.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ Нет прав администратора")
        return
    
    await message.answer(
        "💾 **Интеграция с системой бэкапов**\n\n"
        "Выберите действие:",
        reply_markup=get_backup_keyboard()
    )

async def create_module_backup(services, user_id: int) -> Dict[str, Any]:
    """
    Создание бэкапа данных модуля
    
    Args:
        services: Провайдер сервисов SDB
        user_id: ID пользователя, создающего бэкап
        
    Returns:
        Информация о созданном бэкапе
    """
    try:
        template_service = TemplateService(services, services.modules.get_module_settings("my_module") or {})
        
        # Получаем все данные модуля
        async with services.db.get_session() as session:
            # Здесь можно добавить логику экспорта данных
            backup_data = {
                "module_name": "my_module",
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "created_by": user_id,
                "data": {
                    # Экспортируемые данные модуля
                    "settings": services.modules.get_module_settings("my_module"),
                    "statistics": await template_service.get_global_stats()
                }
            }
            
            # Сохраняем бэкап через систему бэкапов
            if hasattr(services, 'backup_manager'):
                backup_info = await services.backup_manager.create_backup(
                    name=f"module_my_module_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    data=backup_data,
                    module_name="my_module"
                )
                
                return backup_info
            
            return backup_data
            
    except Exception as e:
        logger.error(f"Ошибка создания бэкапа модуля: {e}")
        raise

# === ПРИМЕР 3: ИНТЕГРАЦИЯ С СИСТЕМОЙ МОНИТОРИНГА ===

@integration_router.message(Command("monitoring_integration"))
async def monitoring_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой мониторинга
    
    Этот пример показывает, как отправлять метрики
    и события в систему мониторинга.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ Нет прав администратора")
        return
    
    try:
        # Получаем метрики модуля
        template_service = TemplateService(services, services.modules.get_module_settings("my_module") or {})
        stats = await template_service.get_global_stats()
        
        # Отправляем метрики в систему мониторинга
        metrics = {
            "module_name": "my_module",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_items": stats.get("total_items", 0),
                "active_items": stats.get("active_items", 0),
                "unique_users": stats.get("unique_users", 0)
            }
        }
        
        # Отправляем через систему событий
        if hasattr(services, 'events'):
            await services.events.emit("metrics_collected", metrics)
        
        await message.answer(
            f"📊 **Метрики отправлены в мониторинг**\n\n"
            f"**Всего элементов:** {metrics['metrics']['total_items']}\n"
            f"**Активных элементов:** {metrics['metrics']['active_items']}\n"
            f"**Уникальных пользователей:** {metrics['metrics']['unique_users']}\n\n"
            f"Время отправки: {datetime.now().strftime('%H:%M:%S')}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки метрик: {e}")
        await message.answer("❌ Ошибка отправки метрик")

# === ПРИМЕР 4: ИНТЕГРАЦИЯ С ВНЕШНИМИ СЕРВИСАМИ ===

import aiohttp
import json

@integration_router.message(Command("external_service_integration"))
async def external_service_integration_example(message: types.Message, services):
    """
    Пример интеграции с внешними сервисами
    
    Этот пример показывает, как интегрироваться с внешними
    API и сервисами.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADVANCED):
        await message.answer("❌ Нет доступа к продвинутым функциям")
        return
    
    # Получаем настройки модуля
    settings = services.modules.get_module_settings("my_module") or {}
    api_key = settings.get('api_key', '')
    webhook_url = settings.get('webhook_url', '')
    
    if not api_key:
        await message.answer(
            "❌ **API ключ не настроен**\n\n"
            "Для интеграции с внешними сервисами необходимо настроить API ключ."
        )
        return
    
    loading_msg = await message.answer("⏳ Интегрируюсь с внешним сервисом...")
    
    try:
        # Пример интеграции с внешним API
        async with aiohttp.ClientSession() as session:
            # Отправляем данные во внешний сервис
            payload = {
                "module": "my_module",
                "action": "sync_data",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "user_id": message.from_user.id,
                    "action": "external_integration_test"
                }
            }
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            async with session.post(
                'https://api.external-service.com/webhook',
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Отправляем webhook уведомление (если настроен)
                    if webhook_url:
                        await send_webhook_notification(webhook_url, payload, services)
                    
                    await loading_msg.edit_text(
                        f"✅ **Интеграция успешна**\n\n"
                        f"**Статус:** {response.status}\n"
                        f"**Ответ сервиса:** {result.get('message', 'OK')}\n"
                        f"**Webhook:** {'Отправлен' if webhook_url else 'Не настроен'}"
                    )
                else:
                    await loading_msg.edit_text(
                        f"❌ **Ошибка интеграции**\n\n"
                        f"**Статус:** {response.status}\n"
                        f"**Ошибка:** {await response.text()}"
                    )
    
    except asyncio.TimeoutError:
        await loading_msg.edit_text("❌ Превышено время ожидания ответа от внешнего сервиса")
    except Exception as e:
        logger.error(f"Ошибка внешней интеграции: {e}")
        await loading_msg.edit_text("❌ Ошибка интеграции с внешним сервисом")

async def send_webhook_notification(webhook_url: str, payload: Dict[str, Any], services):
    """
    Отправка webhook уведомления
    
    Args:
        webhook_url: URL для отправки webhook
        payload: Данные для отправки
        services: Провайдер сервисов SDB
    """
    try:
        settings = services.modules.get_module_settings("my_module") or {}
        webhook_secret = settings.get('webhook_secret', '')
        
        async with aiohttp.ClientSession() as session:
            headers = {'Content-Type': 'application/json'}
            
            # Добавляем подпись, если есть секрет
            if webhook_secret:
                import hmac
                import hashlib
                signature = hmac.new(
                    webhook_secret.encode(),
                    json.dumps(payload).encode(),
                    hashlib.sha256
                ).hexdigest()
                headers['X-Signature'] = f'sha256={signature}'
            
            async with session.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    logger.info(f"Webhook уведомление отправлено успешно: {webhook_url}")
                else:
                    logger.warning(f"Webhook уведомление не доставлено: {response.status}")
    
    except Exception as e:
        logger.error(f"Ошибка отправки webhook: {e}")

# === ПРИМЕР 5: ИНТЕГРАЦИЯ С СИСТЕМОЙ ПЛАНИРОВЩИКА ЗАДАЧ ===

@integration_router.message(Command("scheduler_integration"))
async def scheduler_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой планировщика задач
    
    Этот пример показывает, как создавать и управлять
    запланированными задачами.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ Нет прав администратора")
        return
    
    try:
        # Создаем задачу для очистки старых данных
        cleanup_job = {
            "id": f"module_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "module": "my_module",
            "function": "cleanup_old_data",
            "schedule": "0 2 * * *",  # Каждый день в 2:00
            "args": [30],  # Удалять данные старше 30 дней
            "enabled": True
        }
        
        # Регистрируем задачу в планировщике
        if hasattr(services, 'scheduler'):
            await services.scheduler.add_job(cleanup_job)
            
            await message.answer(
                "⏰ **Задача добавлена в планировщик**\n\n"
                f"**ID задачи:** {cleanup_job['id']}\n"
                f"**Функция:** {cleanup_job['function']}\n"
                f"**Расписание:** {cleanup_job['schedule']}\n"
                f"**Статус:** {'✅ Включена' if cleanup_job['enabled'] else '❌ Отключена'}"
            )
        else:
            await message.answer("❌ Планировщик задач недоступен")
    
    except Exception as e:
        logger.error(f"Ошибка создания задачи: {e}")
        await message.answer("❌ Ошибка создания задачи в планировщике")

async def cleanup_old_data(days_old: int = 30):
    """
    Функция очистки старых данных
    
    Args:
        days_old: Количество дней, после которых данные считаются старыми
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Здесь должна быть логика очистки данных модуля
        logger.info(f"Очистка данных модуля старше {days_old} дней (до {cutoff_date})")
        
        # Пример очистки (замените на реальную логику)
        # async with services.db.get_session() as session:
        #     stmt = delete(TemplateModel).where(
        #         TemplateModel.created_at < cutoff_date,
        #         TemplateModel.is_active == False
        #     )
        #     result = await session.execute(stmt)
        #     await session.commit()
        
    except Exception as e:
        logger.error(f"Ошибка очистки старых данных: {e}")

# === ПРИМЕР 6: ИНТЕГРАЦИЯ С СИСТЕМОЙ АНАЛИТИКИ ===

@integration_router.message(Command("analytics_integration"))
async def analytics_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой аналитики
    
    Этот пример показывает, как отправлять данные
    в систему аналитики для анализа использования.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ Нет прав администратора")
        return
    
    try:
        # Собираем аналитические данные
        template_service = TemplateService(services, services.modules.get_module_settings("my_module") or {})
        stats = await template_service.get_global_stats()
        
        # Формируем аналитическое событие
        analytics_event = {
            "event_type": "module_usage",
            "module_name": "my_module",
            "timestamp": datetime.now().isoformat(),
            "user_id": message.from_user.id,
            "properties": {
                "total_items": stats.get("total_items", 0),
                "active_items": stats.get("active_items", 0),
                "unique_users": stats.get("unique_users", 0),
                "action": "analytics_integration_test"
            }
        }
        
        # Отправляем в систему аналитики
        if hasattr(services, 'analytics'):
            await services.analytics.track_event(analytics_event)
        
        # Также отправляем через систему событий
        if hasattr(services, 'events'):
            await services.events.emit("analytics_event", analytics_event)
        
        await message.answer(
            "📈 **Данные отправлены в аналитику**\n\n"
            f"**Событие:** {analytics_event['event_type']}\n"
            f"**Модуль:** {analytics_event['module_name']}\n"
            f"**Всего элементов:** {analytics_event['properties']['total_items']}\n"
            f"**Активных элементов:** {analytics_event['properties']['active_items']}\n"
            f"**Уникальных пользователей:** {analytics_event['properties']['unique_users']}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки аналитических данных: {e}")
        await message.answer("❌ Ошибка отправки данных в аналитику")

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_backup_keyboard():
    """Создает клавиатуру для управления бэкапами"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💾 Создать бэкап",
            callback_data="backup_create"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📋 Список бэкапов",
            callback_data="backup_list"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Восстановить",
            callback_data="backup_restore"
        )
    )
    
    return builder.as_markup()

# === ПРИМЕР 7: ИНТЕГРАЦИЯ С СИСТЕМОЙ КЭШИРОВАНИЯ ===

@integration_router.message(Command("cache_integration"))
async def cache_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой кэширования
    
    Этот пример показывает, как эффективно использовать
    кэширование для оптимизации производительности.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.VIEW_DATA):
        await message.answer("❌ Нет доступа к данным")
        return
    
    cache_key = f"module_data_{message.from_user.id}"
    
    try:
        # Проверяем кэш
        cached_data = await services.cache.get(cache_key)
        
        if cached_data:
            await message.answer(
                f"⚡ **Данные из кэша**\n\n"
                f"**Ключ:** {cache_key}\n"
                f"**Данные:** {cached_data}\n"
                f"**Источник:** Кэш"
            )
        else:
            # Получаем данные из БД
            template_service = TemplateService(services, services.modules.get_module_settings("my_module") or {})
            user_stats = await template_service.get_user_stats(message.from_user.id)
            
            # Кэшируем на 10 минут
            await services.cache.set(cache_key, user_stats, ttl=600)
            
            await message.answer(
                f"💾 **Данные из БД и кэшированы**\n\n"
                f"**Ключ:** {cache_key}\n"
                f"**Данные:** {user_stats}\n"
                f"**Источник:** База данных\n"
                f"**Кэшировано:** Да (10 минут)"
            )
    
    except Exception as e:
        logger.error(f"Ошибка работы с кэшем: {e}")
        await message.answer("❌ Ошибка работы с кэшем")

# === ПРИМЕР 8: ИНТЕГРАЦИЯ С СИСТЕМОЙ ЛОГИРОВАНИЯ ===

@integration_router.message(Command("logging_integration"))
async def logging_integration_example(message: types.Message, services):
    """
    Пример интеграции с системой логирования
    
    Этот пример показывает, как использовать различные
    уровни логирования для отладки и мониторинга.
    """
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ADMIN):
        await message.answer("❌ Нет прав администратора")
        return
    
    # Различные уровни логирования
    logger.debug("Debug сообщение из модуля")
    logger.info("Info сообщение из модуля")
    logger.warning("Warning сообщение из модуля")
    logger.error("Error сообщение из модуля")
    logger.critical("Critical сообщение из модуля")
    
    # Логирование с контекстом
    logger.bind(
        module="my_module",
        user_id=message.from_user.id,
        action="logging_integration_test"
    ).info("Контекстное логирование")
    
    # Логирование в аудит
    log_module_action(
        services,
        "logging_integration_test",
        message.from_user.id,
        {"test_type": "various_log_levels"}
    )
    
    await message.answer(
        "📝 **Логирование выполнено**\n\n"
        "Отправлены сообщения на все уровни логирования:\n"
        "• Debug\n"
        "• Info\n"
        "• Warning\n"
        "• Error\n"
        "• Critical\n\n"
        "Проверьте логи для просмотра сообщений."
    )
