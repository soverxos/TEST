# core/schemas/module_manifest.py

from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, HttpUrl, ValidationInfo
import re
from loguru import logger 


class CommandManifest(BaseModel):
    command: str = Field(..., description="Сама команда (без '/'). Например, 'weather'.")
    description: str = Field(..., description="Описание команды для пользователя (например, для /help).")
    icon: Optional[str] = Field(default=None, description="Эмодзи-иконка для команды (опционально).")
    category: Optional[str] = Field(default=None, description="Категория для группировки команд (опционально).")
    admin_only: bool = Field(default=False, alias="admin", description="Требует ли команда прав администратора.")

class SettingChoiceOption(BaseModel):
    value: Any
    display_name: str

class SettingManifest(BaseModel):
    type: Literal["string", "int", "float", "bool", "choice", "multichoice", "text"] = Field(
        description="Тип настройки."
    )
    label: str = Field(..., description="Человекочитаемое название настройки (для UI).")
    description: Optional[str] = Field(default=None, description="Подробное описание настройки (для UI).")
    default: Optional[Any] = Field(default=None, description="Значение по умолчанию. Обязательно, если required=True и нет значения в пользовательском конфиге.")
    required: bool = Field(default=False, description="Является ли настройка обязательной.")
    options: Optional[List[Union[str, int, float, SettingChoiceOption]]] = Field(
        default=None,
        description="Список доступных вариантов."
    )
    min_value: Optional[Union[int, float]] = Field(default=None, alias="min", description="Минимальное допустимое значение.")
    max_value: Optional[Union[int, float]] = Field(default=None, alias="max", description="Максимальное допустимое значение.")
    regex_validator: Optional[str] = Field(default=None, description="Регулярное выражение для валидации строки.")

    @field_validator('options', mode='before')
    @classmethod
    def _check_options_for_choice_type(cls, v: Optional[List[Any]], info: ValidationInfo) -> Optional[List[Any]]:
        setting_type = info.data.get('type') if info.data else None
        if setting_type in ["choice", "multichoice"] and (v is None or not v):
            raise ValueError(f"Поле 'options' обязательно для типа настройки '{setting_type}'")
        if setting_type not in ["choice", "multichoice"] and v is not None:
            logger.warning(f"Поле 'options' применимо только для 'choice'/'multichoice', но указано для '{setting_type}'.")
        return v

    @field_validator('min_value', 'max_value', mode='before')
    @classmethod
    def _check_min_max_for_numeric_type(cls, v: Optional[Union[int, float]], info: ValidationInfo) -> Optional[Union[int, float]]:
        setting_type = info.data.get('type') if info.data else None
        field_name = info.field_name 
        if setting_type not in ["int", "float"] and v is not None:
            logger.warning(f"Поле '{field_name}' применимо только для 'int'/'float', но указано для '{setting_type}'.")
        return v

    @field_validator('regex_validator', mode='before')
    @classmethod
    def _check_regex_for_string_type(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        setting_type = info.data.get('type') if info.data else None
        if setting_type != "string" and v is not None:
            logger.warning(f"Поле 'regex_validator' применимо только для 'string', но указано для '{setting_type}'.")
        if v is not None:
            try: re.compile(v)
            except re.error as e: raise ValueError(f"Невалидный regex в 'regex_validator': {e}")
        return v

    @field_validator('default', mode='after') 
    @classmethod
    def _check_default_for_required(cls, v: Optional[Any], info: ValidationInfo) -> Optional[Any]:
        if info.data.get('required') and v is None:
             field_label = info.data.get('label', 'Неизвестная настройка') 
             raise ValueError(f"Для обязательной настройки '{field_label}' (required=True) должно быть указано значение 'default' в манифесте.")
        return v

class PermissionManifest(BaseModel): 
    name: str = Field(..., description="Уникальное имя разрешения (например, 'my_module.can_edit_items'). Должно быть в формате 'module_name.permission_key'.")
    description: str = Field(..., description="Человекочитаемое описание разрешения.")

    @field_validator('name')
    @classmethod
    def _validate_permission_name_format(cls, v: str, info: ValidationInfo) -> str:
        if not re.fullmatch(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", v.lower()):
            raise ValueError(f"Имя разрешения '{v}' должно быть в формате 'module_name.permission_key' "
                             f"(например, 'example_module.view_data') и содержать только строчные буквы, цифры, '_' и '.'")
        return v.lower() 


class BackgroundTaskManifest(BaseModel):
    entry_point: str = Field(...)
    schedule: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)

class ModuleMetadata(BaseModel):
    homepage: Optional[HttpUrl] = Field(default=None)
    license: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    min_sdb_core_version: Optional[str] = Field(default=None)
    assign_default_access_to_user_role: bool = Field( # <--- НОВОЕ ПОЛЕ
        default=False,
        alias="public_access",  # Короткий алиас для удобства
        description="Если true, базовое разрешение '{module_name}.access_user_features' будет автоматически назначено роли 'User'. Можно использовать короткое имя 'public_access'."
    )
    
    model_config = {"populate_by_name": True}  # Позволяет использовать и оригинальное имя, и алиас

    @field_validator('min_sdb_core_version', mode='before')
    @classmethod
    def _validate_semver_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            semver_regex = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
            if not re.fullmatch(semver_regex, v):
                raise ValueError(f"min_sdb_core_version ('{v}') должен быть в формате SemVer")
        return v

class ModuleManifest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    name: str = Field(..., min_length=3, pattern=r'^[a-z][a-z0-9_]*[a-z0-9]$')
    display_name: str = Field(..., min_length=3)
    version: str = Field(...)
    description: Optional[str] = Field(default=None)
    author: Optional[str] = Field(default=None)
    
    python_requirements: List[str] = Field(default_factory=list)
    sdb_module_dependencies: List[str] = Field(default_factory=list)
    model_definitions: List[str] = Field(default_factory=list)
    commands: List[CommandManifest] = Field(default_factory=list)
    settings: Dict[str, SettingManifest] = Field(default_factory=dict) 
    declared_permissions: List[PermissionManifest] = Field(default_factory=list, alias="permissions")
    background_tasks: Dict[str, BackgroundTaskManifest] = Field(default_factory=dict)
    metadata: ModuleMetadata = Field(default_factory=ModuleMetadata) # <--- ИЗМЕНЕНО: metadata теперь не Optional, чтобы всегда было поле assign_default_access_to_user_role

    @field_validator('version', mode='before')
    @classmethod
    def _validate_module_version_format(cls, v: str) -> str:
        semver_regex = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        if not re.fullmatch(semver_regex, v):
            raise ValueError(f"Версия модуля ('{v}') должна соответствовать формату SemVer 2.0.0")
        return v

    @field_validator('name', mode='before')
    @classmethod
    def _validate_module_name(cls, v: str) -> str:
        if not v.islower() and "_" not in v: 
            if v.lower() != v: 
                 logger.warning(f"Имя модуля '{v}' содержит заглавные буквы. Рекомендуется snake_case.")
        return v
        
    @field_validator('declared_permissions') 
    @classmethod
    def _validate_permission_names_match_module(cls, v: List[PermissionManifest], info: ValidationInfo) -> List[PermissionManifest]:
        module_name = info.data.get('name') 
        if module_name:
            for perm_manifest in v:
                if not perm_manifest.name.startswith(f"{module_name}."):
                    raise ValueError(
                        f"Имя разрешения '{perm_manifest.name}' в модуле '{module_name}' "
                        f"должно начинаться с префикса '{module_name}.'"
                    )
        return v

    model_config = {
        "extra": "forbid",
        "protected_namespaces": (),
        "validate_assignment": True,
        "populate_by_name": True
    }