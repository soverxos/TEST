# core/app_settings.py

import os
import sys
import warnings
import yaml
from pathlib import Path
from typing import List, Optional, Literal, Any, Dict 
from pydantic import BaseModel, Field, field_validator, HttpUrl, ValidationInfo, AliasChoices

# Подавляем предупреждение urllib3 о LibreSSL/OpenSSL (не критично для безопасности)
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

try:
    from loguru import logger as global_logger 
except ImportError:
    import logging
    global_logger = logging.getLogger("sdb_app_settings_fallback")
    global_logger.warning("Loguru не найден, используется стандартный logging. Пожалуйста, установите Loguru.")

from dotenv import load_dotenv, find_dotenv
from pydantic.networks import PostgresDsn, MySQLDsn, AnyUrl 
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
print(f"DEBUG: PROJECT_ROOT_DIR = {PROJECT_ROOT_DIR}")
ENV_FILENAME = ".env"
DEFAULT_PROJECT_DATA_DIR_NAME = "Data" 
USER_CONFIG_DIR_NAME = "Config" 
USER_CONFIG_FILENAME = "core_settings.yaml"
ENABLED_MODULES_FILENAME = "enabled_modules.json" 
ROOT_CONFIG_TEMPLATE_FILENAME = "config.yaml" 
STRUCTURED_LOGS_ROOT_DIR_NAME = "Logs" 

CLI_MODE = os.environ.get("SDB_CLI_MODE", "false").lower() == "true"
VERBOSE_MODE = os.environ.get("SDB_VERBOSE", "false").lower() == "true"
env_file_path_for_dotenv = None
BOT_TOKEN_FROM_DOTENV: Optional[str] = None
if not CLI_MODE:
    env_file_path_for_dotenv = find_dotenv(filename=ENV_FILENAME, usecwd=True, raise_error_if_not_found=False)
    if env_file_path_for_dotenv and Path(env_file_path_for_dotenv).exists():
        global_logger.info(f"Найден .env файл для python-dotenv: {env_file_path_for_dotenv}")
        load_dotenv(dotenv_path=env_file_path_for_dotenv, override=True)
        BOT_TOKEN_FROM_DOTENV = os.getenv("BOT_TOKEN")
        if BOT_TOKEN_FROM_DOTENV:
            global_logger.info(f"BOT_TOKEN ('****{BOT_TOKEN_FROM_DOTENV[-4:]}') предварительно загружен из .env файла.")
        else:
            global_logger.warning(f"BOT_TOKEN не найден в {env_file_path_for_dotenv} при чтении через python-dotenv/os.getenv.")
    else:
        env_file_at_root = PROJECT_ROOT_DIR / ENV_FILENAME
        if env_file_at_root.exists() and env_file_at_root.is_file():
            global_logger.info(f"Найден .env файл для python-dotenv (вторая попытка в корне проекта): {env_file_at_root}")
            load_dotenv(dotenv_path=env_file_at_root, override=True)
            BOT_TOKEN_FROM_DOTENV = os.getenv("BOT_TOKEN")
            if BOT_TOKEN_FROM_DOTENV:
                global_logger.info(f"BOT_TOKEN ('****{BOT_TOKEN_FROM_DOTENV[-4:]}') успешно загружен (вторая попытка).")
            else:
                global_logger.warning(f"BOT_TOKEN не найден в {env_file_at_root} (вторая попытка).")
        else:
            global_logger.warning(f".env файл не найден python-dotenv. BOT_TOKEN будет искаться в YAML или системных переменных.")

class DBSettings(BaseModel):
    type: Literal["sqlite", "postgresql", "mysql"] = Field(default="sqlite", description="Тип используемой базы данных.")
    sqlite_path: str = Field(
        default=f"Database_files/swiftdevbot.db", 
        description="Относительный путь к файлу SQLite (от корня проекта или project_data_path)."
    )
    pg_dsn: Optional[PostgresDsn] = Field(default=None, description="DSN для PostgreSQL.")
    mysql_dsn: Optional[MySQLDsn] = Field(default=None, description="DSN для MySQL.")
    echo_sql: bool = Field(default=False, description="Логировать SQL-запросы SQLAlchemy (уровень DEBUG).")

    @field_validator('pg_dsn', mode='before')
    @classmethod
    def check_pg_dsn(cls, v: Optional[PostgresDsn], info: ValidationInfo) -> Optional[PostgresDsn]:
        if info.data.get('type') == "postgresql" and not v:
            raise ValueError("pg_dsn должен быть указан для типа БД 'postgresql'.")
        return v

    @field_validator('mysql_dsn', mode='before')
    @classmethod
    def check_mysql_dsn(cls, v: Optional[MySQLDsn], info: ValidationInfo) -> Optional[MySQLDsn]:
        if info.data.get('type') == "mysql" and not v:
            raise ValueError("mysql_dsn должен быть указан для типа БД 'mysql'.")
        return v

class CacheSettings(BaseModel):
    type: Literal["memory", "redis"] = Field(default="memory", description="Тип кэша.")
    redis_url: Optional[str] = Field(default="redis://localhost:6379/0", description="URL для Redis.")

    @field_validator('redis_url', mode='before')
    @classmethod
    def check_redis_url(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        cache_type = info.data.get('type') if info.data else None
        if cache_type == "redis" and not v:
            raise ValueError("redis_url должен быть указан для типа кэша 'redis'.")
        return v

class TelegramSettings(BaseModel):
    token: str = Field(description="Токен Telegram бота (рекомендуется указывать в .env).")
    polling_timeout: int = Field(default=30, ge=1, description="Таймаут long polling (секунды).")

class ModuleRepoSettings(BaseModel):
    index_url: Optional[HttpUrl] = Field(
        default=HttpUrl("https://raw.githubusercontent.com/soverxos/SwiftDevBot-Modules/main/modules_index.json"),
        description="URL к JSON-индексу официальных модулей SDB."
    )

class I18nSettings(BaseModel):
    locales_dir: Path = Field(default=PROJECT_ROOT_DIR / "Systems" / "locales", description="Путь к директории с файлами переводов.")
    domain: str = Field(default="bot", description="Имя домена для переводов.")
    default_locale: str = Field(default="ru", description="Язык по умолчанию.")
    available_locales: List[str] = Field(default_factory=lambda: ["ru", "en", "ua"], description="Список доступных языков.")

class CoreAppSettings(BaseModel):
    project_data_path: Path = Field(
        default=PROJECT_ROOT_DIR / DEFAULT_PROJECT_DATA_DIR_NAME,
        description="Путь к директории данных проекта."
    )
    super_admins: List[int] = Field(default_factory=list, description="Список Telegram ID супер-администраторов.")
    enabled_modules_config_path: Path = Field(
        default=Path(f"{USER_CONFIG_DIR_NAME}/{ENABLED_MODULES_FILENAME}"), 
        description="Путь к файлу со списком активных модулей (относительно директории данных)."
    )
    
    log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_to_file: bool = Field(default=True)
    log_structured_dir: str = Field(
        default=STRUCTURED_LOGS_ROOT_DIR_NAME, 
        description="Базовая директория для структурированных лог-файлов (относительно project_data_path)."
    )
    log_rotation_size: str = Field(
        default="100 MB", 
        description="Максимальный размер одного часового лог-файла перед ротацией (e.g., '100 MB')."
    ) 
    log_retention_period_structured: str = Field(
        default="3 months", 
        description="Как долго хранить структурированные логи (например, '30 days', '3 months', '1 year'). "
                    "Реализуется отдельной задачей очистки."
    )
    
    sdb_version: str = Field(default="0.1.0", pattern=r"^\d+\.\d+\.\d+([\w.-]*[\w])?(\+[\w.-]+)?$",
                             description="Версия ядра SwiftDevBot (SemVer-совместимая).")
    
    setup_bot_commands_on_startup: bool = Field(default=True, description="Устанавливать команды бота при старте.")
    enable_startup_shutdown_notifications: bool = Field(default=True, description="Отправлять уведомления администраторам о запуске/остановке бота.")
    i18n: I18nSettings = Field(default_factory=I18nSettings)

class EnvironmentSettings(BaseSettings):
    CORE_PROJECT_DATA_PATH: Optional[Path] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_PROJECT_DATA_PATH', 'CORE_PROJECT_DATA_PATH'))
    CORE_SUPER_ADMINS: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_SUPER_ADMINS', 'CORE_SUPER_ADMINS'))
    CORE_ENABLED_MODULES_CONFIG_PATH: Optional[Path] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_ENABLED_MODULES_CONFIG_PATH', 'CORE_ENABLED_MODULES_CONFIG_PATH'))
    CORE_LOG_LEVEL: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_LOG_LEVEL', 'CORE_LOG_LEVEL'))
    CORE_LOG_TO_FILE: Optional[bool] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_LOG_TO_FILE', 'CORE_LOG_TO_FILE'))
    
    SDB_CORE_LOG_STRUCTURED_DIR: Optional[str] = Field(default=None)
    SDB_CORE_LOG_ROTATION_SIZE: Optional[str] = Field(default=None)
    SDB_CORE_LOG_RETENTION_PERIOD_STRUCTURED: Optional[str] = Field(default=None)

    CORE_SDB_VERSION: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_SDB_VERSION', 'CORE_SDB_VERSION'))
    CORE_ENABLE_STARTUP_SHUTDOWN_NOTIFICATIONS: Optional[bool] = Field(default=None, validation_alias=AliasChoices('SDB_CORE_ENABLE_STARTUP_SHUTDOWN_NOTIFICATIONS', 'CORE_ENABLE_STARTUP_SHUTDOWN_NOTIFICATIONS'))
    
    DB_TYPE: Optional[Literal["sqlite", "postgresql", "mysql"]] = Field(default=None, validation_alias=AliasChoices('SDB_DB_TYPE', 'DB_TYPE'))
    DB_SQLITE_PATH: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_DB_SQLITE_PATH', 'DB_SQLITE_PATH'))
    DB_PG_DSN: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_DB_PG_DSN', 'DB_PG_DSN')) 
    DB_MYSQL_DSN: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_DB_MYSQL_DSN', 'DB_MYSQL_DSN')) 
    DB_ECHO_SQL: Optional[bool] = Field(default=None, validation_alias=AliasChoices('SDB_DB_ECHO_SQL', 'DB_ECHO_SQL'))

    CACHE_TYPE: Optional[Literal["memory", "redis"]] = Field(default=None, validation_alias=AliasChoices('SDB_CACHE_TYPE', 'CACHE_TYPE'))
    CACHE_REDIS_URL: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_CACHE_REDIS_URL', 'CACHE_REDIS_URL'))
    
    TELEGRAM_POLLING_TIMEOUT: Optional[int] = Field(default=None, validation_alias=AliasChoices('SDB_TELEGRAM_POLLING_TIMEOUT', 'TELEGRAM_POLLING_TIMEOUT'))
    MODULE_REPO_INDEX_URL: Optional[HttpUrl] = Field(default=None, validation_alias=AliasChoices('SDB_MODULE_REPO_INDEX_URL', 'MODULE_REPO_INDEX_URL'))

    SDB_I18N_LOCALES_DIR: Optional[Path] = Field(default=None, validation_alias=AliasChoices('SDB_I18N_LOCALES_DIR', 'I18N_LOCALES_DIR'))
    SDB_I18N_DOMAIN: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_I18N_DOMAIN', 'I18N_DOMAIN'))
    SDB_I18N_DEFAULT_LOCALE: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_I18N_DEFAULT_LOCALE', 'I18N_DEFAULT_LOCALE'))
    SDB_I18N_AVAILABLE_LOCALES: Optional[str] = Field(default=None, validation_alias=AliasChoices('SDB_I18N_AVAILABLE_LOCALES', 'I18N_AVAILABLE_LOCALES'))

    model_config = SettingsConfigDict(
        env_file=None, 
        extra='ignore',
    )

class AppSettings(BaseModel):
    db: DBSettings = Field(default_factory=DBSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    telegram: TelegramSettings
    module_repo: ModuleRepoSettings = Field(default_factory=ModuleRepoSettings)
    core: CoreAppSettings = Field(default_factory=CoreAppSettings)
    project_root: Path = Field(default_factory=lambda: PROJECT_ROOT_DIR)
    model_config = {"validate_assignment": True}

_loaded_settings_cache: Optional[AppSettings] = None
_loguru_console_configured_flag = False

def load_app_settings() -> AppSettings:
    global _loaded_settings_cache, _loguru_console_configured_flag
    if _loaded_settings_cache is not None:
        return _loaded_settings_cache

    # DEBUG логи показываем только в verbose режиме
    if VERBOSE_MODE:
        global_logger.debug(f"Инициализация загрузки конфигурации SDB. Корень проекта: {PROJECT_ROOT_DIR}")
    
    env_s = EnvironmentSettings()
    
    if not CLI_MODE:
        if BOT_TOKEN_FROM_DOTENV:
            global_logger.info(f"BOT_TOKEN ('****{BOT_TOKEN_FROM_DOTENV[-4:]}') был предварительно загружен.")
        else:
            global_logger.warning("BOT_TOKEN не был найден при предварительной загрузке из .env. Будет искаться в YAML.")
    
    pdp_val_from_env = env_s.CORE_PROJECT_DATA_PATH
    core_app_defaults = CoreAppSettings.model_fields
    
    if pdp_val_from_env:
        effective_project_data_path = Path(pdp_val_from_env)
        if not effective_project_data_path.is_absolute():
            effective_project_data_path = (PROJECT_ROOT_DIR / effective_project_data_path).resolve()
    else: 
        default_pdp_model = core_app_defaults["project_data_path"].default
        effective_project_data_path = Path(default_pdp_model) if default_pdp_model else (PROJECT_ROOT_DIR / DEFAULT_PROJECT_DATA_DIR_NAME)
        if not effective_project_data_path.is_absolute():
             effective_project_data_path = (PROJECT_ROOT_DIR / effective_project_data_path).resolve()

    user_config_file_path = effective_project_data_path / USER_CONFIG_DIR_NAME / USER_CONFIG_FILENAME
    yaml_data: Dict[str, Any] = {}
    if user_config_file_path.is_file():
        try:
            with open(user_config_file_path, 'r', encoding='utf-8') as f: yaml_data = yaml.safe_load(f) or {}
            # INFO логи о загрузке конфигурации показываем только в verbose режиме
            if VERBOSE_MODE:
                global_logger.info(f"Загружена конфигурация из пользовательского YAML: {user_config_file_path}")
        except Exception as e_yaml: global_logger.error(f"Ошибка загрузки YAML из {user_config_file_path}: {e_yaml}.")
    else:
        # INFO логи о конфигурации показываем только в verbose режиме
        if VERBOSE_MODE:
            global_logger.info(f"Пользовательский YAML конфиг {user_config_file_path} не найден. Используются дефолты и .env.")

    tg_token_from_yaml = yaml_data.get("telegram", {}).get("token")
    final_tg_token = BOT_TOKEN_FROM_DOTENV or tg_token_from_yaml
    allow_missing_token_env = os.environ.get("SDB_ALLOW_MISSING_BOT_TOKEN", "false").lower() == "true"
    if not final_tg_token and not (allow_missing_token_env or CLI_MODE):
        raise ValueError(f"КРИТИЧНО: BOT_TOKEN не найден! Проверьте .env и YAML ({user_config_file_path}).")
    if not final_tg_token and (allow_missing_token_env or CLI_MODE):
        if not CLI_MODE:
            global_logger.warning("BOT_TOKEN отсутствует, но разрешено продолжить из-за SDB_ALLOW_MISSING_BOT_TOKEN=true. Некоторые операции могут быть недоступны до указания токена.")
        final_tg_token = ""
    
    telegram_s = TelegramSettings(
        token=final_tg_token,
        polling_timeout=env_s.TELEGRAM_POLLING_TIMEOUT or \
                        yaml_data.get("telegram", {}).get("polling_timeout", TelegramSettings.model_fields["polling_timeout"].default)
    )

    db_yaml = yaml_data.get("db", {})
    db_s = DBSettings(
        type=env_s.DB_TYPE or db_yaml.get("type", DBSettings.model_fields["type"].default),
        sqlite_path=env_s.DB_SQLITE_PATH or db_yaml.get("sqlite_path", DBSettings.model_fields["sqlite_path"].default),
        pg_dsn=env_s.DB_PG_DSN or db_yaml.get("pg_dsn"),
        mysql_dsn=env_s.DB_MYSQL_DSN or db_yaml.get("mysql_dsn"),
        echo_sql=env_s.DB_ECHO_SQL if env_s.DB_ECHO_SQL is not None else \
                 db_yaml.get("echo_sql", DBSettings.model_fields["echo_sql"].default)
    )

    cache_yaml = yaml_data.get("cache", {})
    cache_s = CacheSettings(
        type=env_s.CACHE_TYPE or cache_yaml.get("type", CacheSettings.model_fields["type"].default),
        redis_url=env_s.CACHE_REDIS_URL or cache_yaml.get("redis_url", CacheSettings.model_fields["redis_url"].default)
    )

    module_repo_yaml = yaml_data.get("module_repo", {})
    module_repo_s = ModuleRepoSettings(
        index_url=env_s.MODULE_REPO_INDEX_URL or \
                  HttpUrl(str(module_repo_yaml.get("index_url") or ModuleRepoSettings.model_fields["index_url"].default))
    )
    
    core_yaml = yaml_data.get("core", {})
    
    s_admins_str_env = env_s.CORE_SUPER_ADMINS
    s_admins_list_yaml = core_yaml.get("super_admins")
    s_admins_final_list: List[int] = []
    if s_admins_str_env:
        try:
            # Убираем кавычки если есть (python-dotenv может оставить их)
            s_admins_str_clean = s_admins_str_env.strip().strip('"').strip("'")
            # Парсим список ID, разделенных запятой
            s_admins_final_list = []
            for x in s_admins_str_clean.split(','):
                x_clean = x.strip().strip('"').strip("'")
                if x_clean.isdigit():
                    s_admins_final_list.append(int(x_clean))
            global_logger.info(f"Загружены супер-администраторы из SDB_CORE_SUPER_ADMINS: {s_admins_final_list}")
        except ValueError as e: 
            global_logger.error(f"Ошибка парсинга CORE_SUPER_ADMINS из env: '{s_admins_str_env}': {e}")
    elif isinstance(s_admins_list_yaml, list):
        s_admins_final_list = [int(x) for x in s_admins_list_yaml if isinstance(x, (int, str)) and str(x).isdigit()]

    emcp_from_env_val = env_s.CORE_ENABLED_MODULES_CONFIG_PATH
    emcp_from_yaml_val = core_yaml.get("enabled_modules_config_path")
    emcp_default_relative = CoreAppSettings.model_fields["enabled_modules_config_path"].default 
    
    emcp_to_resolve = emcp_from_env_val or (Path(emcp_from_yaml_val) if emcp_from_yaml_val else emcp_default_relative)
    emcp_path_resolved = (effective_project_data_path / emcp_to_resolve).resolve() if not Path(emcp_to_resolve).is_absolute() else Path(emcp_to_resolve).resolve()

    log_structured_dir_final = env_s.SDB_CORE_LOG_STRUCTURED_DIR or core_yaml.get("log_structured_dir", CoreAppSettings.model_fields["log_structured_dir"].default)
    log_rotation_size_final = env_s.SDB_CORE_LOG_ROTATION_SIZE or core_yaml.get("log_rotation_size", CoreAppSettings.model_fields["log_rotation_size"].default)
    log_retention_period_structured_final = env_s.SDB_CORE_LOG_RETENTION_PERIOD_STRUCTURED or core_yaml.get("log_retention_period_structured", CoreAppSettings.model_fields["log_retention_period_structured"].default)

    i18n_yaml = core_yaml.get("i18n", {})
    i18n_model_defaults = I18nSettings.model_fields
    
    available_locales_env_str = env_s.SDB_I18N_AVAILABLE_LOCALES
    available_locales_yaml = i18n_yaml.get("available_locales")
    final_available_locales: List[str]
    if available_locales_env_str:
        final_available_locales = [loc.strip() for loc in available_locales_env_str.split(',')]
    elif isinstance(available_locales_yaml, list):
        final_available_locales = available_locales_yaml
    else:
        final_available_locales = i18n_model_defaults["available_locales"].default_factory() # type: ignore

    locales_dir_env = env_s.SDB_I18N_LOCALES_DIR
    locales_dir_yaml = i18n_yaml.get("locales_dir")
    locales_dir_default = i18n_model_defaults["locales_dir"].default
    
    locales_dir_to_resolve = locales_dir_env or (Path(locales_dir_yaml) if locales_dir_yaml else locales_dir_default)
    resolved_locales_dir = Path(locales_dir_to_resolve)
    if not resolved_locales_dir.is_absolute():
        resolved_locales_dir = (PROJECT_ROOT_DIR / resolved_locales_dir).resolve()

    i18n_s = I18nSettings(
        locales_dir=resolved_locales_dir,
        domain=env_s.SDB_I18N_DOMAIN or i18n_yaml.get("domain", i18n_model_defaults["domain"].default),
        default_locale=env_s.SDB_I18N_DEFAULT_LOCALE or i18n_yaml.get("default_locale", i18n_model_defaults["default_locale"].default),
        available_locales=final_available_locales
    )

    core_s = CoreAppSettings(
        project_data_path=effective_project_data_path,
        super_admins=s_admins_final_list,
        enabled_modules_config_path=emcp_path_resolved,
        log_level=(env_s.CORE_LOG_LEVEL or core_yaml.get("log_level", CoreAppSettings.model_fields["log_level"].default)).upper(), # type: ignore
        log_to_file=env_s.CORE_LOG_TO_FILE if env_s.CORE_LOG_TO_FILE is not None \
                    else core_yaml.get("log_to_file", CoreAppSettings.model_fields["log_to_file"].default),
        log_structured_dir=log_structured_dir_final,
        log_rotation_size=log_rotation_size_final,
        log_retention_period_structured=log_retention_period_structured_final,
        sdb_version=env_s.CORE_SDB_VERSION or core_yaml.get("sdb_version", CoreAppSettings.model_fields["sdb_version"].default),
        setup_bot_commands_on_startup=core_yaml.get("setup_bot_commands_on_startup", CoreAppSettings.model_fields["setup_bot_commands_on_startup"].default), # type: ignore
        enable_startup_shutdown_notifications=env_s.CORE_ENABLE_STARTUP_SHUTDOWN_NOTIFICATIONS if env_s.CORE_ENABLE_STARTUP_SHUTDOWN_NOTIFICATIONS is not None \
                    else core_yaml.get("enable_startup_shutdown_notifications", CoreAppSettings.model_fields["enable_startup_shutdown_notifications"].default),
        i18n=i18n_s
    )
    
    final_settings = AppSettings(db=db_s, cache=cache_s, telegram=telegram_s, module_repo=module_repo_s, core=core_s)

    final_settings.core.project_data_path.mkdir(parents=True, exist_ok=True)
    final_settings.core.enabled_modules_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    structured_logs_root_abs_path = final_settings.core.project_data_path / final_settings.core.log_structured_dir
    structured_logs_root_abs_path.mkdir(parents=True, exist_ok=True)
    
    final_settings.core.i18n.locales_dir.mkdir(parents=True, exist_ok=True)
    
    if final_settings.db.type == "sqlite":
        sqlite_file_abs = Path(final_settings.db.sqlite_path)
        if not sqlite_file_abs.is_absolute():
            if DEFAULT_PROJECT_DATA_DIR_NAME in sqlite_file_abs.parts:
                 sqlite_file_abs = (PROJECT_ROOT_DIR / sqlite_file_abs).resolve()
            else:
                 sqlite_file_abs = (final_settings.core.project_data_path / sqlite_file_abs).resolve()
        final_settings.db.sqlite_path = str(sqlite_file_abs)
        sqlite_file_abs.parent.mkdir(parents=True, exist_ok=True)

    if not _loguru_console_configured_flag:
        try:
            # Проверяем, есть ли уже настроенный handler (например, из sdb.py)
            has_existing_handler = (
                hasattr(global_logger, '_core') and 
                global_logger._core.handlers and 
                len(global_logger._core.handlers) > 0
            )
            
            # Используем глобальную переменную VERBOSE_MODE
            if VERBOSE_MODE:
                # Подробный формат с модулем, функцией и строкой
                log_format_console = ("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
                                      "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
                # Удаляем все существующие handlers только в verbose режиме
                if has_existing_handler:
                    for handler_id_to_remove in list(global_logger._core.handlers.keys()):
                        try: global_logger.remove(handler_id_to_remove)
                        except ValueError: pass
            else:
                # Простой формат: только время и сообщение
                log_format_console = "<green>{time:HH:mm:ss}</green> <level>{message}</level>"
                # В простом режиме не удаляем handlers, если они уже настроены (например, из sdb.py)
                # Если handler уже настроен, просто используем его
            
            # Добавляем handler только если его еще нет (в простом режиме) или всегда (в verbose режиме)
            if VERBOSE_MODE or not has_existing_handler:
                console_log_level_str = final_settings.core.log_level.upper()
                
                cli_debug_env_var = os.environ.get("SDB_CLI_DEBUG_MODE_FOR_LOGGING", "false").lower()
                if cli_debug_env_var == "true":
                    console_log_level_str = "DEBUG"
                    if not VERBOSE_MODE:
                        global_logger.info("Loguru (app_settings): Уровень консольного лога принудительно DEBUG из-за SDB_CLI_DEBUG_MODE_FOR_LOGGING.")

                global_logger.add(sys.stderr, level=console_log_level_str, format=log_format_console, colorize=True)
                if VERBOSE_MODE:
                    global_logger.info(f"Loguru (app_settings): Консольный логгер настроен (verbose mode). Уровень: {console_log_level_str}")
            _loguru_console_configured_flag = True
        except Exception as e_log_setup_console:
            print(f"CRITICAL ERROR in app_settings during Loguru console setup: {e_log_setup_console}", file=sys.stderr)

    # Сообщение об успешной загрузке показываем всегда, но в простом формате (если не verbose)
    if VERBOSE_MODE:
        global_logger.success("Настройки SDB успешно загружены и провалидированы!")
    else:
        # В простом режиме используем info вместо success, чтобы не было лишних символов
        global_logger.info("Настройки SDB успешно загружены и провалидированы!")
    _loaded_settings_cache = final_settings
    return final_settings

try:
    settings: AppSettings = load_app_settings()
except (ImportError, ValueError) as e: 
    print(f"CRITICAL ERROR during SDB settings load/validation: {e}", file=sys.stderr)
    if hasattr(global_logger, 'opt') and callable(global_logger.opt): 
        global_logger.opt(exception=True).critical(f"КРИТИЧЕСКАЯ ОШИБКА Pydantic/SDB при валидации или загрузке настроек: {e}")
    sys.exit(1)
except Exception as e:
    print(f"UNEXPECTED CRITICAL ERROR during initial settings load: {e}", file=sys.stderr)
    if hasattr(global_logger, 'opt') and callable(global_logger.opt):
        global_logger.opt(exception=True).critical(f"НЕПРЕДВИДЕННАЯ КРИТИЧЕСКАЯ ОШИБКА при первоначальной загрузке настроек: {e}")
    sys.exit(1)