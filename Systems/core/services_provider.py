# core/services_provider.py

from typing import Optional, TYPE_CHECKING

from loguru import logger as global_logger 

if TYPE_CHECKING:
    from Systems.core.app_settings import AppSettings
    from Systems.core.database.manager import DBManager
    from Systems.core.cache.manager import CacheManager
    from Systems.core.http_client.manager import HTTPClientManager
    from Systems.core.module_loader import ModuleLoader
    from Systems.core.events.dispatcher import EventDispatcher
    from Systems.core.ui.registry_ui import UIRegistry
    from Systems.core.rbac.service import RBACService
    from Systems.core.users.service import UserService
    from Systems.core.security.signature_manager import ModuleSignatureManager
    from Systems.core.security.sandbox_manager import ModuleSandboxManager
    from Systems.core.security.audit_logger import SecurityAuditLogger
    from Systems.core.security.reputation_system import ModuleReputationSystem
    from Systems.core.security.code_scanner import ModuleCodeScanner
    from Systems.core.security.security_levels import SecurityLevelManager
    from Systems.core.security.anomaly_detection import AnomalyDetector


class BotServicesProvider:
    def __init__(self, settings: 'AppSettings'):
        self._settings: 'AppSettings' = settings
        self._logger = global_logger.bind(service="BotServicesProvider")

        self._db_manager: Optional['DBManager'] = None
        self._cache_manager: Optional['CacheManager'] = None
        self._http_client_manager: Optional['HTTPClientManager'] = None
        self._module_loader: Optional['ModuleLoader'] = None
        self._event_dispatcher: Optional['EventDispatcher'] = None
        self._ui_registry: Optional['UIRegistry'] = None
        self._rbac_service: Optional['RBACService'] = None
        self._user_service: Optional['UserService'] = None
        
        # Security services
        self._signature_manager: Optional['ModuleSignatureManager'] = None
        self._sandbox_manager: Optional['ModuleSandboxManager'] = None
        self._audit_logger: Optional['SecurityAuditLogger'] = None
        self._reputation_system: Optional['ModuleReputationSystem'] = None
        self._code_scanner: Optional['ModuleCodeScanner'] = None
        self._security_level_manager: Optional['SecurityLevelManager'] = None
        self._anomaly_detector: Optional['AnomalyDetector'] = None

        self._logger.info(f"BotServicesProvider создан (версия SDB: {settings.core.sdb_version}). Ожидает настройки сервисов.")

    async def setup_services(self) -> None:
        self._logger.info("Начало асинхронной настройки основных сервисов SDB...")
        
        from Systems.core.database.manager import DBManager 
        try:
            self._db_manager = DBManager(db_settings=self._settings.db, app_settings=self._settings)
            await self._db_manager.initialize() 
            self._logger.success("Сервис DBManager успешно настроен.")
        except Exception as e:
            self._logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА настройки DBManager: {e}", exc_info=True)
            raise

        # Сначала инициализируем ModuleLoader, так как RBACService может от него зависеть для получения разрешений модулей
        from Systems.core.module_loader import ModuleLoader 
        try:
            self._module_loader = ModuleLoader(settings=self._settings, services_provider=self)
            self._module_loader.scan_all_available_modules() 
            self._module_loader._load_enabled_plugin_names() 
            self._logger.success(f"Сервис ModuleLoader инициализирован (найдено {len(self._module_loader.available_modules)} модулей, "
                                 f"активно плагинов {len(self._module_loader.enabled_plugin_names)}).")
        except Exception as e_mod_load:
            self._logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА инициализации ModuleLoader: {e_mod_load}", exc_info=True)
            raise 

        # Проверка и автоматическое создание таблиц ядра, если их нет
        try:
            from sqlalchemy import inspect, text
            from Systems.core.database import core_models
            
            existing_tables = []
            
            # Проверяем существование хотя бы одной таблицы ядра
            if self._settings.db.type == "sqlite":
                # Для SQLite используем простой способ проверки через sqlite_master
                async with self._db_manager._engine.begin() as conn:
                    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sdb_%'"))
                    rows = await result.fetchall()
                    existing_tables = [row[0] for row in rows]
            else:
                # Для PostgreSQL/MySQL используем inspect через sync_engine
                inspector = inspect(self._db_manager._engine.sync_engine)
                existing_tables = inspector.get_table_names()
            
            core_table_names = [
                f"{core_models.SDB_CORE_TABLE_PREFIX}users",
                f"{core_models.SDB_CORE_TABLE_PREFIX}roles",
                f"{core_models.SDB_CORE_TABLE_PREFIX}permissions",
            ]
            
            tables_exist = any(table in existing_tables for table in core_table_names)
            
            if not tables_exist:
                self._logger.warning("Таблицы ядра не найдены. Автоматическое создание таблиц...")
                await self._db_manager.create_all_core_tables()
                self._logger.success("Таблицы ядра успешно созданы автоматически.")
            else:
                self._logger.debug("Таблицы ядра уже существуют.")
        except Exception as e_tables_check:
            self._logger.warning(f"Не удалось проверить существование таблиц ядра: {e_tables_check}. Попытка создания таблиц...")
            try:
                await self._db_manager.create_all_core_tables()
                self._logger.success("Таблицы ядра успешно созданы (после ошибки проверки).")
            except Exception as e_create_tables:
                self._logger.error(f"Критическая ошибка при создании таблиц ядра: {e_create_tables}", exc_info=True)
                raise

        from Systems.core.rbac.service import RBACService 
        try:
            # Передаем self (BotServicesProvider) в RBACService
            self._rbac_service = RBACService(services=self) # <--- ИЗМЕНЕНИЕ ЗДЕСЬ
            if self._db_manager and self._rbac_service:
                try:
                    async with self._db_manager.get_session() as db_session:
                        # Вызываем ensure_default_entities_exist
                        roles_c, core_perms_c, mod_perms_c = await self._rbac_service.ensure_default_entities_exist(db_session) # <--- ИЗМЕНЕНИЕ ЗДЕСЬ
                        await db_session.commit()
                        self._logger.info(f"RBACService.ensure_default_entities_exist отработал. "
                                          f"Ролей создано: {roles_c}, Разрешений ядра: {core_perms_c}, Разрешений модулей: {mod_perms_c}")
                except Exception as e_roles:
                    self._logger.error(f"Критическая ошибка при создании/проверке стандартных RBAC сущностей: {e_roles}", exc_info=True)
            self._logger.success("Сервис RBACService успешно настроен.")
        except ValueError as e_rbac_val: # Например, если DBManager не был передан
            self._logger.error(f"Ошибка инициализации RBACService (возможно, проблема с DBManager или ModuleLoader): {e_rbac_val}")
            self._rbac_service = None
        except Exception as e_rbac:
            self._logger.error(f"Не удалось настроить RBACService: {e_rbac}", exc_info=True)
            self._rbac_service = None 

        from Systems.core.users.service import UserService
        try:
            self._user_service = UserService(services_provider=self) 
            self._logger.success("Сервис UserService успешно настроен.")
        except Exception as e_user_svc:
            self._logger.error(f"Не удалось настроить UserService: {e_user_svc}", exc_info=True)
            self._user_service = None
        
        from Systems.core.cache.manager import CacheManager 
        try:
            self._cache_manager = CacheManager(cache_settings=self._settings.cache)
            await self._cache_manager.initialize()
            if self._cache_manager.is_available():
                 self._logger.success(f"Сервис CacheManager ({self._settings.cache.type}) успешно настроен.")
            else:
                 self._logger.warning(f"CacheManager ({self._settings.cache.type}) инициализирован, но кэш недоступен.")
        except ImportError as e_cache_imp: 
             self._logger.warning(f"Не удалось инициализировать CacheManager: {e_cache_imp}")
        except Exception as e_cache:
            self._logger.error(f"Ошибка настройки CacheManager: {e_cache}", exc_info=True)
            self._cache_manager = None

        from Systems.core.http_client.manager import HTTPClientManager 
        try:
            self._http_client_manager = HTTPClientManager(app_settings=self._settings) 
            await self._http_client_manager.initialize()
            if self._http_client_manager.is_available():
                self._logger.success("Сервис HTTPClientManager успешно настроен.")
            else:
                self._logger.warning("HTTPClientManager инициализирован, но HTTP-клиент недоступен.")
        except ImportError as e_http_imp: 
            self._logger.warning(f"Не удалось инициализировать HTTPClientManager: {e_http_imp}")
        except Exception as e_http:
            self._logger.error(f"Ошибка настройки HTTPClientManager: {e_http}", exc_info=True)
            self._http_client_manager = None

        from Systems.core.events.dispatcher import EventDispatcher 
        try:
            self._event_dispatcher = EventDispatcher()
            self._logger.success("Сервис EventDispatcher успешно инициализирован.")
        except Exception as e_event:
            self._logger.error(f"Ошибка инициализации EventDispatcher: {e_event}", exc_info=True)
            self._event_dispatcher = None

        from Systems.core.ui.registry_ui import UIRegistry 
        try:
            self._ui_registry = UIRegistry()
            self._logger.success("Сервис UIRegistry успешно инициализирован.")
        except Exception as e_ui_reg:
            self._logger.error(f"Ошибка инициализации UIRegistry: {e_ui_reg}", exc_info=True)
            self._ui_registry = None
        
        # Инициализация сервисов безопасности
        from Systems.core.security.signature_manager import ModuleSignatureManager
        try:
            self._signature_manager = ModuleSignatureManager(self._settings)
            self._logger.success("Сервис ModuleSignatureManager успешно инициализирован.")
        except Exception as e_sig:
            self._logger.error(f"Ошибка инициализации ModuleSignatureManager: {e_sig}", exc_info=True)
            self._signature_manager = None
        
        from Systems.core.security.sandbox_manager import ModuleSandboxManager
        try:
            self._sandbox_manager = ModuleSandboxManager(self._settings)
            self._logger.success("Сервис ModuleSandboxManager успешно инициализирован.")
        except Exception as e_sandbox:
            self._logger.error(f"Ошибка инициализации ModuleSandboxManager: {e_sandbox}", exc_info=True)
            self._sandbox_manager = None
        
        from Systems.core.security.audit_logger import SecurityAuditLogger
        try:
            self._audit_logger = SecurityAuditLogger(self._settings)
            self._logger.success("Сервис SecurityAuditLogger успешно инициализирован.")
        except Exception as e_audit:
            self._logger.error(f"Ошибка инициализации SecurityAuditLogger: {e_audit}", exc_info=True)
            self._audit_logger = None
        
        from Systems.core.security.reputation_system import ModuleReputationSystem
        try:
            self._reputation_system = ModuleReputationSystem(self._settings)
            self._logger.success("Сервис ModuleReputationSystem успешно инициализирован.")
        except Exception as e_reputation:
            self._logger.error(f"Ошибка инициализации ModuleReputationSystem: {e_reputation}", exc_info=True)
            self._reputation_system = None
        
        from Systems.core.security.code_scanner import ModuleCodeScanner
        try:
            self._code_scanner = ModuleCodeScanner(self._settings)
            self._logger.success("Сервис ModuleCodeScanner успешно инициализирован.")
        except Exception as e_scanner:
            self._logger.error(f"Ошибка инициализации ModuleCodeScanner: {e_scanner}", exc_info=True)
            self._code_scanner = None
        
        from Systems.core.security.security_levels import SecurityLevelManager
        try:
            self._security_level_manager = SecurityLevelManager(self._settings)
            self._logger.success("Сервис SecurityLevelManager успешно инициализирован.")
        except Exception as e_security:
            self._logger.error(f"Ошибка инициализации SecurityLevelManager: {e_security}", exc_info=True)
            self._security_level_manager = None
        
        from Systems.core.security.anomaly_detection import AnomalyDetector
        try:
            self._anomaly_detector = AnomalyDetector(self._settings)
            self._logger.success("Сервис AnomalyDetector успешно инициализирован.")
        except Exception as e_anomaly:
            self._logger.error(f"Ошибка инициализации AnomalyDetector: {e_anomaly}", exc_info=True)
            self._anomaly_detector = None
        
        # ModuleLoader уже инициализирован выше

        self._logger.info("✅ Первичная настройка всех основных сервисов SDB завершена.")


    async def close_services(self) -> None:
        self._logger.info("Начало процедуры закрытия и освобождения ресурсов сервисов SDB...")
        
        if self._module_loader: self._logger.debug("ModuleLoader не требует специального dispose().")
        if self._ui_registry:
            try: await self._ui_registry.dispose(); self._logger.info("UIRegistry ресурсы освобождены.")
            except Exception as e: self._logger.error(f"Ошибка при освобождении UIRegistry: {e}", exc_info=True)
        if self._event_dispatcher:
            try: await self._event_dispatcher.dispose(); self._logger.info("EventDispatcher ресурсы освобождены.")
            except Exception as e: self._logger.error(f"Ошибка при освобождении EventDispatcher: {e}", exc_info=True)
        if self._http_client_manager:
            try: await self._http_client_manager.dispose(); self._logger.info("HTTPClientManager ресурсы освобождены.")
            except Exception as e: self._logger.error(f"Ошибка при освобождении HTTPClientManager: {e}", exc_info=True)
        if self._cache_manager:
            try: await self._cache_manager.dispose(); self._logger.info("CacheManager ресурсы освобождены.")
            except Exception as e: self._logger.error(f"Ошибка при освобождении CacheManager: {e}", exc_info=True)
        
        if self._user_service: self._logger.debug("UserService не требует специального dispose().")
        if self._rbac_service: self._logger.debug("RBACService не требует специального dispose().")
        
        # Закрытие сервисов безопасности
        if self._audit_logger:
            try: self._audit_logger.force_flush(); self._logger.info("SecurityAuditLogger буфер записан.")
            except Exception as e: self._logger.error(f"Ошибка при записи буфера SecurityAuditLogger: {e}", exc_info=True)
        
        if self._signature_manager: self._logger.debug("ModuleSignatureManager не требует специального dispose().")
        if self._sandbox_manager: self._logger.debug("ModuleSandboxManager не требует специального dispose().")
        if self._reputation_system: self._logger.debug("ModuleReputationSystem не требует специального dispose().")
        if self._code_scanner: self._logger.debug("ModuleCodeScanner не требует специального dispose().")
        if self._security_level_manager: self._logger.debug("SecurityLevelManager не требует специального dispose().")
        if self._anomaly_detector: self._logger.debug("AnomalyDetector не требует специального dispose().")
        
        if self._db_manager:
            try: await self._db_manager.dispose(); self._logger.info("DBManager ресурсы освобождены.")
            except Exception as e: self._logger.error(f"Ошибка при освобождении DBManager: {e}", exc_info=True)
        
        self._logger.info("🏁 Процедура закрытия всех сервисов SDB завершена.")
    
    @property
    def config(self) -> 'AppSettings':
        return self._settings

    @property
    def logger(self):
        return global_logger 

    @property
    def db(self) -> 'DBManager':
        if self._db_manager is None:
            msg = "DBManager не инициализирован! Обращение к БД невозможно."
            self._logger.critical(msg)
            raise RuntimeError(msg)
        return self._db_manager

    @property
    def rbac(self) -> 'RBACService':
        if self._rbac_service is None:
            msg = "RBACService не инициализирован! Функции RBAC будут недоступны."
            self._logger.error(msg) 
            raise AttributeError(msg) 
        return self._rbac_service
    
    @property
    def user_service(self) -> 'UserService':
        if self._user_service is None:
            msg = "UserService не инициализирован! Функции управления пользователями будут недоступны."
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._user_service

    @property
    def cache(self) -> 'CacheManager':
        if self._cache_manager is None or not self._cache_manager.is_available():
            # msg = "CacheManager не инициализирован или кэш недоступен!" # Закомментировано чтобы не спамить, если кэш опционален
            # self._logger.warning(msg)
            raise AttributeError("CacheManager не инициализирован или кэш недоступен! Попытка использовать недоступный кэш.")
        return self._cache_manager

    @property
    def http(self) -> 'HTTPClientManager': 
        if self._http_client_manager is None or not self._http_client_manager.is_available():
            raise AttributeError("HTTPClientManager не инициализирован или HTTP-клиент недоступен! Попытка использовать недоступный HTTP-клиент.")
        return self._http_client_manager

    @property
    def modules(self) -> 'ModuleLoader': 
        if self._module_loader is None:
            msg = "ModuleLoader не инициализирован!" 
            self._logger.critical(msg)
            raise RuntimeError(msg)
        return self._module_loader

    # Security services properties
    @property
    def signature_manager(self) -> 'ModuleSignatureManager':
        if self._signature_manager is None:
            msg = "ModuleSignatureManager не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._signature_manager
    
    @property
    def sandbox_manager(self) -> 'ModuleSandboxManager':
        if self._sandbox_manager is None:
            msg = "ModuleSandboxManager не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._sandbox_manager
    
    @property
    def audit_logger(self) -> 'SecurityAuditLogger':
        if self._audit_logger is None:
            msg = "SecurityAuditLogger не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._audit_logger
    
    @property
    def reputation_system(self) -> 'ModuleReputationSystem':
        if self._reputation_system is None:
            msg = "ModuleReputationSystem не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._reputation_system
    
    @property
    def code_scanner(self) -> 'ModuleCodeScanner':
        if self._code_scanner is None:
            msg = "ModuleCodeScanner не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._code_scanner
    
    @property
    def security_level_manager(self) -> 'SecurityLevelManager':
        if self._security_level_manager is None:
            msg = "SecurityLevelManager не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._security_level_manager
    
    @property
    def anomaly_detector(self) -> 'AnomalyDetector':
        if self._anomaly_detector is None:
            msg = "AnomalyDetector не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._anomaly_detector

    @property
    def events(self) -> 'EventDispatcher':
        if self._event_dispatcher is None:
            msg = "EventDispatcher не инициализирован!"
            self._logger.error(msg) 
            raise AttributeError(msg)
        return self._event_dispatcher
    
    @property
    def ui_registry(self) -> 'UIRegistry':
        if self._ui_registry is None:
            msg = "UIRegistry не инициализирован!"
            self._logger.error(msg)
            raise AttributeError(msg)
        return self._ui_registry