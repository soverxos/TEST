"""
Модели данных для универсального шаблона модуля

Этот файл содержит SQLAlchemy модели для работы с базой данных.
Модели автоматически создают таблицы при инициализации модуля.
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import SDBBaseModel

if TYPE_CHECKING:
    from core.database.core_models import User

class TemplateModel(SDBBaseModel):
    """
    Основная модель данных для шаблона модуля
    
    Эта модель демонстрирует:
    - Базовые поля (id, created_at, updated_at)
    - Связи с пользователями
    - Различные типы данных
    - Индексы для производительности
    """
    
    __tablename__ = "universal_template_data"
    
    # Связь с пользователем
    user_id: Mapped[int] = mapped_column(
        ForeignKey("sdb_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя, создавшего запись"
    )
    
    # Основные поля
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Заголовок записи"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Описание записи"
    )
    
    # Числовые поля
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Приоритет записи (0-100)"
    )
    
    # Булевы поля
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активна ли запись"
    )
    
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Публичная ли запись"
    )
    
    # Дополнительные поля
    tags: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Теги через запятую"
    )
    
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Дополнительные данные в JSON формате"
    )
    
    # Связи (без обратной связи для избежания конфликтов)
    user: Mapped["User"] = relationship(
        "User"
    )
    
    def __repr__(self) -> str:
        return f"<TemplateModel(id={self.id}, title='{self.title}', user_id={self.user_id})>"
    
    def to_dict(self) -> dict:
        """Конвертация в словарь для API"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class UserData(SDBBaseModel):
    """
    Дополнительная модель для хранения пользовательских данных
    
    Эта модель демонстрирует:
    - Связь один-к-одному с пользователем
    - Хранение настроек пользователя
    - JSON данные
    """
    
    __tablename__ = "universal_template_user_data"
    
    # Связь с пользователем (один-к-одному)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("sdb_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="ID пользователя"
    )
    
    # Настройки пользователя
    preferences: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Настройки пользователя в JSON формате"
    )
    
    # Статистика
    items_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Количество созданных элементов"
    )
    
    last_activity: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последней активности"
    )
    
    # Дополнительные поля
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Заметки пользователя"
    )
    
    # Связи (без обратной связи для избежания конфликтов)
    user: Mapped["User"] = relationship(
        "User"
    )
    
    def __repr__(self) -> str:
        return f"<UserData(id={self.id}, user_id={self.user_id}, items_created={self.items_created})>"
    
    def update_activity(self):
        """Обновление времени последней активности"""
        self.last_activity = datetime.now(timezone.utc)
    
    def increment_items_count(self):
        """Увеличение счетчика созданных элементов"""
        self.items_created += 1
        self.update_activity()

# Обратные связи к модели User будут добавлены автоматически
# через back_populates в определениях моделей выше
