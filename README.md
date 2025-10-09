# 🏠 BestPriceCianTelegramBot

Телеграм бот для отслеживания квартир ниже рынка Циан / Telegram bot for tracking apartments below the Cian market

## 🚀 Быстрый старт

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

### 4. Запуск
```bash
# Запуск бота
cd Bot && python3 Bot.py

# Запуск парсера
python3 Test.py
```

## 🔐 Безопасность

Проект использует современный подход к управлению конфигурацией:
- ✅ Чувствительные данные в переменных окружения
- ✅ Файл `.env` исключен из Git
- ✅ Автоматическая валидация настроек
- ✅ Централизованное управление конфигурацией

Подробнее в [SECURITY.md](config/SECURITY.md)

## 📁 Структура проекта

```
├── Bot/                    # Telegram бот
│   ├── Bot.py             # Точка входа
│   ├── Router.py          # Обработчики команд
│   ├── Kb.py              # Клавиатуры
│   └── States.py          # Состояния FSM
├── config/                 # Конфигурация и безопасность
│   ├── __init__.py        # Инициализация пакета
│   ├── Config.py          # Управление конфигурацией
│   ├── .env               # Переменные окружения (НЕ в Git)
│   ├── .env.example       # Шаблон конфигурации
│   ├── SECURITY.md        # Руководство по безопасности
│   └── check_config.py    # Диагностика настроек
├── DB/                     # База данных
│   ├── Models.py          # SQLAlchemy модели
│   └── Request.py         # Запросы к БД
├── CSV_Tools/              # Инструменты для CSV
│   ├── csv_analyzer.py    # Анализ результатов
│   └── CSV_README.md      # Документация
├── Parser.py               # Парсер Cian.ru
├── FileSaver.py           # Сохранение в CSV
└── .env.example           # → config/.env.example (ссылка)
```

## ⚙️ Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | *обязательно* |
| `DATABASE_URL` | URL базы данных | `sqlite+aiosqlite:///dp.sqlite` |
| `PARSER_DELAY` | Задержка между страницами (сек) | `3` |
| `PARSER_DEEP_DELAY` | Задержка при глубоком парсинге (сек) | `2` |
| `REQUEST_TIMEOUT` | Таймаут HTTP запросов (сек) | `30` |
| `MAX_RETRIES` | Максимум повторных попыток | `3` |
