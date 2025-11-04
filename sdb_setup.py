#!/usr/bin/env python3
"""
SwiftDevBot Setup Wizard
Мастер первоначальной настройки SwiftDevBot
"""

import sys
import os
import venv
import subprocess
import yaml
from pathlib import Path

# Определяем корневую директорию проекта
PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PATH = PROJECT_ROOT / ".venv"

def create_and_activate_venv():
    """Создает виртуальное окружение и активирует его"""
    if not VENV_PATH.exists():
        print("\n⚠️ Виртуальное окружение не обнаружено")
        print("\n🚀 Создание виртуального окружения...")
        venv.create(VENV_PATH, with_pip=True)
        print(f"✓ Виртуальное окружение создано в {VENV_PATH}")
    
    # Определяем путь к интерпретатору Python в виртуальном окружении
    if sys.platform == "win32":
        python_path = VENV_PATH / "Scripts" / "python.exe"
        pip_path = VENV_PATH / "Scripts" / "pip.exe"
    else:
        python_path = VENV_PATH / "bin" / "python"
        pip_path = VENV_PATH / "bin" / "pip"
        
    # Активируем виртуальное окружение
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("\n🔄 Активация виртуального окружения и перезапуск скрипта...")
        os.environ["VIRTUAL_ENV"] = str(VENV_PATH)
        os.environ["PATH"] = str(VENV_PATH / "bin") + os.pathsep + os.environ["PATH"]
        os.execv(str(python_path), [str(python_path), __file__])

def install_dependencies():
    """Устанавливает все необходимые зависимости"""
    print("\n📦 Установка зависимостей...")
    pip_cmd = str(VENV_PATH / "bin" / "pip") if sys.platform != "win32" else str(VENV_PATH / "Scripts" / "pip.exe")
    requirements_file = PROJECT_ROOT / "requirements.txt"
    
    try:
        subprocess.run([pip_cmd, "install", "-r", str(requirements_file)], check=True)
        print("✓ Зависимости успешно установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def validate_bot_token(token: str) -> bool:
    """Проверяет формат токена бота"""
    import re
    pattern = r'^\d+:[\w-]{35}$'
    return bool(re.match(pattern, token))

def get_admin_id(prompt_text: str) -> int:
    """Запрашивает и валидирует Telegram ID администратора"""
    while True:
        try:
            admin_id = int(input(prompt_text))
            if admin_id > 0:
                return admin_id
            print("❌ ID должен быть положительным числом")
        except ValueError:
            print("❌ ID должен быть целым числом")

def setup_database():
    """Настраивает подключение к базе данных"""
    print("\n🗄️ Настройка базы данных")
    db_types = {
        "1": "sqlite",
        "2": "postgresql",
        "3": "mysql"
    }
    
    print("\nДоступные типы баз данных:")
    print("1. SQLite (встроенная, рекомендуется)")
    print("2. PostgreSQL")
    print("3. MySQL")
    
    while True:
        choice = input("\nВыберите тип базы данных [1-3] (по умолчанию: 1): ").strip() or "1"
        if choice in db_types:
            db_type = db_types[choice]
            break
        print("❌ Неверный выбор. Пожалуйста, выберите 1, 2 или 3")
    
    if db_type == "sqlite":
        return {
            "type": "sqlite",
            "url": "sqlite+aiosqlite:///Data/Database_files/sdb.db"
        }
    
    # Настройка серверных БД
    config = {"type": db_type}
    config["host"] = input("Хост (по умолчанию: localhost): ").strip() or "localhost"
    config["port"] = input(f"Порт (по умолчанию: {5432 if db_type == 'postgresql' else 3306}): ").strip()
    config["port"] = int(config["port"]) if config["port"].isdigit() else (5432 if db_type == 'postgresql' else 3306)
    config["database"] = input("Имя базы данных: ").strip()
    config["user"] = input("Имя пользователя: ").strip()
    config["password"] = input("Пароль: ").strip()
    
    return config

def setup_cache():
    """Настраивает систему кеширования"""
    print("\n💾 Настройка системы кеширования")
    print("\nДоступные типы кеширования:")
    print("1. Memory (в памяти, рекомендуется)")
    print("2. Redis")
    
    while True:
        choice = input("\nВыберите тип кеширования [1-2] (по умолчанию: 1): ").strip() or "1"
        if choice == "1":
            return {
                "type": "memory",
                "ttl": 3600  # 1 час
            }
        elif choice == "2":
            config = {
                "type": "redis",
                "ttl": 3600  # 1 час
            }
            config["host"] = input("Redis хост (по умолчанию: localhost): ").strip() or "localhost"
            config["port"] = int(input("Redis порт (по умолчанию: 6379): ").strip() or "6379")
            config["db"] = int(input("Redis номер БД (по умолчанию: 0): ").strip() or "0")
            return config
        print("❌ Неверный выбор. Пожалуйста, выберите 1 или 2")

def create_env_file(bot_token: str, admin_id: int, db_config: dict, cache_config: dict):
    """Создает файл .env с настройками"""
    # Создаем базовый конфиг
    env_content = [
        "# --- Telegram Bot ---",
        f"BOT_TOKEN={bot_token}",
        f'SDB_CORE_SUPER_ADMINS="{admin_id}"', # Используем кавычки для консистентности
        "",
        "# --- База Данных ---"
    ]
    
    # Добавляем настройки БД
    env_content.append(f'SDB_DB_TYPE="{db_config["type"]}"')
    if db_config["type"] == "sqlite":
        # Для SQLite используется относительный путь от Data
        sqlite_relative_path = "Database_files/swiftdevbot.db"
        env_content.append(f'SDB_DB_SQLITE_PATH="{sqlite_relative_path}"')
    else:
        # Для PostgreSQL и MySQL формируем DSN
        driver = "psycopg" if db_config["type"] == "postgresql" else "aiomysql"
        db_url = f"{db_config['type']}+{driver}://{db_config['user']}:{db_config['password']}@"
        db_url += f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        if db_config["type"] == "mysql":
            db_url += "?charset=utf8mb4"
        
        dsn_var_name = "SDB_DB_PG_DSN" if db_config["type"] == "postgresql" else "SDB_DB_MYSQL_DSN"
        env_content.append(f'{dsn_var_name}="{db_url}"')
    
    # Добавляем настройки кэша
    env_content.extend([
        "",
        "# --- Кэш ---",
        f'SDB_CACHE_TYPE="{cache_config["type"]}"'
    ])
    
    # ИСПРАВЛЕННЫЙ БЛОК ДЛЯ REDIS
    if cache_config["type"] == "redis":
        redis_url = f"redis://{cache_config['host']}:{cache_config['port']}/{cache_config['db']}"
        env_content.append(f'SDB_CACHE_REDIS_URL="{redis_url}"')
    
    # Добавляем дополнительные настройки для удобства
    env_content.extend([
        "",
        "# --- Настройки Ядра (Core) ---",
        "# Путь к директории данных проекта (по умолчанию ./Data)",
        "# SDB_CORE_PROJECT_DATA_PATH=\"./Data\"",
        "",
        "# --- Настройки Логирования Ядра ---",
        'SDB_CORE_LOG_LEVEL="INFO"'
    ])
    
    # Записываем файл
    env_file_path = PROJECT_ROOT / ".env"
    with open(env_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(env_content))
    print(f"✓ Файл .env создан: {env_file_path}")

def _convert_to_serializable(data):
    """Рекурсивно конвертирует объекты в сериализуемые типы для YAML."""
    from pathlib import Path
    
    if isinstance(data, dict):
        return {key: _convert_to_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_convert_to_serializable(item) for item in data]
    elif isinstance(data, Path):
        return str(data)
    elif hasattr(data, "__class__") and data.__class__.__name__ in ("HttpUrl", "Url"):
        return str(data)
    else:
        return data

def create_core_settings_file():
    """Создает файл core_settings.yaml с настройками по умолчанию"""
    print("\n📝 Создание файла core_settings.yaml...")
    
    try:
        # Добавляем Systems в путь для импорта
        sys.path.insert(0, str(PROJECT_ROOT))
        sys.path.insert(0, str(PROJECT_ROOT / "Systems"))
        
        from Systems.core.app_settings import AppSettings
        
        # Создаем дефолтные настройки
        default_settings = AppSettings(telegram={"token": "dummy"}).model_dump(exclude_defaults=False)
        
        # Удаляем ключи, которые хранятся в .env
        if "telegram" in default_settings:
            del default_settings["telegram"]
        if "db" in default_settings:
            del default_settings["db"]
        if "core" in default_settings and "super_admins" in default_settings["core"]:
            del default_settings["core"]["super_admins"]
        
        # Конвертируем объекты в сериализуемые типы
        serializable_data = _convert_to_serializable(default_settings)
        
        # Создаем путь к файлу
        config_file_path = PROJECT_ROOT / "Data" / "Config" / "core_settings.yaml"
        config_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Записываем YAML файл
        with open(config_file_path, "w", encoding="utf-8") as f:
            yaml.dump(serializable_data, f, indent=2, sort_keys=False, allow_unicode=True)
        
        print(f"✓ Файл core_settings.yaml создан: {config_file_path}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось создать core_settings.yaml: {e}")
        print("   Файл не обязателен - система будет работать с дефолтами и .env")
        return False

def create_project_structure():
    """Создает структуру директорий проекта"""
    print("\n📁 Создание структуры проекта...")
    directories = [
        "Data/Config",
        "Data/Database_files",
        "Data/Logs",
        "modules"
    ]
    
    for directory in directories:
        Path(PROJECT_ROOT / directory).mkdir(parents=True, exist_ok=True)
    print("✓ Структура директорий создана")

def initialize_database():
    """Инициализирует базу данных"""
    print("\n🗃️ Инициализация базы данных...")
    try:
        import alembic.config  # type: ignore[import-untyped]
        alembic_args = [
            '--raiseerr',
            'upgrade', 'head'
        ]
        alembic.config.main(argv=alembic_args)
        print("✓ База данных успешно инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False

def main():
    """Основная функция мастера настройки"""
    print("🚀 Мастер настройки SwiftDevBot\n")
    
    try:
        # Шаг 1: Создание и активация виртуального окружения
        create_and_activate_venv()
        
        # Шаг 2: Установка зависимостей
        if not install_dependencies():
            sys.exit(1)
        
        # Шаг 3: Запрос токена бота и ID администратора
        while True:
            bot_token = input("\nВведите токен вашего Telegram бота (получить у @BotFather): ")
            if validate_bot_token(bot_token):
                break
            print("❌ Неверный формат токена. Пример: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        
        admin_id = get_admin_id("\nВведите ваш Telegram ID (получить у @userinfobot): ")
        
        # Шаг 4: Создание структуры проекта
        create_project_structure()
        
        # Шаг 5: Настройка базы данных
        db_config = setup_database()
        
        # Шаг 6: Настройка кеширования
        cache_config = setup_cache()
        
        # Шаг 7: Создание конфигурационного файла
        create_env_file(bot_token, admin_id, db_config, cache_config)
        
        # Шаг 8: Создание core_settings.yaml
        create_core_settings_file()
        
        # Шаг 9: Инициализация базы данных
        if not initialize_database():
            if input("Продолжить настройку несмотря на ошибки? [y/N]: ").lower() != 'y':
                sys.exit(1)
        
        # Завершение настройки
        print("""
✨ Настройка SwiftDevBot завершена! ✨

Управление ботом:
1. Запуск:    ./sdb start
2. Остановка: ./sdb stop
3. Статус:    ./sdb status

Дополнительные команды:
- ./sdb --help   # Просмотр всех доступных команд
- ./sdb db       # Управление базой данных
- ./sdb module   # Управление модулями
- ./sdb config   # Управление конфигурацией
- ./sdb backup   # Управление резервными копиями

Команды бота в Telegram:
/start  - Начало работы с ботом
/help   - Просмотр доступных команд
/admin  - Доступ к панели администратора

Документация: https://github.com/soverxos/SwiftDevBot-Project/blob/main/README.md
""")
        
    except KeyboardInterrupt:
        print("\n\n❌ Настройка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Произошла ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()