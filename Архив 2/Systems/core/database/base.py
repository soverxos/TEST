# core/database/base.py
from typing import Any, Dict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func, MetaData
from datetime import datetime, timezone 

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata_obj = MetaData(naming_convention=convention)

class Base(DeclarativeBase):
    metadata = metadata_obj

class SDBBaseModel(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now() 
    )
    def to_dict(self, exclude: set = None) -> Dict[str, Any]:
        if exclude is None: exclude = set()
        data = {}
        for prop in self.__mapper__.iterate_properties:
            if hasattr(prop, 'columns') and prop.key not in exclude:
                try: data[prop.key] = getattr(self, prop.key)
                except AttributeError: pass
        return data
    def __repr__(self) -> str:
        pk_column_names = [pk_col.name for pk_col in self.__table__.primary_key.columns]
        pk_values_str = ", ".join(f"{name}={getattr(self, name)!r}" for name in pk_column_names)
        return f"<{self.__class__.__name__}({pk_values_str})>"