# core/logging_manager.py
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, TYPE_CHECKING

from loguru import logger as global_logger 
import parsedatetime as pdt 
from apscheduler.schedulers.asyncio import AsyncIOScheduler 
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from Systems.core.app_settings import AppSettings

class LoggingManager:
    def __init__(self, app_settings: 'AppSettings'):
        self._settings = app_settings.core
        self._app_settings_ref = app_settings 
        self._current_log_handler_id: Optional[int] = None
        self._current_log_file_path: Optional[Path] = None
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._is_initialized = False

        self._logger = global_logger.bind(service="LoggingManager")
        self._logger.info("LoggingManager инициализирован.")

    def _get_log_file_path_for_current_hour(self) -> Path:
        """Генерирует путь к лог-файлу на основе текущего времени."""
        now = datetime.now(timezone.utc)
        year_str = now.strftime("%Y")
        month_num_str = now.strftime("%m")
        month_name_str = now.strftime("%B") # Имя месяца зависит от локали системы
        day_str = now.strftime("%d")
        hour_str = now.strftime("%H")

        base_logs_dir = self._app_settings_ref.core.project_data_path / self._settings.log_structured_dir
        
        target_dir = base_logs_dir / year_str / f"{month_num_str}-{month_name_str}" / day_str
        target_dir.mkdir(parents=True, exist_ok=True)
        
        return target_dir / f"{hour_str}_sdb.log"

    def _setup_loguru_file_sink(self) -> None: 
        """Настраивает (или перенастраивает) файловый sink для Loguru."""
        if self._current_log_handler_id is not None:
            try:
                global_logger.remove(self._current_log_handler_id)
                self._logger.trace(f"Предыдущий файловый хендлер (ID: {self._current_log_handler_id}) удален.")
            except ValueError:
                self._logger.warning(f"Не удалось удалить предыдущий файловый хендлер ID: {self._current_log_handler_id} (возможно, уже удален).")
            self._current_log_handler_id = None
            self._current_log_file_path = None

        if not self._settings.log_to_file:
            self._logger.info("Запись логов в файл отключена в настройках.")
            return

        new_log_file_path = self._get_log_file_path_for_current_hour()
        
        # --- ЖЕСТКО УСТАНАВЛИВАЕМ УРОВЕНЬ ДЛЯ ФАЙЛОВОГО ЛОГА ---
        log_level_for_file = "DEBUG"  # Используем DEBUG для файлов по умолчанию
        # Если нужен TRACE, измени здесь:
        # log_level_for_file = "TRACE" 
        # ---------------------------------------------------------
        
        try:
            handler_id = global_logger.add(
                sink=str(new_log_file_path),
                level=log_level_for_file, 
                rotation=self._settings.log_rotation_size, 
                compression="zip",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
                encoding="utf-8",
                enqueue=True,
                backtrace=True,
                diagnose=True 
            )
            self._current_log_handler_id = handler_id
            self._current_log_file_path = new_log_file_path
            self._logger.success(f"Файловый логгер настроен. Уровень: {log_level_for_file}. Файл: {new_log_file_path}")
        except Exception as e:
            self._logger.error(f"Ошибка при настройке файлового логгера для '{new_log_file_path}': {e}", exc_info=True)
            self._current_log_handler_id = None
            self._current_log_file_path = None

    async def _hourly_log_rotation_check(self) -> None:
        """Проверяет, нужно ли ротировать лог-файл (начался новый час)."""
        self._logger.trace("Выполняется ежечасная проверка ротации логов...")
        if not self._is_initialized or not self._settings.log_to_file:
            self._logger.trace("Проверка ротации пропущена: менеджер не инициализирован или логирование в файл отключено.")
            return

        expected_log_file = self._get_log_file_path_for_current_hour()
        if self._current_log_file_path != expected_log_file:
            self._logger.info(f"Начался новый час. Перенастройка файлового логгера на: {expected_log_file}")
            self._setup_loguru_file_sink() 
        else:
            self._logger.trace(f"Ротация лог-файла не требуется, текущий файл: {self._current_log_file_path}")

    async def _cleanup_old_logs(self) -> None:
        """Удаляет старые директории логов на основе log_retention_period_structured."""
        self._logger.info("Запуск задачи очистки старых логов...")
        if not self._settings.log_to_file:
            self._logger.info("Очистка старых логов пропущена: логирование в файл отключено.")
            return

        retention_str = self._settings.log_retention_period_structured
        cal = pdt.Calendar()
        
        now_dt = datetime.now(timezone.utc)
        past_target_dt, parse_status = cal.parseDT(f"{retention_str} ago", sourceTime=now_dt) # type: ignore
        
        if parse_status == 0 or not past_target_dt:
            self._logger.error(f"Не удалось распарсить период хранения логов: '{retention_str}'. Очистка отменена.")
            return
        
        cutoff_date = past_target_dt 
        self._logger.info(f"Очистка логов старше {cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')} (период: '{retention_str}').")

        structured_logs_root = self._app_settings_ref.core.project_data_path / self._settings.log_structured_dir
        if not structured_logs_root.is_dir():
            return

        deleted_dirs_count = 0
        for year_dir in structured_logs_root.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                if int(year_dir.name) < cutoff_date.year:
                    try:
                        shutil.rmtree(year_dir)
                        self._logger.info(f"Удалена директория старых логов (год): {year_dir}")
                        deleted_dirs_count += 1
                    except Exception as e_rm_year:
                        self._logger.error(f"Ошибка удаления директории логов '{year_dir}': {e_rm_year}")
                    continue 

                if int(year_dir.name) == cutoff_date.year:
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and "-" in month_dir.name:
                            try:
                                month_num_str = month_dir.name.split("-")[0]
                                if month_num_str.isdigit() and int(month_num_str) < cutoff_date.month:
                                    shutil.rmtree(month_dir)
                                    self._logger.info(f"Удалена директория старых логов (месяц): {month_dir}")
                                    deleted_dirs_count +=1
                                    continue
                                
                                if int(month_num_str) == cutoff_date.month:
                                    for day_dir in month_dir.iterdir():
                                        if day_dir.is_dir() and day_dir.name.isdigit():
                                            if int(day_dir.name) < cutoff_date.day:
                                                shutil.rmtree(day_dir)
                                                self._logger.info(f"Удалена директория старых логов (день): {day_dir}")
                                                deleted_dirs_count += 1
                            except Exception as e_rm_month_day:
                                self._logger.error(f"Ошибка удаления директории логов '{month_dir}' или ее поддиректории: {e_rm_month_day}")
        if deleted_dirs_count > 0:
            self._logger.success(f"Очистка старых логов завершена. Удалено директорий: {deleted_dirs_count}.")
        else:
            self._logger.info("Очистка старых логов завершена. Не найдено директорий для удаления.")


    async def initialize_logging(self) -> None: 
        """Инициализирует систему логирования, включая файловый sink и задачи по расписанию."""
        if self._is_initialized:
            self._logger.info("LoggingManager уже инициализирован.")
            return

        self._logger.info("Начало инициализации LoggingManager...")
        
        self._setup_loguru_file_sink() 
        
        self._scheduler = AsyncIOScheduler(timezone=str(timezone.utc))
        self._scheduler.add_job(self._hourly_log_rotation_check, CronTrigger(minute=0)) 
        self._logger.info("Задача _hourly_log_rotation_check добавлена в планировщик (ежечасно).")
        self._scheduler.add_job(self._cleanup_old_logs, CronTrigger(hour=3, minute=30)) 
        self._logger.info("Задача _cleanup_old_logs добавлена в планировщик (ежедневно в 03:30 UTC).")
        
        try:
            self._scheduler.start()
            self._logger.success("Планировщик задач LoggingManager успешно запущен.")
        except Exception as e_scheduler_start:
            self._logger.error(f"Не удалось запустить планировщик задач LoggingManager: {e_scheduler_start}", exc_info=True)
            self._scheduler = None 

        self._is_initialized = True
        self._logger.info("LoggingManager успешно инициализирован.")

    async def shutdown_logging(self) -> None:
        """Останавливает планировщик и корректно завершает работу."""
        self._logger.info("Начало процедуры остановки LoggingManager...")
        if self._scheduler and self._scheduler.running:
            try:
                self._scheduler.shutdown(wait=False) 
                self._logger.info("Планировщик задач LoggingManager остановлен.")
            except Exception as e_scheduler_shutdown:
                self._logger.error(f"Ошибка при остановке планировщика LoggingManager: {e_scheduler_shutdown}", exc_info=True)
        
        if self._current_log_handler_id is not None:
            try:
                global_logger.remove(self._current_log_handler_id)
                self._logger.info(f"Файловый хендлер (ID: {self._current_log_handler_id}) удален при остановке.")
            except ValueError:
                pass 
        
        self._is_initialized = False
        self._logger.info("LoggingManager остановлен.")