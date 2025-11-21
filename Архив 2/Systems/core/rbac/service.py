# core/rbac/service.py
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func as sql_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Systems.core.database.core_models import (Permission,  # Добавлена UserPermission
                                       Role, RolePermission, User,
                                       UserPermission, UserRole)
from Systems.core.schemas.module_manifest import \
    PermissionManifest as ModulePermissionManifestSchema

if TYPE_CHECKING:
    from Systems.core.database.manager import DBManager
    from Systems.core.module_loader import ModuleInfo
    from Systems.core.services_provider import BotServicesProvider

# --- Стандартные Роли ---
DEFAULT_ROLE_USER = "User"
DEFAULT_ROLE_MODERATOR = "Moderator"
DEFAULT_ROLE_ADMIN = "Admin"
DEFAULT_ROLE_SUPER_ADMIN = "SuperAdmin"

DEFAULT_ROLES_DEFINITIONS: Dict[str, str] = {
    DEFAULT_ROLE_USER: "Обычный пользователь с базовыми правами доступа.",
    DEFAULT_ROLE_MODERATOR: "Модератор с правами на просмотр информации и базовое управление.",
    DEFAULT_ROLE_ADMIN: "Администратор, имеет расширенные права в определенных областях.",
    DEFAULT_ROLE_SUPER_ADMIN: "Супер Администратор, имеет неограниченные возможности и полный доступ ко всем функциям системы.",
}

# --- Стандартные Разрешения ЯДРА (Permissions) ---
PERMISSION_CORE_VIEW_ADMIN_PANEL = "core.admin.view_panel"
PERMISSION_CORE_USERS_VIEW_LIST = "core.users.view_list"
PERMISSION_CORE_USERS_VIEW_DETAILS = "core.users.view_details"
PERMISSION_CORE_USERS_EDIT_PROFILE = "core.users.edit_profile"
PERMISSION_CORE_USERS_MANAGE_STATUS = "core.users.manage_status"
PERMISSION_CORE_USERS_ASSIGN_ROLES = "core.users.assign_roles"
PERMISSION_CORE_USERS_DELETE = "core.users.delete"
PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS = "core.users.manage_direct_permissions"  # НОВОЕ РАЗРЕШЕНИЕ

PERMISSION_CORE_ROLES_VIEW = "core.roles.view"
PERMISSION_CORE_ROLES_CREATE = "core.roles.create"
PERMISSION_CORE_ROLES_EDIT = "core.roles.edit"
PERMISSION_CORE_ROLES_DELETE = "core.roles.delete"
PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS = "core.roles.assign_permissions"

PERMISSION_CORE_PERMISSIONS_VIEW = "core.permissions.view"

PERMISSION_CORE_MODULES_VIEW_LIST = "core.modules.view_list"
PERMISSION_CORE_MODULES_TOGGLE_ACTIVATION = "core.modules.toggle_activation"
PERMISSION_CORE_MODULES_MANAGE_SETTINGS = "core.modules.manage_settings"

PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC = "core.system.view_info.basic"
PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL = "core.system.view_info.full"
PERMISSION_CORE_SYSTEM_VIEW_LOGS_BASIC = "core.system.view_logs.basic"
PERMISSION_CORE_SYSTEM_VIEW_LOGS_FULL = "core.system.view_logs.full"
PERMISSION_CORE_SYSTEM_MANAGE_BACKUPS = "core.system.manage_backups"
PERMISSION_CORE_SYSTEM_SEND_BROADCAST = "core.system.send_broadcast"

PERMISSION_CORE_SETTINGS_VIEW = "core.settings.view"
PERMISSION_CORE_SETTINGS_EDIT = "core.settings.edit"


DEFAULT_CORE_PERMISSIONS_DEFINITIONS: Dict[str, str] = {
    PERMISSION_CORE_VIEW_ADMIN_PANEL: "Доступ к административной панели.",
    PERMISSION_CORE_USERS_VIEW_LIST: "Просмотр списка пользователей.",
    PERMISSION_CORE_USERS_VIEW_DETAILS: "Просмотр детальной информации о пользователе.",
    PERMISSION_CORE_USERS_EDIT_PROFILE: "Редактирование профиля пользователя (имя, язык и т.д.).",
    PERMISSION_CORE_USERS_MANAGE_STATUS: "Управление статусом пользователя (активен/заблокирован).",
    PERMISSION_CORE_USERS_ASSIGN_ROLES: "Назначение и снятие ролей с пользователей.",
    PERMISSION_CORE_USERS_DELETE: "Удаление пользователей из системы.",
    PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS: "Управление индивидуальными разрешениями пользователей.",  # ОПИСАНИЕ НОВОГО РАЗРЕШЕНИЯ
    PERMISSION_CORE_ROLES_VIEW: "Просмотр ролей и их разрешений.",
    PERMISSION_CORE_ROLES_CREATE: "Создание новых ролей.",
    PERMISSION_CORE_ROLES_EDIT: "Редактирование существующих ролей (имя, описание).",
    PERMISSION_CORE_ROLES_DELETE: "Удаление ролей.",
    PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS: "Назначение и снятие разрешений с ролей.",
    PERMISSION_CORE_PERMISSIONS_VIEW: "Просмотр списка всех доступных разрешений.",
    PERMISSION_CORE_MODULES_VIEW_LIST: "Просмотр списка модулей и их статусов.",
    PERMISSION_CORE_MODULES_TOGGLE_ACTIVATION: "Включение и отключение плагинов.",
    PERMISSION_CORE_MODULES_MANAGE_SETTINGS: "Управление настройками модулей.",
    PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC: "Просмотр базовой системной информации.",
    PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL: "Просмотр полной системной информации и отладочных данных.",
    PERMISSION_CORE_SYSTEM_VIEW_LOGS_BASIC: "Просмотр основных логов системы.",
    PERMISSION_CORE_SYSTEM_VIEW_LOGS_FULL: "Просмотр всех логов системы и их скачивание.",
    PERMISSION_CORE_SYSTEM_MANAGE_BACKUPS: "Управление резервными копиями системы.",
    PERMISSION_CORE_SYSTEM_SEND_BROADCAST: "Отправка широковещательных сообщений пользователям.",
    PERMISSION_CORE_SETTINGS_VIEW: "Просмотр настроек ядра SwiftDevBot.",
    PERMISSION_CORE_SETTINGS_EDIT: "Редактирование настроек ядра SwiftDevBot (высокий риск).",
}

DEFAULT_PERMISSIONS_FOR_CORE_MODERATOR_ROLE: Set[str] = {
    PERMISSION_CORE_VIEW_ADMIN_PANEL,
    PERMISSION_CORE_USERS_VIEW_LIST,
    PERMISSION_CORE_USERS_VIEW_DETAILS,
    PERMISSION_CORE_SYSTEM_VIEW_INFO_BASIC,
}

DEFAULT_PERMISSIONS_FOR_CORE_ADMIN_ROLE: Set[str] = {
    *DEFAULT_PERMISSIONS_FOR_CORE_MODERATOR_ROLE,
    PERMISSION_CORE_USERS_MANAGE_STATUS,
    PERMISSION_CORE_USERS_ASSIGN_ROLES,
    PERMISSION_CORE_MODULES_VIEW_LIST,
    PERMISSION_CORE_SYSTEM_VIEW_LOGS_BASIC,
    PERMISSION_CORE_ROLES_VIEW,
    PERMISSION_CORE_PERMISSIONS_VIEW,
    PERMISSION_CORE_ROLES_CREATE,
    PERMISSION_CORE_ROLES_EDIT,
    PERMISSION_CORE_ROLES_DELETE,
    PERMISSION_CORE_ROLES_ASSIGN_PERMISSIONS,
    PERMISSION_CORE_USERS_MANAGE_DIRECT_PERMISSIONS,  # Назначаем роли Admin по умолчанию
}

# Супер Администратор имеет ВСЕ разрешения (неограниченные возможности)
DEFAULT_PERMISSIONS_FOR_CORE_SUPER_ADMIN_ROLE: Set[str] = {
    *DEFAULT_PERMISSIONS_FOR_CORE_ADMIN_ROLE,
    # Дополнительные разрешения для супер-админа
    PERMISSION_CORE_USERS_DELETE,
    PERMISSION_CORE_USERS_EDIT_PROFILE,
    PERMISSION_CORE_MODULES_TOGGLE_ACTIVATION,
    PERMISSION_CORE_MODULES_MANAGE_SETTINGS,
    PERMISSION_CORE_SYSTEM_VIEW_INFO_FULL,
    PERMISSION_CORE_SYSTEM_VIEW_LOGS_FULL,
    PERMISSION_CORE_SYSTEM_MANAGE_BACKUPS,
    PERMISSION_CORE_SYSTEM_SEND_BROADCAST,
    PERMISSION_CORE_SETTINGS_VIEW,
    PERMISSION_CORE_SETTINGS_EDIT,
}

DEFAULT_PERMISSIONS_FOR_CORE_USER_ROLE: Set[str] = set()


class RBACService:
    def __init__(self, services: Optional["BotServicesProvider"] = None, db_manager: Optional["DBManager"] = None):
        self._services_provider_ref: Optional["BotServicesProvider"] = services
        if db_manager:
            self._db_manager = db_manager
        elif services and hasattr(services, "db") and services.db is not None:
            self._db_manager = services.db
        else:
            self._db_manager = None
            logger.warning(
                "RBACService инициализирован без DBManager. "
                "Методы ensure_default_... потребуют явной передачи сессии или DBManager."
            )

        self._logger = logger.bind(service="RBACService")
        self._logger.info("RBACService инициализирован.")

    async def _get_role_by_name(self, session: AsyncSession, role_name: str) -> Optional[Role]:
        self._logger.trace(f"Получение роли по имени: '{role_name}'")
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.name == role_name)
        result = await session.execute(stmt)
        role = result.scalars().first()
        self._logger.trace(f"Роль '{role_name}' найдена: {role is not None} (ID: {getattr(role, 'id', 'N/A')})")
        return role

    async def get_or_create_role(
        self, session: AsyncSession, role_name: str, description: Optional[str] = None
    ) -> Optional[Role]:
        role = await self._get_role_by_name(session, role_name)
        if not role:
            role_def_desc = DEFAULT_ROLES_DEFINITIONS.get(role_name)
            current_description = description if description is not None else role_def_desc

            if role_name in DEFAULT_ROLES_DEFINITIONS and description is None:
                current_description = role_def_desc

            self._logger.info(
                f"Роль '{role_name}' не найдена, будет создана с описанием: '{current_description or 'отсутствует'}'."
            )
            role = Role(name=role_name, description=current_description)
            session.add(role)
            try:
                await session.flush([role])
                self._logger.success(f"Роль '{role_name}' создана (сflushed) с ID: {role.id}")
            except Exception as e_flush_role:
                self._logger.error(f"Ошибка при flush для новой роли '{role_name}': {e_flush_role}", exc_info=True)
                return None
        return role

    async def register_permissions_from_modules(self, session: AsyncSession) -> int:
        if not self._services_provider_ref or not hasattr(self._services_provider_ref, "modules"):
            self._logger.error(
                "ModuleLoader не доступен через BotServicesProvider. Регистрация разрешений модулей невозможна."
            )
            return 0

        module_loader = self._services_provider_ref.modules
        declared_perms_manifests: List[ModulePermissionManifestSchema] = (
            module_loader.get_all_declared_permissions_from_active_modules()
        )

        if not declared_perms_manifests:
            self._logger.info("Не найдено разрешений, объявленных в активных модулях, для регистрации.")
            return 0

        self._logger.info(
            f"Найдено {len(declared_perms_manifests)} разрешений в манифестах модулей для регистрации/проверки..."
        )

        created_count = 0

        for perm_mft in declared_perms_manifests:
            existing_perm = await self._get_permission_by_name(session, perm_mft.name)
            if not existing_perm:
                new_perm_obj = await self.get_or_create_permission(session, perm_mft.name, perm_mft.description)
                if new_perm_obj:
                    created_count += 1
                else:
                    self._logger.error(f"Не удалось создать/получить разрешение модуля '{perm_mft.name}'.")
            else:
                if existing_perm.description != perm_mft.description:
                    self._logger.info(
                        f"Описание для существующего разрешения модуля '{perm_mft.name}' отличается. "
                        f"БД: '{existing_perm.description}', Манифест: '{perm_mft.description}'. Описание не обновляется."
                    )
                self._logger.trace(f"Разрешение модуля '{perm_mft.name}' уже существует в БД.")

        if created_count > 0:
            self._logger.success(
                f"{created_count} разрешений из модулей были созданы/обработаны (flush был в get_or_create_permission)."
            )

        return created_count

    async def ensure_default_entities_exist(self, session: AsyncSession) -> Tuple[int, int, int]:
        self._logger.info(
            "Проверка и создание стандартных сущностей RBAC (роли, разрешения ядра, разрешения модулей)..."
        )

        created_core_perms_count = 0
        created_module_perms_count = 0
        created_roles_count = 0
        initial_session_dirty = bool(session.new or session.dirty or session.deleted)

        self._logger.debug("Этап 1: Создание/получение стандартных разрешений ЯДРА.")
        core_permissions_to_add_objs: List[Permission] = []
        for perm_name, perm_description in DEFAULT_CORE_PERMISSIONS_DEFINITIONS.items():
            existing_perm = await self._get_permission_by_name(session, perm_name)
            if not existing_perm:
                new_perm = Permission(name=perm_name, description=perm_description)
                core_permissions_to_add_objs.append(new_perm)
                self._logger.info(f"Разрешение ядра '{perm_name}' подготовлено для добавления.")
                created_core_perms_count += 1

        if core_permissions_to_add_objs:
            session.add_all(core_permissions_to_add_objs)
            self._logger.info(f"{created_core_perms_count} разрешений ядра добавлены в сессию.")

        self._logger.debug("Этап 2: Регистрация разрешений из МАНИФЕСТОВ МОДУЛЕЙ.")
        module_perms_result = await self.register_permissions_from_modules(session)
        if module_perms_result == -1:
            self._logger.error(
                "Критическая ошибка при регистрации разрешений модулей. Дальнейшая инициализация RBAC прервана."
            )
            return 0, 0, -1
        created_module_perms_count = module_perms_result

        self._logger.debug("Этап 3: Создание/получение стандартных РОЛЕЙ.")
        roles_to_add_objs: List[Role] = []
        for role_name, role_description in DEFAULT_ROLES_DEFINITIONS.items():
            existing_role = await self._get_role_by_name(session, role_name)
            if not existing_role:
                new_role = Role(name=role_name, description=role_description)
                roles_to_add_objs.append(new_role)
                self._logger.info(f"Стандартная роль '{role_name}' подготовлена для добавления.")
                created_roles_count += 1

        if roles_to_add_objs:
            session.add_all(roles_to_add_objs)
            self._logger.info(f"{created_roles_count} стандартных ролей добавлены в сессию.")

        if core_permissions_to_add_objs or roles_to_add_objs or created_module_perms_count > 0:
            try:
                self._logger.debug("Этап 4: Выполняется общий flush для получения ID новых сущностей...")
                await session.flush()
                self._logger.debug("Общий Flush выполнен успешно.")
            except Exception as e_flush_all:
                self._logger.error(f"Ошибка при общем flush ролей/разрешений: {e_flush_all}", exc_info=True)
                await session.rollback()
                return 0, 0, 0

        self._logger.debug(f"Этап 5: Назначение разрешений ЯДРА стандартным ролям.")
        assigned_perms_summary: Dict[str, int] = {}

        all_permissions_in_db = await self.get_all_permissions(session)
        all_permissions_map_by_name = {p.name: p for p in all_permissions_in_db}

        role_core_permission_map = {
            DEFAULT_ROLE_SUPER_ADMIN: DEFAULT_PERMISSIONS_FOR_CORE_SUPER_ADMIN_ROLE,
            DEFAULT_ROLE_ADMIN: DEFAULT_PERMISSIONS_FOR_CORE_ADMIN_ROLE,
            DEFAULT_ROLE_MODERATOR: DEFAULT_PERMISSIONS_FOR_CORE_MODERATOR_ROLE,
            DEFAULT_ROLE_USER: DEFAULT_PERMISSIONS_FOR_CORE_USER_ROLE,
        }

        changes_in_role_perms_assignment = False
        for role_name_to_setup, core_perm_names_to_assign in role_core_permission_map.items():
            role_obj = await self._get_role_by_name(session, role_name_to_setup)
            if not role_obj or role_obj.id is None:
                self._logger.error(
                    f"Роль '{role_name_to_setup}' не найдена или не имеет ID после flush. Невозможно назначить разрешения."
                )
                continue

            current_role_assigned_count = 0
            self._logger.info(f"Назначение ядерных разрешений роли '{role_name_to_setup}' (ID: {role_obj.id})...")
            for perm_name in core_perm_names_to_assign:
                perm_obj_to_assign = all_permissions_map_by_name.get(perm_name)
                if not perm_obj_to_assign or perm_obj_to_assign.id is None:
                    self._logger.warning(
                        f"Ядерное разрешение '{perm_name}' для роли '{role_name_to_setup}' не найдено в общем списке или не имеет ID. Пропуск."
                    )
                    continue

                if await self._ensure_role_has_permission_link(session, role_obj.id, perm_obj_to_assign.id):
                    if await self.assign_permission_to_role(
                        session, role_obj, perm_obj_to_assign.name, auto_create_perm=False
                    ):
                        current_role_assigned_count += 1
                        changes_in_role_perms_assignment = True

            if current_role_assigned_count > 0:
                assigned_perms_summary[role_name_to_setup] = current_role_assigned_count
                self._logger.info(
                    f"{current_role_assigned_count} новых ядерных разрешений были подготовлены/назначены роли '{role_name_to_setup}'."
                )

        self._logger.debug(f"Этап 5.1: Автоматическое назначение базовых прав модулей роли '{DEFAULT_ROLE_USER}'.")
        role_user_obj = await self._get_role_by_name(session, DEFAULT_ROLE_USER)
        module_loader = self._services_provider_ref.modules if self._services_provider_ref else None

        auto_assigned_module_perms_count = 0
        if role_user_obj and role_user_obj.id and module_loader:
            # Проверяем только активные модули (их разрешения уже зарегистрированы)
            active_modules = []
            for module_name in module_loader.enabled_plugin_names:
                module_info = module_loader.available_modules.get(module_name)
                if module_info and not module_info.error:
                    active_modules.append(module_info)
            
            # Также добавляем системные модули
            for module_info in module_loader.available_modules.values():
                if module_info.is_system_module and not module_info.error:
                    if module_info not in active_modules:
                        active_modules.append(module_info)
            
            for module_info in active_modules:
                if (
                    module_info.manifest
                    and module_info.manifest.metadata
                    and module_info.manifest.metadata.assign_default_access_to_user_role
                ):

                    base_access_perm_name = f"{module_info.name}.access_user_features"
                    perm_obj = all_permissions_map_by_name.get(base_access_perm_name)
                    if perm_obj and perm_obj.id:
                        if await self._ensure_role_has_permission_link(session, role_user_obj.id, perm_obj.id):
                            if await self.assign_permission_to_role(
                                session, role_user_obj, perm_obj.name, auto_create_perm=False
                            ):
                                self._logger.info(
                                    f"Автоматически назначено разрешение '{perm_obj.name}' роли '{DEFAULT_ROLE_USER}'."
                                )
                                auto_assigned_module_perms_count += 1
                                changes_in_role_perms_assignment = True
                    else:
                        self._logger.warning(
                            f"Не найдено зарегистрированное разрешение '{base_access_perm_name}' для модуля '{module_info.name}', "
                            "хотя он помечен для авто-назначения роли User. Убедитесь, что модуль активен и разрешение объявлено в манифесте."
                        )
        if auto_assigned_module_perms_count > 0:
            if DEFAULT_ROLE_USER in assigned_perms_summary:
                assigned_perms_summary[DEFAULT_ROLE_USER] += auto_assigned_module_perms_count
            else:
                assigned_perms_summary[DEFAULT_ROLE_USER] = auto_assigned_module_perms_count

        final_session_dirty = bool(session.new or session.dirty or session.deleted)
        if final_session_dirty or (
            not initial_session_dirty
            and (
                created_roles_count
                or created_core_perms_count
                or created_module_perms_count > 0
                or any(assigned_perms_summary.values())
            )
        ):
            self._logger.debug("Этап 6: Попытка коммита всех изменений RBAC...")
            try:
                await session.commit()
                summary_log_parts = []
                if created_roles_count:
                    summary_log_parts.append(f"{created_roles_count} ролей создано")
                if created_core_perms_count:
                    summary_log_parts.append(f"{created_core_perms_count} разрешений ядра создано")
                if created_module_perms_count > 0:
                    summary_log_parts.append(
                        f"{created_module_perms_count} разрешений модулей создано/зарегистрировано"
                    )
                for role_name_sum, count_sum in assigned_perms_summary.items():
                    if count_sum > 0:
                        summary_log_parts.append(f"{count_sum} разрешений назначено {role_name_sum}")

                log_msg_commit = (
                    f"Стандартные RBAC сущности успешно созданы/обновлены и закоммичены: "
                    f"{'; '.join(summary_log_parts) or 'нет явных изменений для логирования после назначения прав.'}."
                )
                self._logger.success(log_msg_commit)
            except Exception as e:
                self._logger.error(f"Ошибка при коммите стандартных RBAC сущностей: {e}", exc_info=True)
                await session.rollback()
                return 0, 0, 0
        else:
            self._logger.info("Не было обнаружено фактических изменений в RBAC для коммита.")

        return created_roles_count, created_core_perms_count, created_module_perms_count

    async def _ensure_role_has_permission_link(self, session: AsyncSession, role_id: int, permission_id: int) -> bool:
        self._logger.trace(f"[ENSURE_LINK] Проверка связи для RoleID: {role_id}, PermID: {permission_id}")
        link_exists_stmt = (
            select(RolePermission.id)
            .where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
            .limit(1)
        )
        try:
            link_res = await session.execute(link_exists_stmt)
            scalar_result = link_res.scalar_one_or_none()
            if scalar_result is None:
                self._logger.trace(
                    f"[ENSURE_LINK] Связь для RoleID {role_id}, PermID {permission_id} НЕ найдена (нужно создать)."
                )
                return True
            else:
                self._logger.trace(
                    f"[ENSURE_LINK] Связь для RoleID {role_id}, PermID {permission_id} уже существует (ID: {scalar_result})."
                )
                return False
        except Exception as e_exec_link:
            self._logger.error(
                f"[ENSURE_LINK] Ошибка при проверке связи RolePermission для RoleID {role_id}, PermID {permission_id}: {e_exec_link}",
                exc_info=True,
            )
            return False

    async def assign_role_to_user(self, session: AsyncSession, user: User, role_name: str) -> bool:
        if not user or user.id is None:
            self._logger.error(f"Попытка назначить роль: Пользователь не валиден или не имеет ID (user: {user}).")
            return False

        role_obj = await self.get_or_create_role(session, role_name)
        if not role_obj or role_obj.id is None:
            self._logger.error(
                f"Не удалось получить или создать роль '{role_name}' (ID: {getattr(role_obj, 'id', 'N/A')}) для назначения пользователю {user.id}."
            )
            return False

        self._logger.debug(
            f"[ASSIGN_ROLE_TO_USER] Проверка связи для UserID: {user.id} (тип: {type(user.id)}), RoleID: {role_obj.id} (тип: {type(role_obj.id)})"
        )
        existing_link_stmt = (
            select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_id == role_obj.id).limit(1)
        )
        try:
            existing_link_res = await session.execute(existing_link_stmt)
            scalar_res_link = existing_link_res.scalar_one_or_none()
            self._logger.debug(
                f"[ASSIGN_ROLE_TO_USER] Результат scalar_one_or_none для UserID {user.id}, RoleID {role_obj.id}: {scalar_res_link} (тип: {type(scalar_res_link)})"
            )

            if scalar_res_link is not None:
                self._logger.debug(f"Роль '{role_name}' уже назначена пользователю ID: {user.id}.")
                return True

            new_user_role_link = UserRole(user_id=user.id, role_id=role_obj.id)
            session.add(new_user_role_link)
            self._logger.info(
                f"Роль '{role_name}' (RoleID: {role_obj.id}) добавлена пользователю UserID: {user.id} (ожидает commit)."
            )
            return True
        except Exception as e_assign:
            self._logger.error(
                f"Ошибка при назначении роли '{role_name}' пользователю {user.id}: {e_assign}", exc_info=True
            )
            return False

    async def remove_role_from_user(self, session: AsyncSession, user: User, role_name: str) -> bool:
        if not user or user.id is None:
            self._logger.error("Попытка снять роль с невалидного объекта пользователя (отсутствует ID).")
            return False

        role_to_remove = await self._get_role_by_name(session, role_name)
        if not role_to_remove or role_to_remove.id is None:
            self._logger.warning(
                f"Попытка снять несуществующую роль '{role_name}' или роль без ID с пользователя {user.id}."
            )
            return True

        try:
            stmt_delete = delete(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role_to_remove.id)
            result = await session.execute(stmt_delete)

            if result.rowcount > 0:
                self._logger.info(f"Роль '{role_name}' снята с пользователя {user.id} (ожидает commit).")
                return True
            else:
                self._logger.debug(f"Роль '{role_name}' не была назначена пользователю {user.id}. Снятие не требуется.")
                return True
        except Exception as e:
            self._logger.error(
                f"Ошибка при удалении связи UserRole для пользователя {user.id} и роли '{role_name}': {e}",
                exc_info=True,
            )
            return False

    def user_has_role(self, user: User, role_name: str) -> bool:
        if not user or not user.roles:
            return False
        return any(r.name.lower() == role_name.lower() for r in user.roles if r and r.name)

    async def user_has_role_async(self, session: AsyncSession, user_telegram_id: int, role_name: str) -> bool:
        stmt = select(User).options(selectinload(User.roles)).where(User.telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_db: Optional[User] = result.scalars().first()

        if not user_db:
            self._logger.debug(
                f"Пользователь с Telegram ID {user_telegram_id} не найден при проверке роли '{role_name}'."
            )
            return False
        return self.user_has_role(user_db, role_name)

    def get_user_role_names(self, user: User) -> Set[str]:
        if not user or not user.roles:
            return set()
        return {role.name for role in user.roles if role and role.name}

    async def get_user_roles_async(self, session: AsyncSession, user_telegram_id: int) -> List[Role]:
        stmt = select(User).options(selectinload(User.roles)).where(User.telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_db: Optional[User] = result.scalars().first()

        if not user_db:
            self._logger.debug(f"Пользователь с Telegram ID {user_telegram_id} не найден при запросе его ролей.")
            return []
        return list(user_db.roles) if user_db.roles else []

    async def get_all_roles(self, session: AsyncSession) -> List[Role]:
        stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        result = await session.execute(stmt)
        roles = list(result.scalars().all())
        self._logger.debug(f"Запрошен список всех ролей. Найдено: {len(roles)}.")
        return roles

    async def delete_role(self, session: AsyncSession, role_name_or_id: Union[str, int]) -> bool:
        self._logger.info(f"Попытка удаления роли: '{role_name_or_id}'...")
        role: Optional[Role] = None
        if isinstance(role_name_or_id, str):
            role = await self._get_role_by_name(session, role_name_or_id)
        elif isinstance(role_name_or_id, int):
            role = await session.get(Role, role_name_or_id)

        if not role:
            self._logger.warning(f"Роль '{role_name_or_id}' для удаления не найдена.")
            return False

        if role.name in DEFAULT_ROLES_DEFINITIONS:
            self._logger.error(f"Попытка удаления стандартной роли '{role.name}'. Операция запрещена.")
            return False

        user_role_count_stmt = select(sql_func.count(UserRole.id)).where(UserRole.role_id == role.id)
        user_role_count_res = await session.execute(user_role_count_stmt)
        user_count_with_role = user_role_count_res.scalar_one()

        if user_count_with_role > 0:
            self._logger.error(
                f"Невозможно удалить роль '{role.name}' (ID: {role.id}), так как она назначена {user_count_with_role} пользователю(ям). "
                "Сначала снимите эту роль со всех пользователей."
            )
            return False

        try:
            await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
            await session.delete(role)
            self._logger.warning(
                f"Роль '{role.name}' (ID: {role.id}) и ее связи с разрешениями помечены для удаления (ожидает commit)."
            )
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при попытке удаления роли '{role.name}': {e}", exc_info=True)
            return False

    async def _get_permission_by_name(self, session: AsyncSession, permission_name: str) -> Optional[Permission]:
        self._logger.trace(f"Получение разрешения по имени: '{permission_name}'")
        stmt = select(Permission).where(Permission.name == permission_name)
        result = await session.execute(stmt)
        perm = result.scalars().first()
        self._logger.trace(
            f"Разрешение '{permission_name}' найдено: {perm is not None} (ID: {getattr(perm, 'id', 'N/A')})"
        )
        return perm

    async def get_or_create_permission(
        self, session: AsyncSession, permission_name: str, description: Optional[str] = None
    ) -> Optional[Permission]:
        permission = await self._get_permission_by_name(session, permission_name)
        if not permission:
            perm_def_desc = DEFAULT_CORE_PERMISSIONS_DEFINITIONS.get(permission_name)
            current_description = description if description is not None else perm_def_desc

            if current_description is not None:
                self._logger.info(
                    f"Разрешение '{permission_name}' не найдено, будет создано с описанием: '{current_description}'."
                )
                permission = Permission(name=permission_name, description=current_description)
                session.add(permission)
                try:
                    await session.flush([permission])
                    self._logger.success(f"Разрешение '{permission_name}' создано (сflushed) с ID: {permission.id}")
                except Exception as e_flush_perm:
                    self._logger.error(
                        f"Ошибка при flush для нового разрешения '{permission_name}': {e_flush_perm}", exc_info=True
                    )
                    return None
            else:
                self._logger.warning(
                    f"Разрешение '{permission_name}' не найдено и описание не предоставлено. Не будет создано автоматически."
                )
                return None
        return permission

    async def assign_permission_to_role(
        self,
        session: AsyncSession,
        role: Role,
        permission_name: str,
        auto_create_perm: bool = True,
    ) -> bool:
        if not role or role.id is None:
            self._logger.error(f"Попытка назначить разрешение: Роль не валидна или не имеет ID (role: {role}).")
            return False

        permission_obj: Optional[Permission] = None
        if auto_create_perm:
            permission_obj = await self.get_or_create_permission(session, permission_name, description=None)
        else:
            permission_obj = await self._get_permission_by_name(session, permission_name)

        if not permission_obj or permission_obj.id is None:
            log_msg = (
                f"Не удалось получить"
                + (" или создать" if auto_create_perm else "")
                + f" разрешение '{permission_name}' (ID: {getattr(permission_obj, 'id', 'N/A')}) для назначения роли '{role.name}'."
            )
            self._logger.error(log_msg)
            return False

        self._logger.debug(
            f"[ASSIGN_PERM_TO_ROLE] Проверка/назначение связи для RoleID: {role.id}, PermID: {permission_obj.id}"
        )

        if await self._ensure_role_has_permission_link(session, role.id, permission_obj.id):
            try:
                new_role_perm_link = RolePermission(role_id=role.id, permission_id=permission_obj.id)
                session.add(new_role_perm_link)
                self._logger.info(
                    f"Разрешение '{permission_name}' (PermID: {permission_obj.id}) добавлено роли '{role.name}' (RoleID: {role.id}) (ожидает commit)."
                )
                return True
            except Exception as e_add_link:
                self._logger.error(
                    f"Ошибка при создании объекта RolePermission для RoleID {role.id}, PermID {permission_obj.id}: {e_add_link}",
                    exc_info=True,
                )
                return False
        else:
            link_exists_stmt = (
                select(RolePermission.id)
                .where(RolePermission.role_id == role.id, RolePermission.permission_id == permission_obj.id)
                .limit(1)
            )
            existing_link_res = await session.execute(link_exists_stmt)
            if existing_link_res.scalar_one_or_none() is not None:
                self._logger.trace(f"Разрешение '{permission_name}' уже назначено роли '{role.name}' (подтверждено).")
                return True
            else:
                self._logger.error(
                    f"Не удалось подтвердить или создать связь для разрешения '{permission_name}' и роли '{role.name}'. "
                    "Возможно, ошибка в _ensure_role_has_permission_link или параллельное изменение."
                )
                return False

    async def remove_permission_from_role(self, session: AsyncSession, role: Role, permission_name: str) -> bool:
        if not role or role.id is None:
            return False
        permission_to_remove = await self._get_permission_by_name(session, permission_name)
        if not permission_to_remove or permission_to_remove.id is None:
            self._logger.warning(f"Попытка снять несуществующее разрешение '{permission_name}' с роли '{role.name}'.")
            return True

        try:
            stmt_delete = delete(RolePermission).where(
                RolePermission.role_id == role.id, RolePermission.permission_id == permission_to_remove.id
            )
            result = await session.execute(stmt_delete)
            if result.rowcount > 0:
                self._logger.info(f"Разрешение '{permission_name}' снято с роли '{role.name}' (ожидает commit).")
                return True
            else:
                self._logger.debug(
                    f"Разрешение '{permission_name}' не было назначено роли '{role.name}'. Снятие не требуется."
                )
                return True
        except Exception as e_remove_perm:
            self._logger.error(
                f"Ошибка при снятии разрешения '{permission_name}' с роли '{role.name}': {e_remove_perm}", exc_info=True
            )
            return False

    async def user_has_permission(self, session: AsyncSession, user_telegram_id: int, permission_name: str) -> bool:
        # 1. Проверка на Владельца из .env (высший приоритет)
        if self._services_provider_ref and self._services_provider_ref.config:
            if user_telegram_id in self._services_provider_ref.config.core.super_admins:
                self._logger.trace(
                    f"Пользователь TG ID {user_telegram_id} является Владельцем из .env, разрешение '{permission_name}' предоставлено."
                )
                return True

        # Загружаем пользователя с его ролями и прямыми разрешениями
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),  # Роли и их разрешения
                selectinload(User.direct_permissions),  # Прямые разрешения пользователя
            )
            .where(User.telegram_id == user_telegram_id)
        )
        result = await session.execute(stmt)
        user_db: Optional[User] = result.scalars().first()

        if not user_db:
            self._logger.trace(
                f"Пользователь TG ID {user_telegram_id} не найден при проверке разрешения '{permission_name}'."
            )
            return False
        
        # 2. Проверка на роль SuperAdmin (неограниченные возможности)
        if user_db.roles:
            for role_obj in user_db.roles:
                if role_obj.name == DEFAULT_ROLE_SUPER_ADMIN:
                    self._logger.trace(
                        f"Пользователь TG ID {user_telegram_id} имеет роль 'SuperAdmin', разрешение '{permission_name}' предоставлено (неограниченные возможности)."
                    )
                    return True

        perm_name_lower = permission_name.lower()

        # 3. Проверка прямых разрешений пользователя
        if user_db.direct_permissions:
            for perm_obj in user_db.direct_permissions:
                if perm_obj.name.lower() == perm_name_lower:
                    self._logger.trace(
                        f"Пользователь TG ID {user_telegram_id} имеет прямое разрешение '{permission_name}'."
                    )
                    return True

        # 4. Проверка разрешений через роли
        if not user_db.roles:
            self._logger.trace(
                f"Пользователь TG ID {user_telegram_id} не имеет ролей при проверке разрешения '{permission_name}'."
            )
            # (Если нет прямых прав и нет ролей, то права нет)
            # return False # Это условие уже покрывается следующим return False
        else:  # Если есть роли, проверяем их
            for role_obj in user_db.roles:
                if role_obj.permissions:
                    for perm_obj in role_obj.permissions:
                        if perm_obj.name.lower() == perm_name_lower:
                            self._logger.trace(
                                f"Пользователь TG ID {user_telegram_id} имеет разрешение '{permission_name}' через роль '{role_obj.name}'."
                            )
                            return True

        self._logger.trace(
            f"Пользователь TG ID {user_telegram_id} НЕ имеет разрешения '{permission_name}' (ни прямого, ни через роли)."
        )
        return False

    async def get_all_permissions(self, session: AsyncSession) -> List[Permission]:
        stmt = select(Permission).order_by(Permission.name)
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())
        self._logger.debug(f"Запрошен список всех разрешений. Найдено: {len(permissions)}.")
        return permissions

    async def get_role_permissions(self, session: AsyncSession, role_name: str) -> List[Permission]:
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.name == role_name)
        result = await session.execute(stmt)
        role_with_perms: Optional[Role] = result.scalars().first()

        if not role_with_perms:
            self._logger.warning(f"Запрошены разрешения для несуществующей роли '{role_name}'.")
            return []

        return list(role_with_perms.permissions) if role_with_perms.permissions else []

    # --- Новые методы для управления прямыми разрешениями пользователя ---

    async def assign_direct_permission_to_user(
        self,
        session: AsyncSession,
        user: User,
        permission_name: str,
        auto_create_perm: bool = True,  # Обычно разрешение уже должно существовать
    ) -> bool:
        if not user or user.id is None:
            self._logger.error(
                f"Попытка назначить прямое разрешение: Пользователь не валиден или не имеет ID (user: {user})."
            )
            return False

        permission_obj: Optional[Permission]
        if auto_create_perm:  # Это больше для тестов или специфических случаев
            permission_obj = await self.get_or_create_permission(session, permission_name)
        else:
            permission_obj = await self._get_permission_by_name(session, permission_name)

        if not permission_obj or permission_obj.id is None:
            log_msg = (
                f"Не удалось получить"
                + (" или создать" if auto_create_perm else "")
                + f" разрешение '{permission_name}' для прямого назначения пользователю {user.telegram_id}."
            )
            self._logger.error(log_msg)
            return False

        # Проверяем, нет ли уже такой связи
        existing_link_stmt = (
            select(UserPermission.id)
            .where(UserPermission.user_id == user.id, UserPermission.permission_id == permission_obj.id)
            .limit(1)
        )
        existing_link_res = await session.execute(existing_link_stmt)
        if existing_link_res.scalar_one_or_none() is not None:
            self._logger.debug(f"Прямое разрешение '{permission_name}' уже назначено пользователю {user.telegram_id}.")
            return True  # Считаем успешным, если уже есть

        # Если мы управляем через user.direct_permissions.append()
        # user.direct_permissions.append(permission_obj)
        # session.add(user)
        # ИЛИ, если управляем связующей таблицей напрямую:
        new_user_perm_link = UserPermission(user_id=user.id, permission_id=permission_obj.id)
        session.add(new_user_perm_link)

        self._logger.info(
            f"Прямое разрешение '{permission_name}' добавлено пользователю {user.telegram_id} (ожидает commit)."
        )
        return True

    async def remove_direct_permission_from_user(self, session: AsyncSession, user: User, permission_name: str) -> bool:
        if not user or user.id is None:
            self._logger.error("Попытка снять прямое разрешение с невалидного пользователя.")
            return False

        permission_to_remove = await self._get_permission_by_name(session, permission_name)
        if not permission_to_remove or permission_to_remove.id is None:
            self._logger.warning(
                f"Попытка снять несуществующее прямое разрешение '{permission_name}' с пользователя {user.telegram_id}."
            )
            return True  # Считаем успешным, так как его и не было

        # Если мы управляем через user.direct_permissions.remove()
        # if permission_to_remove in user.direct_permissions: # Нужна загрузка user.direct_permissions
        #     user.direct_permissions.remove(permission_to_remove)
        #     session.add(user)
        #     self._logger.info(f"Прямое разрешение '{permission_name}' снято с пользователя {user.telegram_id} (ожидает commit).")
        #     return True
        # else:
        #     self._logger.debug(f"Прямое разрешение '{permission_name}' не было назначено пользователю {user.telegram_id}. Снятие не требуется.")
        #     return True
        # ИЛИ, если управляем связующей таблицей напрямую:
        stmt_delete = delete(UserPermission).where(
            UserPermission.user_id == user.id, UserPermission.permission_id == permission_to_remove.id
        )
        result = await session.execute(stmt_delete)
        if result.rowcount > 0:
            self._logger.info(
                f"Прямое разрешение '{permission_name}' снято с пользователя {user.telegram_id} (ожидает commit)."
            )
            return True
        else:
            self._logger.debug(
                f"Прямое разрешение '{permission_name}' не было назначено пользователю {user.telegram_id}. Снятие не требуется."
            )
            return True

    async def get_user_direct_permissions(self, session: AsyncSession, user_id: int) -> List[Permission]:
        """Получает список прямых разрешений для пользователя (по его DB ID)."""
        user_db = await session.get(User, user_id, options=[selectinload(User.direct_permissions)])
        if not user_db:
            self._logger.warning(f"Запрошены прямые разрешения для несуществующего пользователя (DB ID: {user_id}).")
            return []
        return list(user_db.direct_permissions) if user_db.direct_permissions else []
