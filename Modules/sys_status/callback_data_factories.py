# Фабрики CallbackData для модуля sys_status

from aiogram.filters.callback_data import CallbackData

# Префикс для колбэков этого модуля, чтобы избежать конфликтов
SYS_STATUS_PREFIX = "sysst"

class SysStatusCallback(CallbackData, prefix=SYS_STATUS_PREFIX):
    """CallbackData для действий в модуле Статус Системы."""
    action: str # Например, "refresh"