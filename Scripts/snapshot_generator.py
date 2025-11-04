import os
from pathlib import Path

# --- Настройки ---
OUTPUT_FILENAME = "project_snapshot.txt"
EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".git", ".idea", ".vscode",
    "build", "dist", "*.egg-info", "node_modules",
    "Data/Cache", "Data/LogsBot", "Data/Temp", "Data/Uploads", # Из твоей структуры Data/
    "logs" # Общая папка логов, если есть
    "modules", # Папка с модулями, если есть
}
EXCLUDE_FILES = {
    OUTPUT_FILENAME,  # Не включать сам файл вывода
    ".DS_Store",
    "*.pyc",
    "*.swp",
    "*.swo",
    # Добавь сюда файлы, которые не нужно включать, например, большие бинарники
    "project_snapshot.txt"
    "TEST.md"
}
EXCLUDE_EXTENSIONS = {
    ".sqlite", ".db", ".db-journal", # Файлы баз данных (могут быть большими)
    ".log", # Уже покрывается EXCLUDE_DIRS, но на всякий случай
    # Добавь расширения, которые не нужно включать
    # ".zip", ".tar.gz"
}
MAX_FILE_SIZE_MB = 2  # Максимальный размер файла для включения его содержимого (в МБ)
MAX_TOTAL_OUTPUT_SIZE_MB = 50 # Примерный лимит на общий размер выходного файла (чтобы не был гигантским)

# Кодировка для чтения файлов
FILE_ENCODING = "utf-8"
# --- Конец настроек ---

def should_exclude_dir(dir_name, exclude_set):
    return dir_name in exclude_set

def should_exclude_file(file_name, file_path, exclude_files_set, exclude_ext_set):
    if file_name in exclude_files_set:
        return True
    if file_path.suffix.lower() in exclude_ext_set:
        return True
    # Можно добавить проверку по маске, если нужно
    # import fnmatch
    # for pattern in exclude_files_set:
    #     if fnmatch.fnmatch(file_name, pattern):
    #         return True
    return False

def get_dir_tree(start_path, indent_char="    ", max_depth=10):
    tree_lines = []
    # Ограничение на глубину рекурсии для предотвращения зацикливания или слишком большого дерева
    if max_depth < 0:
        return ["... (Max depth reached)"]

    try:
        items = sorted(list(start_path.iterdir()), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return [f"... (Permission denied: {start_path})"]
    except FileNotFoundError:
        return [f"... (Not found: {start_path})"]


    for i, item in enumerate(items):
        is_last = i == (len(items) - 1)
        prefix = indent_char + ("└── " if is_last else "├── ")

        if item.is_dir():
            if should_exclude_dir(item.name, EXCLUDE_DIRS):
                tree_lines.append(f"{prefix}{item.name}/ [EXCLUDED_DIR]")
                continue
            tree_lines.append(f"{prefix}{item.name}/")
            # Рекурсивно добавляем поддиректорию
            # Уменьшаем max_depth для каждой итерации
            sub_indent = indent_char + ("    " if is_last else "│   ")
            tree_lines.extend([sub_indent + line for line in get_dir_tree(item, indent_char, max_depth -1)])
        else:
            if should_exclude_file(item.name, item, EXCLUDE_FILES, EXCLUDE_EXTENSIONS):
                tree_lines.append(f"{prefix}{item.name} [EXCLUDED_FILE]")
                continue
            tree_lines.append(f"{prefix}{item.name}")
            
    return tree_lines


def main():
    project_root = Path(".") # Запускать из корня проекта
    snapshot_content = []
    current_total_size = 0
    max_total_bytes = MAX_TOTAL_OUTPUT_SIZE_MB * 1024 * 1024

    # 1. Структура проекта
    snapshot_content.append("=" * 30 + " PROJECT STRUCTURE " + "=" * 30)
    snapshot_content.append(f"{project_root.resolve().name}/")
    tree_str = "\n".join(get_dir_tree(project_root))
    snapshot_content.append(tree_str)
    snapshot_content.append("\n" + "=" * 70 + "\n")
    current_total_size += len(tree_str.encode(FILE_ENCODING, errors='ignore'))


    # 2. Содержимое файлов
    for item_path in project_root.rglob("*"): # Рекурсивный обход всех файлов и папок
        if current_total_size > max_total_bytes:
            snapshot_content.append("\n... (Total output size limit reached, stopping file content inclusion) ...\n")
            print(f"Warning: Total output size limit ({MAX_TOTAL_OUTPUT_SIZE_MB}MB) reached. Some file contents might be omitted.")
            break

        # Проверка на исключение директорий на уровне rglob
        is_in_excluded_dir = False
        for part in item_path.relative_to(project_root).parts:
            if part in EXCLUDE_DIRS:
                is_in_excluded_dir = True
                break
        if is_in_excluded_dir and item_path.is_dir(): # Если сама папка исключена, пропускаем ее rglob
            continue
        if item_path.is_dir(): # Если это директория, пропускаем (уже обработали в дереве)
            if item_path.name in EXCLUDE_DIRS: # Доп. проверка
                 continue
            continue


        relative_path_str = str(item_path.relative_to(project_root))

        # Проверяем, не находится ли файл внутри исключенной директории
        # Это нужно, т.к. rglob может дать файлы из поддиректорий, которые мы хотим исключить целиком
        parent_excluded = False
        for parent in item_path.parents:
            if parent.name in EXCLUDE_DIRS:
                parent_excluded = True
                break
        if parent_excluded:
            # print(f"Skipping (parent excluded): {relative_path_str}")
            continue
            
        if item_path.name in EXCLUDE_DIRS: # Если сам файл - это имя исключенной директории (маловероятно, но для полноты)
            # print(f"Skipping (matches excluded dir name): {relative_path_str}")
            continue

        if should_exclude_file(item_path.name, item_path, EXCLUDE_FILES, EXCLUDE_EXTENSIONS):
            # print(f"Skipping (excluded file/ext): {relative_path_str}")
            continue
        
        snapshot_content.append("-" * 30 + f" FILE: {relative_path_str} " + "-" * 30)
        try:
            file_size = item_path.stat().st_size
            if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                snapshot_content.append(f"[CONTENT OMITTED - File size ({file_size / (1024*1024):.2f} MB) > {MAX_FILE_SIZE_MB} MB]\n")
                print(f"Skipping content of large file: {relative_path_str}")
            else:
                with open(item_path, "r", encoding=FILE_ENCODING, errors="ignore") as f:
                    content = f.read()
                snapshot_content.append(content + "\n")
                current_total_size += len(content.encode(FILE_ENCODING, errors='ignore'))

        except Exception as e:
            snapshot_content.append(f"[ERROR READING FILE: {e}]\n")
            print(f"Error reading file {relative_path_str}: {e}")
        snapshot_content.append("\n" + "=" * 70 + "\n")


    # 3. Запись в файл
    try:
        with open(OUTPUT_FILENAME, "w", encoding=FILE_ENCODING) as f:
            f.write("\n".join(snapshot_content))
        print(f"Project snapshot saved to: {OUTPUT_FILENAME}")
        print(f"Approximate total output size: {current_total_size / (1024*1024):.2f} MB")

    except Exception as e:
        print(f"Error writing snapshot file: {e}")

if __name__ == "__main__":
    main()