# 🚀 Руководство по развертыванию SwiftDevBot

## Содержание

1. [Docker развертывание](#docker-развертывание)
2. [Ручное развертывание](#ручное-развертывание)
3. [Production настройки](#production-настройки)
4. [Мониторинг](#мониторинг)

---

## 🐳 Docker развертывание

### Быстрый старт

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/soverxos/SwiftDevBot-Project.git
cd SwiftDevBot-Project
```

2. **Создайте файл `.env`:**
```bash
cp env.example .env
# Отредактируйте .env и добавьте BOT_TOKEN
```

3. **Запустите через Docker Compose:**
```bash
docker-compose up -d
```

### Структура сервисов

Docker Compose включает:
- **bot** - основной процесс бота
- **web** - веб-панель (порт 8000)
- **db** - PostgreSQL база данных
- **redis** - Redis кэш
- **prometheus** - метрики (порт 9090)
- **grafana** - дашборды (порт 3000)

### Команды Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка всех сервисов
docker-compose down

# Пересборка образов
docker-compose build --no-cache

# Перезапуск конкретного сервиса
docker-compose restart bot
```

### Переменные окружения

Основные переменные для Docker:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here
SDB_CORE_SUPER_ADMINS="123456789"

# База данных (автоматически настроена в docker-compose)
SDB_DB_TYPE=postgresql
SDB_DB_PG_DSN=postgresql+psycopg://sdb_user:sdb_password@sdb_db:5432/swiftdevbot

# Кэш (автоматически настроен в docker-compose)
SDB_CACHE_TYPE=redis
SDB_CACHE_REDIS_URL=redis://sdb_redis:6379/0

# Логирование
SDB_CORE_LOG_LEVEL=INFO
SDB_VERBOSE=false
```

---

## 🔧 Ручное развертывание

### Требования

- Python 3.12+
- PostgreSQL 14+ или MySQL 8+ (опционально, можно использовать SQLite)
- Redis 6+ (опционально)

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/soverxos/SwiftDevBot-Project.git
cd SwiftDevBot-Project
```

2. **Создайте виртуальное окружение:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Настройте проект:**
```bash
python3 sdb_setup.py
```

5. **Инициализируйте базу данных:**
```bash
python3 sdb.py db init
python3 sdb.py db migrate
```

6. **Запустите бота:**
```bash
python3 sdb.py run
```

### Systemd сервис (Linux)

Создайте файл `/etc/systemd/system/swiftdevbot.service`:

```ini
[Unit]
Description=SwiftDevBot Telegram Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/SwiftDevBot-Project
Environment="PATH=/path/to/SwiftDevBot-Project/.venv/bin"
ExecStart=/path/to/SwiftDevBot-Project/.venv/bin/python3 run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация сервиса:
```bash
sudo systemctl daemon-reload
sudo systemctl enable swiftdevbot
sudo systemctl start swiftdevbot
sudo systemctl status swiftdevbot
```

---

## 🏭 Production настройки

### Безопасность

1. **Используйте сильные пароли** для БД и Redis
2. **Ограничьте доступ** к портам (только необходимые)
3. **Используйте HTTPS** для веб-панели (через reverse proxy)
4. **Регулярно обновляйте** зависимости

### Производительность

1. **Используйте PostgreSQL** вместо SQLite для production
2. **Настройте Redis** для кэширования
3. **Оптимизируйте запросы** к БД
4. **Используйте connection pooling**

### Мониторинг

1. **Настройте Prometheus** для сбора метрик
2. **Создайте Grafana дашборды**
3. **Настройте алерты** на критические метрики
4. **Мониторьте логи** через ELK или аналоги

### Резервное копирование

```bash
# Создание бэкапа
python3 sdb.py backup create

# Автоматическое бэкапирование (cron)
0 2 * * * cd /path/to/SwiftDevBot-Project && python3 sdb.py backup create
```

---

## 📊 Мониторинг

### Prometheus метрики

Метрики доступны по адресу: `http://localhost:8000/metrics`

Основные метрики:
- `sdb_events_total` - общее количество событий
- `sdb_events_success_total` - успешные события
- `sdb_events_error_total` - ошибки
- `sdb_event_duration_seconds` - время обработки

### Health Checks

- Краткая проверка: `GET /api/health`
- Детальная проверка: `GET /api/health/detailed`

### Grafana дашборды

После запуска Docker Compose:
1. Откройте `http://localhost:3000`
2. Логин: `admin`, Пароль: `admin`
3. Добавьте Prometheus как источник данных: `http://prometheus:9090`
4. Импортируйте готовые дашборды (если есть)

---

## 🔍 Troubleshooting

### Проблемы с Docker

```bash
# Проверка логов
docker-compose logs bot

# Проверка статуса контейнеров
docker-compose ps

# Перезапуск всех сервисов
docker-compose restart
```

### Проблемы с базой данных

```bash
# Проверка подключения к БД
python3 sdb.py db status

# Применение миграций
python3 sdb.py db migrate

# Откат миграций
python3 sdb.py db downgrade
```

### Проблемы с модулями

```bash
# Список модулей
python3 sdb.py module list

# Перезагрузка модуля
python3 sdb.py module reload module_name

# Проверка логов модуля
python3 sdb.py monitor logs --module module_name
```

---

## 📚 Дополнительные ресурсы

- [Документация API](Docs/API.md)
- [Руководство по модулям](Docs/MODULES.md)
- [Безопасность](Docs/SECURITY.md)
- [Мониторинг](Docs/MONITORING.md)

