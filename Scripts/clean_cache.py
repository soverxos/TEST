import os
import shutil
from pathlib import Path

def clean_pycache(start_path: str = "."):
    """Удаляет все директории __pycache__ и .pyc файлы."""
    
    counter = {"dirs": 0, "files": 0}
    
    for root, dirs, files in os.walk(start_path):
        # Пропускаем директорию .venv если она существует
        if ".venv" in root:
            continue
            
        # Удаляем __pycache__ директории
        if "__pycache__" in dirs:
            cache_path = Path(root) / "__pycache__"
            shutil.rmtree(cache_path)
            print(f"🗑️  Удалена директория: {cache_path}")
            counter["dirs"] += 1
            
        # Удаляем .pyc файлы
        for file in files:
            if file.endswith(".pyc"):
                file_path = Path(root) / file
                os.remove(file_path)
                print(f"🗑️  Удален файл: {file_path}")
                counter["files"] += 1
    
    return counter

if __name__ == "__main__":
    # Изменяем эту строку, чтобы получить корневую директорию проекта
    project_root = str(Path(__file__).parent.parent)
    print(f"🔍 Начинаем поиск в директории: {project_root}")
    results = clean_pycache(project_root)
    
    print("\n📊 Статистика очистки:")
    print(f"- Удалено директорий __pycache__: {results['dirs']}")
    print(f"- Удалено .pyc файлов: {results['files']}")