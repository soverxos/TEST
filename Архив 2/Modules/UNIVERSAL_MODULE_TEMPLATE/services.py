"""
Бизнес-логика универсального шаблона модуля

Этот файл содержит сервисы для работы с данными модуля.
Сервисы инкапсулируют бизнес-логику и работу с базой данных.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from .models import TemplateModel, UserData
from .permissions import MODULE_NAME
from .utils import get_current_timestamp, log_module_action

class TemplateService:
    """
    Основной сервис для работы с данными шаблона модуля
    
    Этот сервис предоставляет методы для:
    - CRUD операций с данными
    - Работы с пользовательскими настройками
    - Статистики и аналитики
    - Валидации данных
    """
    
    def __init__(self, services, settings: Dict[str, Any]):
        """
        Инициализация сервиса
        
        Args:
            services: Провайдер сервисов SDB
            settings: Настройки модуля
        """
        self.services = services
        self.settings = settings
        self.logger = logger.bind(service=f"{MODULE_NAME}.service")
        
        # Получаем настройки
        self.max_items_per_user = settings.get('max_items_per_user', 10)
        self.debug_mode = settings.get('debug_mode', False)
        self.notification_enabled = settings.get('notification_enabled', True)
        
        self.logger.info(f"TemplateService инициализирован с настройками: {settings}")
    
    async def create_item(self, user_id: int, title: str, description: str = None, 
                         priority: int = 0, tags: List[str] = None) -> Optional[TemplateModel]:
        """
        Создание нового элемента
        
        Args:
            user_id: ID пользователя
            title: Заголовок
            description: Описание
            priority: Приоритет (0-100)
            tags: Список тегов
            
        Returns:
            Созданный элемент или None при ошибке
        """
        try:
            async with self.services.db.get_session() as session:
                # Проверяем лимит элементов для пользователя
                count_stmt = select(func.count(TemplateModel.id)).where(
                    TemplateModel.user_id == user_id
                )
                count_result = await session.execute(count_stmt)
                current_count = count_result.scalar()
                
                if current_count >= self.max_items_per_user:
                    self.logger.warning(f"Пользователь {user_id} превысил лимит элементов: {current_count}/{self.max_items_per_user}")
                    return None
                
                # Создаем новый элемент
                new_item = TemplateModel(
                    user_id=user_id,
                    title=title,
                    description=description,
                    priority=priority,
                    tags=",".join(tags) if tags else None,
                    is_active=True,
                    is_public=False
                )
                
                session.add(new_item)
                await session.flush([new_item])
                
                # Обновляем статистику пользователя
                await self._update_user_stats(session, user_id)
                
                await session.commit()
                
                self.logger.info(f"Создан новый элемент {new_item.id} для пользователя {user_id}")
                
                # Логируем в аудит
                log_module_action(
                    self.services,
                    "create_item",
                    user_id,
                    {"item_id": new_item.id, "title": title}
                )
                
                return new_item
                
        except Exception as e:
            self.logger.error(f"Ошибка создания элемента для пользователя {user_id}: {e}")
            return None
    
    async def get_user_items(self, user_id: int, include_inactive: bool = False) -> List[TemplateModel]:
        """
        Получение элементов пользователя
        
        Args:
            user_id: ID пользователя
            include_inactive: Включать ли неактивные элементы
            
        Returns:
            Список элементов пользователя
        """
        try:
            async with self.services.db.get_session() as session:
                stmt = select(TemplateModel).where(TemplateModel.user_id == user_id)
                
                if not include_inactive:
                    stmt = stmt.where(TemplateModel.is_active == True)
                
                stmt = stmt.order_by(TemplateModel.priority.desc(), TemplateModel.created_at.desc())
                
                result = await session.execute(stmt)
                items = list(result.scalars().all())
                
                self.logger.debug(f"Найдено {len(items)} элементов для пользователя {user_id}")
                return items
                
        except Exception as e:
            self.logger.error(f"Ошибка получения элементов пользователя {user_id}: {e}")
            return []
    
    async def get_item_by_id(self, item_id: int, user_id: int = None) -> Optional[TemplateModel]:
        """
        Получение элемента по ID
        
        Args:
            item_id: ID элемента
            user_id: ID пользователя (для проверки доступа)
            
        Returns:
            Элемент или None
        """
        try:
            async with self.services.db.get_session() as session:
                stmt = select(TemplateModel).where(TemplateModel.id == item_id)
                
                if user_id:
                    stmt = stmt.where(TemplateModel.user_id == user_id)
                
                result = await session.execute(stmt)
                item = result.scalars().first()
                
                return item
                
        except Exception as e:
            self.logger.error(f"Ошибка получения элемента {item_id}: {e}")
            return None
    
    async def update_item(self, item_id: int, user_id: int, **kwargs) -> bool:
        """
        Обновление элемента
        
        Args:
            item_id: ID элемента
            user_id: ID пользователя
            **kwargs: Поля для обновления
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            async with self.services.db.get_session() as session:
                # Проверяем, что элемент принадлежит пользователю
                item = await self.get_item_by_id(item_id, user_id)
                if not item:
                    return False
                
                # Обновляем поля
                update_data = {}
                for key, value in kwargs.items():
                    if hasattr(TemplateModel, key) and key not in ['id', 'user_id', 'created_at']:
                        update_data[key] = value
                
                if not update_data:
                    return False
                
                # Выполняем обновление
                stmt = update(TemplateModel).where(
                    TemplateModel.id == item_id,
                    TemplateModel.user_id == user_id
                ).values(**update_data)
                
                await session.execute(stmt)
                await session.commit()
                
                self.logger.info(f"Обновлен элемент {item_id} пользователя {user_id}")
                
                # Логируем в аудит
                log_module_action(
                    self.services,
                    "update_item",
                    user_id,
                    {"item_id": item_id, "updated_fields": list(update_data.keys())}
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления элемента {item_id}: {e}")
            return False
    
    async def delete_item(self, item_id: int, user_id: int) -> bool:
        """
        Удаление элемента
        
        Args:
            item_id: ID элемента
            user_id: ID пользователя
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            async with self.services.db.get_session() as session:
                # Проверяем, что элемент принадлежит пользователю
                item = await self.get_item_by_id(item_id, user_id)
                if not item:
                    return False
                
                # Удаляем элемент
                stmt = delete(TemplateModel).where(
                    TemplateModel.id == item_id,
                    TemplateModel.user_id == user_id
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                if result.rowcount > 0:
                    self.logger.info(f"Удален элемент {item_id} пользователя {user_id}")
                    
                    # Логируем в аудит
                    log_module_action(
                        self.services,
                        "delete_item",
                        user_id,
                        {"item_id": item_id}
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка удаления элемента {item_id}: {e}")
            return False
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получение статистики пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        try:
            async with self.services.db.get_session() as session:
                # Получаем или создаем данные пользователя
                user_data = await self._get_or_create_user_data(session, user_id)
                
                # Считаем активные элементы
                active_count_stmt = select(func.count(TemplateModel.id)).where(
                    TemplateModel.user_id == user_id,
                    TemplateModel.is_active == True
                )
                active_result = await session.execute(active_count_stmt)
                active_count = active_result.scalar()
                
                # Считаем публичные элементы
                public_count_stmt = select(func.count(TemplateModel.id)).where(
                    TemplateModel.user_id == user_id,
                    TemplateModel.is_public == True
                )
                public_result = await session.execute(public_count_stmt)
                public_count = public_result.scalar()
                
                return {
                    "user_id": user_id,
                    "items_created": user_data.items_created,
                    "active_items": active_count,
                    "public_items": public_count,
                    "max_items": self.max_items_per_user,
                    "last_activity": user_data.last_activity,
                    "can_create_more": active_count < self.max_items_per_user
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return {}
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """
        Получение глобальной статистики модуля
        
        Returns:
            Словарь с глобальной статистикой
        """
        try:
            async with self.services.db.get_session() as session:
                # Общее количество элементов
                total_items_stmt = select(func.count(TemplateModel.id))
                total_result = await session.execute(total_items_stmt)
                total_items = total_result.scalar()
                
                # Активные элементы
                active_items_stmt = select(func.count(TemplateModel.id)).where(
                    TemplateModel.is_active == True
                )
                active_result = await session.execute(active_items_stmt)
                active_items = active_result.scalar()
                
                # Уникальные пользователи
                unique_users_stmt = select(func.count(func.distinct(TemplateModel.user_id)))
                users_result = await session.execute(unique_users_stmt)
                unique_users = users_result.scalar()
                
                return {
                    "total_items": total_items,
                    "active_items": active_items,
                    "unique_users": unique_users,
                    "module_version": "1.0.0"
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения глобальной статистики: {e}")
            return {}
    
    async def _get_or_create_user_data(self, session, user_id: int) -> UserData:
        """Получение или создание данных пользователя"""
        stmt = select(UserData).where(UserData.user_id == user_id)
        result = await session.execute(stmt)
        user_data = result.scalars().first()
        
        if not user_data:
            user_data = UserData(user_id=user_id)
            session.add(user_data)
            await session.flush([user_data])
        
        return user_data
    
    async def _update_user_stats(self, session, user_id: int):
        """Обновление статистики пользователя"""
        user_data = await self._get_or_create_user_data(session, user_id)
        user_data.increment_items_count()
        await session.flush([user_data])
    
    async def process_data(self, data: str) -> str:
        """
        Обработка данных (пример бизнес-логики)
        
        Args:
            data: Входные данные
            
        Returns:
            Обработанные данные
        """
        self.logger.info(f"Обработка данных: {data}")
        
        # Пример обработки
        result = f"Обработано: {data.upper()}"
        
        # Логируем в аудит
        if hasattr(self.services, 'audit_logger'):
            from core.security.audit_logger import AuditEventType
            self.services.audit_logger.log_event(
                event_type=AuditEventType.COMMAND_EXECUTION,
                module_name=MODULE_NAME,
                details={"input": data, "output": result}
            )
        
        return result
