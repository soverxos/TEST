# 🚀 БЫСТРАЯ СПРАВОЧНАЯ КАРТОЧКА: КОМАНДЫ БЕЗОПАСНОСТИ SDB

## 🔑 **ОСНОВНЫЕ КОМАНДЫ**

### **Разработчик модулей:**
```bash
# Создать ключи
python3 cli/security.py keys-generate my_key

# Подписать модуль
python3 cli/security.py sign-module modules/my_module.py my_key

# Экспортировать публичный ключ
python3 cli/security.py keys-export my_key --output-file my_key.pem
```

### **Администратор системы:**
```bash
# Импортировать доверенный ключ
python3 cli/security.py keys-import trusted_dev --public-key-file my_key.pem

# Проверить статус системы
python3 cli/security.py modules-status

# Просмотреть логи аудита
python3 cli/security.py audit-logs --hours 24
```

---

## 📋 **ПОЛНЫЙ СПИСОК КОМАНД**

### **🔑 Управление ключами**
```bash
python3 cli/security.py keys-generate <key_id> [--key-size 2048]
python3 cli/security.py keys-list
python3 cli/security.py keys-show <key_id>
python3 cli/security.py keys-export <key_id> --output-file <filename>
python3 cli/security.py keys-import <trusted_id> --public-key-file <filename>
python3 cli/security.py keys-delete <key_id>
```

### **✍️ Подписание модулей**
```bash
python3 cli/security.py sign-module <module_path> <key_id>
python3 cli/security.py modules-scan <module_path>
```

### **🛡️ Управление безопасностью**
```bash
python3 cli/security.py modules-status [--detailed]
python3 cli/security.py trusted-list
python3 cli/security.py trusted-add <key_id>
python3 cli/security.py trusted-remove <key_id>
```

### **🔍 Аудит и мониторинг**
```bash
python3 cli/security.py audit-logs [--hours 24]
python3 cli/security.py modules-anomalies [--hours 24]
python3 cli/security.py modules-reputation
```

### **🔍 Сканирование кода**
```bash
python3 cli/security.py code-scan <module_path> [--detailed]
python3 cli/security.py code-scan-all
```

### **⚙️ Настройки безопасности**
```bash
python3 cli/security.py security-level
python3 cli/security.py security-level-set <level>
python3 cli/security.py policies-show
python3 cli/security.py policies-set <policy> <value>
```

### **📊 Отчеты и статистика**
```bash
python3 cli/security.py report-generate [--format json|csv|txt]
python3 cli/security.py stats-show [--period 7d]
python3 cli/security.py monitor-events [--filter <event_type>]
```

### **🔄 Обслуживание системы**
```bash
python3 cli/security.py cleanup-logs [--days 30]
python3 cli/security.py cleanup-cache
python3 cli/security.py system-check
python3 cli/security.py backup-keys --output-file <filename>
python3 cli/security.py restore-keys --backup-file <filename>
```

### **❓ Справка и диагностика**
```bash
python3 cli/security.py --help
python3 cli/security.py config-check
python3 cli/security.py deps-check
python3 cli/security.py permissions-check
python3 cli/security.py integrity-check
```

---

## 🎯 **БЫСТРЫЙ СТАРТ**

### **1. Разработчик создает модуль:**
```bash
python3 cli/security.py keys-generate alex_dev
python3 cli/security.py sign-module modules/weather.py alex_dev
python3 cli/security.py keys-export alex_dev --output-file alex_key.pem
```

### **2. Администратор загружает модуль:**
```bash
python3 cli/security.py keys-import alex_trusted --public-key-file alex_key.pem
cp weather.py modules/
cp weather.sig modules/
```

### **3. Система автоматически проверяет:**
```bash
python3 cli/security.py modules-scan modules/weather.py
python3 cli/security.py modules-status
```

---

## ⚠️ **ВАЖНЫЕ ПРАВИЛА**

- 🔒 **ПРИВАТНЫЙ КЛЮЧ НИКОМУ НЕ ПЕРЕДАЕТСЯ!**
- 🔓 **ПУБЛИЧНЫЙ КЛЮЧ МОЖНО ПОКАЗЫВАТЬ ВСЕМ!**
- ✅ **ВСЕГДА подписывайте модули перед отправкой**
- ✅ **РЕГУЛЯРНО проверяйте статус системы**
- ✅ **ДЕЛАЙТЕ резервные копии ключей**

---

## 📞 **ПОМОЩЬ**

```bash
python3 cli/security.py --help
python3 cli/security.py <command> --help
```

---

*Краткая справочная карточка SDB Security v0.1.0*
