"""
Конфигурация pytest для тестов SwiftDevBot
"""

import pytest
import asyncio
from pathlib import Path
import sys
import os

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Systems"))

# Устанавливаем переменные окружения для тестов
os.environ.setdefault("SDB_CLI_MODE", "true")
os.environ.setdefault("SDB_VERBOSE", "false")
os.environ.setdefault("SDB_ALLOW_MISSING_BOT_TOKEN", "true")


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir(tmp_path):
    """Создает временную директорию для тестовых данных"""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    (test_dir / "Config").mkdir()
    (test_dir / "Database_files").mkdir()
    (test_dir / "Logs").mkdir()
    return test_dir

