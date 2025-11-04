# core/module_loader.py

import asyncio
import importlib
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from typing import (TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple,
                    Type)

import yaml  # type: ignore
from aiogram import Bot, Dispatcher
from loguru import logger
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError

# Добавляем PermissionManifest в импорты
from .schemas.module_manifest import (ModuleManifest, PermissionManifest,
                                      SettingManifest)

if TYPE_CHECKING:
    from .app_settings import AppSettings, CoreAppSettings
    from .services_provider import BotServicesProvider

MANIFEST_YAML_NAME = "manifest.yaml"
MANIFEST_JSON_NAME = "manifest.json"
MODULE_ENTRY_POINT_FILENAME = "__init__.py"
SETUP_FUNCTION_NAME = "setup_module"
USER_MODULES_SETTINGS_DIR_NAME = "modules_settings"
MODULE_DEFAULT_SETTINGS_FILENAME = "module_settings.yaml"


class ModuleInfo:
    def __init__(
        self,
        name: str,
        path: Path,
        manifest: Optional[ModuleManifest] = None,
        is_enabled: bool = False,
        error: Optional[str] = None,
        is_system_module: bool = False,
    ):
        self.name: str = name
        self.path: Path = path
        self.manifest: Optional[ModuleManifest] = manifest
        self.is_enabled: bool = is_enabled
        self.is_loaded_successfully: bool = False
        self.error: Optional[str] = error
        self.imported_py_module: Optional[Any] = None
        self.is_system_module: bool = is_system_module
        self.current_settings: Dict[str, Any] = {}

    def __repr__(self) -> str:
        status_parts = []
        if self.is_system_module:
            status_parts.append("system")
        if self.is_enabled or self.is_system_module:
            status_parts.append("active_target")
        if self.is_loaded_successfully:
            status_parts.append("loaded")
        if self.current_settings:
            status_parts.append("settings_loaded")
        if self.error:
            status_parts.append(f"error='{self.error[:30]}...'")
        status_str = ", ".join(status_parts) if status_parts else "discovered"
        return f"<ModuleInfo name='{self.name}' ({status_str})>"


class ModuleLoader:
    def __init__(self, settings: "AppSettings", services_provider: "BotServicesProvider"):
        self._settings: "AppSettings" = settings
        self._services: "BotServicesProvider" = services_provider
        self._core_settings: "CoreAppSettings" = self._settings.core

        self.plugins_root_dir: Path = settings.core.project_data_path.parent / "modules"
        self.core_sys_modules_root_dir: Path = settings.core.project_data_path.parent / "Systems" / "core" / "sys_modules"

        self.user_module_settings_base_path: Path = (
            self._core_settings.project_data_path / "Config" / USER_MODULES_SETTINGS_DIR_NAME
        )
        self.user_module_settings_base_path.mkdir(parents=True, exist_ok=True)

        self.available_modules: Dict[str, ModuleInfo] = {}
        self.enabled_plugin_names: List[str] = []

        self._logger = logger.bind(service="ModuleLoader")
        self._logger.info(
            f"ModuleLoader инициализирован. "
            f"Плагины: {self.plugins_root_dir.resolve()}, "
            f"Системные модули: {self.core_sys_modules_root_dir.resolve()}, "
            f"Пользовательские настройки модулей: {self.user_module_settings_base_path.resolve()}"
        )

    def _parse_manifest_file(
        self, module_path: Path, module_name_override: Optional[str] = None
    ) -> Optional[ModuleManifest]:
        yaml_manifest_path = module_path / MANIFEST_YAML_NAME
        json_manifest_path = module_path / MANIFEST_JSON_NAME
        manifest_file_to_parse: Optional[Path] = None
        parser_type: Optional[str] = None

        if yaml_manifest_path.is_file():
            manifest_file_to_parse = yaml_manifest_path
            parser_type = "yaml"
            if json_manifest_path.is_file():
                self._logger.warning(
                    f"В модуле '{module_path.name}' найдены и YAML, и JSON манифесты. Используется YAML."
                )
        elif json_manifest_path.is_file():
            manifest_file_to_parse = json_manifest_path
            parser_type = "json"

        if not manifest_file_to_parse:
            is_plugin = not (module_path.parent.name == "sys_modules" and module_path.parent.parent.name == "core")
            log_func = self._logger.warning if is_plugin else self._logger.debug
            log_func(f"Манифест не найден для модуля '{module_path.name}'.")
            return None
        try:
            with open(manifest_file_to_parse, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) if parser_type == "yaml" else json.load(f)
            if not data:
                self._logger.error(f"Манифест {manifest_file_to_parse.name} в модуле {module_path.name} пуст.")
                return None

            if module_name_override and "name" not in data:
                data["name"] = module_name_override
            elif "name" in data and module_name_override and data["name"] != module_name_override:
                self._logger.warning(
                    f"Имя модуля в манифесте ('{data['name']}') отличается от имени папки ('{module_name_override}') "
                    f"для {manifest_file_to_parse.name}. Используется имя из манифеста: '{data['name']}'."
                )

            manifest = ModuleManifest(**data)
            return manifest
        except Exception as e:
            self._logger.error(
                f"Ошибка парсинга/валидации манифеста {manifest_file_to_parse.name} в {module_path.name}: {e}",
                exc_info=True,
            )
        return None

    def _scan_directory_for_modules(self, directory: Path, is_system_dir: bool) -> None:
        if not directory.is_dir():
            self._logger.warning(
                f"Директория {'системных модулей' if is_system_dir else 'плагинов'} {directory} не найдена."
            )
            return

        for module_dir_path in directory.iterdir():
            if module_dir_path.is_dir() and not module_dir_path.name.startswith((".", "_")):
                module_name_from_path = module_dir_path.name
                manifest = self._parse_manifest_file(
                    module_dir_path, module_name_override=module_name_from_path if is_system_dir else None
                )

                actual_module_name = manifest.name if manifest and manifest.name else module_name_from_path

                if actual_module_name in self.available_modules:
                    self._logger.warning(
                        f"Дублирующееся имя модуля '{actual_module_name}' (из папки '{module_dir_path.name}', "
                        f"тип: {'системный' if is_system_dir else 'плагин'}). "
                        f"Предыдущий модуль с таким именем будет перезаписан в списке доступных."
                    )

                module_info = ModuleInfo(
                    name=actual_module_name,
                    path=module_dir_path,
                    manifest=manifest,
                    is_system_module=is_system_dir,
                    is_enabled=is_system_dir,
                )

                if manifest and manifest.settings:
                    self._load_and_validate_module_settings(module_info)

                self.available_modules[actual_module_name] = module_info
                log_msg_type = "системный модуль" if is_system_dir else "плагин"
                log_msg_details = f"v{manifest.version}" if manifest and manifest.version else "без манифеста/версии"
                self._logger.info(
                    f"Найден {log_msg_type} '{actual_module_name}' ({log_msg_details}) в '{module_dir_path.name}'."
                )

    def _load_and_validate_module_settings(self, module_info: ModuleInfo) -> None:
        module_name = module_info.name
        manifest = module_info.manifest
        module_info.current_settings = {}

        if not manifest or not manifest.settings:
            return

        module_default_config_file = module_info.path / MODULE_DEFAULT_SETTINGS_FILENAME
        user_module_config_file = self.user_module_settings_base_path / f"{module_name}.yaml"

        final_settings: Dict[str, Any] = {}
        for key, setting_mft_def in manifest.settings.items():
            final_settings[key] = setting_mft_def.default

        module_defaults_from_file: Dict[str, Any] = {}
        if module_default_config_file.is_file():
            try:
                with open(module_default_config_file, "r", encoding="utf-8") as f:
                    module_defaults_from_file = yaml.safe_load(f) or {}
                final_settings.update(module_defaults_from_file)
                self._logger.trace(
                    f"Загружены настройки по умолчанию из файла модуля '{module_name}': {module_default_config_file}"
                )
            except Exception as e:
                self._logger.warning(
                    f"Ошибка чтения файла '{module_default_config_file}' для модуля '{module_name}': {e}."
                )

        if not user_module_config_file.exists():
            self._logger.info(
                f"Файл пользовательских настроек для модуля '{module_name}' не найден ({user_module_config_file})."
            )
            source_for_user_config = final_settings.copy()

            if source_for_user_config:
                try:
                    user_module_config_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(user_module_config_file, "w", encoding="utf-8") as f:
                        yaml.dump(source_for_user_config, f, indent=2, sort_keys=False, allow_unicode=True)
                    self._logger.info(
                        f"Создан файл пользовательских настроек для '{module_name}' на основе дефолтов: {user_module_config_file}"
                    )
                except Exception as e_create_user_cfg:
                    self._logger.error(
                        f"Не удалось создать файл пользовательских настроек для '{module_name}': {e_create_user_cfg}."
                    )
            else:
                self._logger.info(
                    f"Для модуля '{module_name}' нет дефолтных значений для генерации пользовательского файла. Файл не создан."
                )
        else:
            try:
                with open(user_module_config_file, "r", encoding="utf-8") as f:
                    user_settings_from_file = yaml.safe_load(f) or {}
                self._logger.info(
                    f"Загружены пользовательские настройки для модуля '{module_name}' из: {user_module_config_file}"
                )
                final_settings.update(user_settings_from_file)
            except Exception as e_load_user:
                self._logger.error(
                    f"Ошибка загрузки пользовательского файла настроек '{user_module_config_file}' для '{module_name}': {e_load_user}."
                )

        validated_settings: Dict[str, Any] = {}
        validation_errors: List[str] = []

        for key, setting_mft_def in manifest.settings.items():
            value_to_validate = final_settings.get(key)

            if value_to_validate is None:
                if setting_mft_def.required:
                    validation_errors.append(
                        f"Отсутствует значение для обязательной настройки '{setting_mft_def.label}' ({key}) модуля '{module_name}'."
                    )
                    continue
                else:
                    validated_settings[key] = None
                    continue

            try:
                validated_value = value_to_validate
                if setting_mft_def.type == "bool":
                    if isinstance(value_to_validate, str):
                        validated_value = value_to_validate.lower() in ["true", "1", "yes", "on", "t"]
                    else:
                        validated_value = bool(value_to_validate)
                elif setting_mft_def.type == "int":
                    validated_value = int(value_to_validate)
                elif setting_mft_def.type == "float":
                    validated_value = float(value_to_validate)
                elif setting_mft_def.type in ["string", "text"]:
                    validated_value = str(value_to_validate)

                key_specific_errors = False
                if setting_mft_def.type == "string" and setting_mft_def.regex_validator:
                    if not re.fullmatch(setting_mft_def.regex_validator, str(validated_value)):
                        validation_errors.append(
                            f"Значение '{validated_value}' для '{key}' не соответствует regex: {setting_mft_def.regex_validator}"
                        )
                        key_specific_errors = True
                if setting_mft_def.type in ["int", "float"]:
                    if setting_mft_def.min_value is not None and validated_value < setting_mft_def.min_value:  # type: ignore
                        validation_errors.append(
                            f"Значение {validated_value} для '{key}' < min ({setting_mft_def.min_value})"
                        )
                        key_specific_errors = True
                    if setting_mft_def.max_value is not None and validated_value > setting_mft_def.max_value:  # type: ignore
                        validation_errors.append(
                            f"Значение {validated_value} для '{key}' > max ({setting_mft_def.max_value})"
                        )
                        key_specific_errors = True
                if setting_mft_def.type == "choice" and setting_mft_def.options:
                    option_values = [
                        opt.value if isinstance(opt, PydanticBaseModel) else opt for opt in setting_mft_def.options
                    ]
                    if validated_value not in option_values:
                        validation_errors.append(
                            f"Значение '{validated_value}' для '{key}' не является допустимым вариантом ({option_values})."
                        )
                        key_specific_errors = True

                if not key_specific_errors:
                    validated_settings[key] = validated_value

            except (ValueError, TypeError) as e_val:
                validation_errors.append(
                    f"Ошибка типа/значения для '{key}' ('{value_to_validate}'): ожидался {setting_mft_def.type}. {e_val}"
                )
            except Exception as e_unknown_val:
                validation_errors.append(f"Неизвестная ошибка валидации для '{key}': {e_unknown_val}")

        if validation_errors:
            error_message = f"Ошибки валидации настроек модуля '{module_name}': {'; '.join(validation_errors)}"
            if module_info.error:
                module_info.error += f"; {error_message}"
            else:
                module_info.error = error_message
            self._logger.error(error_message)

        module_info.current_settings = validated_settings
        if validated_settings or not manifest.settings:
            self._logger.info(f"Актуальные настройки для модуля '{module_name}' загружены и провалидированы.")
            if validated_settings:
                self._logger.debug(f"Итоговые настройки модуля '{module_name}': {validated_settings}")
        else:
            self._logger.warning(
                f"Для модуля '{module_name}' не удалось загрузить/провалидировать ни одной настройки, хотя они описаны в манифесте."
            )

    def scan_all_available_modules(self) -> None:
        self.available_modules.clear()
        self._logger.info("Начало сканирования всех модулей...")
        self._scan_directory_for_modules(self.plugins_root_dir, is_system_dir=False)
        self._scan_directory_for_modules(self.core_sys_modules_root_dir, is_system_dir=True)
        self._logger.info(f"Сканирование всех модулей завершено. Всего найдено: {len(self.available_modules)}")

    def _load_enabled_plugin_names(self) -> None:
        config_file = self._core_settings.enabled_modules_config_path
        self.enabled_plugin_names.clear()
        if config_file.is_file():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.enabled_plugin_names = [m_name for m_name in data if isinstance(m_name, str)]
                elif isinstance(data, dict) and "active_modules" in data and isinstance(data["active_modules"], list):
                    self.enabled_plugin_names = [m_name for m_name in data["active_modules"] if isinstance(m_name, str)]
                else:
                    self._logger.error(
                        f"Неверный формат файла {config_file}. Ожидался список или {{'active_modules': [...]}}."
                    )

                for name, module_info in self.available_modules.items():
                    if not module_info.is_system_module:
                        module_info.is_enabled = name in self.enabled_plugin_names
                self._logger.info(f"Загружен список активных плагинов из {config_file}: {self.enabled_plugin_names}")
            except Exception as e:
                self._logger.error(f"Ошибка загрузки списка активных плагинов из {config_file}: {e}", exc_info=True)
        else:
            self._logger.warning(f"Файл со списком активных плагинов {config_file} не найден.")

    def _check_module_dependencies(self, module_info: ModuleInfo) -> bool:
        if not module_info.manifest:
            return True
        if module_info.manifest.metadata and module_info.manifest.metadata.min_sdb_core_version:
            from packaging.version import parse as parse_version

            current_sdb_version_str = self._settings.core.sdb_version
            try:
                if parse_version(current_sdb_version_str) < parse_version(
                    module_info.manifest.metadata.min_sdb_core_version
                ):
                    module_info.error = (
                        f"Требуется ядро SDB v >= {module_info.manifest.metadata.min_sdb_core_version}, "
                        f"текущая: {current_sdb_version_str}."
                    )
                    self._logger.error(f"Модуль '{module_info.name}': {module_info.error}")
                    return False
            except Exception as e_ver:
                self._logger.error(f"Ошибка сравнения версий ядра для '{module_info.name}': {e_ver}")
                module_info.error = "Ошибка формата версии ядра."
                return False

        if module_info.manifest.sdb_module_dependencies:
            for dep_name in module_info.manifest.sdb_module_dependencies:
                dep_info = self.available_modules.get(dep_name)
                if (
                    not dep_info
                    or not (dep_info.is_enabled or dep_info.is_system_module)
                    or not dep_info.is_loaded_successfully
                ):
                    new_error_msg = f"Требуется активный и успешно загруженный модуль-зависимость '{dep_name}'."
                    module_info.error = (module_info.error + "; " if module_info.error else "") + new_error_msg
                    self._logger.error(f"Модуль '{module_info.name}': {new_error_msg}")
                    return False
        return True

    async def _setup_single_module(
        self, module_info: ModuleInfo, dp: Dispatcher, bot: Bot, import_base_path: str
    ) -> None:
        if not module_info.manifest and not module_info.is_system_module:
            module_info.error = "Манифест отсутствует."
            self._logger.error(f"Плагин '{module_info.name}': {module_info.error}")
            return

        if module_info.error:
            self._logger.error(
                f"Модуль '{module_info.name}' не будет загружен из-за предыдущей ошибки: {module_info.error}"
            )
            return

        if not self._check_module_dependencies(module_info):
            return

        entry_point_py_file = module_info.path / MODULE_ENTRY_POINT_FILENAME
        if not entry_point_py_file.is_file():
            module_info.error = f"Файл точки входа '{MODULE_ENTRY_POINT_FILENAME}' не найден."
            self._logger.error(f"Модуль '{module_info.name}': {module_info.error}")
            return
        try:
            import_path_str = f"{import_base_path}.{module_info.path.name}"
            self._logger.debug(f"Импорт модуля '{module_info.name}' через '{import_path_str}'...")
            loaded_py_module = importlib.import_module(import_path_str)
            module_info.imported_py_module = loaded_py_module
            if not hasattr(loaded_py_module, SETUP_FUNCTION_NAME):
                module_info.error = f"Функция '{SETUP_FUNCTION_NAME}' не найдена."
                self._logger.error(f"Модуль '{module_info.name}': {module_info.error}")
                return

            setup_function: Callable = getattr(loaded_py_module, SETUP_FUNCTION_NAME)
            self._logger.info(f"Вызов {SETUP_FUNCTION_NAME}() для модуля '{module_info.name}'...")
            if asyncio.iscoroutinefunction(setup_function):
                await setup_function(dp=dp, bot=bot, services=self._services)
            else:
                setup_function(dp=dp, bot=bot, services=self._services)
            module_info.is_loaded_successfully = True
            self._logger.success(f"✅ Модуль '{module_info.name}' успешно загружен и настроен.")
        except Exception as e:
            module_info.error = f"Ошибка загрузки/настройки: {e}"
            self._logger.error(f"Модуль '{module_info.name}': {module_info.error}", exc_info=True)

    async def initialize_and_setup_modules(self, dp: Dispatcher, bot: Bot) -> None:
        self.scan_all_available_modules()
        self._load_enabled_plugin_names()

        # Сначала настраиваем системные модули ядра
        self._logger.info("Настройка системных модулей ядра...")
        for module_name, module_info in self.available_modules.items():
            if module_info.is_system_module:
                if module_info.error:
                    self._logger.error(
                        f"Системный модуль '{module_name}' не будет настроен из-за предыдущей ошибки: {module_info.error}"
                    )
                    continue
                await self._setup_single_module(
                    module_info,
                    dp,
                    bot,
                    import_base_path="Systems." + self.core_sys_modules_root_dir.parent.name
                    + "."
                    + self.core_sys_modules_root_dir.name,
                )
        self._logger.info("Настройка системных модулей ядра завершена.")

        if not self.enabled_plugin_names:
            self._logger.info("Нет активных плагинов для настройки.")
        else:
            self._logger.info(f"Настройка {len(self.enabled_plugin_names)} активных плагинов...")
            for plugin_name in self.enabled_plugin_names:
                module_info = self.available_modules.get(plugin_name)
                if not module_info:
                    self._logger.error(f"Активный плагин '{plugin_name}' не найден. Пропуск.")
                    continue
                if module_info.is_system_module:
                    self._logger.warning(f"Модуль '{plugin_name}' системный, но в списке плагинов. Пропуск.")
                    continue
                if module_info.error:
                    self._logger.error(
                        f"Модуль '{plugin_name}' не будет настроен из-за предыдущей ошибки: {module_info.error}"
                    )
                    continue
                await self._setup_single_module(module_info, dp, bot, import_base_path="modules")
            self._logger.info("Настройка активных плагинов завершена.")

    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        return self.available_modules.get(module_name)

    def get_all_modules_info(self) -> List[ModuleInfo]:
        return list(self.available_modules.values())

    def get_loaded_modules_info(self, include_system: bool = True, include_plugins: bool = True) -> List[ModuleInfo]:
        loaded = []
        for info in self.available_modules.values():
            if info.is_loaded_successfully:
                if (info.is_system_module and include_system) or (not info.is_system_module and include_plugins):
                    loaded.append(info)
        return loaded

    def get_module_settings(self, module_name: str) -> Optional[Dict[str, Any]]:
        module_info = self.get_module_info(module_name)
        if module_info:
            if module_info.current_settings:
                return module_info.current_settings
            elif module_info.manifest and module_info.manifest.settings:
                manifest_defaults = {
                    k: v.default for k, v in module_info.manifest.settings.items() if v.default is not None
                }
                if manifest_defaults:
                    self._logger.debug(
                        f"current_settings для модуля '{module_name}' пусты, возвращаем дефолты из манифеста."
                    )
                    return manifest_defaults
                else:
                    self._logger.debug(
                        f"Модуль '{module_name}' не имеет актуальных или дефолтных настроек в манифесте."
                    )
                    return {}  # Возвращаем пустой словарь, если нет ни current_settings, ни дефолтов в манифесте
            else:
                self._logger.debug(f"Модуль '{module_name}' не имеет описания настроек в манифесте.")
                return {}  # Возвращаем пустой словарь
        self._logger.warning(f"Попытка получить настройки для неизвестного модуля '{module_name}'.")
        return None

    def get_all_declared_permissions_from_active_modules(self) -> List[PermissionManifest]:
        """
        Собирает все разрешения, объявленные в манифестах активных
        (enabled) плагинов, а также системных модулей.
        Учитываются только модули без ошибок загрузки манифеста.
        """
        all_perms: Dict[str, PermissionManifest] = {}

        modules_to_check: List[ModuleInfo] = []
        # Добавляем активные плагины
        for module_name in self.enabled_plugin_names:
            module_info = self.available_modules.get(module_name)
            if module_info and not module_info.is_system_module and not module_info.error:
                modules_to_check.append(module_info)

        # Добавляем системные модули
        for module_info in self.available_modules.values():
            if module_info.is_system_module and not module_info.error:
                if (
                    module_info not in modules_to_check
                ):  # Избегаем дублирования, если системный модуль как-то попал в enabled_plugin_names
                    modules_to_check.append(module_info)

        for module_info in modules_to_check:
            if module_info.manifest and module_info.manifest.declared_permissions:
                for perm_mft in module_info.manifest.declared_permissions:
                    if perm_mft.name not in all_perms:
                        all_perms[perm_mft.name] = perm_mft
                    else:
                        self._logger.warning(
                            f"Дублирующееся объявление разрешения '{perm_mft.name}' "
                            f"обнаружено (модуль: '{module_info.name}'). Будет использовано первое встреченное."
                        )

        num_perms = len(all_perms)
        if num_perms > 0:
            self._logger.info(f"Собрано {num_perms} уникальных разрешений, объявленных активными/системными модулями.")
        else:
            self._logger.info("Не найдено разрешений, объявленных в активных/системных модулях.")
        return list(all_perms.values())
