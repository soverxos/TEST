# 🔐 КОМАНДЫ СИСТЕМЫ БЕЗОПАСНОСТИ SDB

Полное руководство по всем командам системы цифровых подписей и безопасности модулей.

---

## 📋 **СОДЕРЖАНИЕ**

1. [Управление ключами](#🔑-управление-ключами)
2. [Подписание модулей](#✍️-подписание-модулей)
3. [Управление безопасностью](#🛡️-управление-безопасностью)
4. [Сканирование и анализ](#🔍-сканирование-и-анализ)
5. [Настройки безопасности](#⚙️-настройки-безопасности)
6. [Мониторинг и отчеты](#📊-мониторинг-и-отчеты)
7. [Обслуживание системы](#🔄-обслуживание-системы)
8. [Справка и диагностика](#❓-справка-и-диагностика)
9. [Быстрые команды](#🚀-быстрые-команды)
10. [Примеры использования](#💡-примеры-использования)

---

## 🔑 **УПРАВЛЕНИЕ КЛЮЧАМИ**

### **Генерация ключей**

Создание новой пары ключей для подписания модулей.

```bash
# Базовая команда
python3 cli/security.py keys-generate <key_id> [--key-size 2048]

# Примеры использования
python3 cli/security.py keys-generate my_developer_key
python3 cli/security.py keys-generate alex_weather_dev --key-size 4096
python3 cli/security.py keys-generate company_signing_key --key-size 2048
python3 cli/security.py keys-generate team_lead_key --key-size 3072
```

**Параметры:**
- `key_id` - Уникальный идентификатор ключа
- `--key-size` - Размер ключа в битах (2048, 3072, 4096)

**Описание:**
Создает пару RSA ключей (приватный и публичный) для подписания модулей. Приватный ключ зашифровывается мастер-паролем и сохраняется локально. Публичный ключ можно экспортировать для передачи администраторам.

---

### **Просмотр ключей**

Просмотр списка всех доступных ключей и их деталей.

```bash
# Показать все ключи
python3 cli/security.py keys-list

# Показать детали конкретного ключа
python3 cli/security.py keys-show <key_id>

# Примеры
python3 cli/security.py keys-show my_developer_key
python3 cli/security.py keys-show alex_weather_dev
```

**Описание:**
- `keys-list` - Показывает список всех доступных ключей с основной информацией
- `keys-show` - Показывает детальную информацию о конкретном ключе

---

### **Экспорт ключей**

Экспорт публичного ключа для передачи администраторам.

```bash
# Экспорт публичного ключа
python3 cli/security.py keys-export <key_id> --output-file <filename>

# Примеры
python3 cli/security.py keys-export my_developer_key --output-file my_key.pem
python3 cli/security.py keys-export alex_weather_dev --output-file alex_public_key.pem
python3 cli/security.py keys-export company_signing_key --output-file company_key.pem
```

**Параметры:**
- `key_id` - Идентификатор ключа для экспорта
- `--output-file` - Имя файла для сохранения публичного ключа

**Описание:**
Экспортирует публичный ключ в формате PEM для передачи администраторам системы. Файл содержит только публичную часть ключа, которая безопасна для распространения.

---

### **Импорт ключей**

Импорт доверенного публичного ключа от разработчика.

```bash
# Импорт доверенного публичного ключа
python3 cli/security.py keys-import <trusted_id> --public-key-file <filename>

# Примеры
python3 cli/security.py keys-import trusted_alex --public-key-file alex_key.pem
python3 cli/security.py keys-import company_key --public-key-file company.pem
python3 cli/security.py keys-import trusted_dev_team --public-key-file dev_team_key.pem
```

**Параметры:**
- `trusted_id` - Идентификатор для доверенного ключа
- `--public-key-file` - Путь к файлу с публичным ключом

**Описание:**
Импортирует публичный ключ разработчика в список доверенных ключей. После импорта модули, подписанные этим ключом, будут считаться безопасными.

---

### **Удаление ключей**

Удаление ключей из системы.

```bash
# Удалить ключ
python3 cli/security.py keys-delete <key_id>

# Примеры
python3 cli/security.py keys-delete old_developer_key
python3 cli/security.py keys-delete compromised_key
python3 cli/security.py keys-delete expired_key
```

**Описание:**
Удаляет ключ из системы. Используйте с осторожностью - удаление ключа сделает невозможной проверку подписей, созданных этим ключом.

---

## ✍️ **ПОДПИСАНИЕ МОДУЛЕЙ**

### **Подписание модулей**

Создание цифровой подписи для модуля.

```bash
# Подписать модуль
python3 cli/security.py sign-module <module_path> <key_id>

# Примеры
python3 cli/security.py sign-module modules/weather.py my_developer_key
python3 cli/security.py sign-module modules/calculator.py alex_weather_dev
python3 cli/security.py sign-module modules/admin_tools.py company_signing_key
python3 cli/security.py sign-module modules/payment.py team_lead_key
```

**Параметры:**
- `module_path` - Путь к файлу модуля
- `key_id` - Идентификатор ключа для подписания

**Описание:**
Создает цифровую подпись модуля с использованием указанного приватного ключа. Подпись сохраняется в файл с расширением `.sig` рядом с модулем.

---

### **Проверка подписей**

Проверка цифровой подписи модуля.

```bash
# Проверить подпись модуля
python3 cli/security.py modules-scan <module_path>

# Примеры
python3 cli/security.py modules-scan modules/weather.py
python3 cli/security.py modules-scan modules/calculator.py
python3 cli/security.py modules-scan modules/admin_tools.py
```

**Описание:**
Проверяет цифровую подпись модуля и выводит результат проверки. Показывает, является ли подпись действительной и доверенной.

---

## 🛡️ **УПРАВЛЕНИЕ БЕЗОПАСНОСТЬЮ**

### **Статус системы безопасности**

Просмотр общего статуса безопасности системы.

```bash
# Показать общий статус
python3 cli/security.py modules-status

# Показать детальный статус
python3 cli/security.py modules-status --detailed

# Показать статус конкретного модуля
python3 cli/security.py modules-status --module <module_name>
```

**Описание:**
Показывает общий статус безопасности системы, включая количество подписанных модулей, доверенных ключей и обнаруженных угроз.

---

### **Управление доверенными ключами**

Управление списком доверенных ключей.

```bash
# Показать список доверенных ключей
python3 cli/security.py trusted-list

# Добавить ключ в доверенные
python3 cli/security.py trusted-add <key_id>

# Удалить ключ из доверенных
python3 cli/security.py trusted-remove <key_id>

# Примеры
python3 cli/security.py trusted-add my_developer_key
python3 cli/security.py trusted-remove compromised_key
```

**Описание:**
Управляет списком доверенных ключей. Только модули, подписанные доверенными ключами, будут загружаться в систему.

---

### **Аудит безопасности**

Просмотр логов аудита и обнаружение аномалий.

```bash
# Показать логи аудита
python3 cli/security.py audit-logs [--hours 24]

# Показать аномалии
python3 cli/security.py modules-anomalies [--hours 24]

# Показать репутацию модулей
python3 cli/security.py modules-reputation

# Примеры
python3 cli/security.py audit-logs --hours 48
python3 cli/security.py modules-anomalies --hours 168
```

**Параметры:**
- `--hours` - Количество часов для анализа (по умолчанию 24)

**Описание:**
- `audit-logs` - Показывает логи всех операций безопасности
- `modules-anomalies` - Обнаруживает аномальное поведение модулей
- `modules-reputation` - Показывает репутацию модулей и разработчиков

---

## 🔍 **СКАНИРОВАНИЕ И АНАЛИЗ**

### **Сканирование кода**

Сканирование модулей на наличие угроз и подозрительного кода.

```bash
# Сканировать модуль на угрозы
python3 cli/security.py code-scan <module_path>

# Сканировать все модули
python3 cli/security.py code-scan-all

# Сканировать с детальным отчетом
python3 cli/security.py code-scan <module_path> --detailed

# Примеры
python3 cli/security.py code-scan modules/weather.py --detailed
python3 cli/security.py code-scan-all
```

**Описание:**
Сканирует код модулей на наличие потенциальных угроз, подозрительных паттернов и вредоносного кода.

---

### **Анализ репутации**

Управление репутацией модулей и разработчиков.

```bash
# Показать репутацию модуля
python3 cli/security.py reputation-show <module_id>

# Показать репутацию разработчика
python3 cli/security.py reputation-developer <developer_id>

# Обновить репутацию
python3 cli/security.py reputation-update <module_id> <score>

# Примеры
python3 cli/security.py reputation-show weather_module
python3 cli/security.py reputation-developer alex_dev
python3 cli/security.py reputation-update weather_module 85
```

**Описание:**
Управляет системой репутации модулей и разработчиков. Репутация влияет на уровень доверия к модулям.

---

## ⚙️ **НАСТРОЙКИ БЕЗОПАСНОСТИ**

### **Уровни безопасности**

Управление уровнями безопасности системы.

```bash
# Показать текущий уровень безопасности
python3 cli/security.py security-level

# Установить уровень безопасности
python3 cli/security.py security-level-set <level>

# Доступные уровни: LOW, MODERATE, HIGH, STRICT
python3 cli/security.py security-level-set HIGH
python3 cli/security.py security-level-set STRICT
python3 cli/security.py security-level-set MODERATE
```

**Описание:**
Управляет общим уровнем безопасности системы. Более высокие уровни требуют более строгих проверок.

---

### **Политики безопасности**

Настройка политик безопасности системы.

```bash
# Показать политики безопасности
python3 cli/security.py policies-show

# Установить политику
python3 cli/security.py policies-set <policy> <value>

# Примеры
python3 cli/security.py policies-set require_signatures true
python3 cli/security.py policies-set min_reputation_score 60
python3 cli/security.py policies-set max_file_size 10485760
python3 cli/security.py policies-set allow_unsigned_modules false
```

**Описание:**
Настраивает политики безопасности, такие как обязательность подписей, минимальная репутация и ограничения размера файлов.

---

## 📊 **МОНИТОРИНГ И ОТЧЕТЫ**

### **Отчеты безопасности**

Генерация отчетов о состоянии безопасности.

```bash
# Генерировать отчет безопасности
python3 cli/security.py report-generate [--format json|csv|txt]

# Показать статистику
python3 cli/security.py stats-show

# Показать статистику за период
python3 cli/security.py stats-show --period 7d

# Примеры
python3 cli/security.py report-generate --format json
python3 cli/security.py stats-show --period 30d
```

**Описание:**
Генерирует отчеты о состоянии безопасности системы и показывает статистику использования.

---

### **Мониторинг в реальном времени**

Мониторинг событий безопасности в реальном времени.

```bash
# Мониторинг событий безопасности
python3 cli/security.py monitor-events

# Мониторинг с фильтром
python3 cli/security.py monitor-events --filter <event_type>

# Примеры
python3 cli/security.py monitor-events --filter signature_verification
python3 cli/security.py monitor-events --filter module_load
```

**Описание:**
Отображает события безопасности в реальном времени с возможностью фильтрации по типу события.

---

## 🔄 **ОБСЛУЖИВАНИЕ СИСТЕМЫ**

### **Очистка и обслуживание**

Очистка старых данных и обслуживание системы.

```bash
# Очистить старые логи
python3 cli/security.py cleanup-logs [--days 30]

# Очистить кэш
python3 cli/security.py cleanup-cache

# Проверить целостность системы
python3 cli/security.py system-check

# Примеры
python3 cli/security.py cleanup-logs --days 7
python3 cli/security.py cleanup-cache
```

**Описание:**
Выполняет операции по очистке и обслуживанию системы безопасности.

---

### **Резервное копирование**

Создание и восстановление резервных копий ключей.

```bash
# Создать резервную копию ключей
python3 cli/security.py backup-keys --output-file keys_backup.tar.gz

# Восстановить ключи из резервной копии
python3 cli/security.py restore-keys --backup-file keys_backup.tar.gz

# Примеры
python3 cli/security.py backup-keys --output-file security_backup_$(date +%Y%m%d).tar.gz
python3 cli/security.py restore-keys --backup-file security_backup_20241208.tar.gz
```

**Описание:**
Создает резервные копии ключей и восстанавливает их при необходимости.

---

## ❓ **СПРАВКА И ДИАГНОСТИКА**

### **Справка**

Получение справки по командам.

```bash
# Показать справку по команде
python3 cli/security.py --help

# Показать справку по подкоманде
python3 cli/security.py keys-generate --help
python3 cli/security.py sign-module --help
python3 cli/security.py modules-status --help
```

**Описание:**
Показывает справку по использованию команд системы безопасности.

---

### **Диагностика**

Проверка состояния системы и конфигурации.

```bash
# Проверить конфигурацию
python3 cli/security.py config-check

# Проверить зависимости
python3 cli/security.py deps-check

# Проверить права доступа
python3 cli/security.py permissions-check

# Проверить целостность файлов
python3 cli/security.py integrity-check
```

**Описание:**
Выполняет диагностику системы безопасности и проверяет корректность конфигурации.

---

## 🚀 **БЫСТРЫЕ КОМАНДЫ**

### **Для разработчика модулей**

```bash
# 1. Создать ключи (делается один раз)
python3 cli/security.py keys-generate my_dev_key

# 2. Подписать модуль
python3 cli/security.py sign-module modules/my_module.py my_dev_key

# 3. Экспортировать публичный ключ
python3 cli/security.py keys-export my_dev_key --output-file my_key.pem
```

### **Для администратора системы**

```bash
# 1. Импортировать доверенный ключ (один раз для каждого разработчика)
python3 cli/security.py keys-import trusted_dev --public-key-file my_key.pem

# 2. Проверить статус системы
python3 cli/security.py modules-status

# 3. Просмотреть логи аудита
python3 cli/security.py audit-logs --hours 24
```

### **Для мониторинга безопасности**

```bash
# 1. Проверить все модули
python3 cli/security.py code-scan-all

# 2. Показать аномалии
python3 cli/security.py modules-anomalies --hours 168

# 3. Сгенерировать отчет
python3 cli/security.py report-generate --format json
```

---

## 💡 **ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ**

### **Полный цикл: Разработчик → Администратор**

#### **Шаг 1: Разработчик создает и подписывает модуль**

```bash
# Создание ключей
python3 cli/security.py keys-generate alex_weather_dev --key-size 2048

# Создание модуля
echo 'def get_weather(): return "Sunny, +25°C"' > modules/weather.py

# Подписание модуля
python3 cli/security.py sign-module modules/weather.py alex_weather_dev

# Экспорт публичного ключа
python3 cli/security.py keys-export alex_weather_dev --output-file alex_weather_key.pem
```

#### **Шаг 2: Администратор импортирует ключ и загружает модуль**

```bash
# Импорт доверенного ключа
python3 cli/security.py keys-import alex_weather_trusted --public-key-file alex_weather_key.pem

# Проверка статуса
python3 cli/security.py modules-status

# Копирование модуля в систему
cp weather.py modules/
cp weather.sig modules/
```

#### **Шаг 3: Автоматическая проверка системой**

```bash
# Проверка подписи
python3 cli/security.py modules-scan modules/weather.py

# Просмотр логов
python3 cli/security.py audit-logs --hours 1
```

### **Корпоративное использование**

#### **Настройка корпоративной безопасности**

```bash
# Установка строгого уровня безопасности
python3 cli/security.py security-level-set STRICT

# Настройка политик
python3 cli/security.py policies-set require_signatures true
python3 cli/security.py policies-set min_reputation_score 70
python3 cli/security.py policies-set allow_unsigned_modules false

# Создание корпоративного ключа
python3 cli/security.py keys-generate company_signing_key --key-size 4096
```

#### **Мониторинг корпоративной безопасности**

```bash
# Ежедневная проверка
python3 cli/security.py modules-status --detailed
python3 cli/security.py modules-anomalies --hours 24

# Еженедельный отчет
python3 cli/security.py report-generate --format json
python3 cli/security.py stats-show --period 7d
```

### **Устранение проблем**

#### **Проблема: Модуль не загружается**

```bash
# Проверка подписи
python3 cli/security.py modules-scan modules/problematic_module.py

# Проверка доверенных ключей
python3 cli/security.py trusted-list

# Просмотр логов
python3 cli/security.py audit-logs --hours 1
```

#### **Проблема: Компрометированный ключ**

```bash
# Удаление компрометированного ключа
python3 cli/security.py keys-delete compromised_key

# Удаление из доверенных
python3 cli/security.py trusted-remove compromised_key

# Проверка системы
python3 cli/security.py system-check
```

---

## 📋 **ПОЛНЫЙ СПИСОК КОМАНД**

```bash
# Управление ключами
python3 cli/security.py keys-generate <key_id> [--key-size 2048]
python3 cli/security.py keys-list
python3 cli/security.py keys-show <key_id>
python3 cli/security.py keys-export <key_id> --output-file <filename>
python3 cli/security.py keys-import <trusted_id> --public-key-file <filename>
python3 cli/security.py keys-delete <key_id>

# Подписание модулей
python3 cli/security.py sign-module <module_path> <key_id>
python3 cli/security.py modules-scan <module_path>

# Управление безопасностью
python3 cli/security.py modules-status [--detailed]
python3 cli/security.py trusted-list
python3 cli/security.py trusted-add <key_id>
python3 cli/security.py trusted-remove <key_id>

# Аудит и мониторинг
python3 cli/security.py audit-logs [--hours 24]
python3 cli/security.py modules-anomalies [--hours 24]
python3 cli/security.py modules-reputation

# Сканирование кода
python3 cli/security.py code-scan <module_path> [--detailed]
python3 cli/security.py code-scan-all

# Настройки безопасности
python3 cli/security.py security-level
python3 cli/security.py security-level-set <level>
python3 cli/security.py policies-show
python3 cli/security.py policies-set <policy> <value>

# Отчеты и статистика
python3 cli/security.py report-generate [--format json|csv|txt]
python3 cli/security.py stats-show [--period 7d]
python3 cli/security.py monitor-events [--filter <event_type>]

# Обслуживание системы
python3 cli/security.py cleanup-logs [--days 30]
python3 cli/security.py cleanup-cache
python3 cli/security.py system-check
python3 cli/security.py backup-keys --output-file <filename>
python3 cli/security.py restore-keys --backup-file <filename>

# Справка и диагностика
python3 cli/security.py --help
python3 cli/security.py config-check
python3 cli/security.py deps-check
python3 cli/security.py permissions-check
python3 cli/security.py integrity-check
```

---

## 🎯 **САМЫЕ ВАЖНЫЕ КОМАНДЫ**

### **Для ежедневного использования:**

```bash
# Разработчик
python3 cli/security.py keys-generate my_key
python3 cli/security.py sign-module modules/my_module.py my_key
python3 cli/security.py keys-export my_key --output-file my_key.pem

# Администратор
python3 cli/security.py keys-import trusted_dev --public-key-file my_key.pem
python3 cli/security.py modules-status
python3 cli/security.py audit-logs
```

### **Для мониторинга:**

```bash
python3 cli/security.py modules-status --detailed
python3 cli/security.py modules-anomalies --hours 24
python3 cli/security.py code-scan-all
```

### **Для диагностики:**

```bash
python3 cli/security.py system-check
python3 cli/security.py config-check
python3 cli/security.py integrity-check
```

---

## ⚠️ **ВАЖНЫЕ ЗАМЕЧАНИЯ**

1. **Приватные ключи никогда не передаются** - только публичные ключи
2. **Регулярно обновляйте ключи** - каждые 2-3 года
3. **Делайте резервные копии ключей** - используйте `backup-keys`
4. **Мониторьте систему** - регулярно проверяйте `modules-status`
5. **Ведите аудит** - просматривайте `audit-logs`

---

## 📞 **ПОДДЕРЖКА**

При возникновении проблем:

1. Проверьте конфигурацию: `python3 cli/security.py config-check`
2. Проверьте целостность системы: `python3 cli/security.py system-check`
3. Просмотрите логи: `python3 cli/security.py audit-logs`
4. Обратитесь к справке: `python3 cli/security.py --help`

---

*Документ создан для системы безопасности SDB v0.1.0*
*Последнее обновление: 2024-12-08*
