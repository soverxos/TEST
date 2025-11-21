# core/database/core_models.py
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, UniqueConstraint, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SDBBaseModel 

SDB_CORE_TABLE_PREFIX = "sdb_"

if TYPE_CHECKING:
    pass 

def get_column_comment(text: str) -> Optional[str]:
    return text

class Permission(SDBBaseModel):
    __tablename__ = f"{SDB_CORE_TABLE_PREFIX}permissions"
    
    name: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        index=True, 
        nullable=False, 
        comment=get_column_comment("Уникальное имя разрешения (например, 'view_users', 'manage_modules')")
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        comment=get_column_comment("Описание разрешения")
    )
    
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=f"{SDB_CORE_TABLE_PREFIX}role_permissions",
        back_populates="permissions",
        lazy="selectin" 
    )
    
    # Новое отношение для прямых разрешений пользователя
    users_with_direct_access: Mapped[List["User"]] = relationship(
        "User",
        secondary=f"{SDB_CORE_TABLE_PREFIX}user_permissions", # Имя новой связующей таблицы
        back_populates="direct_permissions",
        lazy="selectin" # или "noload", если не нужно часто загружать пользователей по разрешению
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"

class RolePermission(SDBBaseModel):
    __tablename__ = f"{SDB_CORE_TABLE_PREFIX}role_permissions"
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name=f'uq_{SDB_CORE_TABLE_PREFIX}role_permissions_role_id_permission_id'),
    )
    
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SDB_CORE_TABLE_PREFIX}roles.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        comment=get_column_comment("ID роли")
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SDB_CORE_TABLE_PREFIX}permissions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        comment=get_column_comment("ID разрешения")
    )

    def __repr__(self) -> str:
        return f"<RolePermission(id={self.id}, role_id={self.role_id}, permission_id={self.permission_id})>"
        
class Role(SDBBaseModel):
    __tablename__ = f"{SDB_CORE_TABLE_PREFIX}roles"
    
    name: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        index=True, 
        nullable=False, 
        comment=get_column_comment("Уникальное имя роли")
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        comment=get_column_comment("Описание роли")
    )
    
    users: Mapped[List["User"]] = relationship(
        "User", 
        secondary=f"{SDB_CORE_TABLE_PREFIX}user_roles",
        back_populates="roles",
        lazy="selectin",
        cascade="save-update, merge" 
    )

    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=f"{SDB_CORE_TABLE_PREFIX}role_permissions",
        back_populates="roles",
        lazy="selectin", 
        cascade="save-update, merge"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"


class UserRole(SDBBaseModel):
    __tablename__ = f"{SDB_CORE_TABLE_PREFIX}user_roles"
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name=f'uq_{SDB_CORE_TABLE_PREFIX}user_roles_user_id_role_id'),
    )
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SDB_CORE_TABLE_PREFIX}users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        comment=get_column_comment("ID пользователя")
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SDB_CORE_TABLE_PREFIX}roles.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        comment=get_column_comment("ID роли")
    )

    def __repr__(self) -> str:
        return f"<UserRole(id={self.id}, user_id={self.user_id}, role_id={self.role_id})>"

# --- Новая модель для связи User <-> Permission ---
class UserPermission(SDBBaseModel):
    __tablename__ = f"{SDB_CORE_TABLE_PREFIX}user_permissions"
    __table_args__ = (
        UniqueConstraint('user_id', 'permission_id', name=f'uq_{SDB_CORE_TABLE_PREFIX}user_permissions_user_id_permission_id'),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SDB_CORE_TABLE_PREFIX}users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment=get_column_comment("ID пользователя")
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SDB_CORE_TABLE_PREFIX}permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment=get_column_comment("ID разрешения")
    )

    def __repr__(self) -> str:
        return f"<UserPermission(id={self.id}, user_id={self.user_id}, permission_id={self.permission_id})>"


class User(SDBBaseModel):
    __tablename__ = f"{SDB_CORE_TABLE_PREFIX}users"

    username_lower: Mapped[Optional[str]] = mapped_column(
        String(32), 
        nullable=True, 
        index=True, 
        comment=get_column_comment("Telegram username в нижнем регистре для поиска")
    )
    
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, 
        unique=True, 
        index=True, 
        nullable=False, 
        comment=get_column_comment("Уникальный Telegram ID пользователя")
    )
    username: Mapped[Optional[str]] = mapped_column( 
        String(32), 
        nullable=True, 
        index=True, 
        comment=get_column_comment("Telegram username (оригинальный регистр)")
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        comment=get_column_comment("Имя пользователя")
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        comment=get_column_comment("Фамилия пользователя")
    )
    preferred_language_code: Mapped[Optional[str]] = mapped_column(
        String(10), 
        nullable=True, 
        comment=get_column_comment("Код языка бота")
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, 
        nullable=False, 
        comment=get_column_comment("Активен ли пользователь")
    )
    is_bot_blocked: Mapped[bool] = mapped_column(
        default=False, 
        nullable=False, 
        comment=get_column_comment("Заблокировал ли пользователь бота")
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, 
        comment=get_column_comment("Время последней активности")
    )

    roles: Mapped[List["Role"]] = relationship(
        "Role", 
        secondary=f"{SDB_CORE_TABLE_PREFIX}user_roles",
        back_populates="users",
        lazy="selectin",
        cascade="save-update, merge"
    )
    
    # Новое отношение для прямых разрешений
    direct_permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=f"{SDB_CORE_TABLE_PREFIX}user_permissions", # Имя новой связующей таблицы
        back_populates="users_with_direct_access",
        lazy="selectin", # или "noload", если не нужно часто загружать права при загрузке юзера
        cascade="save-update, merge" # Позволит управлять через user.direct_permissions.append()
    )
    
    @property
    def full_name(self) -> str:
        parts = []
        if self.first_name: parts.append(self.first_name)
        if self.last_name: parts.append(self.last_name)
        if parts: return " ".join(parts)
        elif self.username: return f"@{self.username}"
        return f"User_{self.telegram_id}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, tg_id={self.telegram_id}, name='{self.full_name}')>"