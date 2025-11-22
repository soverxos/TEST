# Platform Guide — `Docs/Platform_Guide.md`

## Table of Contents

1. [prepareEnvironment()](#prepareenvironment)
2. [configureSecrets()](#configuresecrets)
3. [manageDependencies()](#managedependencies)
4. [initializeDatabase()](#initializedatabase)
5. [runBotCore()](#runbotcore)
6. [controlCLI()](#controlcli)
7. [extendModules()](#extendmodules)
8. [workWithWebPanel()](#workwithwebpanel)
9. [securePlatform()](#secureplatform)
10. [monitorAndMetrics()](#monitorandmetrics)
11. [testingAndCI()](#testingandci)
12. [localizationAndUX()](#localizationandux)
13. [deployAndMaintain()](#deployandmaintain)

## `prepareEnvironment()`

**Purpose**: Set up the system so that SwiftDevBot can be developed, tested, and deployed without collisions or missing dependencies.

```text
Inputs:
  - Git repository: https://github.com/soverxos/SwiftDevBot-Project
  - Python 3.12+
  - Optional services: Postgres/MySQL/Redis
Outputs:
  - Virtual environment (.venv)
  - Installed dependencies from requirements.txt
  - Source tree ready for CLI and web runs
```

Steps:

1. Clone the repository and change directory:
   ```bash
   git clone https://github.com/soverxos/SwiftDevBot-Project.git
   cd SwiftDevBot-Project
   ```
2. Create a Python virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Optional extra tooling:
   ```bash
   make dev
   ```
   This includes `pytest`, `pytest-asyncio`, `pylint`, `black`, `isort`, `mypy`, `pytest-cov`.

## `configureSecrets()`

**Purpose**: Provide the runtime secrets required for the bot (BOT_TOKEN, database credentials, cache settings, super admins).

```text
Inputs:
  - env.example
Outputs:
  - .env populated
  - core_settings.yaml aligned with secrets
```

Steps:

1. Copy `env.example` to `.env`.
2. Fill variables:
   - `BOT_TOKEN` — from @BotFather.
   - `SDB_CORE_SUPER_ADMINS` — comma separated Telegram IDs.
   - Choose `SDB_DB_TYPE` (sqlite/postgresql/mysql) and supply DSN or path.
   - Optionally configure Redis with `SDB_CACHE_TYPE=redis`.
   - Security toggles: `SDB_SECURITY_LEVEL`, `SDB_SECURITY_SIGNATURE_REQUIRED`, `SDB_SECURITY_SANDBOX_ENABLED`.
3. Verify `.env` by running `python3 sdb.py config get` and `python3 sdb.py config show`.

## `manageDependencies()`

**Purpose**: Keep dependencies current and separated per environment.

Steps:

1. Regular installs:
   ```bash
   pip install -r requirements.txt
   ```
2. During development, run `make dev`.
3. For CI or Docker builds rely on `pip install -r requirements.txt && pip install pytest pytest-asyncio httpx`.
4. Lock versions by copying `.venv/lib/python.../pip-selfcheck`, or generate `requirements.txt` snapshots if dependencies change.

## `initializeDatabase()`

**Purpose**: Create and migrate the SQL schema for SwiftDevBot.

Steps:

1. Initialize the database files and directories (project_data/...).
2. Run migrations:
   ```bash
   python3 sdb.py db init
   python3 sdb.py db migrate
   python3 sdb.py db upgrade head
   ```
3. Check Alembic versions under `Systems/migration/versions`.
4. Use `python3 sdb.py db stamp` if you need to align with an existing DB.

## `runBotCore()`

**Purpose**: Start the actual Telegram bot in various modes.

Available commands:

- `python3 sdb.py run` — normal mode.
- `python3 sdb.py run -v` — verbose logging.
- `python3 sdb.py run -d` — debug mode.
- `python3 sdb.py status` — show PID / uptime / memory.
- `python3 sdb.py stop` / `restart` — control the running process.

Environment:
  - `SDB_CLI_MODE` automatically toggled when running via CLI.
  - Log output through Loguru (structured when verbose).

## `controlCLI()`

**Purpose**: Document the CLI surface for operations.

High-level layout:

- `sdb config ...`
- `sdb db ...`
- `sdb module ...`
- `sdb user ...`
- `sdb security ...`
- `sdb system ...`
- `sdb bot ...`
- `sdb monitor ...`
- `sdb notifications ...`
- `sdb cache ...`
- `sdb dev ...`
- `sdb api ...`
- `sdb tasks ...`
- `sdb web ...`
- Commands `run/start/stop/status/restart` registered directly.

Testing:

`tests/test_cli.py` walks through `cli_main_app.registered_groups` and runs `--help` for each path, ensuring no missing entry points.

## `extendModules()`

**Purpose**: Create custom modules and manage plugin lifecycle.

Steps:

1. Create template:
   ```bash
   python3 sdb.py module create my_module
   ```
   Options `--template demo|universal`, `--enable`, `--with-rbac`, `--with-db`.
2. Edit `Modules/my_module/manifest.yaml`:
   - Define name, display_name, version, permissions, dependencies.
3. Implement handlers, keyboards, callback data per module.
4. Register module by enabling it:
   ```bash
   python3 sdb.py module enable my_module
   ```
5. Reload when updating code (performs full bot restart):
   ```bash
   python3 sdb.py module reload my_module
   ```
   **Note:** This command performs a full process restart, not a hot reload, to avoid memory leaks with asyncio event loops.
6. `CryptoManager` signs modules ensuring integrity; new version auto-read from manifest.

## `workWithWebPanel()`

**Purpose**: Operate the FastAPI + React dashboard.

Steps:

1. API resides in `Systems/web/app.py`. Endpoints:
   - `GET /api/users`
   - `POST /api/users/{id}/block`
   - `GET /api/modules`
   - `POST /api/modules/{name}/toggle`
2. Frontend located in `Systems/web/src`.
   - `api.ts` functions wrap fetch with auth token.
   - `Users.tsx` and `Modules.tsx` call `loadUsers/loadModules` and show toast notifications.
3. Tests: `tests/test_web_app.py` (DummySession, ModuleLoader mock).
4. Run web dev server: `npm install && npm run dev`.
5. Use `make web-test` to verify API integration locally within `.venv`.

## `securePlatform()`

**Purpose**: Outline security features.

Components:

- `CryptoManager`: AES-GCM encryption for private keys, dynamic manifest version detection.
- `RateLimiter`: Sliding window per user, default limits, reset, stats, tests to ensure `check_rate_limit` respects dynamic defaults.
- `InputValidator`: sanitizes commands, messages, callback data.
- `AnomalyDetection`, `AuditLogger`, `ReputationSystem`.
- RBAC implemented via `Systems/core/rbac`.

Tips:

1. Keep trusted keys under `project_data/Security/crypto_keys`.
2. Update `Systems/locales/*.yaml` for new UI strings (`admin_texts`, `roles_texts`, `users_texts`).
3. Watch `rate_limiter` tests (`tests/test_rate_limiter.py`).

## `monitorAndMetrics()`

Features:

- `HealthChecker`, `HealthStatus`.
- Metrics collector exports Prometheus-friendly dicts.
- `/metrics` endpoint via FastAPI (Starlette).
- CLI `sdb monitor ...`.

Usage:

1. Check metrics via `http://localhost:8000/metrics`.
2. Health endpoints accessible via `/api/health` and `/api/health/detailed`.
3. `tests/test_health.py` exercises health scenarios (requires pytest-asyncio).

## `testingAndCI()`

Commands:

- `make test` → `pytest tests/ -v`.
- `make web-test` → runs FastAPI tests inside `.venv`.
- `make test-cov` → coverage reports.
- `pytest tests/test_cli.py` → ensures CLI surfaces.
- `pytest tests/test_web_app.py` includes FastAPI + DummySession / ModuleLoader mocks.

CI pipeline:

1. `.github/workflows/ci.yml`:
   - Creates `.venv`.
   - Installs `pytest`, `pytest-cov`, `httpx`, `pytest-asyncio`.
   - Runs `pytest tests/ -v`.
   - Runs `pytest tests/test_web_app.py -v`.
2. Always ensure `pytest-asyncio` present to allow async test execution.

## `localizationAndux()`

Content:

1. All user-facing strings handled by `Translator`.
2. `admin_texts`, `roles_texts`, `users_texts` dictionaries live in `Systems/locales/{ru,en,ua}.yaml`.
3. Avoid hardcoded Russian strings in handlers; use dictionary lookups.
4. Translate new keys whenever you add UI flows (e.g., `admin_sys_info_cache_type`).

## `deployAndMaintain()`

Steps:

1. Build Docker image:
   ```bash
   docker build -t swiftdevbot:latest .
   ```
2. Run via Docker Compose:
   ```bash
   docker-compose up -d
   docker-compose logs -f
   ```
3. Keep modules and configs under version control (exclude `.env`, keys).
4. Update `CHANGELOG.md` with tasks (use `[ ]`/`[x]`).
5. Use `make clean` regularly before packaging.

---
This guide provides structured, function-like entry points to operate, extend, and secure the SwiftDevBot platform. Update it as new subcommands, modules, or integrations arrive.

## `releaseChecklist()`

**Purpose**: Краткий набор действий перед пушем/релизом.

1. Убедиться, что `.env` и `project_data` актуальны, супер-админы корректны.
2. Запустить `make format-check` + `make lint` + `make type-check`.
3. Прогнать `make test` и `make web-test`, и убедиться, что CI проходит локально.
4. Обновить `CHANGELOG.md` (см. шаблон ниже) и `README` с новыми API/CLI.
5. Проверить, что `Docs/Platform_Guide.md` отражает новые команды/модули.
6. Накатить миграции (`python3 sdb.py db migrate`), затем `db upgrade`.
7. Зафиксировать изменения в git, в описаниях PR ссылаться на новые API/фичи.

## `envMatrix()`

**Purpose**: Пример файла `.env` и контрольные значения.

```env
BOT_TOKEN=123456:ABCDEF
SDB_CORE_SUPER_ADMINS="7847397229"

# Database (выберите одну секцию)
SDB_DB_TYPE="sqlite"
SDB_DB_SQLITE_PATH="project_data/Database_files/swiftdevbot.db"

SDB_CACHE_TYPE="memory"

SDB_CORE_LOG_LEVEL="INFO"
SDB_TELEGRAM_POLLING_TIMEOUT="30"

# Безопасность
SDB_SECURITY_LEVEL="moderate"
SDB_SECURITY_SIGNATURE_REQUIRED="true"
SDB_SECURITY_SANDBOX_ENABLED="true"

# Веб-панель (при активной)
SDB_WEB_HOST="127.0.0.1"
SDB_WEB_PORT="8000"
SDB_WEB_USE_SSL="false"
```

Дополнительно для PostgreSQL / MySQL замените блок `sqlite` на DSN:

```env
SDB_DB_TYPE="postgresql"
SDB_DB_POSTGRES_HOST="localhost"
SDB_DB_POSTGRES_PORT="5432"
SDB_DB_POSTGRES_DB="swiftdevbot"
SDB_DB_POSTGRES_USER="postgres"
SDB_DB_POSTGRES_PASSWORD="secret"
```

## `debugPlatform()`

**Purpose**: Шаги для диагностики проблем в проде/разработке.

1. Логи: `project_data/Logs/*.log`, `loguru` выводит `INFO/ERROR`.
2. Проверить `python3 sdb.py status` — если процесс не запущен, `run` создаёт PID.
3. Для ошибок в модуле: `/Modules/<module>/handlers.py` — включить `loguru.logger.opt(depth=1).debug(...)`.
4. Проверьте локализации в `Systems/locales/*.yaml` (fire `admin_texts` etc).
5. Веб — запустите `npm run dev` в `Systems/web`, а `FastAPI` через `python3 sdb.py web start`.
6. Тесты `pytest tests/test_health.py`, `tests/test_rate_limiter.py`, `tests/test_cli.py` выявляют проблему.
7. Используйте `make clean` перед новым билдом.

## `docsUpdate()`

**Purpose**: Поддерживать документацию синхронизированной.

1. Каждый новый API/CLI команда описывайте в `README.md` и `Docs/Platform_Guide.md`.
2. Добавляйте новый ключ локализации в `Systems/locales/{ru,en,ua}.yaml`.
3. Обновляйте `CHANGELOG.md` задачами/фичами и отмечайте `[x]`, когда сделано.
4. Заполняйте `Docs/Platform_Guide` примерами вызовов; добавляйте скриншоты/ссылки при необходимости.
5. Пересобирайте `Docs` и прогоняйте `make test` перед публикацией.

## `useCases()`

**Purpose**: Конкретные рабочие сценарии с командами и ответами бота.

### Сценарий: старт бота и проверка статуса

```bash
python3 sdb.py run --verbose
# Вывод:
# [INFO] Запуск SwiftDevBot ...
# [INFO] PID=12345
# [INFO] Загружено 4 модуля (sys_status, ai_chat, broadcast, custom)

python3 sdb.py status
# `[status] PID=12345 | uptime=1m23s | memory=180MB | modules=4`

python3 sdb.py stop
# `[stop] Процесс остановлен`

python3 sdb.py restart
# `[restart] Остановлено, затем заново запущено`
```

### Сценарий: настройка конфигурации

```bash
python3 sdb.py config init
# Вопросы: BOT_TOKEN, DB type, супер-админ.
python3 sdb.py config set core.log_level DEBUG
python3 sdb.py config storage set redis --redis-url redis://localhost:6379/0
python3 sdb.py config storage status
# `cache.type = redis, redis_url = redis://localhost:6379/0`
```

### Сценарий: управление пользователем

```bash
python3 sdb.py user list
# `ID  Username   Role    Blocked`
python3 sdb.py user block 123456
# `User 123456 заблокирован`
python3 sdb.py user unblock 123456
# `User 123456 снят с бана`
python3 sdb.py user role add 123456 admin
# `Роль admin назначена`
```

### Сценарий: работа с модулями

```bash
python3 sdb.py module list
# `ai_chat (enabled, loaded)`
python3 sdb.py module disable ai_chat
# `ai_chat отключен`
python3 sdb.py module enable ai_chat
# `ai_chat включен`
python3 sdb.py module reload ai_chat
# `ai_chat перезагружен` (полный рестарт процесса бота)
python3 sdb.py module create analytics --with-rbac --enable
# `Шаблон создан Modules/analytics/`
```

### Сценарий: блокировка пользователя из веб UI

1. Открыть веб панель и авторизоваться (токен `sdb_token` хранится в localStorage).
2. Перейти в секцию `Users`, нажать кнопку `Block`.
3. Компонент вызовет `POST /api/users/{id}/block` с телом `{"block": true}`.
4. Ответ `{"success": True, "is_blocked": true}` подтверждает действие, UI показывает `Blocked`.

### Сценарий: включение модуля через веб

1. Компонент `Modules` вызывает `GET /api/modules`, получает список.
2. Нажатие `Enable` вызывает `POST /api/modules/<name>/toggle` с `{"enable": true}`.
3. Ответ `{"success": true, "is_enabled": true}`.
4. `loadModules()` перезагружает таблицу, `toast.success` показывает уведомление.

### Сценарий: тестирование CLI и API

```bash
pytest tests/test_cli.py
# Автоматически перебираются все Typer-группы.
make web-test
# `pytest tests/test_web_app.py` внутри .venv
pytest tests/test_web_app.py --maxfail=1
```

### Сценарий: проверка здоровья

```bash
python3 sdb.py system health
# `Database: reachable`, `Cache: redis (available)`
curl http://localhost:8000/api/health
# `{"status":"ok","details":{...}}`
curl http://localhost:8000/api/health/detailed
# Полные сведения о БД/кэше/модулях
```

### Сценарий: аудит и безопасность

```bash
python3 sdb.py security keys list
# показывает список ключей
python3 sdb.py security sign module Modules/analytics
# Подпись создана и сохранена в audit log
python3 sdb.py security rate-limit reset --user 123456
# `Rate limit reset`
```

### Сценарий: мониторинг через FastAPI

```bash
python3 sdb.py monitor check
# `HealthChecker: all systems healthy`
curl http://localhost:8000/metrics
# Prometheus metrics (counters, gauges)
```

---

## `integrationExamples()`

**Purpose**: Комбинированные сценарии для командной работы над релизом.

### Сценарий: релиз новой функции

1. Обновить код модуля `Modules/new_feature`.
2. Подписать модуль:
   ```bash
   python3 sdb.py security sign module Modules/new_feature
   ```
3. Перезапустить модуль (выполняет полный рестарт бота):
   ```bash
   python3 sdb.py module reload new_feature
   # или напрямую:
   python3 sdb.py restart
   ```
4. Проверить API (`/api/modules`) и UI (`Modules` секция).
5. Запустить `pytest tests/test_web_app.py` + `pytest tests/test_cli.py`.
6. Обновить `CHANGELOG.md`, `Docs/Platform_Guide.md`, `Docs/CLI_Reference.md`.

### Сценарий: усиление безопасности

1. Обновить `.env`:
   ```env
   SDB_SECURITY_LEVEL="strict"
   SDB_SECURITY_SIGNATURE_REQUIRED="true"
   ```
2. Перегенерировать ключи через `python3 sdb.py security keys rotate`.
3. Протестировать `tests/test_rate_limiter.py`.
4. Обновить документацию и запускайте `make test`.

### Сценарий: восстановление после сбоя

1. `python3 sdb.py backup list` — найти последний snapshot.
2. `python3 sdb.py backup restore release-20251121`.
3. `make clean`, `python3 sdb.py db upgrade`.
4. `python3 sdb.py monitor check`.


