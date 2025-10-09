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

### 4. Инициализация базы данных
```bash
# Создание таблиц (только при первом запуске)
python3 DB/init_db.py
```

### 5. Запуск

#### 🚀 Быстрый запуск (рекомендуется)
```bash
# Запуск бота (с автоматической активацией виртуального окружения)
./start_bot.sh

# Запуск парсера
./run_parser.sh

# Поиск квартир (до 15 млн по умолчанию)
./search_apartments.sh
./search_apartments.sh 10000000  # до 10 млн
```

#### 🔧 Ручной запуск
```bash
# Активация виртуального окружения
source .venv/bin/activate

# Запуск бота
cd Bot && python Bot.py

# Запуск парсера с сохранением в БД
python test_final.py

# Управление базой данных
python manage_db.py stats
python manage_db.py search --max-price 10000000
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
│   ├── ApartmentService.py # Сервис работы с объявлениями
│   ├── init_db.py         # Инициализация БД
│   └── Request.py         # Запросы к БД (устарело)
├── Parser.py               # Парсер Cian.ru
├── FileSaver.py           # Сохранение в БД/CSV
└── manage_db.py           # CLI управления БД
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

## 🗄️ База данных

```bash
# Статистика
python3 manage_db.py stats

# Поиск объявлений
python3 manage_db.py search --max-price 10000000
python3 manage_db.py search --metro "Полежаевская" "Беговая"
python3 manage_db.py search --min-price 5000000 --max-price 15000000

# Список станций метро
python3 manage_db.py metro

# Недавно добавленные объявления
python3 manage_db.py recent --days 7
```

Подробная документация: [DB/README.md](DB/README.md)
