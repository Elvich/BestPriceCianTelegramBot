# 🏠 BestPriceCianTelegramBot

Телеграм бот для отслеживания квартир ниже рынка Циан / Telegram bot for tracking apartments below the Cian market

### 1. Клонирование и установка
```bash
git clone https://github.com/Elvich/BestPriceCianTelegramBot.git
cd BestPriceCianTelegramBot
pip3 install -r requirements.txt
```

### 2. Настройка конфигурации
```bash
# Скопируйте шаблон конфигурации
cp config/.env.example config/.env

# Отредактируйте .env файл и укажите ваш BOT_TOKEN
nano config/.env
```

### 3. Проверка конфигурации
```bash
python3 check_config.py
```

### 4. Инициализация базы данных
```bash
# Создание таблиц единой БД (только при первом запуске)
python3 scripts/manage_db.py

# Или инициализация напрямую
python3 DB/init_db.py
```



## 🔐 Безопасность

Проект использует современный подход к управлению конфигурацией:
- ✅ Чувствительные данные в переменных окружения
- ✅ Файл `.env` исключен из Git
- ✅ Автоматическая валидация настроек
- ✅ Централизованное управление конфигурацией

Подробнее в [SECURITY.md](config/SECURITY.md)



## ⚙️ Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | *обязательно* |
| `DATABASE_URL` | URL базы данных | `sqlite+aiosqlite:///dp.sqlite` |
| `PARSER_DELAY` | Задержка между страницами (сек) | `3` |
| `PARSER_DEEP_DELAY` | Задержка при глубоком парсинге (сек) | `2` |
| `REQUEST_TIMEOUT` | Таймаут HTTP запросов (сек) | `30` |
| `MAX_RETRIES` | Максимум повторных попыток | `3` |

