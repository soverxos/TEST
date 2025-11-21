# core/ui/registry_ui.py

from typing import List, Dict, Optional, Callable, Any
from pydantic import BaseModel, Field, field_validator, ValidationError
from loguru import logger


class ModuleUIEntry(BaseModel):
    module_name: str = Field(description="Уникальное имя модуля (должно совпадать с manifest.name)")
    display_name: str = Field(description="Отображаемое имя для кнопки в меню")
    entry_callback_data: str = Field(description="Строка callback_data для кнопки входа в модуль")
    
    icon: Optional[str] = Field(default=None, description="Эмодзи-иконка для кнопки (опционально)")
    description: Optional[str] = Field(
        default=None, 
        description="Краткое описание модуля, может использоваться в UI (например, в списке модулей)"
    )
    order: int = Field(
        default=100, 
        description="Порядок сортировки в меню (меньшее значение означает более высокий приоритет/положение)"
    )
    # Новое поле для указания разрешения, необходимого для отображения этой кнопки в общем меню
    required_permission_to_view: Optional[str] = Field(
        default=None,
        description="Имя разрешения, необходимое для того, чтобы эта точка входа была видна пользователю."
    )

    @field_validator('module_name', 'display_name', 'entry_callback_data')
    @classmethod 
    def names_must_not_be_empty(cls, v: str) -> str: 
        if not v or not v.strip():
            raise ValueError("Имя модуля, отображаемое имя и entry_callback_data не могут быть пустыми строками")
        return v

    class Config:
        validate_assignment = True 
        extra = 'forbid' 


class UIRegistry:
    def __init__(self):
        self._module_entries: Dict[str, ModuleUIEntry] = {}
        self._logger = logger.bind(service="UIRegistry")
        self._logger.info("UIRegistry инициализирован.")

    def register_module_entry(
        self,
        module_name: str,
        display_name: str,
        entry_callback_data: str,
        icon: Optional[str] = None,
        description: Optional[str] = None,
        order: int = 100,
        required_permission_to_view: Optional[str] = None # <--- Новое поле
    ) -> bool:
        if module_name in self._module_entries:
            self._logger.warning(
                f"Модуль '{module_name}' уже зарегистрировал свою UI-точку входа. "
                f"Повторная регистрация перезапишет предыдущую запись."
            )
        
        try:
            entry = ModuleUIEntry(
                module_name=module_name,
                display_name=display_name,
                entry_callback_data=entry_callback_data,
                icon=icon,
                description=description,
                order=order,
                required_permission_to_view=required_permission_to_view # <--- Используем новое поле
            )
            self._module_entries[module_name] = entry
            self._logger.info(f"UI-точка входа для модуля '{module_name}' ('{display_name}') успешно зарегистрирована. "
                              f"Требуемое разрешение для просмотра: '{required_permission_to_view or 'нет'}'.")
            return True
        except ValidationError as e:
            self._logger.error(f"Ошибка валидации данных при регистрации UI-точки входа для модуля '{module_name}': {e}")
            return False
        except Exception as e:
            self._logger.error(f"Неожиданная ошибка при регистрации UI-точки входа для модуля '{module_name}': {e}", exc_info=True)
            return False

    def unregister_module_entry(self, module_name: str) -> bool:
        if module_name in self._module_entries:
            del self._module_entries[module_name]
            self._logger.info(f"UI-точка входа для модуля '{module_name}' была отменена (удалена из реестра).")
            return True
        else:
            self._logger.warning(f"Попытка отменить регистрацию для незарегистрированной UI-точки входа модуля '{module_name}'.")
            return False

    def get_all_module_entries(self) -> List[ModuleUIEntry]: # Убрал for_admin_status, будем проверять required_permission_to_view
        entries = list(self._module_entries.values())
        entries.sort(key=lambda x: (x.order, x.display_name.lower()))
        self._logger.trace(f"Запрошен список ВСЕХ UI-точек входа модулей. Найдено: {len(entries)}")
        return entries

    def get_module_entry(self, module_name: str) -> Optional[ModuleUIEntry]:
        return self._module_entries.get(module_name)

    async def dispose(self) -> None: 
        self._module_entries.clear()
        self._logger.info("UIRegistry очищен (все UI-точки входа модулей удалены).")