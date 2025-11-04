# alembic_migrations/env.py

import asyncio
from logging.config import fileConfig
import os
import sys
from pathlib import Path
import importlib
from typing import List, Optional

# --- Настройка путей ---
ALEMBIC_DIR = Path(__file__).resolve().parent
SDB_PROJECT_ROOT = ALEMBIC_DIR.parent.parent
SDB_SYSTEMS_PATH = ALEMBIC_DIR.parent

if str(SDB_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SDB_PROJECT_ROOT))
    print(f"[Alembic Env] Корень проекта SDB ({SDB_PROJECT_ROOT}) добавлен в sys.path.")
else:
    sys.path.remove(str(SDB_PROJECT_ROOT))
    sys.path.insert(0, str(SDB_PROJECT_ROOT))
    print(f"[Alembic Env] Корень проекта SDB ({SDB_PROJECT_ROOT}) установлен на первую позицию в sys.path.")

if str(SDB_SYSTEMS_PATH) not in sys.path:
    sys.path.insert(0, str(SDB_SYSTEMS_PATH))
    print(f"[Alembic Env] Путь Systems ({SDB_SYSTEMS_PATH}) добавлен в sys.path.")


from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from alembic import context # type: ignore

try:
    from Systems.core.app_settings import settings as sdb_settings
    from Systems.core.database.base import SDBBaseModel
    from Systems.core.database.manager import DBManager
    from Systems.core.module_loader import ModuleLoader, ModuleInfo
    from Systems.core.services_provider import BotServicesProvider
    from Systems.core.database import core_models # noqa: F401
    print("[Alembic Env] Основные компоненты SDB успешно импортированы.")
except ImportError as e_imp:
    print(f"[ALEMBIC ENV ERROR] Критическая ошибка импорта компонентов SDB: {e_imp}")
    print(f"Текущий sys.path при ошибке: {sys.path}")
    sys.exit(1)

target_metadata = SDBBaseModel.metadata

try:
    print("[Alembic Env] Начало динамического импорта моделей активных модулей...")
    temp_bsp_for_alembic = BotServicesProvider(settings=sdb_settings)
    module_loader_for_alembic = ModuleLoader(
        settings=sdb_settings,
        services_provider=temp_bsp_for_alembic # Передаем созданный BSP
    )
    module_loader_for_alembic.scan_all_available_modules()
    module_loader_for_alembic._load_enabled_plugin_names() # Используем _load_enabled_plugin_names

    # Для Alembic нам нужны модели всех АКТИВНЫХ ПЛАГИНОВ
    active_plugin_module_infos: List[ModuleInfo] = [
        info for name, info in module_loader_for_alembic.available_modules.items()
        # ИЗМЕНЕНИЕ ЗДЕСЬ: используем enabled_plugin_names
        if not info.is_system_module and name in module_loader_for_alembic.enabled_plugin_names and info.manifest and info.path
    ]

    if active_plugin_module_infos:
        print(f"[Alembic Env] Найдено {len(active_plugin_module_infos)} активных плагинов для проверки моделей.")
        for module_info in active_plugin_module_infos:
            print(f"[Alembic Env] Проверка плагина: {module_info.name}")
            module_models_file = module_info.path / "models.py"
            module_models_pkg_init = module_info.path / "models" / "__init__.py"
            
            imported_this_module = False
            if module_models_file.is_file():
                # Для плагинов базовый путь импорта "Modules"
                import_target = f"Modules.{module_info.path.name}.models"
                print(f"[Alembic Env] Попытка импорта моделей из файла: {import_target}")
                try:
                    importlib.import_module(import_target)
                    print(f"[Alembic Env] > Успешно импортированы модели из файла: {import_target}")
                    imported_this_module = True
                except ImportError as e_imp_f:
                    print(f"[Alembic Env] > Ошибка импорта моделей из файла {import_target}: {e_imp_f}")
                except Exception as e_f:
                    print(f"[Alembic Env] > Неожиданная ошибка при импорте моделей из файла {import_target}: {type(e_f).__name__} - {e_f}")
            
            if not imported_this_module and module_models_pkg_init.is_file():
                import_target = f"Modules.{module_info.path.name}.models" 
                print(f"[Alembic Env] Попытка импорта моделей из пакета: {import_target}")
                try:
                    importlib.import_module(import_target)
                    print(f"[Alembic Env] > Успешно импортирован пакет моделей: {import_target}")
                except ImportError as e_imp_p:
                    print(f"[Alembic Env] > Ошибка импорта пакета моделей {import_target}: {e_imp_p}")
                except Exception as e_p:
                    print(f"[Alembic Env] > Неожиданная ошибка при импорте пакета моделей {import_target}: {type(e_p).__name__} - {e_p}")
            elif not imported_this_module and not module_models_file.is_file():
                 print(f"[Alembic Env] > Для плагина '{module_info.name}' не найден ни файл models.py, ни пакет models/__init__.py.")
    else:
        print("[Alembic Env] Активных плагинов для импорта моделей не найдено.")
    
    # Если у вас есть системные модули в Systems/core/sys_modules/ с моделями,
    # и они не импортируются автоматически (например, через Systems.core.database.core_models),
    # их нужно будет импортировать здесь явно или добавить механизм их обнаружения.
    # Пример:
    # print("[Alembic Env] Проверка системных модулей ядра...")
    # sys_module_path = SDB_PROJECT_ROOT / "Systems" / "core" / "sys_modules" / "my_sys_module_with_models"
    # if (sys_module_path / "models.py").is_file():
    #    importlib.import_module("Systems.core.sys_modules.my_sys_module_with_models.models")
    #    print("[Alembic Env] Модели из 'my_sys_module_with_models' импортированы.")

    print(f"[Alembic Env] Динамический импорт моделей завершен. Количество таблиц в target_metadata: {len(target_metadata.tables)}")

except Exception as e_load_mod_env:
    print(f"[ALEMBIC ENV ERROR] Ошибка при загрузке или импорте моделей модулей в env.py: {e_load_mod_env}")
    import traceback
    traceback.print_exc()
    print("[ALEMBIC ENV WARNING] Из-за ошибки выше, Alembic может не видеть модели некоторых или всех модулей.")

config = context.config
try:
    temp_db_manager_for_url = DBManager(db_settings=sdb_settings.db, app_settings=sdb_settings)
    db_connection_url = temp_db_manager_for_url._build_db_url()
    config.set_main_option("sqlalchemy.url", db_connection_url)
    print(f"[Alembic Env] sqlalchemy.url установлен из настроек SDB: {db_connection_url[:db_connection_url.find('://')+3]}...")
except Exception as e_db_url_env:
    print(f"[ALEMBIC ENV ERROR] Ошибка получения URL БД из настроек SDB: {e_db_url_env}")
    sys.exit(1)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def _get_dialect_name_from_configured_context() -> Optional[str]:
    try:
        migration_context = context.get_context()
        if migration_context and migration_context.dialect:
            return migration_context.dialect.name.lower()
    except Exception: pass
    return None

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and object.metadata != target_metadata:
        return False
    return True

def compare_type(alem_context, inspected_column, metadata_column, inspected_type, metadata_type):
    dialect_name = _get_dialect_name_from_configured_context()
    if not dialect_name and alem_context.dialect:
        dialect_name = alem_context.dialect.name.lower()

    if dialect_name == 'sqlite':
        inspected_type_str = str(inspected_type).upper()
        metadata_type_str = str(metadata_type).upper()
        if metadata_type_str == 'BIGINTEGER' and inspected_type_str == 'INTEGER': return False
        if metadata_type_str == 'BOOLEAN' and inspected_type_str == 'INTEGER': return False
        if 'DATETIME' in metadata_type_str and 'TIMESTAMP' in inspected_type_str: return False
        if 'TIMESTAMP' in metadata_type_str and 'DATETIME' in inspected_type_str: return False
    elif dialect_name == 'mysql':
        if str(metadata_type).upper() == 'BOOLEAN' and str(inspected_type).upper() == 'TINYINT(1)': return False
    return None

def render_item(type_, obj, autogen_context):
    dialect_name = _get_dialect_name_from_configured_context()
    if not dialect_name and autogen_context.dialect:
         dialect_name = autogen_context.dialect.name.lower()
         
    if dialect_name == 'sqlite':
        if type_ == "table_comment" or type_ == "column_comment":
            return None 
    return False

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=compare_type,
        compare_server_default=True,
        render_item=render_item
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata,
        include_object=include_object,
        compare_type=compare_type,
        compare_server_default=True,
        render_item=render_item
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    db_url_for_engine = config.get_main_option("sqlalchemy.url")
    if not db_url_for_engine:
        raise RuntimeError("sqlalchemy.url не найден в конфигурации Alembic для online режима!")

    connectable_engine: AsyncEngine = create_async_engine(
        db_url_for_engine,
        poolclass=pool.NullPool,
    )
    
    async with connectable_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable_engine.dispose()

if context.is_offline_mode():
    print("[Alembic Env] Запуск миграций в offline режиме...")
    run_migrations_offline()
else:
    print("[Alembic Env] Запуск миграций в online режиме...")
    asyncio.run(run_migrations_online())