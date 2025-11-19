# Dockerfile для SwiftDevBot
FROM python:3.12-slim

# Метаданные
LABEL maintainer="SwiftDevBot Team"
LABEL description="SwiftDevBot - Модульный Telegram Bot Framework"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Создание необходимых директорий
RUN mkdir -p Data/Config Data/Database_files Data/Logs Data/Security

# Установка прав на исполняемые файлы
RUN chmod +x sdb sdb.py run_bot.py sdb_setup.py

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV SDB_CLI_MODE=false
ENV SDB_VERBOSE=false

# Объемы для данных
VOLUME ["/app/Data"]

# Порт для веб-панели (если используется)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/api/health', timeout=5)" || exit 1

# Точка входа
ENTRYPOINT ["python3", "run_bot.py"]

