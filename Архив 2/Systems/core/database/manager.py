# core/database/manager.py

from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Type, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from loguru import logger

from .base import Base
from Systems.core.app_settings import DEFAULT_PROJECT_DATA_DIR_NAME

if TYPE_CHECKING:
    from Systems.core.app_settings import DBSettings, AppSettings

class DBManager:
    def __init__(self, db_settings: 'DBSettings', app_settings: 'AppSettings'): # app_settings теперь обязателен
        self._db_settings: 'DBSettings' = db_settings
        self._app_settings: 'AppSettings' = app_settings
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._db_url: Optional[str] = None

        self._logger = logger.bind(service="DBManager")
        self._logger.info(f"DBManager инициализирован для типа БД: {self._db_settings.type}")

    def _build_db_url(self) -> str:
        if self._db_url:
            return self._db_url

        db_type = self._db_settings.type
        url: str

        if db_type == "sqlite":
            sqlite_path_str = self._db_settings.sqlite_path
            path_obj = Path(sqlite_path_str)
            abs_path: Path

            if path_obj.is_absolute():
                abs_path = path_obj.resolve()
            else:
                # self._app_settings здесь всегда должен быть доступен, т.к. он обязательный параметр конструктора
                if DEFAULT_PROJECT_DATA_DIR_NAME in path_obj.parts:
                    project_root_dir = self._app_settings.core.project_data_path.parent
                    abs_path = (project_root_dir / path_obj).resolve()
                else: 
                    abs_path = (self._app_settings.core.project_data_path / path_obj).resolve()
            
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            self._logger.debug(f"Окончательный абсолютный путь для SQLite: {abs_path}")
            url = f"sqlite+aiosqlite:///{abs_path}"
            
        elif db_type == "postgresql":
            if not self._db_settings.pg_dsn:
                msg = "DSN для PostgreSQL (pg_dsn) не указана в настройках."
                self._logger.error(msg)
                raise ValueError(msg)
            url = str(self._db_settings.pg_dsn)
            
        elif db_type == "mysql":
            if not self._db_settings.mysql_dsn:
                msg = "DSN для MySQL (mysql_dsn) не указана в настройках."
                self._logger.error(msg)
                raise ValueError(msg)
            url = str(self._db_settings.mysql_dsn)
            
        else:
            msg = f"Неподдерживаемый тип базы данных в настройках: '{db_type}'"
            self._logger.error(msg)
            raise ValueError(msg)
        
        self._db_url = url
        return url

    async def initialize(self) -> None:
        if self._engine is not None:
            self._logger.debug("DBManager (engine) уже был инициализирован.")
            return

        db_url = self._build_db_url()
        self._logger.info(f"Инициализация асинхронного движка SQLAlchemy для URL: '{db_url[:db_url.find('://')+3]}...' (детали URL скрыты)")
        
        echo_sql = self._db_settings.echo_sql

        try:
            self._engine = create_async_engine(
                db_url,
                echo=echo_sql, 
                poolclass=NullPool,
            )
            
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            self._logger.success("SQLAlchemy AsyncEngine и SessionFactory успешно созданы.")
        except Exception as e:
            self._logger.critical(f"Ошибка при создании SQLAlchemy Engine или SessionFactory для URL '{db_url}': {e}", exc_info=True)
            self._engine = None
            self._session_factory = None
            raise

    async def dispose(self) -> None:
        if self._engine:
            self._logger.info("Закрытие SQLAlchemy AsyncEngine...")
            try:
                await self._engine.dispose()
                self._logger.success("SQLAlchemy AsyncEngine успешно закрыт.")
            except Exception as e:
                self._logger.error(f"Ошибка при закрытии SQLAlchemy AsyncEngine: {e}", exc_info=True)
            finally:
                self._engine = None
                self._session_factory = None
        else:
            self._logger.debug("DBManager (engine) не был инициализирован или уже закрыт.")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._session_factory:
            msg = "DBManager SessionFactory не инициализирована! Вызовите initialize() перед запросом сессии."
            self._logger.critical(msg)
            raise RuntimeError(msg)

        session: AsyncSession = self._session_factory()
        self._logger.trace(f"Сессия БД {id(session)} открыта.")
        try:
            yield session
        except Exception as e:
            self._logger.error(f"Ошибка в сессии БД {id(session)}: {e}. Выполняется откат (rollback).", exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()
            self._logger.trace(f"Сессия БД {id(session)} закрыта.")

    async def create_all_core_tables(self) -> None:
        if not self._engine:
            err_msg = "DBManager Engine не инициализирован. Невозможно создать таблицы."
            self._logger.error(err_msg)
            raise RuntimeError(err_msg)

        self._logger.info("Запрос на создание всех таблиц ядра на основе Base.metadata...")
        async with self._engine.begin() as conn:
            from Systems.core.database import core_models # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        self._logger.success("Все таблицы ядра (на основе текущего Base.metadata) успешно созданы (или уже существовали).")

    async def create_specific_module_tables(self, module_model_classes: List[Type[Base]]) -> None:
        if not self._engine:
            err_msg = "DBManager Engine не инициализирован. Невозможно создать таблицы модуля."
            self._logger.error(err_msg)
            raise RuntimeError(err_msg)
        if not module_model_classes:
            self._logger.debug("Нет моделей для создания таблиц модуля (список пуст).")
            return

        # Импортируем модели ядра ПЕРЕД извлечением таблиц модулей
        # Это необходимо для того, чтобы SQLAlchemy знал о таблицах ядра (sdb_users, sdb_roles и т.д.)
        # при создании foreign key в таблицах модулей
        from Systems.core.database import core_models # noqa: F401
        
        # Убеждаемся, что таблицы ядра созданы физически в БД перед созданием таблиц модулей
        # Проверяем наличие хотя бы одной таблицы ядра
        from sqlalchemy import inspect, text
        from Systems.core.database.core_models import SDB_CORE_TABLE_PREFIX
        
        # Проверяем существование таблиц ядра в отдельной транзакции
        async with self._engine.begin() as check_conn:
            if self._db_settings.type == "sqlite":
                result = await check_conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sdb_%'"))
                existing_core_tables = [row[0] for row in result.fetchall()]
            else:
                inspector = inspect(self._engine.sync_engine)
                existing_core_tables = [t for t in inspector.get_table_names() if t.startswith("sdb_")]
        
        # Если таблиц ядра нет, создаем их (в отдельной транзакции)
        if not existing_core_tables:
            self._logger.warning("Таблицы ядра не найдены в БД. Создаем их перед созданием таблиц модуля...")
            await self.create_all_core_tables()
            self._logger.success("Таблицы ядра созданы. Продолжаем создание таблиц модуля...")
        else:
            # Проверяем наличие конкретно таблицы sdb_users, так как она нужна для foreign keys
            users_table_name = f"{SDB_CORE_TABLE_PREFIX}users"
            if users_table_name not in existing_core_tables:
                self._logger.warning(f"Таблица '{users_table_name}' не найдена в БД. Создаем таблицы ядра...")
                await self.create_all_core_tables()
                self._logger.success("Таблицы ядра созданы. Продолжаем создание таблиц модуля...")
            else:
                self._logger.debug(f"Таблицы ядра найдены в БД, включая '{users_table_name}': {existing_core_tables[:3]}...")

        tables_to_create = [model_cls.__table__ for model_cls in module_model_classes]
        table_names_str = ", ".join([table.name for table in tables_to_create])
        self._logger.info(f"Запрос на создание таблиц для модуля: [{table_names_str}]")

        async with self._engine.begin() as conn:
            # Важно: модели ядра уже импортированы выше, поэтому они в Base.metadata
            # Таблицы ядра уже проверены и созданы выше, если их не было
            # Используем create_all БЕЗ указания конкретных таблиц, чтобы SQLAlchemy
            # мог правильно обработать все зависимости (foreign keys) между таблицами
            # checkfirst=True гарантирует, что существующие таблицы не будут пересозданы
            # Это создаст только те таблицы, которых еще нет в БД
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    bind=sync_conn, 
                    checkfirst=True
                )
            )
        self._logger.success(f"Таблицы модуля [{table_names_str}] успешно созданы (или уже существовали).")

    async def drop_specific_module_tables(self, module_model_classes: List[Type[Base]]) -> None:
        if not self._engine:
            err_msg = "DBManager Engine не инициализирован. Невозможно удалить таблицы модуля."
            self._logger.error(err_msg)
            raise RuntimeError(err_msg)
        if not module_model_classes:
            self._logger.debug("Нет моделей для удаления таблиц модуля (список пуст).")
            return

        tables_to_drop = [model_cls.__table__ for model_cls in module_model_classes]
        tables_to_drop_ordered = tables_to_drop[::-1] 
        table_names_str = ", ".join([table.name for table in tables_to_drop_ordered])
        
        self._logger.warning(f"ЗАПРОС НА УДАЛЕНИЕ ТАБЛИЦ МОДУЛЯ (ОПАСНО!): [{table_names_str}]")
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all, tables=tables_to_drop_ordered)
        self._logger.success(f"Таблицы модуля [{table_names_str}] успешно УДАЛЕНЫ.")