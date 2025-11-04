# 🚀 SwiftDevBot QUICK USE

Ниже — самые частые команды CLI для быстрого старта и повседневной работы. Все команды вызываются через `./sdb ...` (или `python3 sdb.py ...`).

## Быстрый старт
- Установка и запуск (dev):
```bash
cd /root/Dev
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp env.example .env   # укажите BOT_TOKEN и настройки БД/кэша
./sdb start           # alias на run
```
- Помощь и список групп команд:
```bash
./sdb --help
```

## Управление процессом бота
- Запуск/остановка/перезапуск/статус:
```bash
./sdb run
./sdb stop
./sdb restart
./sdb status
```

## База данных (Alembic)
- Применить миграции / откат / статус / новая ревизия:
```bash
./sdb db upgrade head
./sdb db downgrade 1           # откат на 1 ревизию (или укажите id)
./sdb db status                # current + history
./sdb db revision -m "init"   # создать ревизию (с autogenerate)
```
- Прочее (с осторожностью):
```bash
./sdb db stamp head            # синхронизировать состояние без применения миграций
./sdb db init-core             # прямое создание таблиц ядра (обходит Alembic)
```

## Бэкапы (объединённые: файлы + БД + хеши)
- Создать / перечислить / восстановить / проверить / сравнить:
```bash
./sdb backup create --type=full              # весь проект (рекомендуется)
./sdb backup create --type=files            # только файлы
./sdb backup create --type=db --db-url=...  # только БД (PG/MySQL)
./sdb backup list -t all                    # список бэкапов
./sdb backup info <имя_или_путь>
./sdb backup verify <имя_или_путь>         # проверка целостности
./sdb backup restore <имя_или_путь> <dest> # восстановление
./sdb backup diff <имя_или_путь>           # сравнение с текущим состоянием
```
- Быстрая диагностика перед бэкапом:
```bash
./sdb backup check
```

## Модули (плагины)
- Создание, список, информация, включение/отключение:
```bash
./sdb module create my_plugin                      # демо-шаблон по умолчанию
./sdb module create my_plugin -t demo --enable     # демо + авто-включение
./sdb module create my_plugin -t universal         # полный универсальный шаблон
./sdb module list
./sdb module info my_plugin
./sdb module enable my_plugin
./sdb module disable my_plugin
```
- Установка/обновление/удаление:
```bash
./sdb module install my_plugin -s local     # или --source repo|url --url=...
./sdb module update my_plugin --force
./sdb module uninstall my_plugin --remove-data  # ОПАСНО: удалит таблицы при подтверждении
```
- Сбор зависимостей активных модулей:
```bash
./sdb module sync-deps -o modules_requirements.txt
```

## Безопасность и шифрование
- Аудит безопасности системы и интеграции:
```bash
./sdb security audit -f text                 # или json|html с -o report.html
./sdb security integrations system-info
./sdb security integrations test
```
- Ключи (JWT/API/шифрование) — генерация/ротация/удаление:
```bash
./sdb security keys list
./sdb security keys generate -t encryption -n data_key -l 32 -e 365
./sdb security keys rotate -n data_key -l 32 -e 365
./sdb security keys delete -n data_key
```
- Подписание и проверка модулей, статус защиты:
```bash
./sdb security keys-generate my_signer        # пара ключей для подписания модулей
./sdb security sign-module modules/x.py my_signer
./sdb security modules-scan modules/x.py
./sdb security modules-status
./sdb security modules-anomalies --hours 24
./sdb security modules-reputation            # или с --module
```
- SSL/Firewall (диагностика и базовые действия):
```bash
./sdb security ssl check -d example.com
./sdb security firewall status
./sdb security firewall add-rule --port 8080 --protocol tcp --direction in
```

## Система и обновления
- Общая информация и статус:
```bash
./sdb system info
./sdb system status
```
- Обновление системы с резервной копией и (опционально) перезапуском:
```bash
./sdb system update --branch main --backup --restart
```
- Откат к резервной копии (только файлы проекта):
```bash
./sdb system rollback <backup_name> -y
```

## Полезное
- Проверка конфигурации и окружения:
```bash
./sdb config --help
./sdb utils --help
```
- Мониторинг и уведомления (если подключены):
```bash
./sdb monitor --help
./sdb notifications --help
```

## Типичные сценарии
- Продакшн-обновление:
```bash
./sdb backup create --type=full
./sdb system update --branch main --backup --restart
```
- Создать и включить модуль:
```bash
./sdb module create my_plugin
./sdb module enable my_plugin
./sdb restart
```
- Быстрая проверка безопасности:
```bash
./sdb security audit -f html -o security_report.html
./sdb security modules-status
```

## Траблшутинг
- Бот не стартует: проверьте `BOT_TOKEN` в `.env`, `project_data/Config/core_settings.yaml`, миграции `./sdb db status`, логи в `project_data/Logs`.
- Redis FSM: установите пакет `redis`, поднимите сервер, включите `SDB_CACHE_TYPE="redis"`.
- Базы данных: для PostgreSQL/MySQL заполните `SDB_DB_PG_DSN`/`SDB_DB_MYSQL_DSN` и проверьте доступность.
- Права и безопасность: `.env` рекомендованы права `0600`, ключи храните в `security/keys/` (бэкапите!).
