# SwiftDevBot CLI Reference

Полная документация по командам `sdb.py`. Используй эту страницу, чтобы быстро найти нужный подкомандный набор, узнать описание задач и посмотреть примеры вызовов. Каждый блок содержит назначение группы, ключевые подкоманды и примеры параметров.

## Содержание

1. [run/start/stop/status/restart](#runstartstopstatusrestart)
2. [config](#config)
3. [db](#db)
4. [module](#module)
5. [user](#user)
6. [backup](#backup)
7. [system](#system)
8. [bot](#bot)
9. [monitor](#monitor)
10. [utils](#utils)
11. [security](#security)
12. [notifications](#notifications)
13. [dev](#dev)
14. [api](#api)
15. [cache](#cache)
16. [tasks](#tasks)
17. [web](#web)

---

## `run` / `start` / `stop` / `status` / `restart`

- **Назначение**: управление жизненным циклом процесса бота.
- `run` (alias `start`): запускает основной процесс, прогружает модули, подключает middleware, слушает Telegram. При запуске логирует статистику (PID, uptime, memory).
- `stop`: завершает процесс по PID, очищает lock-файл.
- `status`: показывает текущий PID, uptime, memory, CPU, основные сервисы.
- `restart`: комбинирует `stop` + `run`.

Пример:
```bash
python3 sdb.py stop
python3 sdb.py run --verbose
python3 sdb.py status
```

---

## `config`

- **Цель**: настраивать `.env` и `core_settings.yaml` через CLI (инициализация, чтение, запись).
- `config init` — интерактивный мастер, задаёт токен, БД, супер-админов, генерирует `.env` и `project_data/Config/core_settings.yaml`.
- `config get [key]` — печатает конфиг / конкретный ключ. `--show-defaults` покажет значения по умолчанию.
- `config set key value` — обновляет ключ в `.env` или core_settings (`telegram.token`, `db.pg_dsn` и др.).
- Подгруппы:
  - `config storage set [memory|redis]` — переключает FSM cache backend; требует `--redis-url`.
  - `config storage status` — выводит текущий cache тип.
  - `config db` — управление конкретными настройками БД.
  - `config ...` содержит `confirm_action` вспомогательные команды.

Примеры:
```bash
python3 sdb.py config set core.log_level DEBUG
python3 sdb.py config storage set redis --redis-url redis://localhost:6379/0
```

---

## `db`

- **Назначение**: Alembic-миграции и состояние БД.
- `db init` — создаёт каталоги миграций и `alembic.ini`.
- `db migrate` — генерирует новую миграцию на основе моделей `Systems/core`.
- `db upgrade <revision>` — применяет миграцию. По умолчанию `head`.
- `db downgrade <revision>` — откатывает.
- `db stamp <revision>` — помечает версию без выполнения.
- `db history` / `db current`.

Пример:
```bash
python3 sdb.py db upgrade head
python3 sdb.py db history
```

---

## `module`

- **Работа с модулями** (плагины):
  - `module list` — список всех доступных модулей, их статусы (enabled/disabled/loaded).
  - `module enable NAME` / `disable NAME` — управляет `enabled_modules.json`.
  - `module reload NAME` — перезагружает модуль через полный рестарт процесса бота (не использует importlib.reload из-за риска утечек памяти при работающем asyncio event loop).
  - `module create NAME` — шаблон (demo/universal) с опциями `--enable`, `--with-rbac`, `--with-db`.
  - `module install` / `uninstall` (если реализовано) — добавление/удаление.
  - `module visibility NAME [--public/--private/--show]` — управление видимостью модуля для обычных пользователей.

Специальные команды:
```bash
python3 sdb.py module create analytics --with-rbac
python3 sdb.py module enable ai_chat
python3 sdb.py module visibility my_module --public  # Сделать видимым всем
python3 sdb.py module visibility my_module --show    # Показать текущую настройку
```

---

## `user`

- **Управление пользователями и ролями**:
  - `user list` — список пользователей с ролями (использует DBUser).
  - `user block <id>` / `unblock <id>` — блокирует пользователя в Telegram.
  - `user role add/remove <id> <role>` — назначение ролей.
  - `user reset-password` (если есть) или `user status`.

Пример:
```bash
python3 sdb.py user block 123456
python3 sdb.py user role add 123456 admin
```

---

## `backup`

- **Бэкапы и восстановление**:
  - `backup create` — сохраняет текущее состояние таблиц/кэша/логов.
  - `backup list` — доступные файлы.
  - `backup restore <name>` — восстанавливает snapshot.

Пример:
```bash
python3 sdb.py backup create --description "Перед релизом 0.1.0"
```

---

## `system`

- **Системные команды**:
  - `system info` — выводит состояние ядра (cache, modules, watchdog).
  - `system health` — проверяет зависимости (DB, cache).
  - `system logs` / `system stats`.

Пример:
```bash
python3 sdb.py system info
```

---

## `bot`

- **Интерфейс Bot API**:
  - `bot send-message` — отправка тестового сообщения админам.
  - `bot stats` — информация о бот-пользователях.

Пример:
```bash
python3 sdb.py bot send-message --text "Тест"
```

---

## `monitor`

- **Мониторинг/аналитика**:
  - `monitor metrics` — экспорт метрик, подключается к `MetricsCollector`.
  - `monitor check` — запуск проверки HealthCheck (внутри `HealthChecker`).

Пример:
```bash
python3 sdb.py monitor check
```

---

## `utils`

- **Вспомогательные команды**:
  - `utils dump-config` — экспортирует текущий config в файл.
  - `utils clean-cache`.
  - `utils gen-key`.

Пример:
```bash
python3 sdb.py utils clean-cache
```

---

## `security`

- **Безопасность**:
  - `security keys list` — ключи подписи.
  - `security sign module <path>` — `CryptoManager.sign_module`.
  - `security verify` — проверяет подписи.
  - `security rotate` — ротация ключей.
  - `security rate-limit` — управление `RateLimiter`.

Пример:
```bash
python3 sdb.py security sign module Modules/new_feature
```

---

## `notifications`

- **Управление уведомлениями**:
  - `notifications list` — каналы/чаты.
  - `notifications add` / `remove`.

---

## `dev`

- **Инструменты разработчика**:
  - `dev scaffold` — генерация шаблонов (модулей/компонентов).
  - `dev lint` / `dev test`.

---

## `api`

- **Web API управление**:
  - `api status` — проверка адресов FastAPI.
  - `api regenerate` — регенерация токенов (`sdb_token`).

---

## `cache`

- **Кэш**:
  - `cache status` — memory/redis.
  - `cache flush`.

---

## `tasks`

- **Задачи**:
  - `tasks list` — все запланированные задачи.
  - `tasks run <name>` / `cancel`.

---

## `web`

- **Веб-панель**:
  - `web start` — запускает FastAPI сервер управления.
  - `web migrate` — обновляет статические файлы.
  - `web build` — сборка React UI.
  - `web test` — `make web-test`.

---

## Общие параметры

- `--help` / `-h` — справка.
- `--install-completion` / `--show-completion`.
- `-v` / `--verbose` — включает подробный лог (`SDB_VERBOSE`).
- `-d` / `--debug` — включает debug mode.
- Все подкоманды используют `SDB_CLI_MODE` (обход `BOT_TOKEN` при запуске) за исключением `run/start`.

---

## Как использовать справку

```bash
python3 sdb.py config --help
python3 sdb.py module create --help
```

Каждая подгруппа реализует `Typer`, поэтому `sdb <group> --help` выводит параметры и дополнительные подкоманды (например, `config storage set`).

Тест `tests/test_cli.py` автоматически прогоняет `--help` по каждому пути, чтобы обеспечить актуальность этой документации.


