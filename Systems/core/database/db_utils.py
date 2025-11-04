"""
Утилиты для работы с разными типами баз данных.
"""
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class DatabaseDialectHandler:
    """Класс для обработки специфики разных диалектов БД"""
    
    @staticmethod
    def get_dialect_features(engine: Engine) -> Dict[str, bool]:
        """Возвращает поддерживаемые функции для диалекта БД"""
        dialect_name = engine.dialect.name.lower()
        
        features = {
            'supports_comments': True,
            'supports_check_constraints': True,
            'supports_deferrable_fks': True,
            'supports_sequences': True,
            'supports_returning': True,
            'case_sensitive': True,
        }
        
        if dialect_name == 'sqlite':
            features.update({
                'supports_comments': False,
                'supports_deferrable_fks': False,
                'supports_sequences': False,
                'supports_returning': False,  # Старые версии SQLite
                'case_sensitive': False,
            })
        elif dialect_name in ['mysql', 'mariadb']:
            features.update({
                'supports_comments': True,
                'supports_check_constraints': True,  # MySQL 8.0+
                'supports_deferrable_fks': False,
                'supports_sequences': False,  # До MySQL 8.0
                'supports_returning': False,
                'case_sensitive': False,  # Зависит от настроек
            })
        elif dialect_name == 'postgresql':
            features.update({
                'supports_comments': True,
                'supports_check_constraints': True,
                'supports_deferrable_fks': True,
                'supports_sequences': True,
                'supports_returning': True,
                'case_sensitive': True,
            })
        
        return features
    
    @staticmethod
    def get_recommended_types(engine: Engine) -> Dict[str, str]:
        """Возвращает рекомендуемые типы данных для диалекта"""
        dialect_name = engine.dialect.name.lower()
        
        if dialect_name == 'sqlite':
            return {
                'id': 'INTEGER',
                'bigint': 'INTEGER',
                'string_short': 'TEXT',
                'string_long': 'TEXT',
                'text': 'TEXT',
                'boolean': 'INTEGER',
                'datetime': 'DATETIME',
                'json': 'TEXT',
            }
        elif dialect_name in ['mysql', 'mariadb']:
            return {
                'id': 'INT AUTO_INCREMENT',
                'bigint': 'BIGINT',
                'string_short': 'VARCHAR(255)',
                'string_long': 'TEXT',
                'text': 'TEXT',
                'boolean': 'TINYINT(1)',
                'datetime': 'DATETIME',
                'json': 'JSON',  # MySQL 5.7+
            }
        elif dialect_name == 'postgresql':
            return {
                'id': 'SERIAL',
                'bigint': 'BIGINT',
                'string_short': 'VARCHAR(255)',
                'string_long': 'TEXT',
                'text': 'TEXT',
                'boolean': 'BOOLEAN',
                'datetime': 'TIMESTAMP WITH TIME ZONE',
                'json': 'JSONB',
            }
        
        return {}
    
    @staticmethod
    def create_db_if_not_exists(connection_url: str, db_name: str) -> bool:
        """Создает базу данных, если она не существует (для MySQL/PostgreSQL)"""
        try:
            if 'mysql' in connection_url or 'mariadb' in connection_url:
                # Для MySQL
                base_url = connection_url.rsplit('/', 1)[0]
                engine = create_engine(base_url + '/mysql')
                with engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    conn.commit()
                return True
                
            elif 'postgresql' in connection_url:
                # Для PostgreSQL
                base_url = connection_url.rsplit('/', 1)[0]
                engine = create_engine(base_url + '/postgres')
                with engine.connect() as conn:
                    # PostgreSQL требует автокоммит для CREATE DATABASE
                    conn.execute(text("COMMIT"))
                    result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name})
                    if not result.fetchone():
                        # Используем параметризованный запрос с identifier()
                        from sqlalchemy import sql
                        conn.execute(text('CREATE DATABASE :db_name WITH ENCODING "UTF8"').bindparam(
                            sql.bindparam("db_name", db_name, literal_execute=True)))
                return True
                
        except Exception as e:
            print(f"Ошибка при создании БД {db_name}: {e}")
            return False
        
        return True  # SQLite создается автоматически


def get_db_info_query(dialect_name: str) -> Optional[str]:
    """Возвращает SQL-запрос для получения информации о БД"""
    if dialect_name == 'sqlite':
        return "SELECT sqlite_version() as version"
    elif dialect_name in ['mysql', 'mariadb']:
        return "SELECT VERSION() as version"
    elif dialect_name == 'postgresql':
        return "SELECT version() as version"
    return None


def optimize_for_dialect(engine: Engine) -> Dict[str, Any]:
    """Возвращает оптимальные настройки для диалекта БД"""
    dialect_name = engine.dialect.name.lower()
    
    settings = {}
    
    if dialect_name == 'sqlite':
        settings = {
            'pool_pre_ping': False,
            'pool_recycle': -1,
            'echo': False,
            'connect_args': {
                'check_same_thread': False,
                'timeout': 30,
            }
        }
    elif dialect_name in ['mysql', 'mariadb']:
        settings = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'pool_size': 10,
            'max_overflow': 20,
            'connect_args': {
                'charset': 'utf8mb4',
                'connect_timeout': 60,
            }
        }
    elif dialect_name == 'postgresql':
        settings = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'pool_size': 10,
            'max_overflow': 20,
            'connect_args': {
                'connect_timeout': 60,
                'application_name': 'SwiftDevBot',
            }
        }
    
    return settings